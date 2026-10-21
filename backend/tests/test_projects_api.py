from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationType
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task, TaskChecklistItem, TaskStatus


@pytest.fixture
def project_roles(db):
    return {
        code: Role.objects.create(code=code, name=label)
        for code, label in Role.Code.choices
    }


@pytest.fixture
def project_users(project_roles):
    def make(email, role):
        return User.objects.create_user(
            email=email,
            full_name=email.split("@")[0].title(),
            password="StrongPass@123",
            role=project_roles[role],
        )

    return {
        "admin": make("admin@example.com", Role.Code.ADMIN),
        "manager": make("manager@example.com", Role.Code.MANAGER),
        "manager2": make("manager2@example.com", Role.Code.MANAGER),
        "employee": make("employee@example.com", Role.Code.EMPLOYEE),
        "outsider": make("outsider@example.com", Role.Code.EMPLOYEE),
    }


def api_as(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user=user)
    return client


def make_project(creator, name="Project", members=(), deleted=False):
    project = Project.objects.create(
        name=name,
        description=f"{name} description",
        creator=creator,
        is_deleted=deleted,
    )
    ProjectMember.objects.create(project=project, user=creator)
    for user in members:
        ProjectMember.objects.create(project=project, user=user)
    return project


@pytest.mark.django_db
def test_project_create_uses_jwt_user_adds_creator_member_and_enforces_role(project_users):
    manager = project_users["manager"]
    payload = {
        "name": "Migration API",
        "description": "Django rewrite",
        "start_date": "2026-10-01",
        "end_date": "2026-12-31",
        "creator": project_users["admin"].id,
    }

    anonymous = api_as().post("/api/v1/projects/", payload, format="json")
    employee = api_as(project_users["employee"]).post(
        "/api/v1/projects/", payload, format="json"
    )
    created = api_as(manager).post("/api/v1/projects/", payload, format="json")

    assert anonymous.status_code == 401
    assert employee.status_code == 403
    assert created.status_code == 201
    project = Project.objects.get(name="Migration API")
    assert project.creator == manager
    assert ProjectMember.objects.filter(project=project, user=manager).exists()
    assert created.data["data"]["creator"]["id"] == manager.id


