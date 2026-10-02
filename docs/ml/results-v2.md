# Results v2 — OULAD benchmark, four targets (feature set `oulad-fs-2.0.0`)

> **Provenance: BENCHMARK — The Open University, United Kingdom, 2013–2014 (CC BY 4.0, UCI dataset 349).**
> These numbers describe how the method behaves on this UK dataset. They are **not** evidence about Indian
> students, and **no model here is approved to score real students** (docs/ml/ml-strategy.md §5).

- Run: `oulad-v2-20260924T003349Z` (full report: `ml/reports/oulad-v2-20260924T003349Z/report.md`; every number
  below is copied from its `metrics.json`). V1 baseline: `docs/ml/baseline-results-v1.md`.
- Dataset version `oulad-f853d3b6b35de756`; feature version `oulad-fs-2.0.0` (37 features, 16 more than V1;
  OULAD has no attendance data, so attendance features are absent); score release lag assumption 14 days.
- Temporal leakage guard passed at every decision point (features from the full data equal features from data
  truncated at the cutoff): day 30 (27,450 rows), day 60 (26,353), day 90 (25,558).
- Out-of-time split: train 2013B + 2013J, validation 2014B, test 2014J (test used once, for these numbers).
- Models: logistic regression, random forest, XGBoost; selection on validation PR-AUC only, preferring the
  more interpretable model within 0.010. Intervals: 95% cluster bootstrap over students.

## Targets

| Target | Definition (OULAD `final_result`) | Horizon |
|---|---|---|
| academic | Fail or Withdrawn | end of the module presentation |
| dropout | Withdrawn | end of the module presentation |
| course_failure | Fail (students who later withdraw count as 0) | end of the module presentation |
| engagement | no VLE activity at all in the 14 days after the cutoff | 14 days |

## Held-out test (2014J): selected model per target and decision point

Calibrated probabilities where the out-of-time calibration check applied calibration.

| Target | Day | Prevalence | Selected | PR-AUC | ROC-AUC | Brier | ECE | Calibrated |
|---|---:|---:|---|---|---|---:|---:|---|
| academic | 30 | 0.407 | Random forest | 0.671 [0.657, 0.686] | 0.728 [0.718, 0.738] | 0.207 | 0.070 | yes |
| academic | 60 | 0.381 | XGBoost (**active**) | 0.704 [0.689, 0.720] | 0.777 [0.767, 0.787] | 0.196 | 0.081 | yes |
| academic | 90 | 0.360 | Logistic regression | 0.769 [0.756, 0.783] | 0.822 [0.813, 0.832] | 0.159 | 0.043 | yes |
| dropout | 30 | 0.192 | Logistic regression | 0.331 [0.310, 0.353] | 0.672 [0.656, 0.685] | 0.146 | 0.018 | no |
| dropout | 60 | 0.157 | Logistic regression | 0.255 [0.239, 0.275] | 0.669 [0.654, 0.683] | 0.128 | 0.028 | yes |
| dropout | 90 | 0.129 | Random forest | 0.246 [0.223, 0.270] | 0.695 [0.679, 0.710] | 0.106 | 0.006 | no |
| course_failure | 30 | 0.215 | Random forest | 0.368 [0.350, 0.388] | 0.672 [0.658, 0.684] | 0.161 | 0.058 | yes |
| course_failure | 60 | 0.224 | XGBoost | 0.431 [0.410, 0.456] | 0.730 [0.718, 0.743] | 0.160 | 0.055 | yes |
| course_failure | 90 | 0.232 | Random forest | 0.534 [0.511, 0.559] | 0.789 [0.777, 0.801] | 0.146 | 0.052 | yes |
| engagement | 30 | 0.138 | Logistic regression | 0.605 [0.578, 0.632] | 0.881 [0.870, 0.889] | 0.080 | 0.011 | yes |
| engagement | 60 | 0.211 | Logistic regression | 0.725 [0.706, 0.744] | 0.891 [0.884, 0.898] | 0.105 | 0.055 | no |
| engagement | 90 | 0.202 | Logistic regression | 0.707 [0.684, 0.725] | 0.875 [0.865, 0.883] | 0.102 | 0.035 | yes |

PR-AUC must be read against prevalence (a random ranking scores the prevalence): dropout at day 60 is 0.255
against 0.157, a modest lift; academic at day 90 is 0.769 against 0.360.

## V1 → V2 (academic target, test PR-AUC, same split)

| Day | Logistic regression | Random forest | XGBoost |
|---:|---|---|---|
| 30 | 0.656 → 0.643 (−0.014) | 0.668 → 0.671 (+0.003) | 0.649 → 0.649 (0.000) |
| 60 | 0.707 → 0.690 (−0.017) | 0.716 → 0.722 (+0.006) | 0.711 → 0.704 (−0.007) |
| 90 | 0.766 → 0.769 (+0.003) | 0.775 → 0.779 (+0.004) | 0.764 → 0.760 (−0.004) |

The 16 features added in V2 (recent-window activity, trends, quiz/forum/content splits, score trends) did
**not** materially change academic performance: every difference is within ±0.02 and inside the bootstrap
intervals. They are justified by the trajectory and explanation features they enable, not by accuracy.

## Findings

1. **Signal grows with time** for academic (0.671 → 0.769) and course failure (0.368 → 0.534); dropout gets
   *harder* to rank as early withdrawers leave the cohort (prevalence 0.192 → 0.129).
2. **Withdrawal alone is poorly predicted** (PR-AUC 0.25–0.33). A dropout-only early warning from these
   features would flag many students who stay; academic (fail or withdraw) is the more usable target.
3. **Engagement (no activity in the next 14 days) is the most separable target** (ROC-AUC 0.875–0.891), but it
   is a short-horizon behavioural signal, not an outcome.
4. **The calibration rule is fragile.** Calibration is applied only if an out-of-time check improves both Brier
   and ECE. On the test period, that decision agreed with what calibration actually did to both metrics for
   **20 of 36** models (all three models at all 12 points). Calibration must be re-checked on each
   institution's own data, not inherited from the benchmark.
5. **Cohort shift is real even within one institution**: the selected model's validation (2014B) PR-AUC is
   higher than its test (2014J) PR-AUC at all 12 points (by 0.002 to 0.177), so a model must be re-validated
   on every new cohort before use.

## Cross-module proxy (academic, day 60, logistic regression)

Report: `ml/reports/cross-module-academic-d60-20260924T005225Z/report.md`. Each of the 7 OULAD modules is held out
of training in turn and compared with a model that saw it. Mean / worst degradation on the unseen module:
PR-AUC 0.015 / 0.045, ROC-AUC 0.011 / 0.033, Brier 0.022 / 0.066, **ECE 0.045 / 0.151** (module EEE: 0.114 →
0.265). Ranking transfers reasonably between modules; **calibration does not**. This is a cross-*module* check
within one UK institution — not cross-institution validation, and not evidence about Indian institutions.

## What these results do not show

- Nothing about Indian students, Indian institutions, attendance-based features or the institutional feature set
  `inst-fs-1.0.0` (no institutional training data exists yet).
- Nothing causal: feature contributions are associations (docs/ml/ml-strategy.md).
- Subgroup behaviour is summarised in `docs/ml/fairness.md`.
