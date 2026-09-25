# Risk trajectory

Status: implemented in migration `20260925000900_v2_longitudinal_monitoring.sql`; thresholds are
**provisional** until validated on institutional data. Verified by `supabase/tests/database/090_v2_trajectory_interventions_notifications.sql`.

## What it answers

A single risk estimate says little on its own. The trajectory says how the estimate has **changed** since the
previous estimate for the same student, so that mentors can see who is getting worse, not only who is high.

## How it is computed

A `BEFORE INSERT` trigger (`private.compute_risk_trajectory`) runs for every new row in
`public.risk_predictions`. Clients cannot write these columns; the database fills them.

1. Find the previous prediction for the **same student, same target and same model version**, with an earlier
   `prediction_date` (latest by `prediction_date`, then `scored_at`).
   - Different model versions are never compared: their probabilities are not on the same scale.
   - Different targets (academic, dropout, course failure, engagement) are separate series.
   - A second score on the same day is not compared with the first (the unique key
     `(student_id, prediction_date, model_version, target)` also prevents duplicates).
2. If there is no previous prediction: `trajectory = insufficient_history`; all change columns are `NULL`.
3. Otherwise:
   - `risk_delta = risk_probability − previous risk_probability` (rounded to 5 decimals)
   - `days_since_previous = prediction_date − previous prediction_date`
   - `risk_velocity_per_week = risk_delta / (days_since_previous / 7)`, **only if** the predictions are at least
     `min_days_for_velocity` days apart; otherwise `NULL` (short gaps make weekly rates unstable).
4. Classify (`private.classify_trajectory`):

| Condition (evaluated in order) | `trajectory` |
|---|---|
| no previous prediction | `insufficient_history` |
| `risk_delta ≤ −stable_band` | `improving` |
| `risk_delta < stable_band` | `stable` |
| velocity known and `≥ rapid_velocity_per_week` | `rapidly_increasing` |
| otherwise (rising, velocity below the limit or unknown) | `increasing` |

## Thresholds (single source of truth: `private.trajectory_thresholds()`)

| Parameter | Value | Meaning |
|---|---:|---|
| `stable_band` | 0.05 | Changes smaller than 5 percentage points of probability count as stable. |
| `rapid_velocity_per_week` | 0.10 | A rise of at least 10 percentage points per week is "rapid". |
| `min_days_for_velocity` | 7 | Velocity is only computed across at least 7 days. |

Rationale and limits: these are conservative starting values chosen so that routine noise between weekly scores
does not create alerts. They are **not** calibrated against outcomes: a validated model on institutional data is
needed to check how often each class precedes an adverse outcome. Changing them means a new migration that
replaces `private.trajectory_thresholds()`; existing rows keep the class they were given at insert time.

## Where it is used

| Consumer | Use |
|---|---|
| `private.notify_risk_change` (after insert, **academic target only**) | Alerts the student's active mentors when the trajectory is `increasing` or `rapidly_increasing`, or when the level becomes `high` from something else. Push previews stay generic ("You have a new update in SEWS."). |
| `public.get_mentor_caseload()` | Latest academic prediction per mentee including `trajectory` and `risk_delta`. |
| Mobile, mentor | Exact class ("Rapidly increasing"), probability and change. |
| Mobile, student | Plain wording only: Improving / Steady / Worth a look / Worth a look soon / Not enough history yet. No probability. |
| Rule engine (`services/.../recommendations/engine.py`) | `elevated` + `rapidly_increasing` → mentor meeting; `improving` lowers priority. |

## Limitations

- Trajectory compares model outputs, not the student's real situation; a model change resets the series.
- Irregular scoring intervals change what a delta means; velocity is withheld for gaps under 7 days only.
- Thresholds are provisional (see above).
