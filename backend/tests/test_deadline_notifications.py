from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationType, Preference
from apps.projects.models import Project
from apps.tasks.models import Task, TaskStatus


@pytest.mark.django_db
def test_deadline_command_sends_real_reminders_once_and_skips_inactive_tasks():
    role = Role.objects.get_or_create(code=Role.Code.EMPLOYEE, defaults={"name": "Nhân viên"})[0]
    manager_role = Role.objects.get_or_create(code=Role.Code.MANAGER, defaults={"name": "Quản lý"})[0]
    assignee = User.objects.create_user(
        email="employee@example.com", password="test", role=role
    )
    manager = User.objects.create_user(
        email="manager@example.com", password="test", role=manager_role
    )
    project = Project.objects.create(name="Dự án", creator=manager)
    deleted_project = Project.objects.create(
        name="Dự án đã xóa", creator=manager, is_deleted=True
    )
    todo = TaskStatus.objects.get_or_create(
        code=TaskStatus.Code.TODO, defaults={"name": "Chưa thực hiện"}
    )[0]
    completed = TaskStatus.objects.get_or_create(
        code=TaskStatus.Code.COMPLETED, defaults={"name": "Đã hoàn thành"}
    )[0]
    today = timezone.localdate()

    for title, deadline, status, overrides in (
        ("Còn một ngày", today + timedelta(days=1), todo, {}),
        ("Đến hạn hôm nay", today, todo, {}),
        ("Đã quá hạn", today - timedelta(days=1), todo, {}),
        ("Còn xa", today + timedelta(days=2), todo, {}),
        ("Đã xong", today - timedelta(days=1), completed, {}),
        ("Đã xóa", today, todo, {"is_deleted": True}),
        ("Dự án đã xóa", today, todo, {"project": deleted_project}),
        ("Chưa giao", today, todo, {"assignee": None}),
    ):
        Task.objects.create(
            title=title,
            project=overrides.pop("project", project),
            assignee=overrides.pop("assignee", assignee),
            status=status,
            deadline=deadline,
            **overrides,
        )

    Preference.objects.create(
        user=assignee,
        type=NotificationType.DEADLINE_APPROACHING,
        is_priority=False,
    )

    call_command("send_deadline_notifications", date=today.isoformat())
    call_command("send_deadline_notifications", date=today.isoformat())

    notifications = Notification.objects.filter(user=assignee).order_by("id")
    assert notifications.count() == 3
    assert list(notifications.values_list("type", "message", "is_priority")) == [
        (
            NotificationType.DEADLINE_APPROACHING,
            f'Công việc "Còn một ngày" còn 1 ngày đến hạn ({today + timedelta(days=1):%d/%m/%Y}).',
            False,
        ),
        (
            NotificationType.DEADLINE_APPROACHING,
            f'Công việc "Đến hạn hôm nay" đến hạn hôm nay ({today:%d/%m/%Y}).',
            False,
        ),
        (
            NotificationType.DEADLINE_OVERDUE,
            f'Công việc "Đã quá hạn" đã quá hạn từ ngày {today - timedelta(days=1):%d/%m/%Y}.',
            True,
        ),
    ]


@pytest.mark.django_db
def test_overdue_reminder_is_sent_once_per_deadline_and_skips_on_hold():
    role = Role.objects.get_or_create(
        code=Role.Code.EMPLOYEE, defaults={"name": "Employee"}
    )[0]
    manager_role = Role.objects.get_or_create(
        code=Role.Code.MANAGER, defaults={"name": "Manager"}
    )[0]
    assignee = User.objects.create_user(
        email="overdue-employee@example.com", password="test", role=role
    )
    manager = User.objects.create_user(
        email="overdue-manager@example.com", password="test", role=manager_role
    )
    project = Project.objects.create(name="Overdue project", creator=manager)
    todo = TaskStatus.objects.get_or_create(
        code=TaskStatus.Code.TODO, defaults={"name": "Todo"}
    )[0]
    on_hold = TaskStatus.objects.get_or_create(
        code=TaskStatus.Code.ON_HOLD, defaults={"name": "On hold"}
    )[0]
    today = timezone.localdate()
    Task.objects.create(
        title="Overdue once",
        project=project,
        assignee=assignee,
        status=todo,
        deadline=today - timedelta(days=1),
    )
    Task.objects.create(
        title="Paused overdue",
        project=project,
        assignee=assignee,
        status=on_hold,
        deadline=today - timedelta(days=1),
    )

    for offset in range(4):
        call_command(
            "send_deadline_notifications",
            date=(today + timedelta(days=offset)).isoformat(),
        )

    notifications = Notification.objects.filter(
        user=assignee,
        type=NotificationType.DEADLINE_OVERDUE,
    )
    assert notifications.count() == 1
    assert "Overdue once" in notifications.get().message


@pytest.mark.django_db
def test_deadline_command_accepts_default_current_date():
    call_command("send_deadline_notifications")

    assert Notification.objects.count() == 0


def test_deadline_loop_closes_connections_only_after_sleep(monkeypatch):
    from apps.tasks.management.commands import send_deadline_notifications as command_module

    events = []

    def send(_reference_date):
        events.append("send")
        if events.count("send") == 2:
            raise KeyboardInterrupt
        return 0

    monkeypatch.setattr(command_module, "send_deadline_notifications", send)
    monkeypatch.setattr(command_module.time, "sleep", lambda _seconds: events.append("sleep"))
    monkeypatch.setattr(command_module, "close_old_connections", lambda: events.append("close"))

    with pytest.raises(KeyboardInterrupt):
        call_command("send_deadline_notifications", loop=True, interval=1)

    assert events == ["send", "sleep", "close", "send"]
