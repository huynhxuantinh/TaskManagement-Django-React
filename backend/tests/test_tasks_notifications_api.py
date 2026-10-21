import csv
from datetime import date, timedelta
from io import StringIO

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationType
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task, TaskAuditLog, TaskStatus


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
def test_task_create_enforces_role_membership_and_only_notifies_assignment(
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
    assert created.data["data"]["updated_at"] is not None
    creation_log = TaskAuditLog.objects.get(task_id=created.data["data"]["id"])
    assert creation_log.action == TaskAuditLog.Action.CREATED
    assert creation_log.actor == task_users["manager"]
    assert Notification.objects.filter(
        user=task_users["employee"], type=NotificationType.TASK_ASSIGNED
    ).exists()
    assert set(
        Notification.objects.filter(user=task_users["employee"]).values_list(
            "message", flat=True
        )
    ) == {
        'Bạn được giao công việc "Build task screen".',
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
def test_task_list_supports_deadline_ranges_urgency_filters_and_csv_export(
    task_users, task_statuses, task_project
):
    today = timezone.localdate()
    overdue = make_task(
        task_project, task_statuses, task_users["employee"], title="Overdue", deadline=today - timedelta(days=1)
    )
    soon = make_task(
        task_project, task_statuses, task_users["employee"], title="Due soon", deadline=today + timedelta(days=2)
    )
    make_task(
        task_project, task_statuses, task_users["employee"], title="Later", deadline=today + timedelta(days=5)
    )

    ranged = api_as(task_users["employee"]).get(
        f"/api/v1/tasks/?deadline_from={today}&deadline_to={today + timedelta(days=2)}"
    )
    overdue_response = api_as(task_users["employee"]).get("/api/v1/tasks/?overdue=true")
    soon_response = api_as(task_users["employee"]).get("/api/v1/tasks/?due_soon=true")
    invalid_range = api_as(task_users["employee"]).get(
        f"/api/v1/tasks/?deadline_from={today + timedelta(days=2)}&deadline_to={today}"
    )
    exported = api_as(task_users["employee"]).get("/api/v1/tasks/export/?due_soon=true")

    assert {row["id"] for row in ranged.data["data"]["results"]} == {soon.id}
    assert [row["id"] for row in overdue_response.data["data"]["results"]] == [overdue.id]
    assert soon.id in {row["id"] for row in soon_response.data["data"]["results"]}
    assert invalid_range.status_code == 400
    assert exported.status_code == 200
    assert exported["Content-Type"].startswith("text/csv")
    assert "Due soon" in exported.content.decode("utf-8-sig")
    assert "Later" not in exported.content.decode("utf-8-sig")


@pytest.mark.django_db
def test_task_csv_export_escapes_formula_values(task_users, task_statuses, task_project):
    task_project.name = "@Malicious project"
    task_project.save(update_fields=["name"])
    assignee = task_users["employee"]
    assignee.full_name = "+Malicious assignee"
    assignee.save(update_fields=["full_name"])
    make_task(
        task_project,
        task_statuses,
        assignee,
        title='=HYPERLINK("http://evil","click")',
    )
    make_task(task_project, task_statuses, assignee, title="\t=1+1")
    make_task(task_project, task_statuses, assignee, title="\r=1+1")

    response = api_as(assignee).get("/api/v1/tasks/export/")
    rows = list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))

    formula_row = next(
        row for row in rows[1:] if row[1] == '\'=HYPERLINK("http://evil","click")'
    )
    assert formula_row[1:4] == [
        '\'=HYPERLINK("http://evil","click")',
        "'@Malicious project",
        "'+Malicious assignee",
    ]
    assert {row[1] for row in rows[1:]} >= {"'\t=1+1", "'\r=1+1"}


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
def test_task_planning_fields_are_json_safe_in_audit_log(
    task_users, task_statuses, task_project
):
    parent = make_task(task_project, task_statuses, task_users["employee"])
    task = make_task(task_project, task_statuses, task_users["employee2"])

    response = api_as(task_users["manager"]).patch(
        f"/api/v1/tasks/{task.id}/",
        {"start_date": "2026-11-01", "estimated_hours": "12.50", "parent": parent.id},
        format="json",
    )

    assert response.status_code == 200
    changes = TaskAuditLog.objects.filter(task=task).latest("id").changes
    assert changes["start_date"]["new"] == "2026-11-01"
    assert changes["estimated_hours"]["new"] == "12.50"
    assert changes["parent"]["new"] == {"id": parent.id, "title": parent.title}


@pytest.mark.django_db
def test_status_workflow_requires_note_and_limits_reopening(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/status/"

    forbidden = api_as(task_users["manager2"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "note": "Bắt đầu."}, format="json"
    )
    invalid = api_as(task_users["employee"]).patch(
        url, {"status": "UNKNOWN"}, format="json"
    )
    missing_note = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS}, format="json"
    )
    skipped = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.ON_HOLD}, format="json"
    )
    changed = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "note": "Đã bắt đầu xử lý."}, format="json"
    )
    completed = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.COMPLETED, "note": "Đã hoàn tất."}, format="json"
    )
    employee_reopen = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "note": "Cần mở lại."}, format="json"
    )
    manager_reopen = api_as(task_users["manager"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "note": "Mở lại để bổ sung."}, format="json"
    )

    assert forbidden.status_code == 403
    assert invalid.status_code == 400
    assert missing_note.status_code == 200
    assert skipped.status_code == 400
    assert changed.status_code == 200
    assert changed.data["data"]["status"]["code"] == TaskStatus.Code.IN_PROGRESS
    assert completed.status_code == 200
    assert employee_reopen.status_code == 403
    assert manager_reopen.status_code == 200
    assert Notification.objects.filter(
        user=task_users["manager"], type=NotificationType.STATUS_CHANGED
    ).exists()
    assert Notification.objects.filter(
        user=task_users["manager"],
        type=NotificationType.STATUS_CHANGED,
        message='Công việc "Implement API" đã chuyển sang trạng thái Đang thực hiện.',
    ).exists()


