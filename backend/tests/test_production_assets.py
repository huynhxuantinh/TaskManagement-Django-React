from pathlib import Path

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_production_compose_keeps_data_services_private_and_migrations_one_shot():
    compose_path = REPOSITORY_ROOT / "infra" / "compose.prod.yaml"
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = compose["services"]

    assert {"db", "migration", "backend", "proxy", "backup", "restore"} <= set(
        services
    )
    assert "ports" not in services["db"]
    assert "ports" not in services["backend"]
    assert "migrate_locked" in " ".join(services["migration"]["command"])
    assert services["migration"]["restart"] == "no"
    assert services["backend"]["depends_on"]["migration"]["condition"] == (
        "service_completed_successfully"
    )
    assert services["backend"]["deploy"]["replicas"] == 2
    assert services["backend"]["read_only"] is True
    assert compose["networks"]["private"]["internal"] is True


def test_production_images_build_assets_and_drop_root():
    backend = (REPOSITORY_ROOT / "backend" / "Dockerfile.prod").read_text(
        encoding="utf-8"
    )
    frontend = (REPOSITORY_ROOT / "frontend" / "Dockerfile.prod").read_text(
        encoding="utf-8"
    )

    assert "USER app" in backend
    assert "gunicorn" in backend
    assert "collectstatic" in backend
    assert "npm run build" in frontend
    assert "USER nginx" in frontend


def test_root_docker_context_excludes_secrets_data_and_build_artifacts():
    dockerignore = (REPOSITORY_ROOT / ".dockerignore").read_text(encoding="utf-8")

    for excluded in (".git", ".env", "node_modules", "exports", "backups"):
        assert excluded in dockerignore


def test_playwright_can_opt_into_self_signed_rehearsal_tls():
    config = (REPOSITORY_ROOT / "frontend" / "playwright.config.ts").read_text(
        encoding="utf-8"
    )

    assert "E2E_IGNORE_HTTPS_ERRORS" in config


def test_reverse_proxy_terminates_tls_and_serves_all_runtime_assets():
    nginx = (REPOSITORY_ROOT / "infra" / "nginx" / "nginx.conf").read_text(
        encoding="utf-8"
    )

    assert "listen 8443 ssl" in nginx
    assert "proxy_pass http://backend" in nginx
    assert "location /static/" in nginx
    assert "location /media/" in nginx
    assert "Strict-Transport-Security" in nginx
    assert "X-Forwarded-Proto https" in nginx
    assert "client_body_temp_path /tmp/client_temp" in nginx


def test_backup_and_restore_scripts_verify_checksums_and_protect_source_database():
    scripts = REPOSITORY_ROOT / "infra" / "scripts"
    backup = (scripts / "backup-postgres.sh").read_text(encoding="utf-8")
    restore = (scripts / "restore-postgres.sh").read_text(encoding="utf-8")

    assert "pg_dump" in backup
    assert "--format=custom" in backup
    assert "sha256sum" in backup
    assert "sha256sum -c" in restore
    assert "ALLOW_RESTORE" in restore
    assert 'TARGET_DATABASE" = "$POSTGRES_DB' in restore
    assert "pg_restore" in restore
