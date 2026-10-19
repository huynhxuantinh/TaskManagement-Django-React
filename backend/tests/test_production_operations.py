import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from django.core.management.base import CommandError


BACKEND_DIR = Path(__file__).resolve().parents[1]
PRODUCTION_ENV_KEYS = (
    "DJANGO_SECRET_KEY",
    "DJANGO_ALLOWED_HOSTS",
    "POSTGRES_PASSWORD",
    "CORS_ALLOWED_ORIGINS",
    "CSRF_TRUSTED_ORIGINS",
)


def run_production_settings(**overrides):
    environment = os.environ.copy()
    for key in PRODUCTION_ENV_KEYS:
        environment.pop(key, None)
    environment.update(overrides)
    environment["DJANGO_SETTINGS_MODULE"] = "config.settings.production"
    script = """
import json
from django.conf import settings

print(json.dumps({
    "allowed_hosts": settings.ALLOWED_HOSTS,
    "cors": settings.CORS_ALLOWED_ORIGINS,
    "debug": settings.DEBUG,
    "proxy_header": settings.SECURE_PROXY_SSL_HEADER,
    "secure_auth_cookie": settings.AUTH_COOKIE_SECURE,
    "secure_csrf_cookie": settings.CSRF_COOKIE_SECURE,
    "secure_session_cookie": settings.SESSION_COOKIE_SECURE,
    "ssl_redirect": settings.SECURE_SSL_REDIRECT,
}))
"""
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("environment", "expected_error"),
    [
        (
            {
                "DJANGO_ALLOWED_HOSTS": "tasks.example.test",
                "POSTGRES_PASSWORD": "database-only-secret",
            },
            "DJANGO_SECRET_KEY",
        ),
        (
            {
                "DJANGO_SECRET_KEY": "s" * 64,
                "POSTGRES_PASSWORD": "database-only-secret",
            },
            "DJANGO_ALLOWED_HOSTS",
        ),
        (
            {
                "DJANGO_SECRET_KEY": "s" * 64,
                "DJANGO_ALLOWED_HOSTS": "tasks.example.test",
            },
            "POSTGRES_PASSWORD",
        ),
    ],
)
def test_production_settings_require_explicit_secrets_and_hosts(
    environment, expected_error
):
    result = run_production_settings(**environment)

    assert result.returncode != 0
    assert expected_error in result.stderr


def test_production_settings_enable_https_proxy_security_and_same_origin():
    result = run_production_settings(
        DJANGO_SECRET_KEY="s" * 64,
        DJANGO_ALLOWED_HOSTS="tasks.example.test",
        POSTGRES_PASSWORD="database-only-secret",
    )

    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings == {
        "allowed_hosts": ["tasks.example.test"],
        "cors": [],
        "debug": False,
        "proxy_header": ["HTTP_X_FORWARDED_PROTO", "https"],
        "secure_auth_cookie": True,
        "secure_csrf_cookie": True,
        "secure_session_cookie": True,
        "ssl_redirect": True,
    }


def test_locked_migration_holds_and_releases_postgres_advisory_lock(monkeypatch):
    from apps.core.management.commands import migrate_locked

    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    monkeypatch.setattr(migrate_locked.connection, "vendor", "postgresql")
    monkeypatch.setattr(migrate_locked.connection, "cursor", lambda: cursor)
    migrate = MagicMock()
    monkeypatch.setattr(migrate_locked, "call_command", migrate)

    migrate_locked.Command().handle(database="default", verbosity=0)

    assert cursor.execute.call_args_list == [
        call("SELECT pg_advisory_lock(%s)", [migrate_locked.LOCK_ID]),
        call("SELECT pg_advisory_unlock(%s)", [migrate_locked.LOCK_ID]),
    ]
    migrate.assert_called_once_with(
        "migrate", database="default", interactive=False, verbosity=0
    )


def test_locked_migration_releases_lock_when_migrate_fails(monkeypatch):
    from apps.core.management.commands import migrate_locked

    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    monkeypatch.setattr(migrate_locked.connection, "vendor", "postgresql")
    monkeypatch.setattr(migrate_locked.connection, "cursor", lambda: cursor)
    monkeypatch.setattr(
        migrate_locked,
        "call_command",
        MagicMock(side_effect=CommandError("migration failed")),
    )

    with pytest.raises(CommandError, match="migration failed"):
        migrate_locked.Command().handle(database="default", verbosity=0)

    cursor.execute.assert_called_with(
        "SELECT pg_advisory_unlock(%s)", [migrate_locked.LOCK_ID]
    )
