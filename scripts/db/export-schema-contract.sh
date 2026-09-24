#!/usr/bin/env bash
# Exports the verified public schema (tables → columns → type/nullability, and RPC
# signatures) to supabase/types/schema_contract.json.
#
# Why: `supabase gen types` has no Dart target and needs Docker locally. The mobile
# app's hand-written models are tested against this contract so they can never read
# a column that does not exist. Regenerate after every migration change:
#   bash scripts/db/test-local.sh && bash scripts/db/export-schema-contract.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PSQL="${PGBIN:+$PGBIN/}psql"
export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-54330}"
export PGUSER="${PGUSER:-postgres}"
DB="${SEWS_TEST_DB:-sews_test}"
OUT="$ROOT/supabase/types/schema_contract.json"

mkdir -p "$(dirname "$OUT")"

"$PSQL" -X -A -t -q -v ON_ERROR_STOP=1 -d "$DB" > "$OUT" <<'SQL'
select jsonb_pretty(jsonb_build_object(
  'generated_from', 'supabase/migrations (verified by scripts/db/test-local.sh)',
  'tables', (
    select jsonb_object_agg(t.table_name, t.columns order by t.table_name)
    from (
      select c.table_name,
             jsonb_agg(jsonb_build_object(
               'name', c.column_name,
               'type', c.data_type,
               'nullable', c.is_nullable = 'YES'
             ) order by c.ordinal_position) as columns
      from information_schema.columns c
      where c.table_schema = 'public'
      group by c.table_name
    ) t
  ),
  'rpc', (
    select jsonb_object_agg(p.proname, jsonb_build_object(
             'arguments', pg_get_function_arguments(p.oid),
             'returns', pg_get_function_result(p.oid)
           ) order by p.proname)
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname = 'public'
  )
));
SQL

echo "Wrote $OUT"
