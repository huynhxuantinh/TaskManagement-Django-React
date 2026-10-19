#!/bin/sh
set -eu

: "${PGHOST:?PGHOST is required}"
: "${PGUSER:?PGUSER is required}"
: "${PGPASSWORD:?PGPASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${TARGET_DATABASE:?TARGET_DATABASE is required}"

if [ "${ALLOW_RESTORE:-}" != "YES" ]; then
    echo "Set ALLOW_RESTORE=YES to acknowledge creation of the restore database" >&2
    exit 2
fi
if [ "$TARGET_DATABASE" = "$POSTGRES_DB" ]; then
    echo "Refusing to restore over the source database" >&2
    exit 2
fi
case "$TARGET_DATABASE" in
    *[!A-Za-z0-9_]*) echo "TARGET_DATABASE contains unsafe characters" >&2; exit 2 ;;
esac

dump_file="${1:?usage: restore-postgres.sh /backups/file.dump}"
checksum_file="${dump_file}.sha256"
if [ ! -f "$dump_file" ] || [ ! -f "$checksum_file" ]; then
    echo "Dump or checksum file not found" >&2
    exit 2
fi

(
    cd "$(dirname "$dump_file")"
    sha256sum -c "$(basename "$checksum_file")"
)

database_exists="$(psql --dbname=postgres --tuples-only --no-align \
    --command="SELECT 1 FROM pg_database WHERE datname = '$TARGET_DATABASE'")"
if [ "$database_exists" = "1" ]; then
    table_count="$(psql --dbname="$TARGET_DATABASE" --tuples-only --no-align \
        --command="SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")"
    if [ "$table_count" != "0" ]; then
        echo "Refusing to restore into a non-empty database" >&2
        exit 2
    fi
else
    createdb "$TARGET_DATABASE"
fi

pg_restore \
    --dbname="$TARGET_DATABASE" \
    --exit-on-error \
    --single-transaction \
    --no-owner \
    --no-privileges \
    "$dump_file"

psql --dbname="$TARGET_DATABASE" --set=ON_ERROR_STOP=1 \
    --command="SELECT count(*) AS django_migrations FROM django_migrations;"
printf 'Restore completed: %s\n' "$TARGET_DATABASE"
