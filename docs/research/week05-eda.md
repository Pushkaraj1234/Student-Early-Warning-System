# Week 5 — Data cleaning and exploratory data analysis (OULAD)

Status 2026-10-03. Generated report (every number below comes from it):
[`ml/reports/eda-oulad-20261003T093048Z/report.md`](../../ml/reports/eda-oulad-20261003T093048Z/report.md), with 9 CSV
tables and 5 charts. Reproduce with `ml/.venv/Scripts/python -m ml.analysis.eda --config ml/configs/oulad_v2.json`
(code: `ml/analysis/eda.py`; tests: `ml/tests/test_eda.py`).

> **Provenance: BENCHMARK** (Open University, UK, 2013–14, CC BY 4.0). Not Indian data.
> **Deliberately not done:** any feature–outcome relationship. H2 and H6 are pre-registered
> ([week 4](week04-research-design.md)) and are tested in week 6; exploring them first would undermine the tests.
> Feature tables are profiled on the **training presentations only** (2013B, 2013J), so the test data stays unseen.

## 1. The data

| File | Rows | Missing cells |
|---|---:|---|
| studentInfo (one row per registration) | 32,593 | `imd_band` 1,111 |
| studentRegistration | 32,593 | `date_registration` 45, `date_unregistration` 22,521 (expected: most students never unregister) |
| studentAssessment | 173,912 | `score` 173 |
| assessments | 206 | `date` 11 (exams without a fixed date) |
| studentVle (clicks) | 10,655,280 | none; **787,170 exact duplicate rows** |
| vle, courses | 6,364 / 22 | `week_from`/`week_to` 5,243 each (unused) |

32,593 registrations belong to **28,785 distinct students**; 3,538 students have more than one registration — the
reason every confidence interval in this project resamples *students*, not rows. **3,365 registrations (10.3%) have no
learning-platform activity at all.**

Adverse-outcome share (Fail or Withdrawn) per presentation: 2013B 0.553 · 2013J 0.494 · 2014B 0.570 · 2014J 0.515.
At a decision point the share is lower (e.g. 0.381 in the day-60 test set), because students who already withdrew are no
longer predicted.

## 2. Data-quality issues and how each is handled

| Issue found | Count | Handling in the pipeline (verified in `ml/features/oulad_features.py`) |
|---|---:|---|
| Exact duplicate click rows | 787,170 | Summed per student and day, i.e. treated as separate interactions. Whether they are true repeats cannot be decided from the data — **limitation** |
| Withdrawn but no unregistration date | 93 | Stay in every decision point's population (cannot be removed without a date); label = adverse |
| Unregistration date but result not "Withdrawn" | 9 | Leave the population after the unregistration date; label from `final_result` |
| Missing registration date | 45 | Treated as registered (population rule) |
| Missing assessment score | 173 | Counted as submitted; excluded from score features |
| Assessments with no due date (exams) | 11 | Excluded from "due" and score features |
| Banked submissions (carried from an earlier attempt) | 1,909 | Kept out of current work; counted separately as `banked_assessment_count` |
| Scores outside 0–100 | 0 | — |
| Inconsistent label: IMD band `10-20` (all others end in `%`) | 1 label | Audit attribute only (never a model input); reports must show it as "10-20%" |

**No rows are deleted.** Each issue is handled by an explicit rule, so the same rule applies to future data.

## 3. Distributions and outliers

| Variable (raw) | Median | Mean | Max | Skewness | Far-out share* |
|---|---:|---:|---:|---:|---:|
| Total VLE clicks per registration | 739.5 | 1,355.0 | 24,139 | 2.94 | 2.3% |
| Active VLE days per registration | 47 | 61.9 | 286 | 1.11 | 0% |
| Assessment score | 80 | 75.8 | 100 | −1.08 | 0% |
| Submission delay (days; negative = early) | −1 | −16.7 | 372 | −2.78 | 14.2% |

