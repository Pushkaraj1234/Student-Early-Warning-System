-- SEWS 0001 — private schema and generic trigger helpers.
-- The private schema is NOT exposed through the Supabase Data API. It holds
-- authorization helpers and trigger functions. `authenticated` needs USAGE so that
-- RLS policies (which run with the caller's privileges) can call helper functions.
-- Idempotent: safe to re-run.

create schema if not exists private;

revoke all on schema private from public;
revoke all on schema private from anon;
grant usage on schema private to authenticated, service_role;

-- New functions in private must not be executable by PUBLIC (PostgreSQL default).
alter default privileges in schema private revoke execute on functions from public;

-- Keeps updated_at current on every UPDATE.
create or replace function private.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

revoke all on function private.set_updated_at() from public, anon;
