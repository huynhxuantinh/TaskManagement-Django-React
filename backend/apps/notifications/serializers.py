from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "message", "type", "is_priority", "is_read", "created_at")


class NotificationResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = NotificationSerializer(read_only=True)


class NotificationListDataSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)
    next = serializers.URLField(read_only=True, allow_null=True)
    previous = serializers.URLField(read_only=True, allow_null=True)
    results = NotificationSerializer(many=True, read_only=True)


class NotificationListResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = NotificationListDataSerializer(read_only=True)


class ReadAllDataSerializer(serializers.Serializer):
    updated_count = serializers.IntegerField(read_only=True)


class ReadAllResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)
    data = ReadAllDataSerializer(read_only=True)

