import pytest
from django.db import connection
from django.test import Client


@pytest.mark.django_db
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
