from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationType
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task, TaskStatus


@pytest.fixture
def task_roles(db):
    return {
        code: Role.objects.create(code=code, name=label)
        for code, label in Role.Code.choices
    }


@pytest.fixture
def task_users(task_roles):
    def make(email, role):
        return User.objects.create_user(
            email=email,
            full_name=email.split("@")[0].title(),
            password="StrongPass@123",
            role=task_roles[role],
        )

    return {
        "admin": make("admin@example.com", Role.Code.ADMIN),
        "manager": make("manager@example.com", Role.Code.MANAGER),
        "manager2": make("manager2@example.com", Role.Code.MANAGER),
        "employee": make("employee@example.com", Role.Code.EMPLOYEE),
        "employee2": make("employee2@example.com", Role.Code.EMPLOYEE),
        "outsider": make("outsider@example.com", Role.Code.EMPLOYEE),
    }


@pytest.fixture
def task_statuses(db):
    return {
        code: TaskStatus.objects.create(code=code, name=label)
        for code, label in TaskStatus.Code.choices
    }


@pytest.fixture
def task_project(task_users):
    project = Project.objects.create(name="Internal ERP", creator=task_users["manager"])
    for user in (
        task_users["manager"],
        task_users["manager2"],
        task_users["employee"],
        task_users["employee2"],
    ):
        ProjectMember.objects.create(project=project, user=user)
    return project


def api_as(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user=user)
    return client


def make_task(project, statuses, assignee, **overrides):
    values = {
        "title": "Implement API",
        "description": "Task API contract",
        "project": project,
        "assignee": assignee,
        "status": statuses[TaskStatus.Code.TODO],
        "priority": Task.Priority.MEDIUM,
        "deadline": timezone.localdate() + timedelta(days=3),
    }
    values.update(overrides)
    return Task.objects.create(**values)


@pytest.mark.django_db
def test_task_create_enforces_role_membership_and_creates_notifications(
    task_users, task_statuses, task_project
):
    payload = {
        "title": "Build task screen",
        "description": "React integration",
        "project_id": task_project.id,
        "assignee_id": task_users["employee"].id,
        "status": TaskStatus.Code.TODO,
        "priority": Task.Priority.HIGH,
        "deadline": "2026-10-25",
    }

    assert api_as().post("/api/v1/tasks/", payload, format="json").status_code == 401
    assert (
        api_as(task_users["employee"])
        .post("/api/v1/tasks/", payload, format="json")
        .status_code
        == 403
    )
    invalid = api_as(task_users["manager"]).post(
        "/api/v1/tasks/",
        {**payload, "assignee_id": task_users["outsider"].id},
        format="json",
    )
    created = api_as(task_users["manager"]).post(
        "/api/v1/tasks/", payload, format="json"
    )

    assert invalid.status_code == 400
    assert "assignee_id" in invalid.data["errors"]
    assert created.status_code == 201
    assert created.data["data"]["status"]["code"] == TaskStatus.Code.TODO
    assert created.data["data"]["assignee"]["id"] == task_users["employee"].id
    assert Notification.objects.filter(
        user=task_users["employee"], type=NotificationType.TASK_ASSIGNED
    ).exists()
    assert Notification.objects.filter(
        user=task_users["employee"], type=NotificationType.DEADLINE_APPROACHING
    ).exists()
    assert set(
        Notification.objects.filter(user=task_users["employee"]).values_list(
            "message", flat=True
        )
    ) == {
        'Bạn được giao công việc "Build task screen".',
        'Công việc "Build task screen" sắp đến hạn vào ngày 25/10/2026.',
    }


@pytest.mark.django_db
def test_task_list_scope_filters_search_and_hides_deleted(
    task_users, task_statuses, task_project
):
    mine = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        title="Matching work",
        priority=Task.Priority.HIGH,
    )
    make_task(task_project, task_statuses, task_users["employee2"], title="Other work")
    make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        title="Deleted work",
        is_deleted=True,
    )

    admin = api_as(task_users["admin"]).get("/api/v1/tasks/")
    manager = api_as(task_users["manager2"]).get("/api/v1/tasks/")
    employee = api_as(task_users["employee"]).get(
        f"/api/v1/tasks/?project={task_project.id}&assignee={task_users['employee'].id}"
        f"&status=TODO&priority=3&deadline={mine.deadline}&search=matching"
    )
    outsider = api_as(task_users["outsider"]).get("/api/v1/tasks/")

    assert admin.data["data"]["count"] == 2
    assert manager.data["data"]["count"] == 2
    assert [row["id"] for row in employee.data["data"]["results"]] == [mine.id]
    assert outsider.data["data"]["count"] == 0


