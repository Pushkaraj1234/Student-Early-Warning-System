# EWS v3 — weekly longitudinal model: results

Status 2026-10-08. Run `oulad-ts-v3-20261005T192442Z`
([report](../../ml/reports/oulad-ts-v3-20261005T192442Z/report.md), `results.json`, 4 charts). Plan, feature list and
pre-specified comparisons: [ews-v3-longitudinal-plan.md](../research/ews-v3-longitudinal-plan.md). Reproduce:
`ml/.venv/Scripts/python -m ml.longitudinal.experiment --config ml/configs/longitudinal_v3.json` (code
`ml/longitudinal/`, tests `ml/tests/test_longitudinal_*.py`).

> **Provenance: BENCHMARK** (OULAD, UK, 2013–14). Not Indian data; no model here is approved for real students.

## 1. Data

757,357 student-weeks (29,177 registrations, weeks 1–30), 55 features (37 v2 + 18 longitudinal). The leakage guard
(rebuilding a week from data cut at its cutoff gives identical features) passed at weeks 2, 4, 8, 13, 20 and 30.
Test (2014J): 252,842 student-weeks of 10,201 registrations; Fail/Withdrawn 35.3%, withdraw within 4 weeks 3.1%,
within 8 weeks 5.5%. Retention (Kaplan–Meier, training presentations): 96.7% at week 4, 90.5% at week 13, 81.8% at
week 30; at week 13, 86.3% of the least active week-1 tertile vs 93.4% of the most active.

## 2. Fail or Withdrawn, predicted every week (test 2014J, 95% student-bootstrap intervals)

| Model | Test PR-AUC | ROC-AUC | Brier | ECE |
|---|---:|---:|---:|---:|
| Random forest (v3 features) | **0.775** [0.765, 0.787] | 0.839 | 0.153 | 0.054 |
| Ensemble (XGBoost + LSTM) — *selected on validation* | 0.770 [0.758, 0.781] | 0.838 | 0.156 | 0.055 |
| XGBoost (v3 features) | 0.769 [0.758, 0.781] | 0.836 | 0.157 | 0.050 |
| GRU / LSTM / TCN | 0.765 / 0.762 / 0.762 | 0.836 / 0.834 / 0.837 | ≈ 0.158 | 0.042–0.062 |
| XGBoost (v2 features) | 0.764 [0.752, 0.776] | 0.833 | 0.159 | 0.051 |
| L1 logistic (LASSO, v3) | 0.754 [0.742, 0.766] | 0.827 | 0.159 | 0.042 |
| Prevalence (chance) | 0.353 | 0.500 | 0.230 | — |

**Every model is within 0.02 PR-AUC of every other.** Rolling-origin CV agrees (mean test PR-AUC over three
time-ordered folds: XGBoost 0.817, LSTM 0.814, LASSO 0.808).

## 3. Pre-specified comparisons (Holm-corrected, fixed before the run)

| ID | Comparison | Effect [95% CI] | Holm p | Statistical result | Practical reading (pre-set rule) |
|---|---|---|---:|---|---|
| P1 | v3 longitudinal features vs v2 features (XGBoost) | +0.0053 [0.0042, 0.0065] | 0.002 | supported | **practically negligible** (< 0.01) |
| P2 | best sequence model (LSTM) vs XGBoost | −0.0078 [−0.0102, −0.0054] | 0.002 | supported (a difference) | LSTM is slightly **worse**; negligible |
| P4 | 2-week persistence rule lowers the student false-alarm rate | 0.099 [0.091, 0.107] lower | 0.002 | supported | real reduction, but it costs recall (§4) |
| P5 | LASSO degrades less than XGBoost on an unseen module | median −0.002, 6 of 7 modules | 0.055 | **not supported** | direction as expected, effect tiny for both |

The honest reading:

1. **The new longitudinal features and the deep sequence models did not materially improve accuracy** on OULAD.
   The 37 v2 features (7/14/30-day windows, trends, completion, scores) already capture most of the trajectory;
   the 18 new ones add 0.005 PR-AUC. GRU/LSTM/TCN learn the same signal as gradient-boosted trees, no better.
   This is a useful negative result: SEWS does not need deep sequence models to work well, and the simpler,
   explainable models remain the right default.
