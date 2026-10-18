from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import serializers

from apps.notifications.models import NotificationType, Preference


MAX_AVATAR_SIZE = 2 * 1024 * 1024
AVATAR_SIGNATURES = {
    "image/png": ("png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/jpeg": ("jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/gif": ("gif", lambda data: data.startswith((b"GIF87a", b"GIF89a"))),
    "image/webp": (
        "webp",
        lambda data: len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    ),
}


def save_avatar(user, uploaded_file):
    if uploaded_file.size > MAX_AVATAR_SIZE:
        raise serializers.ValidationError(
            {"file": ["Ảnh đại diện không được vượt quá 2 MB."]}
        )
    detected = AVATAR_SIGNATURES.get(uploaded_file.content_type)
    header = uploaded_file.read(16)
    uploaded_file.seek(0)
    if not detected or not detected[1](header):
        raise serializers.ValidationError(
            {"file": ["Chỉ chấp nhận ảnh PNG, JPEG, GIF hoặc WebP hợp lệ."]}
        )
    extension = detected[0]
    storage_name = default_storage.save(
        f"avatars/{uuid4().hex}.{extension}",
        ContentFile(uploaded_file.read()),
    )
    user.avatar = default_storage.url(storage_name)
    user.save(update_fields=["avatar"])
    return user


@transaction.atomic
def upsert_preferences(user, values):
    for item in values:
        Preference.objects.update_or_create(
            user=user,
            type=item["type"],
            defaults={"is_priority": item["is_priority"]},
        )


def complete_preferences(user):
    stored = {
        preference.type: preference.is_priority
        for preference in Preference.objects.filter(user=user)
    }
    return [
        {"type": notification_type, "is_priority": stored.get(notification_type, False)}
        for notification_type in NotificationType.values
    ]

