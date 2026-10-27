from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework import serializers

from apps.notifications.models import NotificationType, Preference

from .models import Role, User


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


def ensure_active_admin_remains(user):
    active_admin_ids = list(
        User.objects.filter(
            is_active=True,
            role__code=Role.Code.ADMIN,
        )
        .order_by("id")
        .select_for_update(of=("self",))
        .values_list("id", flat=True)
    )
    if user.pk in active_admin_ids and len(active_admin_ids) == 1:
        raise ValidationError(
            {"detail": "Hệ thống phải còn ít nhất một quản trị viên hoạt động."}
        )


@transaction.atomic
def transfer_owned_projects(user, replacement):
    from apps.projects.models import Project, ProjectMember

    projects = list(
        Project.objects.filter(creator=user, is_deleted=False)
        .order_by("id")
        .select_for_update(of=("self",))
    )
    if not projects:
        return 0
    if replacement is None:
        raise ValidationError(
            {"reassign_to_id": "Hãy chọn quản trị viên hoặc quản lý tiếp quản dự án."}
        )
    replacement = (
        User.objects.select_related("role")
        .select_for_update(of=("self",))
        .get(pk=replacement.pk)
    )
    if replacement.pk == user.pk:
        raise ValidationError(
            {"reassign_to_id": "Người tiếp quản phải khác chủ dự án hiện tại."}
        )
    if not replacement.is_active or replacement.role.code not in {
        Role.Code.ADMIN,
        Role.Code.MANAGER,
    }:
        raise ValidationError(
            {"reassign_to_id": "Người tiếp quản phải là quản trị viên hoặc quản lý đang hoạt động."}
        )
    for project in projects:
        ProjectMember.objects.get_or_create(project=project, user=replacement)
    Project.objects.filter(pk__in=[project.pk for project in projects]).update(
        creator=replacement
    )
    return len(projects)


@transaction.atomic
def change_user_role(user, role, replacement=None):
    if role.code != Role.Code.ADMIN:
        ensure_active_admin_remains(user)
    if role.code not in {Role.Code.ADMIN, Role.Code.MANAGER}:
        transfer_owned_projects(user, replacement)
    user.role = role
    user.save(update_fields=["role"])
    return user


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


@transaction.atomic
def deactivate_and_reassign_tasks(user, replacement, actor):
    from apps.projects.models import ProjectMember
    from apps.tasks.models import Task, TaskStatus
    from apps.tasks.services import TaskService

    ensure_active_admin_remains(user)
    transfer_owned_projects(user, replacement)
    tasks = list(
        Task.objects.filter(
            assignee=user,
            is_deleted=False,
            project__is_deleted=False,
        )
        .exclude(status__code=TaskStatus.Code.COMPLETED)
        .select_related("project", "assignee", "status")
        .order_by("id")
        .select_for_update(of=("self",))
    )
    if tasks and replacement is None:
        raise ValidationError(
            {"reassign_to_id": "Hãy chọn người nhận các công việc đang mở."}
        )
    if replacement is not None:
        if replacement.pk == user.pk:
            raise ValidationError(
                {"reassign_to_id": "Người nhận phải khác tài khoản bị vô hiệu hóa."}
            )
        project_ids = {task.project_id for task in tasks}
        membership_count = ProjectMember.objects.filter(
            project_id__in=project_ids, user=replacement
        ).count()
        if membership_count != len(project_ids):
            raise ValidationError(
                {"reassign_to_id": "Người nhận phải là thành viên của mọi dự án có công việc cần chuyển."}
            )
        for task in tasks:
            TaskService.update_task(task, {"assignee": replacement}, actor)
    user.is_active = False
    user.save(update_fields=["is_active"])
    return len(tasks)

