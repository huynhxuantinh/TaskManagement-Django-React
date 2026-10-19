from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class EmptySerializer(serializers.Serializer):
    pass


class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="role.code", read_only=True)
    avatar_url = serializers.CharField(source="avatar", read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "full_name",
            "email",
            "role",
            "avatar_url",
            "is_active",
            "created_at",
            "permissions",
        )

    def get_permissions(self, user) -> list[str]:
        return [user.role.code]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=100)
    full_name = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=100)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class DeactivateSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class LoginDataSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)


class AccessDataSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)


class UserResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = UserSerializer(read_only=True)


class LoginResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = LoginDataSerializer(read_only=True)


class AccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = AccessDataSerializer(read_only=True)


class EmptyResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = serializers.JSONField(read_only=True, allow_null=True)