@pytest.mark.django_db
def test_task_detail_update_delete_permissions_and_soft_delete(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/"

    assert api_as(task_users["employee"]).get(url).status_code == 200
    assert api_as(task_users["employee2"]).get(url).status_code == 404
    assert (
        api_as(task_users["manager2"])
        .patch(url, {"title": "Hijacked"}, format="json")
        .status_code
        == 403
    )
    updated = api_as(task_users["manager"]).patch(
        url,
        {
            "title": "Updated safely",
            "assignee_id": task_users["employee2"].id,
            "deadline": "2026-11-01",
        },
        format="json",
    )
    deleted = api_as(task_users["admin"]).delete(url)

    assert updated.status_code == 200
    assert updated.data["data"]["title"] == "Updated safely"
    assert deleted.status_code == 204
    task.refresh_from_db()
    assert task.is_deleted is True
    assert Task.objects.filter(pk=task.pk).exists()
    assert api_as(task_users["manager"]).get(url).status_code == 404


@pytest.mark.django_db
def test_assignee_can_change_status_and_status_code_is_validated(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/status/"

    forbidden = api_as(task_users["manager2"]).patch(
        url, {"status": TaskStatus.Code.COMPLETED}, format="json"
    )
    invalid = api_as(task_users["employee"]).patch(
        url, {"status": "UNKNOWN"}, format="json"
    )
    changed = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS}, format="json"
    )

    assert forbidden.status_code == 403
    assert invalid.status_code == 400
    assert changed.status_code == 200
    assert changed.data["data"]["status"]["code"] == TaskStatus.Code.IN_PROGRESS
    assert Notification.objects.filter(
        user=task_users["manager"], type=NotificationType.STATUS_CHANGED
    ).exists()
    assert Notification.objects.get(
        user=task_users["manager"], type=NotificationType.STATUS_CHANGED
    ).message == 'Công việc "Implement API" đã chuyển sang trạng thái Đang thực hiện.'


@pytest.mark.django_db(transaction=True)
def test_task_creation_rolls_back_when_notification_fails(
    monkeypatch, task_users, task_statuses, task_project
):
    from apps.tasks.services import TaskService

    def fail_notification(**_kwargs):
        raise RuntimeError("notification unavailable")

    monkeypatch.setattr(Notification.objects, "create", fail_notification)
    with pytest.raises(RuntimeError, match="notification unavailable"):
        TaskService.create_task(
            {
                "title": "Must roll back",
                "project": task_project,
                "assignee": task_users["employee"],
                "status": task_statuses[TaskStatus.Code.TODO],
                "priority": Task.Priority.MEDIUM,
            }
        )

    assert not Task.objects.filter(title="Must roll back").exists()


@pytest.mark.django_db
def test_notifications_are_owner_scoped_and_can_be_marked_read(
    task_users,
):
    own = Notification.objects.create(
        user=task_users["employee"],
        message="Assigned",
        type=NotificationType.TASK_ASSIGNED,
    )
    other = Notification.objects.create(
        user=task_users["employee2"],
        message="Other",
        type=NotificationType.GENERAL,
    )
    client = api_as(task_users["employee"])

    listed = client.get("/api/v1/notifications/?is_read=false")
    hidden = client.patch(f"/api/v1/notifications/{other.id}/read/")
    marked = client.patch(f"/api/v1/notifications/{own.id}/read/")
    Notification.objects.create(
        user=task_users["employee"],
        message="Second",
        type=NotificationType.GENERAL,
    )
    all_read = client.post("/api/v1/notifications/read-all/")

    assert listed.status_code == 200
    assert [row["id"] for row in listed.data["data"]["results"]] == [own.id]
    assert hidden.status_code == 404
    assert marked.status_code == 200
    assert marked.data["data"]["is_read"] is True
    assert all_read.status_code == 200
    assert all_read.data["data"]["updated_count"] == 1
    other.refresh_from_db()
    assert other.is_read is False


@pytest.mark.django_db
def test_task_status_metadata_and_overdue_field(
    task_users, task_statuses, task_project
):
    task = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        deadline=date.today() - timedelta(days=1),
    )

    metadata = api_as(task_users["employee"]).get(
        "/api/v1/metadata/task-statuses/"
    )
    detail = api_as(task_users["employee"]).get(f"/api/v1/tasks/{task.id}/")

    assert {row["code"] for row in metadata.data["data"]} == set(task_statuses)
    assert detail.data["data"]["is_overdue"] is True
