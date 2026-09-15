#!/usr/bin/env bash
#
# Restore a backup into a scratch database and prove it works (DEPLOYMENT.md §8).
#
#   ./scripts/restore-drill.sh <dump file> <scratch database URL> [--max-age-hours N]
#
# 1. Checks the dump against its .sha256, if one is present.
# 2. Refuses to touch the live database (the scratch URL must differ from
#    DATABASE_URL) or a scratch database that already has tables.
# 3. Restores with pg_restore, stopping at the first error.
# 4. Runs `manage.py verify_restore` against the restored copy: migrations
#    applied, order totals and lines add up, paid orders have payments, loyalty
#    balances match their ledger, staff 2FA secrets readable.
# 5. Prints a line to record in DEPLOYMENT.md §8 — the date a restore was last
#    proven.
#
# Run it with the same SECRET_KEY and settings as the environment the dump came
# from, so the staff two-factor check means something.
#
set -euo pipefail

cd "$(dirname "$0")/.." || exit 2

usage() {
  echo "usage: $0 <dump file> <scratch database URL> [--max-age-hours N]" >&2
  exit 2
}

[[ $# -ge 2 ]] || usage
dump="$1"
scratch="$2"
shift 2
verify_args=("$@")

[[ -f "$dump" ]] || { echo "❌ No such dump: $dump" >&2; exit 2; }
case "$scratch" in
  postgres://*|postgresql://*) ;;
  *) echo "❌ The scratch database must be a Postgres URL." >&2; exit 2 ;;
esac

# Compare without scheme spelling, credentials or query string: the same database
# reached as postgresql:// with another password and ?sslmode is still the live one.
strip() { sed -E 's#^postgres(ql)?://#postgres://#; s#^(postgres://)[^@/]*@#\1#; s#\?.*$##; s#/+$##' <<< "$1"; }
if [[ -n "${DATABASE_URL:-}" && "$(strip "$scratch")" == "$(strip "$DATABASE_URL")" ]]; then
  echo "❌ The scratch URL is DATABASE_URL. A drill never restores over the live database." >&2
  exit 2
fi

if [[ -f "$dump.sha256" ]]; then
  echo "→ Checking checksum"
  (cd "$(dirname "$dump")" && sha256sum --check --quiet "$(basename "$dump").sha256")
else
  echo "⚠️  No $dump.sha256 — integrity not checked."
fi

tables="$(psql "$scratch" --no-psqlrc --tuples-only --no-align \
  -c "select count(*) from information_schema.tables where table_schema = 'public'")"
if [[ "${tables//[[:space:]]/}" != "0" ]]; then
  echo "❌ The scratch database already has $tables table(s). Use an empty database." >&2
  exit 2
fi

started=$(date +%s)
echo "→ Restoring $(basename "$dump")"
pg_restore --dbname="$scratch" --no-owner --no-privileges --exit-on-error "$dump"

echo "→ Verifying the restored database"
python_bin="${PYTHON:-python}"
DATABASE_URL="$scratch" "$python_bin" manage.py verify_restore "${verify_args[@]}"

elapsed=$(( $(date +%s) - started ))
echo
echo "✅ Restore drill passed in ${elapsed}s."
echo "   Record in backend/docs/DEPLOYMENT.md §8:"
echo "   | $(date -u +%Y-%m-%d) | $(basename "$dump") | ${elapsed}s | <who> |"
