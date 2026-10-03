# Training a model from the institution's own data

Status 2026-10-03. The pipeline is built and proven end to end on **synthetic** data. No model has been trained on
real institutional data yet, because none exists in SEWS.

## What it does

`python -m sews_services.jobs train --institution <uuid> --data-provenance institutional` (from the repository root,
with the services environment; docs/architecture/deployment.md):

1. **Terms.** Takes the institution's completed odd/even terms (`academic_terms`) whose results are published for
   at least 80% of their students (`min_label_coverage`).
2. **Out-of-time split by term.** The latest term is the test set, the one before it validation, the rest
   training — at least **3** terms. With 4 or more, whether to calibrate is decided on an earlier out-of-time check
   (fit on the earlier terms, calibrate on the last training term, evaluate on the validation term).
3. **Features.** For every student enrolled in a term and every decision point (days 30, 60 and 90 of the term),
   the `inst-fs-1.0.0` features — computed by the **same `build_features` code the live scoring job uses**, so
   training and scoring cannot drift apart. The temporal leakage guard runs for every term and decision point;
   any leak stops the run before anything is trained.
4. **Label** (`sews_services/features/labels.py`, shared with monitoring): 1 if the student withdrew from, or
   received F/Ab in, any course of the term; 0 if every result is published and none is adverse; otherwise the
   student is left out.
5. **Models and evaluation** — the benchmark pipeline's source-independent core (`train_feature_table` in
   `ml/training/train.py`): logistic regression, random forest and XGBoost; imbalance strategies compared on
   validation; seed stability; calibration only if the out-of-time check improves both Brier and ECE; risk
   thresholds from validation; **one** test evaluation with cluster-bootstrap 95% intervals; drift between
   training and test; a versioned, hashed artifact per model.
6. **Registration.** The selected model per decision point is added to `public.model_registry` with status
   `development`. Nothing scores real students until a person approves it (below).

Settings: `ml/configs/institutional_v1.json` (validated by `InstitutionalTrainingConfig`; the model-selection fields
are shared with benchmark training). Output: one JSON line of aggregates; `--report-dir` also writes `metrics.json`
and `report.md`. No student identifier is written anywhere (tested).

## What the data must contain

| Needed | Why |
|---|---|
| At least 3 completed odd/even terms in `academic_terms` | train / validation / test (4 for the calibration check) |
| Enrolments (`student_courses`) with withdrawals and published grades (`result_published_at`) | the label |
| Attendance, assignments and submissions with due/submitted/graded times, LMS events, past `academic_records` | the features (missing sources leave features empty, never invented) |
| At least 20 adverse and 20 non-adverse students in every split (`min_class_count_per_split`) | otherwise that decision point is skipped and reported |

## Assumptions and limitations (read before trusting a model)

- **Event time, not recording time.** Live scoring uses only what SEWS had *recorded* by the scoring time. History
  imported in bulk is "recorded" on the import day, which would hide all of it, so training replays each term by
  when things happened: attendance from its date, LMS events when they occurred, submissions and grades at their
  timestamps, an excusal at the due date. If an institution records data late (e.g. attendance entered weekly),
  live features will lag the training features; monitoring compares the two.
- **No withdrawal date in the schema.** A student who had already withdrawn before a decision point is still in
  that term's population. Adding a withdrawal date (a future migration) would remove this bias.
- **Population.** Students enrolled in the term's courses, whatever their status today — required, or the students
  who later withdrew (adverse outcomes) would be filtered out.
- **No fairness audit.** The institutional schema holds no audit attributes, so subgroup performance cannot be
  measured (docs/ml/fairness.md). An institution must decide this before approving a model.
- Results describe one institution's past cohorts; re-train and re-evaluate when rules, grading or the LMS change.

## Approving a model (owner / institution)

The database enforces the lifecycle `development → validated → staging → production` and allows `production` only
for **institutional** data, with calibration metrics and a recorded approver (`approved_by`, `approved_at`); at most
one production model per target and institution. There is **no approval button in the app yet**: an operator runs,
after reviewing the run report,

```sql
update public.model_registry set status = 'validated' where version = '<model version>';
update public.model_registry set status = 'staging' where version = '<model version>';
update public.model_registry
   set status = 'production', approved_by = '<approving admin profile id>', approved_at = now()
 where version = '<model version>';
```

The artifact folder must also be present in `SEWS_MODEL_REGISTRY_ROOT` where the scoring job runs; scoring refuses an
artifact whose hash differs from the registry.

## Proof on synthetic data (2026-10-03)

`python -m sews_services.training.synthetic --students 400 --seed 7` (development only) created a separate synthetic
institution: one cohort over four completed semesters and the current one — 310,844 attendance records, 11,070
submissions, 204,559 LMS events; 78 withdrawals; adverse prevalence 16.9–22.5% per term. Then
`train --data-provenance synthetic` with the default configuration (3 models × 3 decision points, about 3 minutes):

- Split: train 2024-25 odd + even (770 students), validation 2025-26 odd (351), test 2025-26 even (332, prevalence
  0.169); calibration check present; leakage guard passed at days 30, 60 and 90 for all 4 terms.
- Selected (random forest at every decision point), held-out test:

| Decision point | Test PR-AUC [95% CI] | ROC-AUC | Brier | ECE |
|---:|---|---:|---:|---:|
| day 30 | 0.709 [0.583, 0.810] | 0.914 | 0.083 | 0.028 |
| day 60 | 0.705 [0.587, 0.806] | 0.919 | 0.082 | 0.041 |
| day 90 | 0.719 [0.592, 0.814] | 0.909 | 0.082 | 0.037 |

- The three models were registered as `development` / `synthetic` (not tied to any institution). The day-60 model
  then scored all 322 active students of the current term (`score --model-version ...`, development only): 181
  stable, 76 watch, 38 elevated, 27 high; the recommendation job created suggestions from them.
- Full report: `ml/reports/inst-v1-20261002T183834Z/report.md` (aggregates only; checked to contain none of the
  400 synthetic student ids).

**These numbers only show that the pipeline works.** The generator builds the outcome from the same behaviour the
features measure, so real data will score differently — and a synthetic model can never be approved for production.
Tests: `services/tests/test_institutional_training.py` (15, on a smaller synthetic history).
