from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification

from .models import Task, TaskAuditLog, TaskStatus
from .workflow import validate_transition


AUDITED_TASK_FIELDS = ("title", "description", "assignee", "priority", "deadline", "start_date", "estimated_hours", "progress", "parent")

def audit_value(field, value):
    if field == "assignee":
        if value is None:
            return None
        return {"id": value.id, "full_name": value.full_name}
    if field in {"deadline", "start_date"}:
        return value.isoformat() if value else None
    if field == "estimated_hours":
        return str(value) if value is not None else None
    if field == "parent":
        return {"id": value.id, "title": value.title} if value else None
    return value


@transaction.atomic
def send_deadline_notifications(reference_date=None):
    today = reference_date or timezone.localdate()
    tasks = (
        Task.objects.filter(
            is_deleted=False,
            project__is_deleted=False,
            assignee__isnull=False,
            deadline__isnull=False,
            deadline__lte=today + timedelta(days=1),
        )
        .exclude(status__code=TaskStatus.Code.COMPLETED)
        .select_related("assignee")
        .order_by("id")
    )
    processed = 0
    for task in tasks:
        if task.deadline < today:
            notification_type = NotificationType.DEADLINE_OVERDUE
            stage = "overdue"
            message = (
                f'Công việc "{task.title}" đã quá hạn từ ngày '
                f"{task.deadline:%d/%m/%Y}."
            )
        elif task.deadline == today:
            notification_type = NotificationType.DEADLINE_APPROACHING
            stage = "today"
            message = (
                f'Công việc "{task.title}" đến hạn hôm nay '
                f"({task.deadline:%d/%m/%Y})."
            )
        else:
            notification_type = NotificationType.DEADLINE_APPROACHING
            stage = "tomorrow"
            message = (
                f'Công việc "{task.title}" còn 1 ngày đến hạn '
                f"({task.deadline:%d/%m/%Y})."
            )
        create_notification(
            task.assignee,
            notification_type,
            message,
            default_priority=True,
            dedupe_key=(
                f"deadline:{task.id}:{task.assignee_id}:{task.deadline}:{stage}:"
                f"{today if stage == 'overdue' else task.deadline}"
            ),
        )
        processed += 1
    return processed


class TaskService:
    @staticmethod
    @transaction.atomic
    def create_task(validated_data, actor=None):
        data = dict(validated_data)
        data.setdefault(
            "status", TaskStatus.objects.get(code=TaskStatus.Code.TODO)
        )
        if data["status"].code == TaskStatus.Code.COMPLETED:
            data["completed_at"] = timezone.now()
        task = Task.objects.create(**data)
        TaskAuditLog.objects.create(
            task=task,
            actor=actor,
            action=TaskAuditLog.Action.CREATED,
            changes={
                "title": {"old": None, "new": task.title},
                "assignee": {
                    "old": None,
                    "new": audit_value("assignee", task.assignee),
                },
                "deadline": {
                    "old": None,
                    "new": audit_value("deadline", task.deadline),
                },
                "status": {"old": None, "new": task.status.code},
            },
        )
        if task.assignee:
            create_notification(
                task.assignee,
                NotificationType.TASK_ASSIGNED,
                f'Bạn được giao công việc "{task.title}".',
            )
        return task

    @staticmethod
    @transaction.atomic
    def update_task(task, validated_data, actor=None):
        task = (
            Task.objects.select_for_update(of=("self",))
            .select_related("project", "project__creator", "assignee", "status")
            .get(pk=task.pk)
        )
        old_assignee_id = task.assignee_id
        changes = {}
        for field, value in validated_data.items():
            old_value = getattr(task, field)
            if field in AUDITED_TASK_FIELDS and old_value != value:
                changes[field] = {
                    "old": audit_value(field, old_value),
                    "new": audit_value(field, value),
                }
            setattr(task, field, value)
        if not changes:
            return task
        task.save()
        TaskAuditLog.objects.create(
            task=task,
            actor=actor,
            action=TaskAuditLog.Action.UPDATED,
            changes=changes,
        )

        if task.assignee and task.assignee_id != old_assignee_id:
            create_notification(
                task.assignee,
                NotificationType.TASK_ASSIGNED,
                f'Bạn được giao công việc "{task.title}".',
            )
        return task

    @staticmethod
    @transaction.atomic
    def change_status(task, new_status, actor, note=""):
        task = (
            Task.objects.select_for_update(of=("self",))
            .select_related("project", "project__creator", "assignee", "status")
            .get(pk=task.pk)
        )
        was_completed = task.status.code == TaskStatus.Code.COMPLETED
        is_completed = new_status.code == TaskStatus.Code.COMPLETED
        if task.status_id == new_status.id:
            return task
        old_status = task.status.code
        note = validate_transition(task, new_status, actor, note)
        if is_completed and not was_completed:
            task.completed_at = timezone.now()
        elif not is_completed:
            task.completed_at = None
        task.status = new_status
        task.save(update_fields=["status", "completed_at", "updated_at"])
        TaskAuditLog.objects.create(
            task=task,
            actor=actor,
            action=TaskAuditLog.Action.STATUS_CHANGED,
            changes={
                "status": {"old": old_status, "new": new_status.code},
                **({"note": {"old": None, "new": note}} if note else {}),
            },
        )
        recipients = {task.project.creator_id, task.assignee_id}
        recipients.discard(None)
        recipients.discard(actor.id)
        for user_id in recipients:
            create_notification(
                task.project.creator if user_id == task.project.creator_id else task.assignee,
                NotificationType.STATUS_CHANGED,
                f'Công việc "{task.title}" đã chuyển sang trạng thái {new_status.name}.',
            )
        return task

    @staticmethod
    @transaction.atomic
    def delete_task(task, actor):
        task.is_deleted = True
        task.save(update_fields=["is_deleted", "updated_at"])
        TaskAuditLog.objects.create(
            task=task,
            actor=actor,
            action=TaskAuditLog.Action.DELETED,
            changes={"is_deleted": {"old": False, "new": True}},
        )
        return task

