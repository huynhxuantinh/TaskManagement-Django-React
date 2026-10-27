from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationType, Preference
from apps.projects.models import Project, ProjectMember
from apps.reports.models import ReportMessage
from apps.tasks.models import TaskAuditLog
from apps.tasks.models import Task, TaskStatus


@pytest.fixture
def report_roles(db):
    return {
        code: Role.objects.get_or_create(code=code, defaults={"name": label})[0]
        for code, label in Role.Code.choices
    }


@pytest.fixture
def report_users(report_roles):
    def make(email, role):
        return User.objects.create_user(
            email=email,
            full_name=email.split("@")[0].title(),
            password="StrongPass@123",
            role=report_roles[role],
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
def report_statuses(db):
    return {
        code: TaskStatus.objects.get_or_create(code=code, defaults={"name": label})[0]
        for code, label in TaskStatus.Code.choices
    }


@pytest.fixture
def report_data(report_users, report_statuses):
    managed = Project.objects.create(name="Managed", creator=report_users["manager"])
    other = Project.objects.create(name="Other", creator=report_users["manager2"])
    for project, users in (
        (managed, [report_users["manager"], report_users["employee"], report_users["employee2"]]),
        (other, [report_users["manager2"], report_users["employee"]]),
    ):
        for user in users:
            ProjectMember.objects.create(project=project, user=user)

    today = timezone.localdate()
    tasks = [
        Task.objects.create(
            title="Done",
            project=managed,
            assignee=report_users["employee"],
            status=report_statuses[TaskStatus.Code.COMPLETED],
            deadline=today + timedelta(days=1),
            completed_at=timezone.now(),
        ),
        Task.objects.create(
            title="Overdue",
            project=managed,
            assignee=report_users["employee"],
            status=report_statuses[TaskStatus.Code.IN_PROGRESS],
            deadline=today - timedelta(days=1),
        ),
        Task.objects.create(
            title="Second assignee",
            project=managed,
            assignee=report_users["employee2"],
            status=report_statuses[TaskStatus.Code.TODO],
        ),
        Task.objects.create(
            title="Other project",
            project=other,
            assignee=report_users["employee"],
            status=report_statuses[TaskStatus.Code.TODO],
        ),
    ]
    return {"managed": managed, "other": other, "tasks": tasks}


def api_as(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
def test_user_list_is_admin_only_searchable_and_filterable(report_users):
    assert api_as().get("/api/v1/users/").status_code == 401
    assert api_as(report_users["manager"]).get("/api/v1/users/").status_code == 403

    response = api_as(report_users["admin"]).get(
        "/api/v1/users/?role=EMPLOYEE&is_active=true&search=employee&page_size=1"
    )

    assert response.status_code == 200
    assert response.data["data"]["count"] == 2
    assert response.data["data"]["results"][0]["role"] == Role.Code.EMPLOYEE
    assert "password" not in response.data["data"]["results"][0]


@pytest.mark.django_db
def test_admin_can_create_internal_account(report_users, report_roles):
    payload = {
        "username": "New.User",
        "email": "NEW.USER@EXAMPLE.COM",
        "full_name": "New User",
        "role": Role.Code.EMPLOYEE,
        "password": "StrongPass@456",
    }

    assert api_as().post("/api/v1/users/", payload, format="json").status_code == 401
    assert (
        api_as(report_users["manager"])
        .post("/api/v1/users/", payload, format="json")
        .status_code
        == 403
    )
    created = api_as(report_users["admin"]).post(
        "/api/v1/users/", payload, format="json"
    )

    assert created.status_code == 201
    account = User.objects.get(username="new.user")
    assert account.email == "new.user@example.com"
    assert account.full_name == "New User"
    assert account.role == report_roles[Role.Code.EMPLOYEE]
    assert account.check_password("StrongPass@456")
    assert account.password != "StrongPass@456"
    assert "password" not in created.data["data"]


@pytest.mark.django_db
def test_admin_account_creation_validates_duplicates_and_password(report_users):
    base = {
        "username": "employee",
        "email": "created@example.com",
        "full_name": "Created User",
        "role": Role.Code.EMPLOYEE,
        "password": "StrongPass@456",
    }
    report_users["employee"].username = "employee"
    report_users["employee"].save(update_fields=["username"])
    client = api_as(report_users["admin"])

    duplicate = client.post("/api/v1/users/", base, format="json")
    weak = client.post(
        "/api/v1/users/",
        {**base, "username": "created", "password": "123"},
        format="json",
    )

    assert duplicate.status_code == 400
    assert "username" in duplicate.data["errors"]
    assert weak.status_code == 400
    assert "password" in weak.data["errors"]


@pytest.mark.django_db
def test_user_detail_update_and_role_change_enforce_self_or_admin(
    report_users, report_roles
):
    employee = report_users["employee"]
    self_update = api_as(employee).patch(
        f"/api/v1/users/{employee.id}/",
        {"full_name": "Employee Updated", "is_active": False},
        format="json",
    )
    hidden = api_as(employee).get(f"/api/v1/users/{report_users['employee2'].id}/")
    forbidden_role = api_as(employee).patch(
        f"/api/v1/users/{employee.id}/role/",
        {"role": Role.Code.MANAGER},
        format="json",
    )
    changed_role = api_as(report_users["admin"]).patch(
        f"/api/v1/users/{employee.id}/role/",
        {"role": Role.Code.MANAGER},
        format="json",
    )

    employee.refresh_from_db()
    assert self_update.status_code == 200
    assert employee.full_name == "Employee Updated"
    assert employee.is_active is True
    assert hidden.status_code == 404
    assert forbidden_role.status_code == 403
    assert changed_role.status_code == 200
    assert employee.role_id == report_roles[Role.Code.MANAGER].id


@pytest.mark.django_db
def test_admin_cannot_deactivate_or_demote_self(report_users):
    admin = report_users["admin"]

    deactivated = api_as(admin).patch(
        f"/api/v1/users/{admin.id}/",
        {"is_active": False},
        format="json",
    )
    demoted = api_as(admin).patch(
        f"/api/v1/users/{admin.id}/role/",
        {"role": Role.Code.MANAGER},
        format="json",
    )

    admin.refresh_from_db()
    assert deactivated.status_code == 400
    assert demoted.status_code == 400
    assert admin.is_active is True
    assert admin.role.code == Role.Code.ADMIN


@pytest.mark.django_db
def test_two_admins_cannot_demote_each_other_to_zero_active_admins(
    report_users, report_roles
):
    first = report_users["admin"]
    second = User.objects.create_user(
        email="second-admin@example.com",
        full_name="Second Admin",
        password="StrongPass@123",
        role=report_roles[Role.Code.ADMIN],
    )

    first_change = api_as(first).patch(
        f"/api/v1/users/{second.id}/role/",
        {"role": Role.Code.MANAGER},
        format="json",
    )
    second_change = api_as(second).patch(
        f"/api/v1/users/{first.id}/role/",
        {"role": Role.Code.MANAGER},
        format="json",
    )

    first.refresh_from_db()
    second.refresh_from_db()
    assert first_change.status_code == 200
    assert second_change.status_code == 400
    assert first.role.code == Role.Code.ADMIN
    assert second.role.code == Role.Code.MANAGER


@pytest.mark.django_db
def test_two_admins_cannot_deactivate_each_other_to_zero_active_admins(
    report_users, report_roles
):
    first = report_users["admin"]
    second = User.objects.create_user(
        email="backup-admin@example.com",
        full_name="Backup Admin",
        password="StrongPass@123",
        role=report_roles[Role.Code.ADMIN],
    )

    first_change = api_as(first).patch(
        f"/api/v1/users/{second.id}/",
        {"is_active": False},
        format="json",
    )
    second_change = api_as(second).patch(
        f"/api/v1/users/{first.id}/",
        {"is_active": False},
        format="json",
    )

    first.refresh_from_db()
    second.refresh_from_db()
    assert first_change.status_code == 200
    assert second_change.status_code == 400
    assert first.is_active is True
    assert second.is_active is False


@pytest.mark.django_db
def test_deactivating_user_requires_and_audits_task_reassignment(
    report_users, report_statuses
):
    project = Project.objects.create(name="Transfer", creator=report_users["manager"])
    ProjectMember.objects.bulk_create(
        [
            ProjectMember(project=project, user=report_users["manager"]),
            ProjectMember(project=project, user=report_users["employee"]),
            ProjectMember(project=project, user=report_users["employee2"]),
        ]
    )
    task = Task.objects.create(
        title="Needs transfer",
        project=project,
        assignee=report_users["employee"],
        status=report_statuses[TaskStatus.Code.IN_PROGRESS],
    )
    url = f"/api/v1/users/{report_users['employee'].id}/"

    missing_replacement = api_as(report_users["admin"]).patch(
        url, {"is_active": False}, format="json"
    )
    deactivated = api_as(report_users["admin"]).patch(
        url,
        {"is_active": False, "reassign_to_id": report_users["employee2"].id},
        format="json",
    )

    task.refresh_from_db()
    report_users["employee"].refresh_from_db()
    assert missing_replacement.status_code == 400
    assert deactivated.status_code == 200
    assert report_users["employee"].is_active is False
    assert task.assignee_id == report_users["employee2"].id
    assert TaskAuditLog.objects.filter(
        task=task,
        actor=report_users["admin"],
        action=TaskAuditLog.Action.UPDATED,
        changes__assignee__new__id=report_users["employee2"].id,
    ).exists()


@pytest.mark.django_db
def test_deactivating_project_owner_requires_eligible_replacement(report_users):
    owner = report_users["manager"]
    replacement = report_users["manager2"]
    project = Project.objects.create(name="Owned project", creator=owner)
    ProjectMember.objects.create(project=project, user=owner)
    url = f"/api/v1/users/{owner.id}/"
    client = api_as(report_users["admin"])

    missing = client.patch(url, {"is_active": False}, format="json")
    invalid = client.patch(
        url,
        {"is_active": False, "reassign_to_id": report_users["employee"].id},
        format="json",
    )
    transferred = client.patch(
        url,
        {"is_active": False, "reassign_to_id": replacement.id},
        format="json",
    )

    owner.refresh_from_db()
    project.refresh_from_db()
    assert missing.status_code == 400
    assert invalid.status_code == 400
    assert transferred.status_code == 200
    assert owner.is_active is False
    assert project.creator_id == replacement.id
    assert ProjectMember.objects.filter(
        project=project, user=replacement
    ).exists()


@pytest.mark.django_db
def test_demoting_project_owner_requires_eligible_replacement(
    report_users, report_roles
):
    owner = report_users["manager"]
    replacement = report_users["manager2"]
    project = Project.objects.create(name="Managed project", creator=owner)
    ProjectMember.objects.create(project=project, user=owner)
    url = f"/api/v1/users/{owner.id}/role/"
    client = api_as(report_users["admin"])

    missing = client.patch(url, {"role": Role.Code.EMPLOYEE}, format="json")
    owner.refresh_from_db()
    project.refresh_from_db()
    assert missing.status_code == 400
    assert owner.role_id == report_roles[Role.Code.MANAGER].id
    assert project.creator_id == owner.id

    transferred = client.patch(
        url,
        {
            "role": Role.Code.EMPLOYEE,
            "reassign_to_id": replacement.id,
        },
        format="json",
    )

    owner.refresh_from_db()
    project.refresh_from_db()
    assert transferred.status_code == 200
    assert owner.role_id == report_roles[Role.Code.EMPLOYEE].id
    assert project.creator_id == replacement.id
    assert ProjectMember.objects.filter(
        project=project, user=replacement
    ).exists()


@pytest.mark.django_db
def test_preferences_are_owner_scoped_and_upserted(report_users):
    employee = report_users["employee"]
    url = f"/api/v1/users/{employee.id}/preferences/"
    payload = [
        {"type": NotificationType.TASK_ASSIGNED, "is_priority": True},
        {"type": NotificationType.STATUS_CHANGED, "is_priority": False},
    ]

    assert api_as(report_users["employee2"]).get(url).status_code == 404
    updated = api_as(employee).put(url, payload, format="json")
    listed = api_as(employee).get(url)

    assert updated.status_code == 200
    assert Preference.objects.filter(user=employee).count() == 2
    assert len(listed.data["data"]) == len(NotificationType.values)
    priority = {row["type"]: row["is_priority"] for row in listed.data["data"]}
    assert priority[NotificationType.TASK_ASSIGNED] is True


@pytest.mark.django_db
def test_avatar_upload_validates_real_file_and_uses_generated_name(
    report_users, tmp_path
):
    employee = report_users["employee"]
    url = f"/api/v1/users/{employee.id}/avatar/"
    fake = SimpleUploadedFile("../../attack.png", b"not-an-image", "image/png")
    png = SimpleUploadedFile(
        "../../profile.png",
        b"\x89PNG\r\n\x1a\n" + b"safe-image-data",
        "image/png",
    )

    with override_settings(MEDIA_ROOT=tmp_path):
        rejected = api_as(employee).post(url, {"file": fake}, format="multipart")
        uploaded = api_as(employee).post(url, {"file": png}, format="multipart")

    employee.refresh_from_db()
    assert rejected.status_code == 400
    assert uploaded.status_code == 200
    assert employee.avatar.startswith("/media/avatars/")
    assert ".." not in employee.avatar
    assert employee.avatar.endswith(".png")


@pytest.mark.django_db
def test_dashboard_summary_is_scoped_by_role(report_users, report_statuses, report_data):
    admin = api_as(report_users["admin"]).get("/api/v1/dashboard/summary/")
    manager = api_as(report_users["manager"]).get("/api/v1/dashboard/summary/")
    employee = api_as(report_users["employee"]).get("/api/v1/dashboard/summary/")

    assert admin.data["data"]["project_count"] == 2
    assert admin.data["data"]["task_count"] == 4
    assert manager.data["data"]["project_count"] == 1
    assert manager.data["data"]["task_count"] == 3
    assert manager.data["data"]["missing_estimate_count"] == 3
    assert employee.data["data"]["task_count"] == 3
    assert employee.data["data"]["overdue_task_count"] == 1
    assert len(employee.data["data"]["recent_tasks"]) == 3


@pytest.mark.django_db
def test_workload_is_admin_or_manager_scoped(report_users, report_statuses, report_data):
    assert (
        api_as(report_users["employee"]).get("/api/v1/reports/workload/").status_code
        == 403
    )
    manager = api_as(report_users["manager"]).get("/api/v1/reports/workload/")
    admin = api_as(report_users["admin"]).get("/api/v1/reports/workload/")

    manager_rows = {row["user"]["id"]: row for row in manager.data["data"]}
    admin_rows = {row["user"]["id"]: row for row in admin.data["data"]}
    assert manager_rows[report_users["employee"].id]["total_tasks"] == 2
    assert manager_rows[report_users["employee"].id]["completed_before_deadline"] == 1
    assert report_users["outsider"].id not in manager_rows
    assert admin_rows[report_users["employee"].id]["total_tasks"] == 3
    assert admin_rows[report_users["outsider"].id]["is_available"] is True


@pytest.mark.django_db
def test_workload_includes_projects_where_manager_is_a_member(
    report_users, report_statuses
):
    project = Project.objects.create(
        name="Shared project", creator=report_users["manager2"]
    )
    ProjectMember.objects.bulk_create(
        [
            ProjectMember(project=project, user=report_users["manager"]),
            ProjectMember(project=project, user=report_users["employee"]),
        ]
    )
    Task.objects.create(
        title="Visible through membership",
        project=project,
        assignee=report_users["employee"],
        status=report_statuses[TaskStatus.Code.IN_PROGRESS],
    )

    response = api_as(report_users["manager"]).get("/api/v1/reports/workload/")

    assert response.status_code == 200
    rows = {row["user"]["id"]: row for row in response.data["data"]}
    assert rows[report_users["employee"].id]["total_tasks"] == 1


@pytest.mark.django_db
def test_workload_uses_completion_time_instead_of_creation_time(
    report_users, report_statuses, report_data
):
    today = timezone.localdate()
    Task.objects.create(
        title="Created early but completed late",
        project=report_data["managed"],
        assignee=report_users["employee"],
        status=report_statuses[TaskStatus.Code.COMPLETED],
        created_at=timezone.now() - timedelta(days=10),
        deadline=today - timedelta(days=5),
        completed_at=timezone.now(),
    )
    Task.objects.create(
        title="Historical completion time unknown",
        project=report_data["managed"],
        assignee=report_users["employee"],
        status=report_statuses[TaskStatus.Code.COMPLETED],
        created_at=timezone.now() - timedelta(days=10),
        deadline=today + timedelta(days=5),
        completed_at=None,
    )

    response = api_as(report_users["manager"]).get("/api/v1/reports/workload/")
    rows = {row["user"]["id"]: row for row in response.data["data"]}

    assert rows[report_users["employee"].id]["completed_before_deadline"] == 1


@pytest.mark.django_db
def test_project_report_and_top_contributors_are_project_scoped(
    report_users, report_statuses, report_data
):
    project = report_data["managed"]
    report_url = f"/api/v1/reports/projects/{project.id}/"
    top_url = f"/api/v1/reports/projects/{project.id}/top-contributors/"

    hidden = api_as(report_users["outsider"]).get(report_url)
    report = api_as(report_users["employee"]).get(report_url)
    contributors = api_as(report_users["employee"]).get(top_url)

    assert hidden.status_code == 404
    assert report.data["data"]["total_tasks"] == 3
    assert report.data["data"]["completed_tasks"] == 1
    assert report.data["data"]["progress"] == 33
    assert report.data["data"]["missing_estimate_count"] == 3
    assert contributors.data["data"][0]["user"]["id"] == report_users["employee"].id
    assert contributors.data["data"][0]["completed_tasks"] == 1


@pytest.mark.django_db
def test_report_messages_validate_members_and_scope_sender_receiver(
    report_users, report_statuses, report_data
):
    project = report_data["managed"]
    payload = {
        "project_id": project.id,
        "receiver_id": report_users["employee"].id,
        "title": "Weekly report",
        "content": "Work completed",
        "sender_id": report_users["outsider"].id,
    }

    invalid_receiver = api_as(report_users["manager"]).post(
        "/api/v1/reports/messages/",
        {**payload, "receiver_id": report_users["outsider"].id},
        format="json",
    )
    sent = api_as(report_users["manager"]).post(
        "/api/v1/reports/messages/", payload, format="json"
    )
    message = ReportMessage.objects.get()
    sender_list = api_as(report_users["manager"]).get("/api/v1/reports/messages/")
    outsider_list = api_as(report_users["outsider"]).get("/api/v1/reports/messages/")
    sender_read = api_as(report_users["manager"]).patch(
        f"/api/v1/reports/messages/{message.id}/read/"
    )
    receiver_read = api_as(report_users["employee"]).patch(
        f"/api/v1/reports/messages/{message.id}/read/"
    )

    assert invalid_receiver.status_code == 400
    assert sent.status_code == 201
    assert message.sender == report_users["manager"]
    assert Notification.objects.filter(
        user=report_users["employee"],
        type=NotificationType.GENERAL,
        message='Bạn nhận được báo cáo "Weekly report" từ Manager.',
    ).exists()
    assert sender_list.data["data"]["count"] == 1
    assert outsider_list.data["data"]["count"] == 0
    assert sender_read.status_code == 403
    assert receiver_read.status_code == 200
    message.refresh_from_db()
    assert message.is_read is True


@pytest.mark.django_db
def test_dashboard_query_count_is_bounded(
    django_assert_max_num_queries, report_users, report_statuses, report_data
):
    for index in range(2):
        Task.objects.create(
            title=f"Recent task {index}",
            project=report_data["managed"],
            assignee=report_users["employee"],
            status=report_statuses[TaskStatus.Code.TODO],
        )

    with django_assert_max_num_queries(7):
        response = api_as(report_users["manager"]).get("/api/v1/dashboard/summary/")

    assert response.status_code == 200
    assert len(response.data["data"]["recent_tasks"]) == 5
