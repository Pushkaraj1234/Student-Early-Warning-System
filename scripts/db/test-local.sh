#!/usr/bin/env bash
# Local database verification for SEWS (no Docker required).
#
# 1. Recreates a throwaway database on a local PostgreSQL cluster.
# 2. Applies the Supabase emulation shim (scripts/db/supabase_local_shim.sql).
# 3. Applies every migration in supabase/migrations in order — TWICE, to prove the
#    migrations are idempotent.
# 4. Applies supabase/seed.sql (synthetic data only).
# 5. Runs every pgTAP file in supabase/tests/database and fails on any failure,
#    missing test, or plan mismatch.
#
# The same pgTAP files run unchanged under `supabase test db` on a real Supabase stack.
#
# Environment (defaults suit the disposable cluster described in README.md):
#   PGBIN   directory containing psql         (default: psql on PATH)
#   PGHOST  (default localhost)   PGPORT (default 54330)   PGUSER (default postgres)
#   SEWS_TEST_DB  database name to (re)create (default sews_test)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PSQL="${PGBIN:+$PGBIN/}psql"
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-54330}"
export PGUSER="${PGUSER:-postgres}"
export PGOPTIONS="${PGOPTIONS:--c client_min_messages=warning}"
DB="${SEWS_TEST_DB:-sews_test}"

if [[ ! "$DB" =~ ^[a-z_][a-z0-9_]*$ ]]; then
  echo "Refusing unsafe database name: $DB" >&2
  exit 2
fi

run_sql_file() {
  "$PSQL" -X -q -v ON_ERROR_STOP=1 --single-transaction -d "$DB" -f "$1" >/dev/null
}

echo "==> Recreating database $DB on $PGHOST:$PGPORT"
"$PSQL" -X -q -v ON_ERROR_STOP=1 -d postgres -c "drop database if exists $DB with (force);" -c "create database $DB;"
"$PSQL" -X -q -v ON_ERROR_STOP=1 -d postgres \
  -c "alter database $DB set search_path = \"\$user\", public, extensions;"

echo "==> Applying Supabase emulation shim"
run_sql_file "$ROOT/scripts/db/supabase_local_shim.sql"

shopt -s nullglob
migrations=("$ROOT"/supabase/migrations/*.sql)
if [[ ${#migrations[@]} -eq 0 ]]; then
  echo "No migrations found" >&2
  exit 1
fi

for pass in 1 2; do
  echo "==> Applying ${#migrations[@]} migrations (pass $pass of 2)"
  for f in "${migrations[@]}"; do
    run_sql_file "$f"
  done
done

if [[ -f "$ROOT/supabase/seed.sql" ]]; then
  echo "==> Applying seed.sql"
  run_sql_file "$ROOT/supabase/seed.sql"
fi

echo "==> Running pgTAP tests"
tests=("$ROOT"/supabase/tests/database/*.sql)
if [[ ${#tests[@]} -eq 0 ]]; then
  echo "No tests found" >&2
  exit 1
fi

total_files=0
failed_files=0
total_asserts=0
for t in "${tests[@]}"; do
  total_files=$((total_files + 1))
  name="$(basename "$t")"
  set +e
  out="$("$PSQL" -X -A -t -q -v ON_ERROR_STOP=1 -d "$DB" -f "$t" 2>&1)"
  status=$?
  set -e

  planned="$(printf '%s\n' "$out" | sed -n 's/^1\.\.\([0-9][0-9]*\)$/\1/p' | head -n1)"
  passed="$(printf '%s\n' "$out" | grep -c '^ok ' || true)"
  failed="$(printf '%s\n' "$out" | grep -c '^not ok ' || true)"

  if [[ $status -ne 0 || -z "$planned" || "$failed" -ne 0 || "$passed" -ne "$planned" ]]; then
    failed_files=$((failed_files + 1))
    echo "FAIL $name (exit=$status planned=${planned:-none} ok=$passed not_ok=$failed)"
    printf '%s\n' "$out" | grep -E '^(not ok|#|psql|ERROR)' | head -n 40 || true
  else
    total_asserts=$((total_asserts + passed))
    echo "ok   $name ($passed assertions)"
  fi
done

echo "==> $((total_files - failed_files))/$total_files test files passed, $total_asserts assertions"
[[ $failed_files -eq 0 ]]
