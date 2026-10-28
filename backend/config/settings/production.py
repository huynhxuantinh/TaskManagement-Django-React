import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def required_environment(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be set in production")
    return value


SECRET_KEY = required_environment("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith(("unsafe-", "change-")):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be a strong production-only value"
    )

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must contain explicit production hosts"
    )

database_password = required_environment("POSTGRES_PASSWORD")
if database_password == "task_management_dev":
    raise ImproperlyConfigured("POSTGRES_PASSWORD must not use the dev default")
DATABASES["default"]["PASSWORD"] = database_password  # noqa: F405

cache_url = required_environment("CACHE_URL")
if not cache_url.startswith(("redis://", "rediss://")):
    raise ImproperlyConfigured("CACHE_URL must use redis:// or rediss://")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": cache_url,
        "KEY_PREFIX": "task-management",
        "TIMEOUT": 300,
        "OPTIONS": {
            "socket_connect_timeout": 3,
            "socket_timeout": 3,
        },
    }
}

DEBUG = False
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS")  # noqa: F405
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")  # noqa: F405
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "true").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
AUTH_COOKIE_SECURE = True
ALLOW_PUBLIC_REGISTRATION = False
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"
