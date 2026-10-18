import base64
import json
import os

import pytest
from django.core.management import call_command

from apps.accounts.models import User
from apps.core.crypto import decrypt_bytes, encrypt_bytes
from apps.core.legacy_import import payload_manifest
from tests.test_legacy_import import sample_payload


@pytest.mark.django_db
def test_import_command_decrypts_bundle_and_honors_dry_run(tmp_path, monkeypatch):
    key = os.urandom(32)
    monkeypatch.setenv("LEGACY_EXPORT_KEY", base64.b64encode(key).decode("ascii"))
    payload = sample_payload()
    bundle_path = tmp_path / "legacy-export.tmx"
    bundle_path.write_bytes(encrypt_bytes(json.dumps(payload).encode("utf-8"), key))
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(payload_manifest(payload)), encoding="utf-8")

    call_command(
        "import_legacy",
        bundle=str(bundle_path),
        manifest=str(manifest_path),
        dry_run=True,
    )

    assert User.objects.count() == 0


def test_aes_bundle_round_trip_and_rejects_wrong_key():
    key = os.urandom(32)
    encrypted = encrypt_bytes(b"sensitive legacy data", key)

    assert decrypt_bytes(encrypted, key) == b"sensitive legacy data"
    with pytest.raises(ValueError, match="decrypt"):
        decrypt_bytes(encrypted, os.urandom(32))
