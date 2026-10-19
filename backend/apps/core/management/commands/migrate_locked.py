from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


LOCK_ID = 1_410_224_013


class Command(BaseCommand):
    help = "Apply Django migrations while holding a PostgreSQL advisory lock"

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("migrate_locked requires PostgreSQL")

        database = options.get("database", "default")
        verbosity = options.get("verbosity", 1)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_lock(%s)", [LOCK_ID])

        try:
            call_command(
                "migrate",
                database=database,
                interactive=False,
                verbosity=verbosity,
            )
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])

        self.stdout.write(self.style.SUCCESS("Migrations applied with advisory lock"))
