from types import SimpleNamespace

import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.accounts.permissions import IsAdmin, IsAdminOrManager, IsSelfOrAdmin
from apps.accounts.throttles import LoginRateThrottle


AUTH_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]


@pytest.fixture
def roles(db):
    return {
        code: Role.objects.create(code=code, name=label)
        for code, label in Role.Code.choices
    }


def create_user(roles, role=Role.Code.EMPLOYEE, **values):
    values.setdefault("email", f"{role.lower()}@example.com")
    values.setdefault("full_name", role.title())
    values.setdefault("password", "StrongPass@123")
    return User.objects.create_user(role=roles[role], **values)


def login(client, email, password):
    return client.post(
        "/api/v1/auth/login/",
        {"email": email, "password": password},
        format="json",
    )


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=AUTH_HASHERS)
def test_login_accepts_username_and_keeps_password_hashed(roles):
    user = create_user(
        roles,
        role=Role.Code.ADMIN,
        username="admin",
        email="admin@task.local",
        password="123",
    )

    response = login(APIClient(), "admin", "123")

    assert response.status_code == 200
    assert response.data["data"]["user"]["username"] == "admin"
    user.refresh_from_db()
    assert user.password != "123"
    assert user.check_password("123")


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=AUTH_HASHERS)
def test_refresh_rotates_token_rejects_reuse_and_requires_csrf(roles):
    user = create_user(roles)
    client = APIClient(enforce_csrf_checks=True)
    assert login(client, user.email, "StrongPass@123").status_code == 200
    old_refresh = client.cookies["refresh_token"].value

    missing_csrf = client.post("/api/v1/auth/refresh/", {}, format="json")
    assert missing_csrf.status_code == 403

    csrf = client.cookies["csrftoken"].value
    refreshed = client.post(
        "/api/v1/auth/refresh/", {}, format="json", HTTP_X_CSRFTOKEN=csrf
    )
    assert refreshed.status_code == 200
    assert refreshed.data["data"]["access"]
    assert client.cookies["refresh_token"].value != old_refresh

    client.cookies["refresh_token"] = old_refresh
    reused = client.post(
        "/api/v1/auth/refresh/", {}, format="json", HTTP_X_CSRFTOKEN=csrf
    )
    assert reused.status_code == 401


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=AUTH_HASHERS)
def test_logout_blacklists_refresh_and_clears_cookie(roles):
    user = create_user(roles)
    client = APIClient(enforce_csrf_checks=True)
    signed_in = login(client, user.email, "StrongPass@123")
    access = signed_in.data["data"]["access"]
    refresh = client.cookies["refresh_token"].value
    csrf = client.cookies["csrftoken"].value
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/auth/logout/", {}, format="json", HTTP_X_CSRFTOKEN=csrf
    )

    assert response.status_code == 200
    assert response.cookies["refresh_token"]["max-age"] == 0
    client.credentials()
    client.cookies["refresh_token"] = refresh
    assert (
        client.post(
            "/api/v1/auth/refresh/", {}, format="json", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 401
    )


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=AUTH_HASHERS)
def test_change_password_checks_current_password_and_revokes_refresh_sessions(roles):
    user = create_user(roles)
    client = APIClient(enforce_csrf_checks=True)
    signed_in = login(client, user.email, "StrongPass@123")
    access = signed_in.data["data"]["access"]
    old_refresh = client.cookies["refresh_token"].value
    csrf = client.cookies["csrftoken"].value
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    wrong = client.post(
        "/api/v1/auth/change-password/",
        {"current_password": "wrong", "new_password": "NewStrongPass@456"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert wrong.status_code == 400

    changed = client.post(
        "/api/v1/auth/change-password/",
        {
            "current_password": "StrongPass@123",
            "new_password": "NewStrongPass@456",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert changed.status_code == 200
    user.refresh_from_db()
    assert user.check_password("NewStrongPass@456")
    assert user.password.startswith("argon2$")

    client.credentials()
    client.cookies["refresh_token"] = old_refresh
    assert (
        client.post(
            "/api/v1/auth/refresh/", {}, format="json", HTTP_X_CSRFTOKEN=csrf
        ).status_code
        == 401
    )


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=AUTH_HASHERS)
def test_deactivate_disables_account_and_existing_tokens(roles):
    user = create_user(roles)
    client = APIClient(enforce_csrf_checks=True)
    signed_in = login(client, user.email, "StrongPass@123")
    access = signed_in.data["data"]["access"]
    csrf = client.cookies["csrftoken"].value
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    response = client.post(
        "/api/v1/auth/deactivate/",
        {"password": "StrongPass@123"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.is_active is False
    assert client.get("/api/v1/auth/me/").status_code == 401


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=AUTH_HASHERS)
def test_register_always_creates_employee_and_rejects_duplicate_email(roles):
    client = APIClient()
    payload = {
        "email": "new@example.com",
        "full_name": "New User",
        "password": "StrongPass@123",
        "role": "ADMIN",
    }

    created = client.post("/api/v1/auth/register/", payload, format="json")
    duplicate = client.post("/api/v1/auth/register/", payload, format="json")

    assert created.status_code == 201
    assert created.data["data"]["role"] == "EMPLOYEE"
    assert User.objects.get(email="new@example.com").role.code == "EMPLOYEE"
    assert duplicate.status_code == 409
    assert duplicate.data["success"] is False


@pytest.mark.django_db
@override_settings(PASSWORD_HASHERS=AUTH_HASHERS)
@pytest.mark.parametrize("role", list(Role.Code.values))
def test_me_uses_authenticated_identity_and_current_database_role(roles, role):
    user = create_user(roles, role=role)
    client = APIClient()
    signed_in = login(client, user.email, "StrongPass@123")
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {signed_in.data['data']['access']}"
    )

    response = client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    assert response.data["data"]["id"] == user.id
    assert response.data["data"]["role"] == role
    assert role in response.data["data"]["permissions"]


@pytest.mark.django_db
def test_auth_errors_use_contract_envelope_and_me_rejects_anonymous(roles):
    invalid = login(APIClient(), "missing@example.com", "wrong")
    anonymous = APIClient().get("/api/v1/auth/me/")

    assert invalid.status_code == 401
    assert invalid.data == {
        "success": False,
        "message": "Tên đăng nhập hoặc mật khẩu không đúng.",
        "data": None,
        "errors": {},
    }
    assert anonymous.status_code == 401
    assert anonymous.data["success"] is False


def test_openapi_exposes_bearer_auth_schema():
    response = APIClient().get("/api/schema/")

    assert response.status_code == 200
    assert "jwtAuth" in response.data["components"]["securitySchemes"]


@pytest.mark.django_db
def test_rbac_primitives_cover_admin_manager_employee_and_self(roles):
    admin = create_user(roles, role=Role.Code.ADMIN)
    manager = create_user(roles, role=Role.Code.MANAGER)
    employee = create_user(roles, role=Role.Code.EMPLOYEE)
    view = SimpleNamespace()

    assert IsAdmin().has_permission(SimpleNamespace(user=admin), view)
    assert not IsAdmin().has_permission(SimpleNamespace(user=manager), view)
    assert IsAdminOrManager().has_permission(SimpleNamespace(user=manager), view)
    assert not IsAdminOrManager().has_permission(SimpleNamespace(user=employee), view)
    assert IsSelfOrAdmin().has_object_permission(
        SimpleNamespace(user=employee), view, employee
    )
    assert IsSelfOrAdmin().has_object_permission(
        SimpleNamespace(user=admin), view, employee
    )
    assert not IsSelfOrAdmin().has_object_permission(
        SimpleNamespace(user=manager), view, employee
    )


@pytest.mark.django_db
def test_login_is_rate_limited_per_ip_and_email(roles, monkeypatch):
    cache.clear()
    monkeypatch.setattr(LoginRateThrottle, "get_rate", lambda _self: "2/min")
    client = APIClient()

    first = login(client, "missing@example.com", "wrong")
    second = login(client, "missing@example.com", "wrong")
    limited = login(client, "missing@example.com", "wrong")

    assert first.status_code == 401
    assert second.status_code == 401
    assert limited.status_code == 429
