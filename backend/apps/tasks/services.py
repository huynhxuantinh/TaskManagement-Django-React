from django.db import transaction

from apps.notifications.models import Notification, NotificationType, Preference

from .models import Task, TaskStatus


def create_notification(user, notification_type, message, default_priority=False):
    configured_priority = Preference.objects.filter(
        user=user, type=notification_type
    ).values_list("is_priority", flat=True).first()
    return Notification.objects.create(
        user=user,
        type=notification_type,
        message=message,
        is_priority=(
            default_priority
            if configured_priority is None
            else configured_priority
        ),
    )


class TaskService:
    @staticmethod
    @transaction.atomic
    def create_task(validated_data):
        data = dict(validated_data)
        data.setdefault(
            "status", TaskStatus.objects.get(code=TaskStatus.Code.TODO)
        )
        task = Task.objects.create(**data)
        if task.assignee:
            create_notification(
                task.assignee,
                NotificationType.TASK_ASSIGNED,
                f'Bạn được giao công việc "{task.title}".',
            )
            if task.deadline:
                create_notification(
                    task.assignee,
                    NotificationType.DEADLINE_APPROACHING,
                    f'Công việc "{task.title}" có hạn {task.deadline:%d/%m/%Y}.',
                    default_priority=True,
                )
        return task

    @staticmethod
    @transaction.atomic
    def update_task(task, validated_data):
        old_assignee_id = task.assignee_id
        old_deadline = task.deadline
        for field, value in validated_data.items():
            setattr(task, field, value)
        task.save()

        if task.assignee and task.assignee_id != old_assignee_id:
            create_notification(
                task.assignee,
                NotificationType.TASK_ASSIGNED,
                f'Bạn được giao công việc "{task.title}".',
            )
        if task.assignee and task.deadline and task.deadline != old_deadline:
            create_notification(
                task.assignee,
                NotificationType.DEADLINE_APPROACHING,
                f'Công việc "{task.title}" có hạn {task.deadline:%d/%m/%Y}.',
                default_priority=True,
            )
        return task

    @staticmethod
    @transaction.atomic
    def change_status(task, new_status, actor):
        task.status = new_status
        task.save(update_fields=["status"])
        recipients = {task.project.creator_id, task.assignee_id}
        recipients.discard(None)
        recipients.discard(actor.id)
        for user_id in recipients:
            create_notification(
                task.project.creator if user_id == task.project.creator_id else task.assignee,
                NotificationType.STATUS_CHANGED,
                f'Công việc "{task.title}" chuyển sang {new_status.name}.',
            )
        return task

