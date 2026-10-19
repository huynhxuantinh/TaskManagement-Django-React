from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationType(models.TextChoices):
    GENERAL = "GENERAL", "Hệ thống"
    TASK_ASSIGNED = "TASK_ASSIGNED", "Giao việc"
    STATUS_CHANGED = "STATUS_CHANGED", "Thay đổi trạng thái"
    PROJECT_ADDED = "PROJECT_ADDED", "Thêm vào dự án"
    DEADLINE_APPROACHING = "DEADLINE_APPROACHING", "Sắp đến hạn"


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.CharField(max_length=255)
    type = models.CharField(max_length=30, choices=NotificationType.choices)
    is_priority = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(
                fields=["user", "is_read", "created_at"],
                name="notif_user_read_created_idx",
            )
        ]


class Preference(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    type = models.CharField(max_length=30, choices=NotificationType.choices)
    is_priority = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "type"], name="notification_preference_unique"
            )
        ]
