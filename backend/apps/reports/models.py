from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.projects.models import Project


class ReportMessage(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="reports")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_reports",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_reports",
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["receiver", "is_read"], name="report_receiver_read_idx"),
            models.Index(fields=["project", "created_at"], name="report_project_created_idx"),
        ]
