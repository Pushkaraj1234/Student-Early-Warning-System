# Versioning

Every component that can change behaviour carries a version, and every stored prediction records which versions
produced it. Current values (2026-10-02):

| Component | Current version | Where it is defined | Where it is recorded / checked |
|---|---|---|---|
| Database schema | `4.1.0` | `public.get_platform_versions()` (migration `20261002001200`) | read by clients through the function |
| Migrations | 12 files, `20260924000100` … `20261002001200` | `supabase/migrations/` (timestamp-ordered) | applied in order; the local suite applies them twice to prove idempotency |
| Mobile app | `2.0.0+2` | `apps/mobile/pubspec.yaml`, `appVersion` in `lib/core/app_version.dart` | a test checks both agree |
| Minimum supported mobile app | `2.0.0` | `get_platform_versions()` → `minimum_mobile_app` | older builds see "Update required" |
| Inference API | `1.0.0` | `API_VERSION` in `ml/inference/schemas.py` | `api_version` in every response; `GET /v1/version`; a test checks it equals `inference_api` in the database |
| Benchmark dataset | `oulad-<16 hex>` | `ml.data.oulad.dataset_version` (SHA-256 over the source files) | model metadata, registry `dataset_version`, predictions |
| Feature sets | `oulad-fs-1.0.0`, `oulad-fs-2.0.0` (benchmark); `inst-fs-1.0.0` (institutional) | `ml/features/definitions.py`; `services/sews_services/features/institutional.py` | model metadata, registry, `risk_predictions.feature_version`, `private.feature_snapshots.feature_version` |
| Models | e.g. `oulad-v2-20260924T003349Z-acad-xgb-d60` | training run: `{run_name}-{UTC timestamp}-{target}-{model}-d{cutoff}` | artifact folder + `metadata.json` with SHA-256 of the model file; `public.model_registry.version` and `artifact_sha256` |
| Outcome method | `outcomes-1.0.0` | `METHOD_VERSION` in `services/sews_services/jobs/outcomes.py` | `intervention_outcome_measures.method_version` |
| Recommendation rules | `rules-1.0.0` | `RULES_VERSION` in `services/sews_services/recommendations/engine.py` | `interventions.rule_version`, written by the recommendation job with `rule_id` (schema 4.1.0) |
| Python services / ML packages | `1.0.0` | `services/pyproject.toml`, `ml/pyproject.toml` | dependencies pinned in `requirements.lock` files |

## Rules

- **Semantic versioning** for the database schema, mobile app and inference API: MAJOR for breaking changes
  (removed/renamed fields or functions, changed meaning), MINOR for backwards-compatible additions, PATCH for fixes.
- **Migrations are append-only.** Never edit an applied migration; write a new one. Each migration must be
  idempotent (safe to re-run), keep RLS enabled and ship with pgTAP tests. Bump `database_schema` in
  `get_platform_versions()` in the migration that changes the contract.
- **Breaking the mobile contract** (removing a column or function the app uses) requires raising
  `minimum_mobile_app` in the same migration and shipping the new app first.
- **Changing any feature definition** requires a new feature-set version; old models keep their version and
  the scoring job refuses a model whose feature version differs from the builder's.
- **A new model is a new version**, never an overwrite: artifacts are write-once folders, the registry version is
  unique, and a model's identity fields cannot be changed after registration (database trigger).
- **Predictions are never re-labelled.** Each `risk_predictions` row keeps the model, feature and dataset versions
  that produced it (copied from the registry by the database), so any past prediction can be traced.
- **Trajectories never compare versions:** a model change starts a new trajectory series (docs/ml/risk-trajectory.md).
- **Method changes get a new method version** (outcome measures), and old rows stay.

## Rule-set versions

Since schema 4.1.0 (migration `20261002001200_rules_version.sql`) every suggestion the recommendation job creates
stores the rule that fired (`rule_id`) and the rule-set version (`rule_version`). The database requires the two together, allows them only
on rule-engine rows (`source = 'model_rule'`), and makes both immutable; clients cannot write them. Suggestions
created before 4.1.0 keep `rule_version = null` because their rule set cannot be proven. Any change to a rule's
logic or thresholds needs a new `RULES_VERSION` and a row below.

| Rules version | Date | Change |
|---|---|---|
| `rules-1.0.0` | 2026-09-24 | Initial rule set (see `RULES` in `engine.py`). |
