# Backups and recovery

Status 2026-10-02. Facts about Supabase backups are from Supabase's documentation ("Database Backups",
"supabase db dump"), checked on that date; plans and limits can change, so re-check before relying on them.

## What must be recoverable

| Asset | Where it lives | How it is recovered |
|---|---|---|
| Database (all SEWS tables, including the `auth` schema with user accounts) | Supabase Postgres | Supabase backups or an owner-run `pg_dump` (below) |
| Schema | `supabase/migrations/` in Git | Re-apply the migrations to a new project |
| Model artifacts | `SEWS_MODEL_REGISTRY_ROOT` folder (write-once, SHA-256 recorded in `model_registry`) | Owner's copy of that folder; a restored artifact must match the registry hash or scoring refuses it |
| Android upload key | Owner's keystore (never in Git) | Owner's own backup only — it cannot be recreated |
| Secrets (database password, service-role key) | Supabase dashboard / secret store | Rotated in the dashboard, never restored from files |

SEWS stores no files in Supabase Storage and its migrations create no custom database roles, so neither
backup limitation below affects it today.

## Supabase backup facts (from the docs)

- **Free plan: no automatic backups.** Supabase recommends that free projects "regularly export their data
  using the Supabase CLI `db dump` command and maintain off-site backups".
- Daily backups: Pro 7 days, Team 14 days, Enterprise up to 30 days. Restore from Dashboard → Database →
  Backups; the project is unavailable during a restore.
- Point-in-time recovery: an add-on for Pro, Team and Enterprise (needs at least the Small compute add-on;
  7/14/28-day retention).
- Database backups exclude Storage objects and do not keep custom role passwords.

## Testing project (current)

It holds synthetic data only and can be rebuilt from Git (`db push --include-seed`); no backup is required.
The owner's plan tier is not recorded here.

## Production project (required before real data)

1. Use a plan with daily backups, or enable point-in-time recovery, according to how much data loss the
   institution can accept.
2. Regardless of plan, keep an **off-site, encrypted** logical backup under the institution's control. Note:
   `supabase db dump` runs `pg_dump` in Docker and by default dumps **schema only** and **excludes the
   `auth` and `storage` schemas**; it is not a complete backup by itself. A complete logical dump with the
   PostgreSQL client tools (version ≥ the server's):

   ```bash
   pg_dump --format=custom --no-owner --file=sews-$(date +%F).dump "$SEWS_BACKUP_DATABASE_URL"
   ```

   `SEWS_BACKUP_DATABASE_URL` is a secret (owner's secret store). The dump contains personal data: encrypt it,
   restrict access, and apply the institution's retention period.
3. **Test a restore** at least once per semester into a scratch project: restore, run the pgTAP suite, and
   check row counts. An untested backup is not a backup.
4. Record each restore test (date, backup used, result) in this document.

## Not yet done

- No production project exists, so no backup schedule or restore test has been run.
- No automated off-site dump job exists; it would run where the batch jobs run (`docs/architecture/deployment.md`).
