from datetime import datetime, timezone

import pytest

from apps.accounts.models import Role, User
from apps.core.legacy_import import (
    LegacyDataValidationError,
    canonical_table_hash,
    import_payload,
    legacy_datetime_to_utc,
    validate_payload,
)
from apps.notifications.models import Notification, Preference
from apps.projects.models import Project, ProjectMember
from apps.reports.models import ReportMessage
from apps.tasks.models import Task, TaskStatus


def sample_payload():
    return {
        "roles": [{"legacy_id": 4, "name": "Admin"}],
        "users": [
            {
                "id": 1,
                "full_name": "Admin User",
                "email": "ADMIN@example.com",
                "password": "$2a$11$legacy",
                "role_legacy_id": 4,
                "is_active": True,
                "created_at": "2026-01-01T00:30:00",
                "avatar": None,
            }
        ],
        "projects": [
            {
                "id": 1,
                "name": "Internal Project",
                "description": None,
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "creator_id": 1,
                "is_deleted": False,
                "created_at": "2026-01-01T01:00:00",
            }
        ],
        "project_members": [
            {
                "id": 1,
                "project_id": 1,
                "user_id": 1,
                "joined_at": "2026-01-01T01:30:00",
            }
        ],
        "task_statuses": [{"legacy_id": 5, "name": "To Do"}],
        "tasks": [
            {
                "id": 1,
                "title": "Build importer",
                "description": None,
                "project_id": 1,
                "assignee_id": 1,
                "status_legacy_id": 5,
                "priority": 2,
                "deadline": "2026-01-31",
                "is_deleted": False,
                "created_at": "2026-01-01T02:00:00",
            }
        ],
        "notifications": [
            {
                "id": 1,
                "user_id": 1,
                "message": "Assigned",
                "type": "TASK_ASSIGNED",
                "is_priority": True,
                "is_read": False,
                "created_at": "2026-01-01T02:30:00",
            }
        ],
        "preferences": [
            {
                "id": 1,
                "user_id": 1,
                "type": "TASK_ASSIGNED",
                "is_priority": True,
            }
        ],
        "reports": [
            {
                "id": 1,
                "project_id": 1,
                "sender_id": 1,
                "receiver_id": 1,
                "title": "Status",
                "content": "Done",
                "is_read": False,
                "created_at": "2026-01-01T03:00:00",
            }
        ],
    }


def test_legacy_datetime_uses_asia_saigon_and_crosses_utc_date_boundary():
    converted = legacy_datetime_to_utc("2026-01-01T00:30:00")

    assert converted == datetime(2025, 12, 31, 17, 30, tzinfo=timezone.utc)


def test_validation_reports_duplicate_email_and_orphan():
    payload = sample_payload()
    payload["users"].append({**payload["users"][0], "id": 2, "email": "admin@EXAMPLE.com"})
    payload["tasks"][0]["assignee_id"] = 999

    with pytest.raises(LegacyDataValidationError) as error:
        validate_payload(payload)

    assert "duplicate email" in str(error.value).lower()
    assert "orphan" in str(error.value).lower()


@pytest.mark.django_db
def test_import_is_dry_run_capable_and_idempotent():
    payload = sample_payload()

    dry_run_report = import_payload(payload, dry_run=True)
    assert dry_run_report["dry_run"] is True
    assert User.objects.count() == 0

    first_report = import_payload(payload)
    second_report = import_payload(payload)

    assert first_report["counts"] == second_report["counts"]
    assert Role.objects.count() == 1
    assert User.objects.count() == 1
    assert Project.objects.count() == 1
    assert ProjectMember.objects.count() == 1
    assert TaskStatus.objects.count() == 1
    assert Task.objects.count() == 1
    assert Notification.objects.count() == 1
    assert Preference.objects.count() == 1
    assert ReportMessage.objects.count() == 1


def test_canonical_hash_is_stable_regardless_of_row_order():
    rows = [{"id": 2, "name": "B"}, {"id": 1, "name": "A"}]

    assert canonical_table_hash(rows) == canonical_table_hash(list(reversed(rows)))
