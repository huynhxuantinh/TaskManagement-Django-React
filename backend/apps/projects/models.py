from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone


class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_projects",
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(start_date__isnull=True)
                    | Q(end_date__isnull=True)
                    | Q(end_date__gte=F("start_date"))
                ),
                name="project_dates_ordered",
            )
        ]
        indexes = [
            models.Index(fields=["creator", "is_deleted"], name="project_creator_active_idx"),
            models.Index(fields=["is_deleted", "created_at"], name="project_active_created_idx"),
        ]

    def __str__(self):
        return self.name


class ProjectMember(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="project_memberships",
    )
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"], name="project_member_unique"
            )
        ]
        indexes = [models.Index(fields=["user", "project"], name="member_user_project_idx")]

    def __str__(self):
        return f"{self.project_id}:{self.user_id}"
