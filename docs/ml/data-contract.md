# ML Data Contract (v1)

Enforced in code by `ml/data/contract.py::validate_feature_table` before every training or evaluation run.

## Prediction-time feature table

One row = one prediction unit (a student in a course context) at one prediction date.

| Column | Type | Rule |
|---|---|---|
| `student_id` | string | Pseudonymous source identifier; not null |
| `context_id` | string | Course/term context (OULAD: `module-presentation`); not null |
| `prediction_date` | datetime64 | The cutoff. **Every feature uses only information available on or before it.** For OULAD this is a *nominal* date (presentation start: 1 Feb for "B", 1 Oct for "J", plus the cutoff day) because OULAD records only relative days |
| `cutoff_day` | int ≥ 0 | Days since the context start |
| `split_group` | string | Time-ordered group used for out-of-time splits (OULAD: presentation) |
| feature columns | float | Numeric, finite; NaN = "not available at prediction time"; booleans and strings rejected |
| `target` | int | 0/1 only. v1: 1 = `final_result ∈ {Fail, Withdrawn}` |
| `audit_*` | string | Subgroup attributes for fairness audits only; rejected if used as features |

`(student_id, context_id, prediction_date)` must be unique.

## Temporal rules (tested in `ml/tests/test_features_temporal.py`)

- VLE activity: rows with `date ≤ cutoff`.
- Submissions: `date_submitted ≤ cutoff`.
- Scores: `date_submitted + score_release_lag_days ≤ cutoff` (OULAD has no release dates; the lag is a
  configured **assumption**, 14 days in v1).
- Population: registered on/before the cutoff (or unknown) and **not** unregistered on/before it.
  `date_unregistration` is used only for this filter; `final_result` only for the target.
- Adding any record dated after the cutoff leaves every feature unchanged (asserted).

## Feature set `oulad-fs-1.0.0` (21 features)

Engagement: `clicks_to_date`, `active_days_to_date`, `clicks_last_{7,14,30}d`, `clicks_trend_{7,14,30}d`
(change vs the preceding equal window, per day), `clicks_change_from_baseline`, `days_since_last_activity`.
Assignment: `assessments_due_to_date`, `assignment_completion_rate`, `late_submission_rate`,
`mean_submission_delay_days`. Academic: `mean_score_to_date`, `last_score`, `course_relative_score`.
Prior: `num_of_prev_attempts`, `studied_credits`, `registration_lead_days`, `banked_assessment_count`.
Definitions: `ml/features/definitions.py`.

**Attendance features are absent**: OULAD has no attendance data and none are fabricated.

## Inference contract (`ml/inference/schemas.py`)

Request: `student_id`, `prediction_date`, `features` (every model feature; number or `null`),
optional `model_version`, `top_k` (1–20).
Response: `prediction_id`, `model_version`, `risk_probability`, `risk_level`
(`stable|watch|elevated|high`, from thresholds stored in the artifact), `top_factors`
(`feature`, `contribution`, `direction`, `rank`, `feature_value`), plus `feature_version`,
`dataset_version`, `data_provenance`, `explanation_units`.
Structured error codes: `invalid_request`, `empty_input`, `missing_features`, `unknown_features`,
`invalid_type`, `non_finite_value`, `invalid_model_version`, `model_not_found`, `model_unavailable`,
`model_not_permitted`, `internal_error`. Raw input values are never echoed.
