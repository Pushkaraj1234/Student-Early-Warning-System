# SEWS — Student Early Warning & Intervention System

> **Status (2026-09-24):** Supabase foundation, student mobile app V1 and baseline ML pipeline are implemented
> and verified **locally**. Nothing has been applied to the hosted Supabase project yet, and the app has not
> been run against a real backend or device. See "Verification status" below.

## Purpose

SEWS is a mobile-first, research-grade student success platform. It:

1. identifies **early signals** of future academic difficulty;
2. **explains** the main contributing factors;
3. **recommends** interventions, which a human mentor reviews and decides on.

Predictions are probabilistic estimates, **never guaranteed outcomes**. Explanations describe model
associations, **not causes**. See [docs/research/project-scope.md](docs/research/project-scope.md).

## Architecture

```
Flutter app (untrusted client, publishable key only)
    │  user JWT
    ▼
Supabase: Auth · PostgreSQL + RLS · (Storage/Realtime not used in V1)
    ▲  writes versioned predictions (server-side secret key — scoring job, not built yet)
    │
ML inference interface (ml/inference) ◄── model registry (ml/artifacts) ◄── training & evaluation (ml/training)
```

Details: [system-architecture.md](docs/architecture/system-architecture.md) ·
[technology-decisions.md](docs/architecture/technology-decisions.md) ·
[database-design.md](docs/database/database-design.md) ·
[data-contract.md](docs/ml/data-contract.md) · [baseline-results-v1.md](docs/ml/baseline-results-v1.md) ·
[results-v2.md](docs/ml/results-v2.md) · [longitudinal-v3.md](docs/ml/longitudinal-v3.md) ·
[external-datasets.md](docs/ml/external-datasets.md) · [fairness.md](docs/ml/fairness.md) ·
[institutional-training.md](docs/ml/institutional-training.md) ·
[deployment.md](docs/architecture/deployment.md) · [backups.md](docs/architecture/backups.md) ·
[production-readiness.md](docs/production-readiness.md) ·
Course (research methodology, 10 weeks): [course-alignment.md](docs/research/course-alignment.md)

## Repository structure

```
apps/mobile/            Flutter app for Android and the web (feature-first: data / domain / application / presentation)
  config/dev.example.json   build config template (copy to dev.local.json — git-ignored)
  web/ · vercel.json · tool/   website shell, Vercel config (rewrite + security headers), build and preview scripts
ml/                     Python ML pipeline: data/ features/ training/ evaluation/ models/ explainability/ inference/ tests/
  configs/oulad_v1.json     training configuration (dataset path is configurable)
  data/raw/ (git-ignored)   downloaded datasets        artifacts/ (git-ignored)  trained models
  reports/                  evaluation reports (aggregate metrics only)
supabase/               config.toml, migrations/ (12), tests/database/ (pgTAP), seed.sql (synthetic), types/schema_contract.json
scripts/db/             local database test harness (no Docker needed) and schema-contract export
docs/                   research, architecture, database, ML and security documentation
```

## Setup requirements

| Tool | Used for | Verified on dev machine |
|---|---|---|
| Flutter stable + Android SDK | mobile app | Flutter 3.41.4 / Dart 3.11.1, Android SDK 36.1 |
| Python 3.13 | ML pipeline | 3.13.2 (venv at `ml/.venv`, packages in `ml/requirements.lock`) |
| PostgreSQL 18 | local database tests | 18.3 (+ pgTAP 1.3.3 via `extension_control_path`) |
| Node.js | Supabase CLI via `npx supabase` | CLI 2.117.0 |
| Docker | `supabase start`, `supabase test db`, `supabase gen types` | **not installed** |

## Local development

```bash
# Database: fresh DB, migrations applied twice (idempotency), synthetic seed, pgTAP tests
PGBIN="/c/Program Files/PostgreSQL/18/bin" bash scripts/db/test-local.sh
PGBIN="/c/Program Files/PostgreSQL/18/bin" bash scripts/db/export-schema-contract.sh

# ML
python -m venv ml/.venv && ml/.venv/Scripts/python -m pip install -r ml/requirements.lock
ml/.venv/Scripts/python -m ml.training.train --config ml/configs/oulad_v1.json

# Mobile
cd apps/mobile && cp config/dev.example.json config/dev.local.json   # then add the publishable key
flutter run --dart-define-from-file=config/dev.local.json

# Website (same Flutter app, built for the browser; served like Vercel will serve it)
cd apps/mobile && flutter build web --release --csp --no-web-resources-cdn --dart-define-from-file=config/<file>.json
python tool/serve_web.py   # http://localhost:8080
```

The local test cluster used here listens on port 54330 (`initdb` + `pg_ctl`, see docs/database/database-design.md §8).

## Environment variables

