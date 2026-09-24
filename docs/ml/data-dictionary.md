# Data Dictionary

> Status: **PROPOSED v0.1**. No feature below is implemented. Feature set version to be assigned on first implementation: `fs-0.1.0`.
> Every feature is defined **as of a cutoff time *t***. "Window" means the interval (*t* − *w*, *t*].

## 1. Canonical (institution-agnostic) features — planned

| Feature | Type | Definition (as of *t*) | Source table | Leakage notes |
|---|---|---|---|---|
| `attendance_rate_to_date` | float [0,1] | present ÷ (present + absent) sessions with `session_date ≤ t` and `recorded_at ≤ t`. Excused sessions are excluded from both counts | `attendance_records` | Must not use the end-of-term summary |
| `attendance_rate_last_14d` | float [0,1] | Same as above, restricted to a 14-day window | `attendance_records` | Window length is a versioned parameter |
| `attendance_trend` | float | Slope of weekly attendance rate up to *t* (null if < 3 weeks of data) | `attendance_records` | |
| `consecutive_absences` | int ≥ 0 | Longest current run of absences ending at *t* | `attendance_records` | |
| `assessments_due_to_date` | int ≥ 0 | Assessments with `due_at ≤ t` | `assessments` | |
| `missed_submission_rate` | float [0,1] | Due assessments with no submission by *t* ÷ assessments due | `assessments`, `assessment_results` | A late submission after *t* must not be counted |
| `late_submission_rate` | float [0,1] | Submissions made after `due_at` ÷ submissions, counting only those submitted ≤ *t* | `assessment_results` | |
| `mean_released_score_pct` | float [0,100] | Mean of score ÷ max_score for results with `released_at ≤ t` (null if none) | `assessment_results` | **Grades released after *t* are excluded**, even if the submission was earlier |
| `weighted_score_to_date` | float | Weight-adjusted released scores up to *t* | `assessment_results`, `assessments` | |
| `engagement_active_days_14d` | int | Days with ≥ 1 engagement event in a 14-day window | `engagement_events` | Only if an LMS source exists **[OPEN]** |
| `engagement_trend` | float | Slope of weekly engagement up to *t* | `engagement_events` | |
| `prior_term_gpa` | float | GPA of the most recent **completed** term before the term containing *t* | `students` / results **[OPEN]** | Previous terms only |
| `prior_attempts` | int ≥ 0 | Earlier attempts of the same course | enrolments **[OPEN]** | |
| `weeks_elapsed` | int | Whole weeks between the term start and *t* | `academic_terms` | Needed if a single model covers several decision points |

**Missing values:** a null is kept as null. The model handles it natively (XGBoost) or through a pipeline imputer fitted on training data only. A missing-indicator feature is added where missingness itself is informative (e.g. `no_released_scores_yet`).

## 2. Attributes excluded from model inputs by default

These may be stored **only** under the restricted-access rules, and **only** if used for fairness auditing (RQ4) with approval:
gender, caste/category, religion, disability status, family income, region or urban/rural indicator, age.

These are never collected: health or medical details, biometrics, precise location.

## 3. Label definitions

| Label | Definition | Status |
|---|---|---|
| `y_course_fail` | 1 if the student fails ≥ 1 course in the term | candidate |
| `y_gpa_below` | 1 if term GPA < institution threshold | candidate |
| `y_attendance_shortfall` | 1 if final attendance < institution eligibility threshold | candidate; high label-proximity risk |
| `y_withdraw` | 1 if withdrawn before term end | candidate |

The primary label is **[OPEN]**. See `problem-definition.md` §3.

## 4. Benchmark mapping — OULAD (UK; `benchmark` tier)

The column names below are those published with OULAD. **They must be checked against the actual downloaded files before any code relies on them.**

| OULAD file | Columns used | Maps to | Leakage notes |
|---|---|---|---|
| `studentInfo.csv` | `code_module`, `code_presentation`, `id_student`, `num_of_prev_attempts`, `studied_credits`, `final_result` | `prior_attempts`; label | `final_result` is the **label only**. Demographic columns (`gender`, `region`, `highest_education`, `imd_band`, `age_band`, `disability`) are excluded from the inputs by default and used only for the subgroup audit |
| `studentRegistration.csv` | `date_registration`, `date_unregistration` | exclusion rule | `date_unregistration` is a **direct leak** for withdrawal. It is used only to exclude students who had already left before *t* |
| `assessments.csv` | `id_assessment`, `assessment_type`, `date`, `weight` | `assessments_due_to_date` | `date` is the due day, counted from module start |
| `studentAssessment.csv` | `id_assessment`, `id_student`, `date_submitted`, `is_banked`, `score` | submission and score features | There is no release date, so a release lag must be assumed and documented (sensitivity analysis). Banked results come from earlier presentations and are treated as prior record |
| `studentVle.csv` | `id_student`, `id_site`, `date`, `sum_click` | engagement features | Only rows with `date ≤ t` are used |
| `vle.csv` | `id_site`, `activity_type` | engagement breakdown (optional) | |

Dates in OULAD are integers: **days relative to the module presentation start**. They can be negative. Cutoffs for the benchmark are therefore expressed in days, not calendar dates.

## 5. Synthetic data

- The generator's parameters (base rates, correlations, missingness) are documented next to the generator and versioned.
- Every synthetic record is tagged with a `synthetic` dataset version. The synthetic seed is **never** loaded into production.