@pytest.mark.django_db
def test_optional_status_note_accepts_blank_value(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])

    changed = api_as(task_users["employee"]).patch(
        f"/api/v1/tasks/{task.id}/status/",
        {"status": TaskStatus.Code.IN_PROGRESS, "note": ""},
        format="json",
    )

    assert changed.status_code == 200
    log = TaskAuditLog.objects.get(task=task, action=TaskAuditLog.Action.STATUS_CHANGED)
    assert "note" not in log.changes


@pytest.mark.django_db
def test_allowed_transitions_match_status_change_permission(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/"

    visible = api_as(task_users["manager2"]).get(url)
    blocked = api_as(task_users["manager2"]).patch(
        f"{url}status/",
        {"status": TaskStatus.Code.IN_PROGRESS},
        format="json",
    )
    allowed = api_as(task_users["employee"]).get(url)

    assert visible.status_code == 200
    assert visible.data["data"]["allowed_transitions"] == []
    assert blocked.status_code == 403
    assert {item["code"] for item in allowed.data["data"]["allowed_transitions"]} == {
        TaskStatus.Code.IN_PROGRESS,
        TaskStatus.Code.ON_HOLD,
        TaskStatus.Code.COMPLETED,
    }


@pytest.mark.django_db
def test_invalid_completed_transition_returns_bad_request_for_manager(
    task_users, task_statuses, task_project
):
    task = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        status=task_statuses[TaskStatus.Code.COMPLETED],
    )

    response = api_as(task_users["manager"]).patch(
        f"/api/v1/tasks/{task.id}/status/",
        {"status": TaskStatus.Code.TODO},
        format="json",
    )

    assert response.status_code == 400
    assert "status" in response.data["errors"]


@pytest.mark.django_db
def test_status_change_sets_and_clears_completed_at(
    task_users, task_statuses, task_project
):
    task = make_task(task_project, task_statuses, task_users["employee"])
    url = f"/api/v1/tasks/{task.id}/status/"
    before_completion = timezone.now()

    completed = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "note": "Đang thực hiện."}, format="json"
    )
    completed = api_as(task_users["employee"]).patch(
        url, {"status": TaskStatus.Code.COMPLETED, "note": "Đã hoàn thành."}, format="json"
    )

    task.refresh_from_db()
    assert completed.status_code == 200
    assert task.completed_at is not None
    assert task.completed_at >= before_completion
    assert completed.data["data"]["completed_at"] is not None

    reopened = api_as(task_users["manager"]).patch(
        url, {"status": TaskStatus.Code.IN_PROGRESS, "note": "Mở lại để kiểm tra."}, format="json"
    )

    task.refresh_from_db()
    assert reopened.status_code == 200
    assert task.completed_at is None
    assert reopened.data["data"]["completed_at"] is None


@pytest.mark.django_db
def test_task_history_records_actor_time_and_before_after_values(
    task_users, task_statuses, task_project
):
    original_deadline = timezone.localdate() + timedelta(days=3)
    task = make_task(
        task_project,
        task_statuses,
        task_users["employee"],
        deadline=original_deadline,
    )
    before_change = timezone.now()

    updated = api_as(task_users["manager"]).patch(
        f"/api/v1/tasks/{task.id}/",
        {
            "assignee_id": task_users["employee2"].id,
            "deadline": "2026-11-01",
        },
        format="json",
    )
    changed = api_as(task_users["employee2"]).patch(
        f"/api/v1/tasks/{task.id}/status/",
        {"status": TaskStatus.Code.IN_PROGRESS, "note": "Bắt đầu xử lý."},
        format="json",
    )
    repeated = api_as(task_users["employee2"]).patch(
        f"/api/v1/tasks/{task.id}/status/",
        {"status": TaskStatus.Code.IN_PROGRESS},
        format="json",
    )
    history = api_as(task_users["manager"]).get(
        f"/api/v1/tasks/{task.id}/history/"
    )
    hidden = api_as(task_users["outsider"]).get(
        f"/api/v1/tasks/{task.id}/history/"
    )

    task.refresh_from_db()
    assert updated.status_code == 200
    assert changed.status_code == 200
    assert repeated.status_code == 200
    assert task.updated_at >= before_change
    assert updated.data["data"]["updated_at"] is not None
    assert history.status_code == 200
    assert hidden.status_code == 404
    assert history.data["data"]["count"] == 2
    rows = history.data["data"]["results"]
    assert [row["action"] for row in rows] == [
        TaskAuditLog.Action.STATUS_CHANGED,
        TaskAuditLog.Action.UPDATED,
    ]
    assert rows[0]["actor"]["id"] == task_users["employee2"].id
    assert rows[0]["changes"] == {
        "status": {"old": TaskStatus.Code.TODO, "new": TaskStatus.Code.IN_PROGRESS},
        "note": {"old": None, "new": "Bắt đầu xử lý."},
    }
    assert rows[1]["actor"]["id"] == task_users["manager"].id
    assert rows[1]["changes"] == {
        "assignee": {
            "old": {
                "id": task_users["employee"].id,
                "full_name": task_users["employee"].full_name,
            },
            "new": {
                "id": task_users["employee2"].id,
                "full_name": task_users["employee2"].full_name,
            },
        },
        "deadline": {"old": original_deadline.isoformat(), "new": "2026-11-01"},
    }
    assert all(row["created_at"] for row in rows)


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
