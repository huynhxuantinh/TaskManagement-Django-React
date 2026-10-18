from rest_framework import serializers

from apps.notifications.models import NotificationType, Preference

from .models import Role, User
from .serializers import UserSerializer


class UserSelfUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name",)


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name", "email", "is_active")

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