2. **Some of the new features do matter to the model:** `difficulty_adjusted_score` and `on_time_ratio_to_date` are
   in XGBoost's top 6 SHAP features (with assignment completion, course-relative score, days since last activity
   and score trend). They largely replace information that other features already carried.
3. **Robustness to an unseen module:** both models lose very little (LASSO ≤ 0.009, XGBoost ≤ 0.036 PR-AUC; the
   largest loss is XGBoost on module CCC). The "simple models degrade less" claim from the team's report pointed
   the right way (6 of 7 modules) but was not significant.

## 4. Turning weekly risk into alerts (ensemble, thresholds from validation)

| Policy at the F1 threshold (0.362) | Students at risk alerted | Students not at risk ever alerted | Median lead time | Alert switches per student |
|---|---:|---:|---:|---:|
| raw weekly threshold | 98.2% | 85.4% | 23 weeks | 1.78 |
| 2 consecutive weeks | 79.8% | 75.5% | 33 weeks | 1.83 |
| smoothed risk (EWMA) | 97.8% | 82.5% | 23 weeks | 1.15 |

**Important finding:** a threshold chosen for single student-weeks (F1 on student-weeks: recall 0.80, precision
0.59) is far too low for *student-level* alerting — over 30 weeks, 85% of students who end up passing cross it at
least once. The persistence rule removes 10 points of false alarms but loses 18 points of recall, so the pre-set
deployment rule kept the raw policy. Smoothing (EWMA) is the better trade-off: almost the same recall, fewer false
alarms, about a third fewer alert switches (1.15 vs 1.78) and risk-tier changes (1.93 vs 2.91). For SEWS this
means: alert thresholds must be set on **students over a term** (or by mentor capacity, e.g. the top 10%), not on
student-weeks. Lead times are long (median 23 weeks before the outcome), so earlier alerts are possible.

## 5. Other results

- **Calibration:** raw XGBoost probabilities are already reasonable (ECE 0.050); isotonic 0.049, Platt 0.054.
- **Uncertainty (MC dropout, LSTM):** uncertainty tracks errors well (Spearman 0.66 between uncertainty and error).
  The most certain 80% of predictions have PR-AUC 0.805, the least certain 20% only 0.520 — uncertain predictions
  should go to a mentor for judgement rather than trigger an automatic alert.
- **Fairness:** on the weekly panel the female–male recall gap is small (−0.010 [−0.030, 0.010]); per-group
  thresholds over-corrected it (+0.043), so they should not be applied blindly. Larger gaps remain for age 55+
  (recall gap 0.088) and unknown deprivation band (0.106). Using demographics as inputs changed PR-AUC by 0.002
  and widened the gender gap — support for keeping them out of the model.
- **Counterfactuals (week 8):** for 23% of flagged students one or two actionable changes bring the risk below the
  threshold — most often submitting on time, completing the due assessments, or being active in the last two
  weeks. For the rest, no small change suffices (the risk rests on accumulated history).
- **Withdrawal within 4 / 8 weeks** stays hard: test PR-AUC 0.11 / 0.14–0.16 against 3.1% / 5.5% chance. SMOTE
  never helped; class weights helped XGBoost slightly on test but not on validation. The weekly hazard model
  ranks *when* students leave about as well as the direct model (C-index 0.61 at week 4, 0.67 at week 8).
  Strongest weekly hazard factors: an inactivity streak, low assignment completion, low on-time ratio, higher
  study load.
- **Drift:** `assessments_due_to_date` differs strongly between training and test presentations (PSI 0.83) — the
  2014J assessment calendar is different. Calendar-dependent features need monitoring in production.
- **Training note:** all 12 sequence models stopped at epoch 9; retraining the best LSTM with two other seeds
  stopped at epoch 8 with validation loss flat from epoch 6, so the common stopping point came from the shared
  batch order, not from a training error.

## 6. What this changes in SEWS

1. Keep the explainable tabular models as the default; add sequence models only if institutional data shows a gain.
2. Set alert thresholds at the student level (or by mentor capacity), use smoothed risk, and route uncertain
   predictions to mentors.
3. Monitor calendar-dependent features for drift.
4. The external datasets ([external-datasets.md](external-datasets.md)) repeat the main pattern: each new
   assessment result is the strongest signal, and simple models are competitive.
