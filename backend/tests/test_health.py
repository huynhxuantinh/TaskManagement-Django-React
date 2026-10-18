import pytest
from django.db import DatabaseError, connection
from django.test import Client


def test_health_is_independent_from_database(monkeypatch):
    monkeypatch.setattr(
        connection,
        "cursor",
        lambda: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )

    response = Client().get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_ready_confirms_database_connection():
    response = Client().get("/ready/")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_ready_reports_unavailable_database(monkeypatch):
    monkeypatch.setattr(
        connection,
        "cursor",
        lambda: (_ for _ in ()).throw(DatabaseError("database unavailable")),
    )

    response = Client().get("/ready/")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "database": "unavailable",
    }
