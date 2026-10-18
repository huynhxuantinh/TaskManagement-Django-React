import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from django.core.management.color import no_style
from django.db import connection, transaction

from apps.accounts.models import Role, User
from apps.notifications.models import Notification, NotificationType, Preference
from apps.projects.models import Project, ProjectMember
from apps.reports.models import ReportMessage
from apps.tasks.models import Task, TaskStatus

LEGACY_TIME_ZONE = ZoneInfo("Asia/Saigon")
TABLE_NAMES = (
    "roles",
    "users",
    "projects",
    "project_members",
    "task_statuses",
    "tasks",
    "notifications",
    "preferences",
    "reports",
)

ROLE_CODES = {
    "admin": Role.Code.ADMIN,
    "manager": Role.Code.MANAGER,
    "employee": Role.Code.EMPLOYEE,
}
STATUS_CODES = {
    "to do": TaskStatus.Code.TODO,
    "in progress": TaskStatus.Code.IN_PROGRESS,
    "completed": TaskStatus.Code.COMPLETED,
    "on hold": TaskStatus.Code.ON_HOLD,
}
NOTIFICATION_TYPES = {
    0: NotificationType.GENERAL,
    1: NotificationType.TASK_ASSIGNED,
    2: NotificationType.STATUS_CHANGED,
    3: NotificationType.PROJECT_ADDED,
    4: NotificationType.DEADLINE_APPROACHING,
    "GENERAL": NotificationType.GENERAL,
    "TASK_ASSIGNED": NotificationType.TASK_ASSIGNED,
    "STATUS_CHANGED": NotificationType.STATUS_CHANGED,
    "PROJECT_ADDED": NotificationType.PROJECT_ADDED,
    "DEADLINE_APPROACHING": NotificationType.DEADLINE_APPROACHING,
}


class LegacyDataValidationError(ValueError):
    pass


def legacy_datetime_to_utc(value: str | datetime) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=LEGACY_TIME_ZONE)
    return parsed.astimezone(timezone.utc)


def parse_date(value: str | date | None) -> date | None:
    if value in (None, ""):
        return None
    return date.fromisoformat(value) if isinstance(value, str) else value


def datetime_text(value: str | datetime) -> str:
    return legacy_datetime_to_utc(value).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def canonical_table_hash(rows: list[dict[str, Any]]) -> str:
    canonical_rows = [
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    ]
    content = "".join(f"{row}\n" for row in sorted(canonical_rows))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def role_code(name: str) -> str:
    try:
        return ROLE_CODES[name.strip().casefold()]
    except KeyError as error:
        raise LegacyDataValidationError(f"Unmapped role: {name}") from error


def status_code(name: str) -> str:
    try:
        return STATUS_CODES[name.strip().casefold()]
    except KeyError as error:
        raise LegacyDataValidationError(f"Unmapped task status: {name}") from error


def notification_type(value: int | str) -> str:
    key = value.upper() if isinstance(value, str) else value
    try:
        return NOTIFICATION_TYPES[key]
    except KeyError as error:
        raise LegacyDataValidationError(f"Unmapped notification type: {value}") from error


def validate_payload(payload: dict[str, list[dict[str, Any]]]) -> None:
    errors: list[str] = []
    missing = [table for table in TABLE_NAMES if table not in payload]
    if missing:
        errors.append(f"Missing tables: {', '.join(missing)}")

    users = payload.get("users", [])
    emails: set[str] = set()
    for row in users:
        email = row["email"].strip().casefold()
        if email in emails:
            errors.append(f"Duplicate email: {row['email']}")
        emails.add(email)

    role_ids = {row["legacy_id"] for row in payload.get("roles", [])}
    user_ids = {row["id"] for row in users}
    project_ids = {row["id"] for row in payload.get("projects", [])}
    status_ids = {row["legacy_id"] for row in payload.get("task_statuses", [])}

    for row in payload.get("roles", []):
        try:
            role_code(row["name"])
        except LegacyDataValidationError as error:
            errors.append(str(error))
    for row in payload.get("task_statuses", []):
        try:
            status_code(row["name"])
        except LegacyDataValidationError as error:
            errors.append(str(error))
    for row in users:
        if row["role_legacy_id"] not in role_ids:
            errors.append(f"Orphan user role: user {row['id']}")
    for row in payload.get("projects", []):
        if row["creator_id"] not in user_ids:
            errors.append(f"Orphan project creator: project {row['id']}")
    for row in payload.get("project_members", []):
        if row["project_id"] not in project_ids or row["user_id"] not in user_ids:
            errors.append(f"Orphan project member: {row['id']}")
    for row in payload.get("tasks", []):
        if row["project_id"] not in project_ids:
            errors.append(f"Orphan task project: task {row['id']}")
        if row.get("assignee_id") is not None and row["assignee_id"] not in user_ids:
            errors.append(f"Orphan task assignee: task {row['id']}")
        if row["status_legacy_id"] not in status_ids:
            errors.append(f"Orphan task status: task {row['id']}")
        if row["priority"] not in (1, 2, 3):
            errors.append(f"Invalid task priority: task {row['id']}")

    seen_preferences: set[tuple[int, str]] = set()
    for table in ("notifications", "preferences"):
        for row in payload.get(table, []):
            if row["user_id"] not in user_ids:
                errors.append(f"Orphan {table} user: {row['id']}")
            try:
                mapped_type = notification_type(row["type"])
            except LegacyDataValidationError as error:
                errors.append(str(error))
                continue
            if table == "preferences":
                key = (row["user_id"], mapped_type)
                if key in seen_preferences:
                    errors.append(f"Duplicate preference: user {row['user_id']} {mapped_type}")
                seen_preferences.add(key)

    for row in payload.get("reports", []):
        if row["project_id"] not in project_ids:
            errors.append(f"Orphan report project: report {row['id']}")
        if row["sender_id"] not in user_ids or row["receiver_id"] not in user_ids:
            errors.append(f"Orphan report user: report {row['id']}")

    memberships = {
        (row["project_id"], row["user_id"])
        for row in payload.get("project_members", [])
    }
    for row in payload.get("projects", []):
        if (row["id"], row["creator_id"]) not in memberships:
            errors.append(f"Project creator is not a member: project {row['id']}")

    if errors:
        raise LegacyDataValidationError("; ".join(errors))