@pytest.mark.django_db
def test_project_dates_are_validated(project_users):
    response = api_as(project_users["manager"]).post(
        "/api/v1/projects/",
        {
            "name": "Invalid dates",
            "start_date": "2026-12-31",
            "end_date": "2026-01-01",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "end_date" in response.data["errors"]


@pytest.mark.django_db
def test_project_list_is_scoped_searchable_ordered_and_hides_deleted(project_users):
    visible = make_project(
        project_users["manager"], "Alpha", members=[project_users["employee"]]
    )
    other = make_project(project_users["manager2"], "Beta")
    make_project(project_users["manager"], "Deleted", deleted=True)

    admin_response = api_as(project_users["admin"]).get(
        "/api/v1/projects/?ordering=-name&page_size=1"
    )
    employee_response = api_as(project_users["employee"]).get(
        "/api/v1/projects/?search=alpha"
    )
    outsider_response = api_as(project_users["outsider"]).get("/api/v1/projects/")

    assert admin_response.status_code == 200
    assert admin_response.data["data"]["count"] == 2
    assert admin_response.data["data"]["results"][0]["id"] == other.id
    assert [row["id"] for row in employee_response.data["data"]["results"]] == [
        visible.id
    ]
    assert outsider_response.data["data"]["count"] == 0


@pytest.mark.django_db
def test_project_detail_returns_404_outside_scope_instead_of_leaking_existence(
    project_users,
):
    project = make_project(
        project_users["manager"], members=[project_users["employee"]]
    )

    member = api_as(project_users["employee"]).get(
        f"/api/v1/projects/{project.id}/"
    )
    outsider = api_as(project_users["outsider"]).get(
        f"/api/v1/projects/{project.id}/"
    )

    assert member.status_code == 200
    assert member.data["data"]["id"] == project.id
    assert outsider.status_code == 404


@pytest.mark.django_db
def test_only_admin_or_creator_manager_can_update_and_soft_delete(project_users):
    owner = project_users["manager"]
    participant = project_users["manager2"]
    project = make_project(owner, members=[participant])

    forbidden = api_as(participant).patch(
        f"/api/v1/projects/{project.id}/", {"name": "Hijacked"}, format="json"
    )
    updated = api_as(owner).patch(
        f"/api/v1/projects/{project.id}/", {"name": "Updated"}, format="json"
    )
    deleted = api_as(project_users["admin"]).delete(
        f"/api/v1/projects/{project.id}/"
    )

    assert forbidden.status_code == 403
    assert updated.status_code == 200
    assert updated.data["data"]["name"] == "Updated"
    assert deleted.status_code == 204
    project.refresh_from_db()
    assert project.is_deleted is True
    assert Project.objects.filter(pk=project.pk).exists()
    assert api_as(owner).get(f"/api/v1/projects/{project.id}/").status_code == 404


@pytest.mark.django_db
def test_member_add_list_remove_conflicts_and_management_scope(project_users):
    owner = project_users["manager"]
    participant = project_users["manager2"]
    employee = project_users["employee"]
    outsider = project_users["outsider"]
    project = make_project(owner, members=[participant])
    url = f"/api/v1/projects/{project.id}/members/"

    added = api_as(owner).post(url, {"user_id": employee.id}, format="json")
    duplicate = api_as(owner).post(url, {"email": employee.email}, format="json")
    forbidden = api_as(participant).post(
        url, {"user_id": outsider.id}, format="json"
    )
    members = api_as(employee).get(url)
    hidden = api_as(outsider).get(url)
    remove_creator = api_as(owner).delete(
        f"/api/v1/projects/{project.id}/members/{owner.id}/"
    )
    removed = api_as(owner).delete(
        f"/api/v1/projects/{project.id}/members/{employee.id}/"
    )
    missing = api_as(owner).delete(
        f"/api/v1/projects/{project.id}/members/{employee.id}/"
    )

    assert added.status_code == 201
    assert Notification.objects.filter(
        user=employee,
        type=NotificationType.PROJECT_ADDED,
        message='Bạn đã được thêm vào dự án "Project".',
    ).exists()
    assert duplicate.status_code == 409
    assert forbidden.status_code == 403
    assert members.status_code == 200
    assert {row["user"]["id"] for row in members.data["data"]["results"]} == {
        owner.id,
        participant.id,
        employee.id,
    }
    assert hidden.status_code == 404
    assert remove_creator.status_code == 409
    assert removed.status_code == 204
    assert missing.status_code == 404


@pytest.mark.django_db
def test_project_progress_uses_only_active_tasks(project_users):
    project = make_project(project_users["manager"])
    todo = TaskStatus.objects.create(code="TODO", name="To Do")
    done = TaskStatus.objects.create(code="COMPLETED", name="Completed")
    Task.objects.create(title="Todo", project=project, status=todo)
    Task.objects.create(title="Done", project=project, status=done)
    Task.objects.create(
        title="Deleted done", project=project, status=done, is_deleted=True
    )

    response = api_as(project_users["manager"]).get(
        f"/api/v1/projects/{project.id}/"
    )

    assert response.status_code == 200
    assert response.data["data"]["progress"] == 50
    assert response.data["data"]["member_count"] == 1


@pytest.mark.django_db
def test_project_progress_uses_average_weight_for_missing_estimates(project_users):
    project = make_project(project_users["manager"])
    todo = TaskStatus.objects.create(code="TODO", name="To Do")
    done = TaskStatus.objects.create(code="COMPLETED", name="Completed")
    empty = api_as(project_users["manager"]).get(
        f"/api/v1/projects/{project.id}/"
    )
    Task.objects.create(
        title="Estimated and done",
        project=project,
        status=done,
        estimated_hours=Decimal("10"),
    )
    Task.objects.create(title="Missing estimate", project=project, status=todo)

    response = api_as(project_users["manager"]).get(
        f"/api/v1/projects/{project.id}/"
    )

    assert empty.data["data"]["progress"] == 0
    assert response.data["data"]["progress"] == 50
    assert response.data["data"]["missing_estimate_count"] == 1


@pytest.mark.django_db
def test_project_progress_uses_checklist_and_returns_to_manual_after_reopen(
    project_users,
):
    project = make_project(project_users["manager"])
    todo = TaskStatus.objects.create(code="TODO", name="To Do")
    done = TaskStatus.objects.create(code="COMPLETED", name="Completed")
    task = Task.objects.create(
        title="Checklist task",
        project=project,
        status=todo,
        progress=30,
        estimated_hours=Decimal("4"),
    )
    TaskChecklistItem.objects.create(task=task, title="Done", is_completed=True)
    TaskChecklistItem.objects.create(task=task, title="Open")

    checklist_progress = api_as(project_users["manager"]).get(
        f"/api/v1/projects/{project.id}/"
    )
    task.status = done
    task.save(update_fields=["status"])
    completed_progress = api_as(project_users["manager"]).get(
        f"/api/v1/projects/{project.id}/"
    )
    task.status = todo
    task.checklist_items.all().delete()
    task.save(update_fields=["status"])
    reopened_progress = api_as(project_users["manager"]).get(
        f"/api/v1/projects/{project.id}/"
    )

    assert checklist_progress.data["data"]["progress"] == 50
    assert completed_progress.data["data"]["progress"] == 100
    assert reopened_progress.data["data"]["progress"] == 30


@pytest.mark.django_db
def test_parent_progress_and_hours_are_aggregated_from_children(project_users):
    project = make_project(project_users["manager"])
    todo = TaskStatus.objects.create(code="TODO", name="To Do")
    done = TaskStatus.objects.create(code="COMPLETED", name="Completed")
    parent = Task.objects.create(
        title="Parent",
        project=project,
        status=todo,
        progress=0,
        estimated_hours=Decimal("100"),
    )
    Task.objects.create(
        title="First child",
        project=project,
        parent=parent,
        status=todo,
        progress=50,
        estimated_hours=Decimal("2"),
    )
    Task.objects.create(
        title="Second child",
        project=project,
        parent=parent,
        status=done,
        estimated_hours=Decimal("6"),
    )

    project_response = api_as(project_users["manager"]).get(
        f"/api/v1/projects/{project.id}/"
    )
    task_response = api_as(project_users["manager"]).get(
        f"/api/v1/tasks/{parent.id}/"
    )

    assert project_response.data["data"]["progress"] == 88
    assert task_response.data["data"]["effective_progress"] == 88
    assert task_response.data["data"]["effective_estimated_hours"] == "8.00"


@pytest.mark.django_db
def test_project_list_query_count_is_bounded(project_users):
    manager = project_users["manager"]
    for index in range(6):
        make_project(manager, f"Project {index}", members=[project_users["employee"]])

    with CaptureQueriesContext(connection) as queries:
        response = api_as(manager).get("/api/v1/projects/?page_size=20")

    assert response.status_code == 200
    assert len(queries) <= 3
