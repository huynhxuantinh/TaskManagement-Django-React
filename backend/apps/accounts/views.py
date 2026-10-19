from django.conf import settings
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.middleware.csrf import get_token, rotate_token
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.api import enforce_csrf, failure, success

from .models import Role, User
from .serializers import (
    AccessResponseSerializer,
    ChangePasswordSerializer,
    DeactivateSerializer,
    EmptySerializer,
    EmptyResponseSerializer,
    LoginResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    UserResponseSerializer,
)
from .throttles import LoginRateThrottle, RefreshRateThrottle


def _set_refresh_cookie(response, token):
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        str(token),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite="Lax",
        path=settings.AUTH_REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response):
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite="Lax",
    )


def _blacklist_all(user):
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)


class RegisterView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(
        tags=["Auth"], request=RegisterSerializer, responses={201: UserResponseSerializer}
    )
    def post(self, request):
        if not settings.ALLOW_PUBLIC_REGISTRATION:
            return failure("Đăng ký công khai đã bị tắt.", status=403)
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            return failure("Email đã tồn tại.", {"email": ["Email đã tồn tại."]}, 409)
        try:
            with transaction.atomic():
                employee = Role.objects.get(code=Role.Code.EMPLOYEE)
                user = User.objects.create_user(
                    email=email,
                    full_name=serializer.validated_data["full_name"],
                    password=serializer.validated_data["password"],
                    role=employee,
                )
        except IntegrityError:
            return failure("Email đã tồn tại.", {"email": ["Email đã tồn tại."]}, 409)
        return success(UserSerializer(user).data, "Đăng ký thành công.", 201)


class LoginView(GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]
    serializer_class = LoginSerializer

    @extend_schema(
        tags=["Auth"], request=LoginSerializer, responses={200: LoginResponseSerializer}
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["email"].strip().lower()
        matched_user = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).only("email").first()
        user = authenticate(
            request=request,
            email=matched_user.email if matched_user else identifier,
            password=serializer.validated_data["password"],
        )
        if user is None:
            return failure("Tên đăng nhập hoặc mật khẩu không đúng.", status=401)
        refresh = RefreshToken.for_user(user)
        rotate_token(request._request)
        get_token(request._request)
        response = success(
            {"access": str(refresh.access_token), "user": UserSerializer(user).data},
            "Đăng nhập thành công.",
        )
        _set_refresh_cookie(response, refresh)
        return response


class RefreshView(GenericAPIView):
    permission_classes = [AllowAny]
    throttle_classes = [RefreshRateThrottle]
    serializer_class = EmptySerializer

    @extend_schema(
        tags=["Auth"],
        request=None,
        responses={200: AccessResponseSerializer},
        description="Rotate refresh cookie; requires X-CSRFToken.",
    )
    def post(self, request):
        enforce_csrf(request)
        encoded = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not encoded:
            raise AuthenticationFailed("Refresh token không hợp lệ.")
        try:
            old_token = RefreshToken(encoded)
            user = User.objects.get(pk=old_token["user_id"], is_active=True)
            old_token.blacklist()
            new_token = RefreshToken.for_user(user)
        except (TokenError, User.DoesNotExist, KeyError) as error:
            raise AuthenticationFailed("Refresh token không hợp lệ.") from error
        response = success(
            {"access": str(new_token.access_token)}, "Làm mới token thành công."
        )
        _set_refresh_cookie(response, new_token)
        return response


class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmptySerializer

    @extend_schema(
        tags=["Auth"],
        request=None,
        responses={200: EmptyResponseSerializer},
        description="Blacklist refresh cookie; requires X-CSRFToken.",
    )
    def post(self, request):
        enforce_csrf(request)
        encoded = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if encoded:
            try:
                RefreshToken(encoded).blacklist()
            except TokenError:
                pass
        response = success(message="Đăng xuất thành công.")
        _clear_refresh_cookie(response)
        return response


class MeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    @extend_schema(tags=["Auth"], responses={200: UserResponseSerializer})
    def get(self, request):
        return success(UserSerializer(request.user).data, "Lấy hồ sơ thành công.")


class ChangePasswordView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    @extend_schema(
        tags=["Auth"],
        request=ChangePasswordSerializer,
        responses={200: EmptyResponseSerializer},
    )
    def post(self, request):
        enforce_csrf(request)
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["current_password"]):
            return failure(
                "Mật khẩu hiện tại không đúng.",
                {"current_password": ["Mật khẩu hiện tại không đúng."]},
            )
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        _blacklist_all(request.user)
        response = success(message="Đổi mật khẩu thành công.")
        _clear_refresh_cookie(response)
        return response


class DeactivateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeactivateSerializer

    @extend_schema(
        tags=["Auth"],
        request=DeactivateSerializer,
        responses={200: EmptyResponseSerializer},
    )
    def post(self, request):
        enforce_csrf(request)
        serializer = DeactivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(serializer.validated_data["password"]):
            return failure(
                "Mật khẩu không đúng.", {"password": ["Mật khẩu không đúng."]}
            )
        request.user.is_active = False
        request.user.save(update_fields=["is_active"])
        _blacklist_all(request.user)
        response = success(message="Tài khoản đã được vô hiệu hóa.")
        _clear_refresh_cookie(response)
        return response