def target_rows_from_payload(payload: dict[str, list[dict[str, Any]]]):
    return {
        "roles": [
            {**row, "code": role_code(row["name"])} for row in payload["roles"]
        ],
        "users": [
            {
                **row,
                "email": row["email"].strip().lower(),
                "avatar": row.get("avatar") or "",
                "created_at": datetime_text(row["created_at"]),
            }
            for row in payload["users"]
        ],
        "projects": [
            {
                **row,
                "description": row.get("description") or "",
                "created_at": datetime_text(row["created_at"]),
            }
            for row in payload["projects"]
        ],
        "project_members": [
            {**row, "joined_at": datetime_text(row["joined_at"])}
            for row in payload["project_members"]
        ],
        "task_statuses": [
            {**row, "code": status_code(row["name"])}
            for row in payload["task_statuses"]
        ],
        "tasks": [
            {
                **row,
                "description": row.get("description") or "",
                "created_at": datetime_text(row["created_at"]),
            }
            for row in payload["tasks"]
        ],
        "notifications": [
            {
                **row,
                "type": notification_type(row["type"]),
                "created_at": datetime_text(row["created_at"]),
            }
            for row in payload["notifications"]
        ],
        "preferences": [
            {**row, "type": notification_type(row["type"])}
            for row in payload["preferences"]
        ],
        "reports": [
            {**row, "created_at": datetime_text(row["created_at"])}
            for row in payload["reports"]
        ],
    }


def payload_manifest(payload: dict[str, list[dict[str, Any]]]):
    target_rows = target_rows_from_payload(payload)
    return {
        "counts": {table: len(rows) for table, rows in target_rows.items()},
        "hashes": {
            table: canonical_table_hash(rows) for table, rows in target_rows.items()
        },
    }


def database_rows():
    return {
        "roles": [
            {"legacy_id": row.legacy_id, "name": row.name, "code": row.code}
            for row in Role.objects.all()
        ],
        "users": [
            {
                "id": row.id,
                "full_name": row.full_name,
                "email": row.email,
                "password": row.password,
                "role_legacy_id": row.role.legacy_id,
                "is_active": row.is_active,
                "created_at": datetime_text(row.created_at),
                "avatar": row.avatar,
            }
            for row in User.objects.select_related("role")
        ],
        "projects": [
            {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "start_date": row.start_date.isoformat() if row.start_date else None,
                "end_date": row.end_date.isoformat() if row.end_date else None,
                "creator_id": row.creator_id,
                "is_deleted": row.is_deleted,
                "created_at": datetime_text(row.created_at),
            }
            for row in Project.objects.all()
        ],
        "project_members": [
            {
                "id": row.id,
                "project_id": row.project_id,
                "user_id": row.user_id,
                "joined_at": datetime_text(row.joined_at),
            }
            for row in ProjectMember.objects.all()
        ],
        "task_statuses": [
            {"legacy_id": row.legacy_id, "name": row.name, "code": row.code}
            for row in TaskStatus.objects.all()
        ],
        "tasks": [
            {
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "project_id": row.project_id,
                "assignee_id": row.assignee_id,
                "status_legacy_id": row.status.legacy_id,
                "priority": row.priority,
                "deadline": row.deadline.isoformat() if row.deadline else None,
                "is_deleted": row.is_deleted,
                "created_at": datetime_text(row.created_at),
            }
            for row in Task.objects.select_related("status")
        ],
        "notifications": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "message": row.message,
                "type": row.type,
                "is_priority": row.is_priority,
                "is_read": row.is_read,
                "created_at": datetime_text(row.created_at),
            }
            for row in Notification.objects.all()
        ],
        "preferences": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "type": row.type,
                "is_priority": row.is_priority,
            }
            for row in Preference.objects.all()
        ],
        "reports": [
            {
                "id": row.id,
                "project_id": row.project_id,
                "sender_id": row.sender_id,
                "receiver_id": row.receiver_id,
                "title": row.title,
                "content": row.content,
                "is_read": row.is_read,
                "created_at": datetime_text(row.created_at),
            }
            for row in ReportMessage.objects.all()
        ],
    }


