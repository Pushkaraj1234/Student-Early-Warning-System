# Intervention outcomes

Status: tables and workflow in migrations `20260925000900` (V2) and `20260925001000` (V3); job in
`services/sews_services/jobs/outcomes.py` (method `outcomes-1.0.0`). Verified by
`supabase/tests/database/090_*.sql`, `100_v3_checkins_outcomes.sql` and `services/tests/test_jobs.py`.

**These measures are descriptive. They must never be reported as the effect of an intervention.**

## What is recorded

### 1. The intervention's own history (`public.interventions`)

The status workflow is enforced by the database; timestamps are set by the trigger, never by clients.

| Event | Status | Recorded as |
|---|---|---|
| Rule engine suggests | `recommended` (hidden from the student) | `created_at`, `source = model_rule`, `rule_id`, `rule_version` (schema 4.1.0+), `reason`, `priority` |
| Staff create or approve (offer) | `pending` | `offered_at`, `reviewed_by`/`reviewed_at` for approvals |
| Assigned to a staff member | (any open status) | `assigned_to`, `assigned_at` |
| Student accepts | `accepted` | `responded_at` |
| Student declines | `declined` | `responded_at`, `decline_reason` (not_needed, already_receiving_support, not_convenient, other) |
| Staff complete | `completed` | `completed_at`, `outcome` |
| Staff cancel | `cancelled` | `cancelled_at` |

Counts of offered / accepted / declined / completed come directly from these columns.

`outcome` (improved, no_change, worsened, not_assessed) is the **staff member's observation**. The app says so when
it is recorded: "Your observation only. It is not proof that the intervention caused a change."

### 2. Before/after indicators (`public.intervention_outcome_measures`)

Computed by `compute_outcomes` for every **completed** intervention and, as a descriptive comparison group, every
**declined** one.

| Window | Definition (dates in the institution's time zone) |
|---|---|
| Baseline | the 28 days ending the day before the offer (`offered_at`, or `created_at` if never offered) |
| Follow-up | the 28 days starting the day after the anchor (`completed_at` for completed, `responded_at` for declined) |

A follow-up window is computed only after it has fully ended, so values never change later.

| Indicator | Definition in a window |
|---|---|
| `attendance_rate` | present + late ÷ (present + late + absent); excused sessions excluded |
| `assignment_completion_rate` | assignments due in the window that were submitted by the window's end ÷ assignments due (excused excluded) |
| `mean_score_pct` | mean of score ÷ max score × 100 for work graded in the window |
| `risk_probability` | mean academic risk probability of predictions dated in the window |

A value is `NULL` when the window has no data; nothing is imputed. Rows are unique per
(intervention, indicator, method version), so re-running the job is safe, and a new method gets a new version
instead of overwriting old rows.

Access: rows are readable by anyone who can see the intervention under RLS; only the service role writes them.

## Why these numbers are not causal

- **No control group.** Students who did not receive the intervention are not matched or randomised.
- **Self-selection.** Students choose to accept or decline; people who accept may differ in motivation or circumstance.
- **Selection on high risk.** Interventions start when indicators look bad, so later values tend to improve anyway
  (regression to the mean).
- **Timing.** Term calendars, exams and holidays change attendance and scores regardless of support.
- **Other support.** Students may receive help the system does not record.
- **Declined is not a control group.** The declined group is shown for context only; it differs from those who accepted.

Acceptable wording: "Among completed attendance follow-ups, median attendance was X before and Y after."
Not acceptable: "The follow-up improved attendance by Y − X."

## What would be needed for causal claims

A pre-registered evaluation design approved by the institution and an ethics review, for example randomised
or stepped-wedge rollout, or a carefully matched comparison with sensitivity analysis. None of this is implemented.

## Remaining work

- No scheduler runs `compute_outcomes` yet (tested library function only).
- No reporting screen summarises outcome measures yet; they are available in the database.
