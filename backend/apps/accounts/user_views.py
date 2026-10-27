from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from apps.core.api import success

from .models import Role, User
from .permissions import has_role
from .serializers import UserResponseSerializer, UserSerializer
from .user_serializers import (
    AvatarUploadSerializer,
    PreferenceListResponseSerializer,
    PreferenceWriteSerializer,
    RoleUpdateSerializer,
    UserAdminCreateSerializer,
    UserAdminUpdateSerializer,
    UserListResponseSerializer,
    UserSelfUpdateSerializer,
)
from .user_services import (
    change_user_role,
    complete_preferences,
    deactivate_and_reassign_tasks,
    save_avatar,
    upsert_preferences,
)


@extend_schema_view(
    list=extend_schema(tags=["Users"], responses={200: UserListResponseSerializer}),
    create=extend_schema(
        tags=["Users"],
        request=UserAdminCreateSerializer,
        responses={201: UserResponseSerializer},
    ),
    retrieve=extend_schema(tags=["Users"], responses={200: UserResponseSerializer}),
    partial_update=extend_schema(tags=["Users"], responses={200: UserResponseSerializer}),
)
class UserViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["full_name", "email"]
    ordering_fields = ["full_name", "email", "created_at"]
    ordering = ["full_name", "id"]
    http_method_names = ["get", "patch", "put", "post", "head", "options"]

    def get_queryset(self):
        queryset = User.objects.select_related("role")
        if not self.request.user.is_authenticated:
            return queryset.none()
        if has_role(self.request.user, Role.Code.ADMIN):
            return self._apply_filters(queryset)
        return queryset.filter(pk=self.request.user.pk)

    def _apply_filters(self, queryset):
        role = self.request.query_params.get("role")
        if role in Role.Code.values:
            queryset = queryset.filter(role__code=role)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=is_active == "true")
        return queryset

    def list(self, request, *args, **kwargs):
        if not has_role(request.user, Role.Code.ADMIN):
            raise PermissionDenied("Chỉ quản trị viên được xem danh sách người dùng.")
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(UserSerializer(page, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        return success(UserSerializer(self.get_object()).data, "Lấy người dùng thành công.")

    def create(self, request, *args, **kwargs):
        if not has_role(request.user, Role.Code.ADMIN):
            raise PermissionDenied("Chỉ quản trị viên được tạo tài khoản.")
        serializer = UserAdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user = serializer.save()
        except IntegrityError as error:
            raise ValidationError("Tên đăng nhập hoặc email đã tồn tại.") from error
        user = User.objects.select_related("role").get(pk=user.pk)
        return success(UserSerializer(user).data, "Tạo tài khoản thành công.", 201)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer_class = (
            UserAdminUpdateSerializer
            if has_role(request.user, Role.Code.ADMIN)
            else UserSelfUpdateSerializer
        )
        serializer = serializer_class(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        replacement = serializer.validated_data.pop("reassign_to", None)
        requested_deactivation = (
            user.is_active and serializer.validated_data.get("is_active") is False
        )
        if requested_deactivation and user.pk == request.user.pk:
            raise ValidationError(
                {"is_active": "Quản trị viên không thể tự vô hiệu hóa tài khoản."}
            )
        if (
            has_role(request.user, Role.Code.ADMIN)
            and requested_deactivation
        ):
            deactivate_and_reassign_tasks(user, replacement, request.user)
        elif replacement is not None:
            raise ValidationError(
                {"reassign_to_id": "Chỉ dùng khi vô hiệu hóa tài khoản."}
            )
        serializer.save()
        user = User.objects.select_related("role").get(pk=user.pk)
        return success(UserSerializer(user).data, "Cập nhật người dùng thành công.")

    @extend_schema(
        tags=["Users"], request=RoleUpdateSerializer, responses={200: UserResponseSerializer}
    )
    def change_role(self, request, pk=None):
        if not has_role(request.user, Role.Code.ADMIN):
            raise PermissionDenied("Chỉ quản trị viên được đổi vai trò.")
        user = get_object_or_404(User.objects.select_related("role"), pk=pk)
        serializer = RoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        replacement = serializer.validated_data.get("reassign_to")
        if user.pk == request.user.pk and role.code != Role.Code.ADMIN:
            raise ValidationError(
                {"role": "Quản trị viên không thể tự hạ quyền."}
            )
        change_user_role(user, role, replacement)
        return success(UserSerializer(user).data, "Cập nhật vai trò thành công.")

    @extend_schema(
        tags=["Users"], request=AvatarUploadSerializer, responses={200: UserResponseSerializer}
    )
    def upload_avatar(self, request, pk=None):
        user = self.get_object()
        serializer = AvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        save_avatar(user, serializer.validated_data["file"])
        return success(UserSerializer(user).data, "Cập nhật ảnh đại diện thành công.")

    @extend_schema(
        tags=["Users"], methods=["GET"], responses={200: PreferenceListResponseSerializer}
    )
    @extend_schema(
        tags=["Users"], methods=["PUT"], request=PreferenceWriteSerializer(many=True),
        responses={200: PreferenceListResponseSerializer}
    )
    def preferences(self, request, pk=None):
        user = self.get_object()
        if request.method == "PUT":
            serializer = PreferenceWriteSerializer(data=request.data, many=True)
            serializer.is_valid(raise_exception=True)
            types = [item["type"] for item in serializer.validated_data]
            if len(types) != len(set(types)):
                raise ValidationError({"type": ["Mỗi loại thông báo chỉ xuất hiện một lần."]})
            upsert_preferences(user, serializer.validated_data)
        return success(complete_preferences(user), "Lấy tùy chọn thông báo thành công.")

