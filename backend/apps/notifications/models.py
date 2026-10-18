from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationType(models.TextChoices):
    GENERAL = "GENERAL", "General"
    TASK_ASSIGNED = "TASK_ASSIGNED", "Task assigned"
    STATUS_CHANGED = "STATUS_CHANGED", "Status changed"
    PROJECT_ADDED = "PROJECT_ADDED", "Project added"
    DEADLINE_APPROACHING = "DEADLINE_APPROACHING", "Deadline approaching"


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