def database_manifest():
    rows = database_rows()
    return {
        "counts": {table: len(values) for table, values in rows.items()},
        "hashes": {
            table: canonical_table_hash(values) for table, values in rows.items()
        },
    }


def _reset_sequences():
    models = [
        Role,
        User,
        Project,
        ProjectMember,
        TaskStatus,
        Task,
        Notification,
        Preference,
        ReportMessage,
    ]
    statements = connection.ops.sequence_reset_sql(no_style(), models)
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def _database_counts():
    return {
        "roles": Role.objects.count(),
        "users": User.objects.count(),
        "projects": Project.objects.count(),
        "project_members": ProjectMember.objects.count(),
        "task_statuses": TaskStatus.objects.count(),
        "tasks": Task.objects.count(),
        "notifications": Notification.objects.count(),
        "preferences": Preference.objects.count(),
        "reports": ReportMessage.objects.count(),
    }


def import_payload(payload: dict[str, list[dict[str, Any]]], dry_run: bool = False):
    validate_payload(payload)

    with transaction.atomic():
        roles = {}
        for row in payload["roles"]:
            role, _ = Role.objects.update_or_create(
                legacy_id=row["legacy_id"],
                defaults={"code": role_code(row["name"]), "name": row["name"]},
            )
            roles[row["legacy_id"]] = role

        for row in payload["users"]:
            User.objects.update_or_create(
                id=row["id"],
                defaults={
                    "full_name": row["full_name"],
                    "email": row["email"].strip().lower(),
                    "password": row["password"],
                    "role": roles[row["role_legacy_id"]],
                    "is_active": row["is_active"],
                    "is_staff": False,
                    "is_superuser": False,
                    "created_at": legacy_datetime_to_utc(row["created_at"]),
                    "avatar": row.get("avatar") or "",
                },
            )

        for row in payload["projects"]:
            Project.objects.update_or_create(
                id=row["id"],
                defaults={
                    "name": row["name"],
                    "description": row.get("description") or "",
                    "start_date": parse_date(row.get("start_date")),
                    "end_date": parse_date(row.get("end_date")),
                    "creator_id": row["creator_id"],
                    "is_deleted": row["is_deleted"],
                    "created_at": legacy_datetime_to_utc(row["created_at"]),
                },
            )

        for row in payload["project_members"]:
            ProjectMember.objects.update_or_create(
                id=row["id"],
                defaults={
                    "project_id": row["project_id"],
                    "user_id": row["user_id"],
                    "joined_at": legacy_datetime_to_utc(row["joined_at"]),
                },
            )

        statuses = {}
        for row in payload["task_statuses"]:
            task_status, _ = TaskStatus.objects.update_or_create(
                legacy_id=row["legacy_id"],
                defaults={"code": status_code(row["name"]), "name": row["name"]},
            )
            statuses[row["legacy_id"]] = task_status

        for row in payload["tasks"]:
            Task.objects.update_or_create(
                id=row["id"],
                defaults={
                    "title": row["title"],
                    "description": row.get("description") or "",
                    "project_id": row["project_id"],
                    "assignee_id": row.get("assignee_id"),
                    "status": statuses[row["status_legacy_id"]],
                    "priority": row["priority"],
                    "deadline": parse_date(row.get("deadline")),
                    "is_deleted": row["is_deleted"],
                    "created_at": legacy_datetime_to_utc(row["created_at"]),
                },
            )

        for row in payload["notifications"]:
            Notification.objects.update_or_create(
                id=row["id"],
                defaults={
                    "user_id": row["user_id"],
                    "message": row["message"],
                    "type": notification_type(row["type"]),
                    "is_priority": row["is_priority"],
                    "is_read": row["is_read"],
                    "created_at": legacy_datetime_to_utc(row["created_at"]),
                },
            )

        for row in payload["preferences"]:
            Preference.objects.update_or_create(
                id=row["id"],
                defaults={
                    "user_id": row["user_id"],
                    "type": notification_type(row["type"]),
                    "is_priority": row["is_priority"],
                },
            )

        for row in payload["reports"]:
            ReportMessage.objects.update_or_create(
                id=row["id"],
                defaults={
                    "project_id": row["project_id"],
                    "sender_id": row["sender_id"],
                    "receiver_id": row["receiver_id"],
                    "title": row["title"],
                    "content": row["content"],
                    "is_read": row["is_read"],
                    "created_at": legacy_datetime_to_utc(row["created_at"]),
                },
            )

        _reset_sequences()
        report = {"dry_run": dry_run, "counts": _database_counts()}
        if dry_run:
            transaction.set_rollback(True)
        return report