\*Beyond Tukey's outer fences (Q1 − 3·IQR, Q3 + 3·IQR).

- Click counts are **heavily right-skewed** (chart: log scale) — a few very active students. They are legitimate, so they
  are **kept**: tree models are insensitive to scale, and logistic regression standardises its inputs.
- Scores are **left-skewed** (most students score well; median 80).
- Submission delay has long tails (very early or very late submissions); the per-student mean delay is used as a
  feature and the tails are kept.

## 4. Missing values in the features (informative, not errors)

At a decision point a feature is missing when it is **not defined yet**, which is information in itself (training
presentations):

| Feature | Day 30 | Day 60 | Day 90 | Why |
|---|---:|---:|---:|---|
| Score features (e.g. `mean_score_to_date`) | 83.7% | 15.7% | 8.6% | Scores are released about 14 days after submission; few exist by day 30 |
| `score_trend_per_30d` | 98.2% | 63.4% | 21.7% | Needs at least two released scores |
| `late_submission_rate` (and mean delay) | 24.2% | 10.1% | 8.3% | No submission yet |
| `completion_rate_last_30d` | 15.7% | 8.1% | 35.8% | Undefined when no assignment fell due in the last 30 days (common at day 90) |
| `days_since_last_activity` | 3.4% | 2.3% | 2.2% | No activity yet |
| Other engagement features (clicks, active days, quiz, forum) | 0% | 0% | 0% | Zero activity is a value, not missing |

Exact values per feature: the report's day-30/60/90 tables and the missing-values chart.
Handling: logistic regression and random forest fill gaps with the training median **and add a "was missing"
indicator column**; XGBoost handles missing values natively. This is also why the pre-registered H2c tests the score
family at **day 90**, when scores exist.

## 5. Feature engineering and redundancy

37 features in five families: engagement 17, quiz 5, assignment 6, academic scores 5, prior record 4 (definitions:
`ml/features/definitions.py`; data rules: [data-contract.md](../ml/data-contract.md)). Every feature is computed **as
of** the decision point, and the leakage guard verifies this before any training.

Near-duplicate pairs at day 60 (Spearman |ρ| ≥ 0.9, between features only — not with the outcome):
assignment completion rate ↔ completion rate in last 30 days (0.980); clicks in last 14 days ↔ content clicks in last 14
days (0.952); mean score ↔ last score (0.946); score trend ↔ change from first score (0.935); mean score ↔ course-relative
score (0.924); clicks to date ↔ clicks in last 30 days (0.915); clicks to date ↔ active days to date (0.907).
Consequences: tree models are unaffected; logistic-regression **coefficients** of these pairs are not individually
interpretable (predictions are unaffected); in explanations, correlated features share credit, so related factors
should be read together.

## 6. Who is in the data (audit attributes — never model inputs)

Gender: M 54.8%, F 45.2% · Age: 0–35 70.4%, 35–55 28.9%, 55+ 0.7% · Declared disability 9.7% · IMD band missing 3.4% ·
Highest education: A level or equivalent 43.1%, lower than A level 40.4%, HE qualification 14.5%.
The 55+ group (0.7%) is too small for a reliable subgroup audit (see [fairness.md](../ml/fairness.md)).

## 7. Charts (in the report folder)

1. `clicks_per_registration.png` — total clicks per registration, log scale.
2. `assessment_scores.png` — score distribution.
3. `submission_delay.png` — submission timing relative to the due date.
4. `feature_correlation_day60.png` — feature–feature correlation heatmap.
5. `feature_missingness.png` — missing share per feature at days 30, 60 and 90.

## 8. Notes

- `matplotlib` 3.11.2 was added to `ml/requirements.lock` for the charts (pip-audit: no known vulnerabilities). With it
  installed, the `shap` library emits three third-party deprecation warnings during tests; they come from shap's own
  colour module, not from project code.
- Excel / Power BI (course tools) can open the CSV tables in `tables/` directly.
