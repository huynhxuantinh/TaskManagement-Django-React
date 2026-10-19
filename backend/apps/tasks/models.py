from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.projects.models import Project


class TaskStatus(models.Model):
    class Code(models.TextChoices):
        TODO = "TODO", "Chưa thực hiện"
        IN_PROGRESS = "IN_PROGRESS", "Đang thực hiện"
        COMPLETED = "COMPLETED", "Đã hoàn thành"
        ON_HOLD = "ON_HOLD", "Tạm dừng"

    legacy_id = models.PositiveBigIntegerField(unique=True)
    code = models.CharField(max_length=20, choices=Code.choices, unique=True)
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name


class Task(models.Model):
    class Priority(models.IntegerChoices):
        LOW = 1, "Thấp"
        MEDIUM = 2, "Trung bình"
        HIGH = 3, "Cao"

    title = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks")
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
    )
    status = models.ForeignKey(TaskStatus, on_delete=models.PROTECT, related_name="tasks")
    priority = models.PositiveSmallIntegerField(choices=Priority.choices, default=Priority.MEDIUM)
    deadline = models.DateField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(priority__gte=1, priority__lte=3),
                name="task_priority_valid",
            )
        ]
        indexes = [
            models.Index(fields=["project", "status"], name="task_project_status_idx"),
            models.Index(fields=["assignee", "is_deleted"], name="task_assignee_active_idx"),
            models.Index(fields=["deadline"], name="task_deadline_idx"),
            models.Index(fields=["is_deleted", "created_at"], name="task_active_created_idx"),
        ]

    def __str__(self):
        return self.title
