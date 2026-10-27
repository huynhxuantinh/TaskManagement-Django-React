import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.projects.models import Project, ProjectMember


@pytest.mark.django_db
def test_admin_can_assign_active_manager_as_project_owner():
    admin_role = Role.objects.get_or_create(code=Role.Code.ADMIN, defaults={"name": "Quản trị viên"})[0]
    manager_role = Role.objects.get_or_create(code=Role.Code.MANAGER, defaults={"name": "Quản lý"})[0]
    employee_role = Role.objects.get_or_create(code=Role.Code.EMPLOYEE, defaults={"name": "Nhân viên"})[0]
    admin = User.objects.create_user(email="admin-owner@example.com", password="test", role=admin_role)
    manager = User.objects.create_user(email="manager-owner@example.com", password="test", role=manager_role)
    employee = User.objects.create_user(email="employee-owner@example.com", password="test", role=employee_role)
    client = APIClient()
    client.force_authenticate(admin)
    payload = {
        "name": "Assigned project",
        "start_date": "2026-11-01",
        "end_date": "2026-12-01",
    }

    created = client.post(
        "/api/v1/projects/", {**payload, "creator_id": manager.id}, format="json"
    )
    invalid = client.post(
        "/api/v1/projects/", {**payload, "name": "Invalid owner", "creator_id": employee.id}, format="json"
    )

    assert created.status_code == 201
    project = Project.objects.get(pk=created.data["data"]["id"])
    assert project.creator == manager
    assert ProjectMember.objects.filter(project=project, user=manager).exists()
    assert invalid.status_code == 400
    assert "creator_id" in invalid.data["errors"]
