import os

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from apps.accounts.models import Role, User
from apps.tasks.models import TaskStatus


@pytest.mark.django_db
def test_lookup_rows_are_seeded_by_migrations():
    assert set(Role.objects.values_list("code", flat=True)) == set(Role.Code.values)
    assert set(TaskStatus.objects.values_list("code", flat=True)) == set(
        TaskStatus.Code.values
    )


@pytest.mark.django_db
def test_create_superuser_assigns_admin_role_automatically():
    user = User.objects.create_superuser(
        email="root@example.com",
        full_name="Root Admin",
        password="StrongProductionPass@123",
    )

    assert user.role.code == Role.Code.ADMIN
    assert user.is_staff is True
    assert user.is_superuser is True


@pytest.mark.django_db
def test_bootstrap_admin_uses_environment_and_is_idempotent(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "owner@example.com")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_FULL_NAME", "Production Owner")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "owner")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "StrongProductionPass@123")

    call_command("bootstrap_admin")
    call_command("bootstrap_admin")

    user = User.objects.get(email="owner@example.com")
    assert User.objects.count() == 1
    assert user.username == "owner"
    assert user.role.code == Role.Code.ADMIN
    assert user.check_password("StrongProductionPass@123")


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_seed_demo_is_blocked_outside_debug_mode():
    with pytest.raises(CommandError, match="seed_demo"):
        call_command("seed_demo")

    assert User.objects.count() == 0


@pytest.mark.django_db
def test_bootstrap_admin_requires_password_environment(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "owner@example.com")
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    with pytest.raises(CommandError, match="BOOTSTRAP_ADMIN_PASSWORD"):
        call_command("bootstrap_admin")
