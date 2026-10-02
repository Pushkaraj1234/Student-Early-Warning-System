# SEWS V2–V4 implementation plan and decision log

Started 2026-09-24. This file is the working plan; items are ticked only after verification.

## Owner decisions (2026-09-24)
- Downloads: Python backend packages (fastapi, uvicorn, pyjwt[crypto], psycopg[binary], httpx) and
  pip-audit. Dart dependencies are checked against the OSV API with a script (no osv-scanner binary).
- Cross-institution validation: build the framework; run it on OULAD **modules** labelled
  "cross-module within one UK institution — NOT cross-institution evidence".
- Interventions: the **student** accepts/declines an offered intervention; staff create, assign,
  complete (with outcome) or cancel. Rule-engine suggestions are hidden from students until a mentor
  reviews them.
- Hosted Supabase project stays untouched until the owner confirms (carried over).

## Design decisions (documented where implemented)
- Intervention states: recommended → pending (offered) → accepted | declined; accepted → completed;
  recommended|pending|accepted → cancelled. Status changes only through RPCs; a trigger rejects any
  other transition.
- Trajectory: computed in the database between consecutive predictions of the **same model version
  and target**; thresholds documented in docs/ml/risk-trajectory.md (provisional).
- Live predictions require a model-registry row in status `production`; development databases can set
  `sews.environment = 'development'` to allow non-production (synthetic/demo) models.
- Identity vs ML data: `private.ml_subject_map` maps students to random ML ids; feature snapshots use
  ML ids only; no client access.
- Terms: `academic_terms` (odd/even/summer per academic year) give the "current semester" window.
- Targets (V3): academic (Fail or Withdrawn), dropout (Withdrawn), course failure (Fail), engagement
  (no LMS activity in the next 14 days). Attendance risk NOT built: no attendance data exists.
- Calibration is applied only if an out-of-time check shows it improves Brier and ECE.

