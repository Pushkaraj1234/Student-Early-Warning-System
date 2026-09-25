# Environments

SEWS separates **development**, **staging** and **production**. Local development never points at hosted data;
this is enforced in code where possible, not only by convention.

## Summary

| | Development | Staging | Production |
|---|---|---|---|
| Database | Local Postgres / local Supabase stack (loopback only) | Its own hosted Supabase project | Hosted Supabase production project |
| Data | Synthetic only (`supabase/seed.sql`) | Synthetic or approved test data | Real institutional data |
| `SEWS_ENV` (services) | `development` | `staging` | `production` |
| Models allowed to score | Any registered non-retired model (the session sets `sews.environment = development`) | Registry `production` models only | Registry `production` models only, trained on **institutional** data |
| Allowed training provenance | benchmark, synthetic, institutional | benchmark, synthetic, institutional (configurable) | institutional only (enforced) |
| API docs (`/docs`, `/openapi.json`) | on | off | off |
| JWT verification secret or JWKS | optional | required | required |
| Seed data | yes | no | **never** |

## How each rule is enforced

### Services (`services/sews_services/config.py`, `load_settings`)

Startup fails with a `ConfigError` (messages never contain secrets) when:

- `SEWS_ENV` is not one of `development`, `staging`, `production`;
- `development` uses a database host that is not `localhost`, `127.0.0.1` or `::1`, so a developer machine
  cannot connect to a hosted database even by mistake;
- `staging` uses a local database, or a host containing `SEWS_PRODUCTION_PROJECT_REF`;
- `production` uses a local database, or allows any provenance other than `institutional`;
- outside development, neither `SEWS_JWT_SECRET` nor `SEWS_JWT_JWKS_URL` is set, or the JWKS URL is not `https`.

`Settings.__repr__` hides the database URL and JWT secret, so settings are safe to log.

### Database

- The prediction gate (`private.check_registered_model`) accepts a non-`production` registry model only when the
  session sets `sews.environment = 'development'`. Only `supabase/seed.sql` and development jobs set it;
  production databases never do.
- RLS is enabled on every public table in every environment. It is never disabled to fix an application bug.

### Mobile (`apps/mobile/lib/core/config/app_config.dart`)

- Configuration is compiled in with `--dart-define-from-file` (`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`).
  Files named `*.local.json` are git-ignored; `config/dev.example.json` is the template and points at the local
  stack.
- `SUPABASE_URL` must be `https`, except `http` on `localhost`, `127.0.0.1` or `10.0.2.2` (Android emulator)
  for local development.
- Secret keys (`sb_secret_…`) and legacy `service_role` JWTs are refused at startup. Only the publishable key,
  which is safe because every table is protected by RLS, may be compiled into the app.

## Environment variables

| Variable | Component | Secret | Notes |
|---|---|---|---|
| `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` | mobile | no | per environment, via `--dart-define-from-file` |
| `SEWS_ENV` | services | no | `development` / `staging` / `production` |
| `SEWS_DATABASE_URL` | services | **yes** | server-side role connection (service role on hosted Supabase) |
| `SEWS_PRODUCTION_PROJECT_REF` | services | no | lets staging refuse the production database |
| `SEWS_JWT_SECRET` or `SEWS_JWT_JWKS_URL` | inference API | secret: **yes** / JWKS: no | verifies callers' tokens |
| `SEWS_JWT_AUDIENCE` | inference API | no | optional audience check |
| `SEWS_ALLOWED_PROVENANCE` | services | no | comma list; production is forced to `institutional` |
| `SEWS_MODEL_REGISTRY_ROOT` | services | no | folder of verified model artifacts |
| `SEWS_RATE_LIMIT_PER_MINUTE`, `SEWS_MAX_BODY_BYTES` | inference API | no | defaults 60 and 16 384 |
| `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD` | Supabase CLI | **yes** | developer shell / CI secrets only |
| `PGBIN`, `PGHOST`, `PGPORT`, `PGUSER`, `SEWS_TEST_DB` | local test scripts | no | local test cluster (default port 54330) |

Secrets live in the platform's secret store or the developer's shell, never in Git, the mobile app or logs.

## Local development in practice

- **Database tests:** a local PostgreSQL 18 cluster (port 54330) with a Supabase emulation shim
  (`scripts/db/supabase_local_shim.sql`); `bash scripts/db/test-local.sh` rebuilds a throwaway database.
  The services integration tests rebuild their own throwaway database (`sews_services_test`) on the same cluster.
- **Full local Supabase stack:** `supabase/config.toml` configures `supabase start` (API on port 54321).
  This needs Docker, which is **not installed** on the current development machine, so the full stack
  (Auth, Realtime, Studio) has not been run locally yet.
- **Mobile against the local stack:** copy `config/dev.example.json` to `config/dev.local.json` and set the
  local publishable key printed by `supabase start`.

## Hosted project status

The owner supplied one hosted Supabase project (ref `rzekfmfuskknadrchkhg`, PostgreSQL 17.6) and on
2026-09-26 designated it a **testing** project (not production). The owner applied all 11 migrations and the
synthetic seed with `npx supabase@2.117.0 db push --linked --include-seed` after a dry run. Verified afterwards
(read-only, anon key): all 11 migrations recorded remotely; every public table and function refuses the `anon`
role (`42501`). It holds **synthetic data only**; real student data needs a separate production project.
The mobile app targets it with `config/testing.local.json` (git-ignored). The pgTAP suite has not been run
against it (`supabase test db` needs Docker).

## Promotion path

1. Development: migrations and tests pass locally (`test-local.sh`, all suites).
2. Staging: apply migrations to the staging project (`supabase db push`), run the pgTAP suite there
   (`supabase test db`), exercise the app against staging.
3. Production: apply the same, already-tested migrations; register and approve models through the registry
   lifecycle; never load seed data.

Backups and recovery for the hosted projects are not yet documented (remaining work).
