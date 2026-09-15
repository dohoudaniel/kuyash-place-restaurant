#!/usr/bin/env bash
#
# Take a Postgres backup that can actually be restored (DEPLOYMENT.md §8).
#
#   DATABASE_URL=postgres://… ./scripts/backup-db.sh [output-dir]
#
# Writes kuyash-<UTC timestamp>.dump (pg_dump custom format) and a .sha256 next
# to it, then reads the dump's table of contents back to prove the file is a
# complete archive rather than a truncated one. The managed platform's daily
# backups and point-in-time recovery remain the primary copy; this is the
# portable copy you restore in a drill, keep off-platform, or take before a
# risky migration.
#
# Never commit the output: dumps hold customer data. backups/ is git-ignored.
#
set -euo pipefail

cd "$(dirname "$0")/.." || exit 2

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "❌ DATABASE_URL is not set." >&2
  exit 2
fi
case "$DATABASE_URL" in
  postgres://*|postgresql://*) ;;
  *)
    echo "❌ DATABASE_URL is not a Postgres URL. Local SQLite needs no dump: copy db.sqlite3." >&2
    exit 2
    ;;
esac

out_dir="${1:-backups}"
mkdir -p "$out_dir"
chmod 700 "$out_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump="$out_dir/kuyash-$stamp.dump"

umask 077
echo "→ Dumping to $dump"
# --no-owner/--no-privileges: restorable into a database owned by another role
# (a scratch database, a different platform).
pg_dump --dbname="$DATABASE_URL" --format=custom --compress=6 \
  --no-owner --no-privileges --file="$dump"

entries="$(pg_restore --list "$dump" | grep -cE '^[0-9]+;' || true)"
if [[ "$entries" -eq 0 ]]; then
  echo "❌ The dump has no entries. Do not rely on it." >&2
  exit 1
fi
if ! pg_restore --list "$dump" | grep -qE 'TABLE DATA .*django_migrations'; then
  echo "❌ The dump has no django_migrations data. It is not a Kuyash database." >&2
  exit 1
fi

(cd "$out_dir" && sha256sum "$(basename "$dump")" > "$(basename "$dump").sha256")

size="$(du -h "$dump" | cut -f1)"
echo "✅ Backup written: $dump ($size, $entries archive entries)"
echo "   Checksum:       $dump.sha256"
echo "   Prove it:       ./scripts/restore-drill.sh $dump <scratch database URL>"
