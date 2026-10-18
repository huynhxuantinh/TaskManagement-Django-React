import base64
import hashlib
import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.core.crypto import decrypt_bytes
from apps.core.legacy_import import database_manifest, import_payload, payload_manifest


class Command(BaseCommand):
    help = "Import an AES-256-GCM encrypted legacy SQL Server export"

    def add_arguments(self, parser):
        parser.add_argument("--bundle", required=True)
        parser.add_argument("--manifest", required=True)
        parser.add_argument("--key-env", default="LEGACY_EXPORT_KEY")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        key_text = os.getenv(options["key_env"])
        if not key_text:
            raise CommandError(f"Missing encryption key env: {options['key_env']}")
        try:
            key = base64.b64decode(key_text, validate=True)
            bundle_path = Path(options["bundle"]).resolve(strict=True)
            manifest_path = Path(options["manifest"]).resolve(strict=True)
            payload = json.loads(decrypt_bytes(bundle_path.read_bytes(), key))
            expected = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as error:
            raise CommandError(str(error)) from error

        actual_export = payload_manifest(payload)
        self._assert_manifest(expected, actual_export, "export")
        report = import_payload(payload, dry_run=options["dry_run"])

        if not options["dry_run"]:
            self._import_media(expected, manifest_path.parent, key)
            self._assert_manifest(expected, database_manifest(), "database")

        report["manifest_verified"] = True
        self.stdout.write(json.dumps(report, sort_keys=True))

    def _assert_manifest(self, expected, actual, source):
        for section in ("counts", "hashes"):
            if expected.get(section) != actual.get(section):
                raise CommandError(f"{source} {section} does not match manifest")

    def _import_media(self, manifest, export_dir: Path, key: bytes):
        media_root = Path(settings.MEDIA_ROOT).resolve()
        for item in manifest.get("media", []):
            encrypted_path = (export_dir / item["encrypted_file"]).resolve()
            if export_dir not in encrypted_path.parents:
                raise CommandError("Media export path escapes export directory")
            plaintext = decrypt_bytes(encrypted_path.read_bytes(), key)
            checksum = hashlib.sha256(plaintext).hexdigest()
            if checksum != item["sha256"]:
                raise CommandError(f"Media checksum mismatch: {item['destination']}")
            destination = (media_root / item["destination"]).resolve()
            if media_root not in destination.parents:
                raise CommandError("Media destination escapes MEDIA_ROOT")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            temporary.write_bytes(plaintext)
            temporary.replace(destination)
