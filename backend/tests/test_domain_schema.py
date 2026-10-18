from datetime import date

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import Role, User
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task, TaskStatus


@pytest.mark.django_db
def test_user_email_is_normalized_and_case_insensitively_unique():
    role = Role.objects.create(code=Role.Code.ADMIN, name="Admin", legacy_id=4)
    User.objects.create_user(
        email="Admin@Example.COM",
        full_name="Admin",
        role=role,
        password="safe-test-password",
    )

    assert User.objects.get().email == "admin@example.com"

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            email="ADMIN@example.com",
            full_name="Duplicate",
            role=role,
            password="safe-test-password",
        )


@pytest.mark.django_db
def test_project_member_and_task_constraints_are_enforced():
    role = Role.objects.create(code=Role.Code.MANAGER, name="Manager", legacy_id=5)
    user = User.objects.create_user(
        email="manager@example.com",
        full_name="Manager",
        role=role,
        password="safe-test-password",
    )
    project = Project.objects.create(
        name="Migration",
        creator=user,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    ProjectMember.objects.create(project=project, user=user)

    with pytest.raises(IntegrityError), transaction.atomic():
        ProjectMember.objects.create(project=project, user=user)

    status = TaskStatus.objects.create(
        code=TaskStatus.Code.TODO,
        name="To Do",
        legacy_id=5,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        Task.objects.create(
            title="Invalid priority",
            project=project,
            status=status,
            priority=4,
        )

