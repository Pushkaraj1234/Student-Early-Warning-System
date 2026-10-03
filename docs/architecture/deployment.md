# Deployment and operations

Status 2026-10-02. What exists, how each part is run, and the decisions and secrets that only the owner can
provide. Environments and their safety rules: `docs/architecture/environments.md`.

## What runs where

| Part | Runs on | State |
|---|---|---|
| Database, Auth, Realtime | Hosted Supabase (testing project `rzekfmfuskknadrchkhg`) | Live, synthetic data. Migration `20261002001200_rules_version.sql` still has to be pushed (see below). |
| Mobile app | Android phones (Flutter) | Debug and release APKs build; release is signed with the debug key until the owner adds an upload key. |
| Batch jobs (scoring, recommendations, outcomes, monitoring, notification delivery) | Any machine with Python 3.13 and network access to the database | Runnable through `python -m sews_services.jobs`; **not scheduled anywhere yet** (owner decision). |
| Inference API (FastAPI) | Any container/VM host | Tested locally; **not deployed** (owner decision). |
| Push notifications | — | **Not configured.** No push provider is integrated; notifications are in-app only. |

## Batch jobs

```bash
# from the repository root, with the services virtual environment
PYTHONPATH="services:." services/.venv/bin/python -m sews_services.jobs --help   # Windows: services;. and Scripts\python
```

| Command | Scope | Writes |
|---|---|---|
| `score --institution <uuid> [--target academic] [--model-version V]` | one institution | `risk_predictions`, `risk_factors`, identity-free feature snapshots |
| `recommend --institution <uuid>` | one institution | rule suggestions (`status = recommended`, with `rule_id` and `rule_version`), never visible to students before review |
| `outcomes` | all institutions | descriptive outcome measures for finished interventions |
| `monitor --model-registry-id <uuid> [--window-days 7] [--no-reference]` | one registered model | monitoring snapshot and drift alerts (window = the last complete local days, reference = the days before) |
| `deliver [--batch-size 100]` | all | processes pending notifications; with no push provider configured they are marked `skipped` |
| `train --institution <uuid> --data-provenance institutional\|synthetic [--config F] [--report-dir D]` | one institution | trains on its completed terms and registers the selected models as `development` (docs/ml/institutional-training.md) |

Nightly order per institution: `score` → `recommend` → `outcomes` → `deliver`; then `monitor` for each
production model. `train` runs on demand, typically after a semester's results are published; approving a
trained model is a separate, human step (docs/ml/institutional-training.md). Output is one JSON line of counts (no identifiers). Exit codes: `0` done, `1` database error
(logged as class and SQLSTATE only), `2` invalid configuration or arguments, `3` refused (e.g. no production
model, artifact hash mismatch, model trained on a disallowed data provenance, temporal leakage, too few terms
with published results).

Required environment (secrets from the scheduler's secret store, never a file in Git):
`SEWS_ENV`, `SEWS_DATABASE_URL` (**secret**: the service-role/`postgres` connection string),
`SEWS_MODEL_REGISTRY_ROOT` (folder of verified model artifacts), optionally `SEWS_ALLOWED_PROVENANCE` and
`SEWS_PRODUCTION_PROJECT_REF`. The jobs do not need the API's JWT settings.

**Today `score` refuses to run on any real project**: no model is registered with status `production`, and in
production only models trained on institutional data are allowed (`docs/ml/ml-strategy.md` §5). This is
intended. The demo predictions in the testing project are seed fixtures, not model output.

### Owner decision: where the jobs run

Any of these works because each job is one short process; all need the database secret in a secret store.

| Option | Notes |
|---|---|
| A small always-on VM with cron | Simplest to reason about; the owner maintains the machine. |
| A CI scheduler (e.g. a scheduled GitHub Actions workflow) | No server to maintain; the secret lives in the repository's encrypted secrets; the repository must stay private. |
| A cloud scheduler + container job | Most robust; most setup. |

Not chosen on the owner's behalf: it decides where student data is processed and who holds the database secret.

## Applying the pending migration (owner)

```bash
npx supabase@2.117.0 db push --linked --dry-run   # should list only 20261002001200_rules_version.sql
npx supabase@2.117.0 db push --linked             # without --include-seed: the hosted seed is already loaded
```

Existing hosted suggestions keep `rule_version = null` (their rule set cannot be proven); new ones from the job
carry it. Schema version becomes `4.1.0`; the app's minimum version is unchanged.

## Admin account for the testing project (owner)

Same procedure as the mentor account: Authentication → Users → Add user (tick *Auto Confirm User*) with
`admin.test@synthetic.example.com`, then in the SQL Editor:

```sql
update public.profiles
   set role = 'admin', institution_id = 'a0000000-0000-4000-8000-000000000001', full_name = 'Synthetic Admin'
 where id = (select id from auth.users where email = 'admin.test@synthetic.example.com');
```

## Android release signing (owner)

`android/app/build.gradle.kts` signs release builds with the key named in `apps/mobile/android/key.properties`.
That file and every `*.jks`/`*.keystore` are git-ignored. Without it, release builds are signed with the
**debug** key (installable for testing, not publishable). The owner creates and keeps the upload key:

```bash
keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

`apps/mobile/android/key.properties` (`storeFile` is resolved relative to `apps/mobile/android/app/`):

```properties
storePassword=<owner's password>
keyPassword=<owner's password>
keyAlias=upload
storeFile=<path to upload-keystore.jks>
```

Back the keystore and passwords up outside the repository: a lost upload key cannot be recovered by anyone.
The application id `io.sews.sews_mobile` is permanent once published; change it (to a domain the owner
controls) before the first Play Store upload if desired.

## Email for real sign-ups (owner)

Supabase's built-in email service only sends to the project's team members, so real students cannot confirm
their addresses. Configure a custom SMTP provider in the dashboard's Auth SMTP settings (Supabase guide:
"Send emails with custom SMTP") with the institution's sending domain. The app already maps the related error codes to clear messages.

## Production project (owner)

Create a **separate** Supabase project for real data; never load `seed.sql` into it. Apply the migrations, run
the pgTAP suite against it (`supabase test db`, which needs Docker), configure SMTP, backups
(`docs/architecture/backups.md`) and the job schedule, then build the app with a production config file
(`--dart-define-from-file`).
