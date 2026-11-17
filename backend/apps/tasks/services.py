from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from apps.accounts.models import Role
from apps.notifications.models import NotificationType
from apps.notifications.services import create_notification
from apps.projects.models import Project, ProjectMember

from .models import Task, TaskAuditLog, TaskChecklistItem, TaskStatus
from .workflow import can_change_task_status, validate_transition


AUDITED_TASK_FIELDS = ("title", "description", "assignee", "priority", "deadline", "start_date", "estimated_hours", "progress", "parent")


class TaskUpdateConflict(APIException):
    status_code = 409
    default_detail = 'Công việc đã được người khác cập nhật. Vui lòng tải lại trước khi lưu.'

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


class ChecklistService:
    @staticmethod
    def locked_task(task_id, actor):
        from rest_framework.exceptions import NotFound, ValidationError

        try:
            task = Task.objects.select_for_update(of=("self",)).select_related("status", "project").get(pk=task_id)
        except Task.DoesNotExist as error:
            raise NotFound("Không tìm thấy công việc.") from error
        if task.is_deleted or task.project.is_deleted:
            raise NotFound("Không tìm thấy công việc.")
        if not can_change_task_status(task, actor):
            raise PermissionDenied('Bạn không có quyền cập nhật checklist công việc này.')
        if actor.role.code != Role.Code.ADMIN and not ProjectMember.objects.filter(project_id=task.project_id, user_id=actor.id).exists():
            raise PermissionDenied('Bạn không còn là thành viên dự án này.')
        if task.status.code == TaskStatus.Code.COMPLETED:
            raise ValidationError({"checklist": "Hãy mở lại công việc trước khi sửa checklist."})
        return task

    @staticmethod
    @transaction.atomic
    def create(task_id, values, actor):
        task = ChecklistService.locked_task(task_id, actor)
        totals = task.checklist_items.aggregate(count=Count("id"), max_position=Max("position"))
        if totals["count"] >= 100:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"checklist": "Mỗi công việc tối đa 100 mục checklist."})
        max_position = totals["max_position"]
        item = TaskChecklistItem.objects.create(
            task=task,
            position=(max_position + 1 if max_position is not None else 0),
            title=values["title"],
            is_completed=values.get("is_completed", False),
        )
        TaskAuditLog.objects.create(task=task, actor=actor, action=TaskAuditLog.Action.CHECKLIST_CREATED, changes={"item": {"id": item.id, "title": item.title}})
        return item

    @staticmethod
    @transaction.atomic
    def update(task_id, item_id, values, actor):
        task = ChecklistService.locked_task(task_id, actor)
        try:
            item = TaskChecklistItem.objects.get(task=task, pk=item_id)
        except TaskChecklistItem.DoesNotExist as error:
            from rest_framework.exceptions import NotFound
            raise NotFound("Không tìm thấy mục checklist.") from error
        old = {field: getattr(item, field) for field in ("title", "is_completed")}
        for field in old:
            if field in values:
                setattr(item, field, values[field])
        item.save()
        changes = {field: {"old": old[field], "new": getattr(item, field)} for field in old if old[field] != getattr(item, field)}
        if changes:
            changes["item"] = {"id": item.id, "title": item.title}
            TaskAuditLog.objects.create(task=task, actor=actor, action=TaskAuditLog.Action.CHECKLIST_UPDATED, changes=changes)
        return item

    @staticmethod
    @transaction.atomic
    def delete(task_id, item_id, actor):
        task = ChecklistService.locked_task(task_id, actor)
        try:
            item = TaskChecklistItem.objects.get(task=task, pk=item_id)
        except TaskChecklistItem.DoesNotExist as error:
            from rest_framework.exceptions import NotFound
            raise NotFound("Không tìm thấy mục checklist.") from error
        changes = {"item": {"id": item.id, "title": item.title}}
        item.delete()
        TaskAuditLog.objects.create(task=task, actor=actor, action=TaskAuditLog.Action.CHECKLIST_DELETED, changes=changes)

    @staticmethod
    @transaction.atomic
    def reorder(task_id, item_ids, actor):
        from rest_framework.exceptions import ValidationError

        task = ChecklistService.locked_task(task_id, actor)
        items = list(task.checklist_items.select_for_update(of=("self",)).order_by("position", "id"))
        old_ids = [item.id for item in items]
        if len(item_ids) != len(set(item_ids)) or set(item_ids) != set(old_ids):
            raise ValidationError({"item_ids": "Danh sách mục checklist không hợp lệ."})
        by_id = {item.id: item for item in items}
        ordered = [by_id[item_id] for item_id in item_ids]
        for position, item in enumerate(ordered):
            item.position = position
        TaskChecklistItem.objects.bulk_update(ordered, ["position"])
        TaskAuditLog.objects.create(
            task=task, actor=actor, action=TaskAuditLog.Action.CHECKLIST_REORDERED,
            changes={"order": {"old": old_ids, "new": item_ids}, 'order_titles': {str(item.id): item.title for item in items}},
        )
        return ordered


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
        .exclude(
            status__code__in=[
                TaskStatus.Code.COMPLETED,
                TaskStatus.Code.ON_HOLD,
            ]
        )
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
                f"deadline:{task.id}:{task.assignee_id}:{task.deadline}:{stage}"
            ),
        )
        processed += 1
    return processed


