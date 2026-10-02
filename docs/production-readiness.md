# Production-readiness report

Date 2026-10-02 (work after commit `d398a2d`). **Verdict: not ready for real students.** The software works end to
end on synthetic data and its safety controls are tested, but it has no model trained on institutional data, no
scheduled jobs, no production project and no real-user email. Each blocker below needs an owner decision, an
account or data that only the owner can provide.

## Verified (with evidence)

| Area | Result | How it was verified |
|---|---|---|
| Database | 12 migrations apply twice (idempotent); 14 pgTAP files, 390 assertions pass | `bash scripts/db/test-local.sh` (local PostgreSQL 18) |
| Row-level security | 27/27 public tables have RLS; 0 anonymous EXECUTE on public functions; 0 client grants on `private`; every SECURITY DEFINER function pins `search_path` | catalogue queries on the rebuilt test database; per-role pgTAP tests (anon, student, mentor, faculty, admin) |
| Hosted testing project | 11 migrations applied by the owner; `anon` refused everywhere (`42501`) | read-only checks with the anon key (2026-09-26) |
| Services | 115 tests (incl. the batch-job CLI and the recommendation job against a rebuilt local DB); ruff, format, mypy --strict clean | `services/.venv` |
| ML pipeline | 139 tests; ruff, mypy clean; temporal leakage guard passes at days 30/60/90 | `ml/.venv`; docs/ml/results-v2.md |
| Mobile | analyzer clean; 109 tests; debug and release APKs build; the release APK launches and validates input on the emulator | `flutter analyze`, `flutter test`, `flutter build apk --release` |
| Live app (hosted testing project, synthetic data) | Student: sign-in, dashboard, explanation, check-in, attendance, assignments, accepting an offer, notifications. Mentor: caseload, student detail, review & offer, completion with outcome | driven on the Android emulator, 2026-09-26 |
| Dependencies | no known vulnerabilities (pip-audit for both lock files; OSV for 106 Dart packages) | 2026-10-02 |

## Blockers before real student data (owner)

| # | Blocker | Why it blocks | Reference |
|---|---|---|---|
| 1 | **No institutional model.** Only benchmark (UK) models exist; production refuses non-institutional models | Without it there are no real predictions | docs/ml/ml-strategy.md §5, docs/ml/results-v2.md |
| 2 | **Jobs are not scheduled.** The CLI exists; nothing runs it | Predictions, suggestions and outcomes would never update | docs/architecture/deployment.md |
| 3 | **No production Supabase project** (the hosted one is testing-only, synthetic data) | Real data must not share a project with seed data | docs/architecture/environments.md |
| 4 | **No custom SMTP** | Real students cannot confirm their email addresses | docs/architecture/deployment.md |
| 5 | **No backups or restore test** for a production project | Data loss would be unrecoverable (the Free plan has no automatic backups) | docs/architecture/backups.md |
| 6 | **No release signing key**; application id not confirmed | Play Store distribution is impossible | docs/architecture/deployment.md |
| 7 | **No agreed fairness limits**, and no audit attributes in the institutional schema | A model cannot be approved responsibly, and live subgroup monitoring is impossible | docs/ml/fairness.md |
| 8 | **Institutional governance**: data-processing basis, retention periods, who may act on suggestions, and the institution's confirmation of the rule thresholds (75% attendance, 40% pass mark) | Legal and ethical prerequisites | docs/research/problem-definition.md, `engine.py` |

## Known gaps that do not block a pilot

- Migration `20261002001200_rules_version.sql` is not yet applied to the hosted testing project (owner push).
- Admin screens are covered by widget tests but have not been exercised live (needs an admin test account).
- pgTAP has not run against a hosted project (`supabase test db` needs Docker, which is not installed).
- No push notifications (in-app only); the delivery job marks notifications `skipped`.
- iOS has not been built or tested.
- The inference API is tested locally but not deployed (the batch scoring job does not need it).

## Suggested order

1. Owner: apply the pending migration; create the admin test account; walk through the admin screens.
2. Owner: decide where the jobs run; create the production project with backups and SMTP.
3. Institution: provide historical records (attendance, assessments, results) under an agreed basis; train,
   evaluate (including the subgroup audit) and approve a first institutional model through the registry.
4. Pilot with one department, human review of every suggestion, and outcome tracking before wider use.