## ML design (V2–V4)
- Feature set `oulad-fs-2.0.0` (superset of v1): windows 7/14/30 days + presentation-to-date ("current
  semester") for all clicks, quiz clicks (activity_type quiz/externalquiz), forum clicks (forumng),
  content clicks (everything else); active days per window; trends (last window − previous window)/days;
  change from baseline; assignment submissions/completion in last 30 days; grade trend (slope of released
  scores, ≥2 scores) and change from first score. Attendance: not available in OULAD (documented).
  Loader aggregates studentVle per student-day-activity group (joined with vle.csv).
- Runtime leakage guard: before training, features built from the full data must equal features built
  from data truncated at the cutoff (sample of registrations); any mismatch aborts training.
- Targets: academic (Fail|Withdrawn), dropout (Withdrawn), course_failure (Fail), engagement (no VLE
  activity in (t, t+14]); each with horizon, population, dataset, metrics, validation documented.
- Calibration decision: fit model on 2013B, calibrator on 2013J, compare raw vs calibrated Brier+ECE on
  2014B; apply only if both improve; report raw and calibrated on test either way.
- Fairness: per-subgroup PR-AUC, recall/FNR, FPR, precision, mean predicted vs observed, ECE; disparity
  = max−min across groups with n≥100 and ≥10 positives.
- Cross-group: leave-one-module-out + out-of-time (train on other modules' 2013B/2013J/2014B → test
  module M's 2014J) vs a pooled reference trained on all modules including M (same periods); raw
  probabilities, imbalance "none"; degradation reported per module. A pooled reference was chosen over
  an in-module-only model because single modules are small and would confound size with shift.
  Label: NOT cross-institution evidence.
- Data sufficiency: a (target, cutoff) is trained only if every split has ≥ `min_class_count_per_split`
  (default 20) positives and negatives; otherwise it is skipped and the reason reported.
- Drift: PSI (10 reference-quantile bins) warn ≥0.10, critical ≥0.25 (conventional heuristics);
  missing-rate change warn ≥0.05, critical ≥0.15; outcome-rate change warn ≥0.05, critical ≥0.10;
  PR-AUC drop warn ≥0.05, critical ≥0.10.
- Explanations by audience: student (plain, no probability, no contribution numbers, non-stigmatising),
  mentor (factor values, contributions, units, provenance), admin (+ lineage, validation, calibration).
- Registry export: ModelMetadata → model_registry row (status development).

## Checklist

Database verified 2026-10-02: 14 pgTAP files, 390 assertions (mutation check on gating and check-ins: 2026-09-25).
Note: migrations are idempotent but do not repair manual drift (a hand-dropped inline constraint is not recreated).
### Database
- [x] V2 migration: terms, LMS integrations, canonical engagement events, prediction trajectory, intervention workflow, notifications delivery + types, realtime publication
- [x] V3 migration: check-ins, intervention priority/reason/outcome measures, monitoring snapshots
- [x] V4 migration: model registry + states, prediction gating, ML subject ids, feature snapshots, drift alerts, system events, versions
- [x] pgTAP tests for all of the above (isolation, mentor scope, trajectory, transitions, delivery state, unauthorized creation, duplicates)
### ML
- [x] Feature set v2 (7/14/30/term windows; attendance-analogue n/a; assignments, grades, LMS, quiz, engagement trends) + leakage tests — `ml/features/{definitions,oulad_features,targets,leakage}.py`, `ml/tests/test_v2_features_targets_leakage.py`; runtime guard passed on real OULAD days 30/60/90 (37 features)
- [x] Multi-target training code + data-sufficiency skip + documented targets/horizons (`ml/training/train.py`, `ml/features/targets.py`) — synthetic end-to-end tests pass; real OULAD run: see results doc
- [x] Calibration decision procedure; fairness (FPR/FNR/calibration gap/ECE by subgroup + disparity)
- [x] Cross-group framework + tests (`ml/training/cross_group.py`); OULAD module-proxy run: see results doc
- [x] Drift (PSI, missingness, prediction/outcome, performance drop) + monitoring snapshot (`ml/monitoring/drift.py`)
- [x] Audience explanations (`ml/explainability/audiences.py`), registry export (`ml/models/registry_export.py`), inference `api_version` 1.0.0 + `target`
- ML suite 2026-09-24: 133 tests pass; ruff clean; mypy --strict clean (38 files)

### Services
- [x] LMS adapter abstraction + normalisation (CSV + Moodle log adapters; hashed ids; no raw payloads) — `services/sews_services/lms`
- [x] Institutional as-of features `inst-fs-1.0.0` + leakage guard, scoring job (registry gate, hash check, provenance, feature-version check, ML ids, identity-free snapshots), rule engine `rules-1.0.0`, recommendation job, outcome measures `outcomes-1.0.0`, monitoring (snapshots, drift alerts, label-time performance), notification delivery worker
- [x] FastAPI inference API (JWT HS256/JWKS, role check, rate limiting, body limit, stable errors, metrics, no PII logs), environment-safety config
- Services suite 2026-09-24: 101 tests pass (39 against a rebuilt local DB); ruff clean; mypy --strict clean (28 files)
### Mobile
- [x] Mentor role: dashboard, student detail (trends, trajectory, factors, interventions), intervention actions, messages
- [x] Student: offered interventions accept/decline, check-ins, trajectory, realtime notifications (Realtime not exercised in tests: no socket in widget tests)
- [x] Admin: model/monitoring view; role routing; minimum-version gate (app 2.0.0)
- Mobile 2026-09-25: flutter analyze clean; 102 tests pass (incl. 9 V2 widget tests); debug APK built
### Docs & verification
- [x] 2026-10-02: federated-learning design (docs/architecture/federated-learning.md; no prototype — not justified),
      backups (docs/architecture/backups.md), deployment (docs/architecture/deployment.md), ML results
      (docs/ml/results-v2.md), fairness notes (docs/ml/fairness.md); environments and versioning updated
- [x] Docs referenced by code written 2026-09-25: docs/ml/risk-trajectory.md, docs/ml/monitoring.md,
      docs/ml/intervention-outcomes.md, docs/architecture/versioning.md, docs/architecture/environments.md (owner chose
      this path; config.py reference corrected). Mobile dev example config now points at the local stack.
- [x] Rules version stored with interventions: migration `20261002001200_rules_version.sql` (schema 4.1.0), job writes
      `rule_version`, pgTAP `120_rules_version.sql`; seed suggestions aligned with `rules-1.0.0` (hosted push: owner)
- [x] CLI for the jobs: `python -m sews_services.jobs` (`services/sews_services/jobs/cli.py`, 13 tests)
- [ ] Scheduler for the jobs — owner decides where (docs/architecture/deployment.md)
- [x] Security checks 2026-09-25: pip-audit (services + ml locks) no known vulns; OSV (106 hosted pub packages) no known
      vulns, checker positive-controlled; 27/27 public tables have RLS; 0 client grants on private schema; 0 anon EXECUTE on
      public functions; all SECURITY DEFINER functions pin search_path; no string-built SQL in services/ml
- [x] 2026-10-02 all suites + builds: database 14 files / 390 assertions; ML 139; services 115; mobile 109; debug and
      release APKs; dependency audits clean; production-readiness report: docs/production-readiness.md