class TaskService:
    @staticmethod
    def lock_project(project_id):
        project = Project.objects.select_for_update(of=('self',), no_key=True).filter(pk=project_id, is_deleted=False).first()
        if project is None:
            raise NotFound('Không tìm thấy dự án.')
        return project

    @staticmethod
    def validate_project_deadline(project, deadline):
        if deadline and project.end_date and deadline > project.end_date:
            raise ValidationError({'deadline': ['Hạn hoàn thành không được sau ngày kết thúc dự án.']})

    @staticmethod
    def lock_parent(parent_id):
        return Task.objects.select_for_update(of=('self',)).select_related('status').filter(pk=parent_id).first()

    @staticmethod
    @transaction.atomic
    def update_assignee_progress(task_id, progress, expected_updated_at, actor):
        task = Task.objects.select_for_update(of=('self',)).select_related('status', 'project').filter(pk=task_id).first()
        if not task or task.is_deleted or task.project.is_deleted:
            raise NotFound('Không tìm thấy công việc.')
        if not actor.is_active or task.assignee_id != actor.id or not ProjectMember.objects.filter(project_id=task.project_id, user_id=actor.id).exists():
            raise PermissionDenied('Chỉ người được giao và còn là thành viên mới được cập nhật tiến độ.')
        if expected_updated_at != task.updated_at:
            raise TaskUpdateConflict()
        if task.status.code == TaskStatus.Code.COMPLETED:
            raise ValidationError({'progress': ['Hãy mở lại công việc trước khi cập nhật tiến độ.']})
        if task.checklist_items.exists() or task.subtasks.filter(is_deleted=False).exists():
            raise ValidationError({'progress': ['Tiến độ được tính tự động từ checklist hoặc công việc con.']})
        return TaskService.update_task(task, {'progress': progress, 'expected_updated_at': expected_updated_at}, actor)

    @staticmethod
    def lock_assignee_membership(project_id, assignee):
        if assignee is None:
            return
        if not ProjectMember.objects.select_for_update(of=('self',)).filter(
            project_id=project_id, user_id=assignee.id,
        ).exists():
            raise ValidationError({'assignee_id': ['Người được giao phải là thành viên dự án.']})

    @staticmethod
    @transaction.atomic
    def create_task(validated_data, actor=None):
        data = dict(validated_data)
        note = data.pop('note', '').strip()
        project = TaskService.lock_project(data['project'].pk)
        TaskService.validate_project_deadline(project, data.get('deadline'))
        data['project'] = project
        if data.get('parent'):
            parent = Task.objects.select_for_update(of=('self',)).select_related('status').filter(pk=data['parent'].pk).first()
            if not parent or parent.is_deleted or parent.project_id != data['project'].id or parent.parent_id:
                raise ValidationError({'parent': ['Công việc cha phải thuộc cùng dự án, chưa bị xóa và không phải công việc con.']})
            if parent.status.code == TaskStatus.Code.COMPLETED:
                raise ValidationError({'parent': ['Hãy mở lại công việc cha trước.']})
            data['parent'] = parent
        TaskService.lock_assignee_membership(data['project'].id, data.get('assignee'))
        data.setdefault(
            "status", TaskStatus.objects.get(code=TaskStatus.Code.TODO)
        )
        if data['status'].code == TaskStatus.Code.ON_HOLD and not note:
            raise ValidationError({'note': ['Vui lòng nhập lý do tạm dừng.']})
        if data["status"].code == TaskStatus.Code.COMPLETED:
            data["completed_at"] = timezone.now()
        task = Task.objects.create(**data)
        TaskAuditLog.objects.create(
            task=task,
            actor=actor,
            action=TaskAuditLog.Action.CREATED,
            changes={
                **{field: {'old': None, 'new': audit_value(field, getattr(task, field))} for field in AUDITED_TASK_FIELDS},
                "status": {"old": None, "new": task.status.code},
                **({'note': {'old': None, 'new': note}} if note else {}),
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
        validated_data = dict(validated_data)
        expected = validated_data.pop('expected_updated_at', None)
        parent = validated_data.get('parent')
        if 'parent' in validated_data or 'deadline' in validated_data:
            project = TaskService.lock_project(task.project_id)
            if 'deadline' in validated_data:
                TaskService.validate_project_deadline(project, validated_data['deadline'])
        if 'parent' in validated_data:
            if parent is not None:
                parent = TaskService.lock_parent(parent.pk)
        task = (
            Task.objects.select_for_update(of=("self",))
            .select_related("project", "project__creator", "assignee", "status")
            .get(pk=task.pk)
        )
        if task.is_deleted or task.project.is_deleted:
            raise NotFound('Không tìm thấy công việc.')
        if expected is None or expected != task.updated_at:
            raise TaskUpdateConflict()
        if 'progress' in validated_data and (
            task.checklist_items.exists() or task.subtasks.filter(is_deleted=False).exists()
        ):
            raise ValidationError({'progress': ['Tiến độ được tính tự động từ checklist hoặc công việc con.']})
        if 'parent' in validated_data and validated_data['parent'] is not None:
            if not parent or parent.is_deleted or parent.project_id != task.project_id or parent.parent_id or parent.pk == task.pk:
                raise ValidationError({'parent': ['Công việc cha phải thuộc cùng dự án, chưa bị xóa và không phải công việc con.']})
            if parent.status.code == TaskStatus.Code.COMPLETED:
                raise ValidationError({'parent': ['Hãy mở lại công việc cha trước.']})
            if task.subtasks.filter(is_deleted=False).exists():
                raise ValidationError({'parent': ['Công việc đang có công việc con không thể trở thành công việc con.']})
            validated_data['parent'] = parent
        if 'assignee' in validated_data:
            TaskService.lock_assignee_membership(task.project_id, validated_data['assignee'])
        old_assignee_id = task.assignee_id
        old_assignee = task.assignee
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

        if old_assignee and task.assignee_id != old_assignee_id:
            is_member = ProjectMember.objects.filter(project_id=task.project_id, user_id=old_assignee_id).exists()
            message = (
                f'Bạn không còn được phân công công việc "{task.title}".'
                if is_member else 'Một công việc trước đây được giao cho bạn đã thay đổi người phụ trách.'
            )
            create_notification(old_assignee, NotificationType.GENERAL, message)
        if task.assignee and task.assignee_id != old_assignee_id:
            create_notification(
                task.assignee,
                NotificationType.TASK_ASSIGNED,
                f'Bạn được giao công việc "{task.title}".',
            )
        elif task.assignee and task.assignee.is_active and (not actor or actor.pk != task.assignee_id):
            labels = {'title': 'tên', 'description': 'nội dung', 'deadline': 'hạn hoàn thành', 'priority': 'mức ưu tiên'}
            changed_fields = [label for field, label in labels.items() if field in changes]
            if changed_fields and ProjectMember.objects.filter(project_id=task.project_id, user_id=task.assignee_id).exists():
                create_notification(
                    task.assignee, NotificationType.GENERAL,
                    f'Công việc "{task.title}" đã thay đổi: {", ".join(changed_fields)}.',
                )
        return task

    @staticmethod
    @transaction.atomic
    def change_status(task, new_status, actor, note="", confirm_incomplete_checklist=False, expected_status=None):
        expected_parent_id = task.parent_id
        if expected_parent_id is not None:
            Task.objects.select_for_update(of=('self',)).filter(pk=expected_parent_id).first()
        task = (
            Task.objects.select_for_update(of=("self",))
            .select_related("project", "project__creator", "assignee", "status", "parent__status")
            .get(pk=task.pk)
        )
        if task.is_deleted or task.project.is_deleted:
            raise NotFound('Không tìm thấy công việc.')
        if task.parent_id != expected_parent_id:
            raise TaskUpdateConflict('Công việc cha đã thay đổi. Vui lòng tải lại trước khi xác nhận.')
        if not can_change_task_status(task, actor):
            raise PermissionDenied('Bạn không có quyền đổi trạng thái công việc này.')
        if actor.role.code != Role.Code.ADMIN and not ProjectMember.objects.filter(
            project_id=task.project_id, user_id=actor.id,
        ).exists():
            raise PermissionDenied('Bạn không còn là thành viên dự án này.')
        if expected_status != task.status.code:
            raise TaskUpdateConflict('Trạng thái công việc đã thay đổi. Vui lòng tải lại trước khi xác nhận.')
        unfinished_subtasks = list(
            task.subtasks.filter(is_deleted=False)
            .exclude(status__code=TaskStatus.Code.COMPLETED)
            .order_by("id")
            .select_for_update(of=("self",))
        )
        task.unfinished_subtasks_count = len(unfinished_subtasks)
        was_completed = task.status.code == TaskStatus.Code.COMPLETED
        is_completed = new_status.code == TaskStatus.Code.COMPLETED
        if was_completed and not is_completed and task.assignee_id:
            task.assignee_is_member = ProjectMember.objects.select_for_update(of=('self',)).filter(
                project_id=task.project_id, user_id=task.assignee_id,
            ).exists()
        if task.status_id == new_status.id:
            return task
        incomplete_count = task.checklist_items.filter(is_completed=False).count() if is_completed else 0
        if incomplete_count and not confirm_incomplete_checklist:
            raise ValidationError({'confirm_incomplete_checklist': ['Checklist còn mục chưa hoàn thành. Vui lòng xác nhận trước khi hoàn thành công việc.']})
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
                **({
                    'checklist_incomplete_confirmed': {'old': None, 'new': True},
                    'checklist_unfinished_count': {'old': None, 'new': incomplete_count},
                } if incomplete_count else {}),
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
        task = Task.objects.select_for_update(of=('self',)).get(pk=task.pk)
        tasks = list(
            Task.objects.filter(pk__in=[task.pk, *task.subtasks.values_list("pk", flat=True)])
            .filter(is_deleted=False)
            .order_by("id")
            .select_for_update(of=("self",))
        )
        for item in tasks:
            item.is_deleted = True
            item.save(update_fields=["is_deleted", "updated_at"])
            TaskAuditLog.objects.create(
                task=item,
                actor=actor,
                action=TaskAuditLog.Action.DELETED,
                changes={"is_deleted": {"old": False, "new": True}},
            )
        return task

