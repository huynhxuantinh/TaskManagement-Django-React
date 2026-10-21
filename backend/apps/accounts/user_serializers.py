from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.notifications.models import NotificationType, Preference

from .models import Role, User
from .serializers import UserSerializer


class UserSelfUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name",)


class UserAdminCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    email = serializers.EmailField(max_length=100)
    full_name = serializers.CharField(max_length=100)
    role = serializers.SlugRelatedField(
        slug_field="code", queryset=Role.objects.all()
    )
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_username(self, value):
        username = value.strip().lower()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("Tên đăng nhập đã tồn tại.")
        return username

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Email đã tồn tại.")
        return email

    def validate(self, attrs):
        candidate = User(
            username=attrs["username"],
            email=attrs["email"],
            full_name=attrs["full_name"],
            role=attrs["role"],
        )
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)}) from error
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    reassign_to_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        source="reassign_to",
        write_only=True,
        required=False,
    )

    class Meta:
        model = User
        fields = ("full_name", "email", "is_active", "reassign_to_id")

    def validate_email(self, value):
        email = value.strip().lower()
        queryset = User.objects.filter(email__iexact=email)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("Email đã tồn tại.")
        return email


class RoleUpdateSerializer(serializers.Serializer):
    role = serializers.SlugRelatedField(
        slug_field="code", queryset=Role.objects.all()
    )


class AvatarUploadSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)


class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        fields = ("type", "is_priority")


class PreferenceWriteSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=NotificationType.choices)
    is_priority = serializers.BooleanField()


class UserListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)
    results = UserSerializer(many=True, read_only=True)


class UserListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = UserListDataSerializer(read_only=True)


class PreferenceListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = PreferenceSerializer(many=True, read_only=True)