| Variable | Used by | Secret? | Where |
|---|---|---|---|
| `SUPABASE_URL` | mobile | no | `apps/mobile/config/dev.local.json` |
| `SUPABASE_PUBLISHABLE_KEY` | mobile | no (RLS-protected) | `apps/mobile/config/dev.local.json` (git-ignored). The app **refuses** `sb_secret_…` and service-role keys |
| `SEWS_ENV`, `SEWS_DATABASE_URL`, `SEWS_JWT_SECRET` / `SEWS_JWT_JWKS_URL`, … | backend services | database URL and JWT secret: **YES** | server secret store — never Flutter, never Git. Full list and rules: `docs/architecture/environments.md` |
| `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DB_PASSWORD` | Supabase CLI | **YES** | developer shell / CI secrets |
| `PGBIN`, `PGHOST`, `PGPORT`, `PGUSER`, `SEWS_TEST_DB` | `scripts/db/*.sh` | no | shell |

## Testing

| Layer | Command | Result (2026-10-02) |
|---|---|---|
| Database | `bash scripts/db/test-local.sh` | 12 migrations applied twice; 14 files, 390 assertions passed |
| ML | `ml/.venv/Scripts/python -m pytest -c ml/pyproject.toml ml/tests` · `ruff check --config ml/pyproject.toml ml` · `mypy --config-file ml/pyproject.toml ml` | 181 passed (2026-10-08) · clean · clean |
| Services | `services/.venv/Scripts/python -m pytest -c services/pyproject.toml services/tests` · `ruff check --config services/pyproject.toml services` · `mypy --config-file services/pyproject.toml services/sews_services services/tests` | 130 passed (incl. tests against a rebuilt local DB) · clean · clean |
| Mobile | `flutter analyze` · `flutter test` · `flutter build apk --debug` / `--release` | no issues · 109 passed · both built; the release APK launches on the emulator (signed with the debug key until the owner adds one) |
| Website (2026-10-05) | `flutter analyze` · `flutter test` · `flutter build web --release --csp --no-web-resources-cdn` · `bash tool/vercel_build.sh` | no issues · 115 passed · built; runs in the browser under the production Content-Security-Policy (sign-in screen, clean addresses, deep links redirect to sign-in) |
| Dependencies | `pip-audit -r services/requirements.lock` / `ml/requirements.lock` · `python scripts/security/osv_check_pub.py apps/mobile/pubspec.lock` | no known vulnerabilities (106 Dart packages) |

## Verification status

Verified locally: RLS scope for anon/student/mentor/faculty/admin (database tests); registration, login,
logout, session restoration, email-confirmation handling (against a fake Supabase HTTP backend); empty,
network-failure, invalid-data and prediction-unavailable states (widget tests); leakage-safe features and
inference validation (Python tests).

Verified against the hosted **testing** project (2026-09-26, synthetic data): migrations applied; `anon` refused
everywhere; the student and mentor flows on the Android emulator, from offer to completion.

**Not yet verified:** pgTAP on hosted Supabase (`supabase test db` needs Docker); sign-up with real email
delivery (needs custom SMTP); the admin screens live; iOS. Full status: [production-readiness.md](docs/production-readiness.md).

## Deployment overview

- **Database:** `npx supabase link` → inspect remote schema (`migration list`, `db pull`) → `db push` →
  run pgTAP against the linked DB. Configure Auth in the dashboard (email confirmation, password policy,
  redirect URL `io.sews.app://login-callback`). Never load `seed.sql` into a project with real data.
- **Website:** the Flutter app built for the web, prepared for Vercel (`apps/mobile/vercel.json`, root
  directory `apps/mobile`, publishable key from Vercel's environment variables); steps in
  [deployment.md](docs/architecture/deployment.md#website-vercel). Not deployed yet.
- **Mobile:** Android release builds; iOS needs a macOS build host.
- **Batch jobs:** `python -m sews_services.jobs score|recommend|outcomes|monitor|deliver|train` (one job per
  process, for any scheduler); where they run is an owner decision. `train` builds models from the institution's
  own past terms ([institutional-training.md](docs/ml/institutional-training.md)). See [deployment.md](docs/architecture/deployment.md).
- **ML:** benchmark-trained models are **not** approved for real students. Deployments scoring real
  students must construct `InferenceService(..., allowed_provenance={"institutional"})`.

## Security rules

1. Never put secrets in client code; the app rejects secret/service-role keys at startup.
2. Every exposed table has RLS enabled with explicit, tested policies; `anon` has no privileges.
3. Roles come from `public.profiles`, never from the client; sign-up always creates a `student`.
4. Every schema change is an idempotent migration in `supabase/migrations/`.
5. Minimum data; no real student data before the prerequisites in [security-model.md](docs/security/security-model.md) §7.
6. Label every dataset `benchmark`, `synthetic` or `institutional`. OULAD is UK data — **not Indian data**.
7. No ML claims without held-out, out-of-time evaluation.
