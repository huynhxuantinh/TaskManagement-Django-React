#!/bin/sh
set -eu

: "${PGHOST:?PGHOST is required}"
: "${PGUSER:?PGUSER is required}"
: "${PGPASSWORD:?PGPASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"

OUTPUT_DIR="${1:-/backups}"
case "$POSTGRES_DB" in
    *[!A-Za-z0-9_]*) echo "POSTGRES_DB contains unsafe characters" >&2; exit 2 ;;
esac

umask 077
mkdir -p "$OUTPUT_DIR"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump_file="$OUTPUT_DIR/${POSTGRES_DB}_${timestamp}.dump"
partial_file="${dump_file}.partial"
trap 'rm -f "$partial_file"' EXIT

pg_dump \
    --dbname="$POSTGRES_DB" \
    --format=custom \
    --compress=9 \
    --no-owner \
    --no-privileges \
    --file="$partial_file"

pg_restore --list "$partial_file" > "${dump_file}.list"
mv "$partial_file" "$dump_file"
(
    cd "$OUTPUT_DIR"
    sha256sum "$(basename "$dump_file")" > "$(basename "$dump_file").sha256"
)

cat > "${dump_file}.json" <<EOF
{"database":"$POSTGRES_DB","created_at":"$timestamp","format":"postgres-custom","checksum":"sha256"}
EOF

trap - EXIT
printf '%s\n' "$dump_file"
