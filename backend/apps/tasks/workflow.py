from apps.accounts.models import Role
from apps.projects.permissions import can_manage_project
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import TaskStatus


TRANSITIONS = {
    TaskStatus.Code.TODO: {
        TaskStatus.Code.IN_PROGRESS,
        TaskStatus.Code.ON_HOLD,
        TaskStatus.Code.COMPLETED,
    },
    TaskStatus.Code.IN_PROGRESS: {
        TaskStatus.Code.ON_HOLD,
        TaskStatus.Code.COMPLETED,
    },
    TaskStatus.Code.ON_HOLD: {
        TaskStatus.Code.IN_PROGRESS,
        TaskStatus.Code.COMPLETED,
    },
    TaskStatus.Code.COMPLETED: {TaskStatus.Code.IN_PROGRESS},
}


def note_required(current_code, target_code):
    return target_code == TaskStatus.Code.ON_HOLD or current_code == TaskStatus.Code.COMPLETED


def can_change_task_status(task, actor):
    return can_manage_project(actor, task.project) or task.assignee_id == actor.id


def allowed_transitions(task, actor):
    if not can_change_task_status(task, actor):
        return []
    codes = TRANSITIONS.get(task.status.code, set())
    if task.status.code == TaskStatus.Code.COMPLETED and actor.role.code not in {
        Role.Code.ADMIN,
        Role.Code.MANAGER,
    }:
        codes = set()
    return [
        {"code": code, "note_required": note_required(task.status.code, code)}
        for code in TaskStatus.Code.values
        if code in codes
    ]


def validate_transition(task, new_status, actor, note):
    allowed = {item["code"]: item for item in allowed_transitions(task, actor)}
    if new_status.code not in allowed:
        if (
            task.status.code == TaskStatus.Code.COMPLETED
            and new_status.code == TaskStatus.Code.IN_PROGRESS
            and actor.role.code not in {Role.Code.ADMIN, Role.Code.MANAGER}
        ):
            raise PermissionDenied("Chỉ quản trị viên hoặc quản lý được phép mở lại công việc đã hoàn thành.")
        raise ValidationError({"status": "Trạng thái mới không hợp lệ với tiến trình hiện tại."})
    note = note.strip()
    if allowed[new_status.code]["note_required"] and not note:
        raise ValidationError({"note": "Vui lòng nhập ghi chú cho lần thay đổi trạng thái này."})
    return note
