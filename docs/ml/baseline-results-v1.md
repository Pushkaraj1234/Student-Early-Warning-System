# Baseline Results v1 — OULAD (benchmark)

> **Provenance: BENCHMARK — The Open University, United Kingdom, 2013–2014 (CC BY 4.0, UCI dataset 349).**
> These results describe how the method behaves on this UK dataset. They are **not** evidence about Indian
> students, and **no model here is approved to score real students** (docs/ml/ml-strategy.md §5).

- Run: `oulad-baseline-v1-20260923T222002Z` (full report: `ml/reports/oulad-baseline-v1-20260923T222002Z/report.md`, metrics: `metrics.json`)
- Dataset version: `oulad-f853d3b6b35de756` (content hash of the 7 source CSVs; download SHA-256 `f2ed1902…c6d3e4`, 46,748,244 bytes; 32,593 registrations — the bundled `OULAD.names` says 32,953)
- Feature version `oulad-fs-1.0.0`; target = Fail or Withdrawn; score release lag assumption = 14 days
- Out-of-time split: train 2013B + 2013J, validation 2014B, test 2014J (test touched once)
- Libraries: Python 3.13.2, numpy 2.5.3, pandas 3.0.6, scikit-learn 1.9.1, xgboost 3.4.1, shap 0.52.0

## Held-out test (2014J), calibrated probabilities, 95% cluster-bootstrap CIs

| Day | Test prevalence | Model | PR-AUC | ROC-AUC | Recall / precision, top 10% flagged |
|---|---|---|---|---|---|
| 30 | 0.407 | Logistic regression (**selected**) | 0.656 [0.641, 0.672] | 0.712 [0.702, 0.722] | 0.203 / 0.825 |
| 30 | | Random forest | 0.668 [0.652, 0.682] | 0.726 [0.716, 0.735] | 0.205 / 0.834 |
| 30 | | XGBoost | 0.649 [0.634, 0.666] | 0.718 [0.708, 0.728] | 0.191 / 0.778 |
| 60 | 0.381 | Logistic regression | 0.707 [0.693, 0.722] | 0.756 [0.746, 0.767] | 0.243 / 0.924 |
| 60 | | Random forest | 0.716 [0.702, 0.731] | 0.783 [0.774, 0.793] | 0.238 / 0.908 |
| 60 | | XGBoost (**selected, active**) | 0.711 [0.696, 0.726] | 0.781 [0.771, 0.791] | 0.235 / 0.897 |
| 90 | 0.360 | Logistic regression (**selected**) | 0.766 [0.753, 0.780] | 0.820 [0.811, 0.829] | 0.267 / 0.963 |
| 90 | | Random forest | 0.775 [0.763, 0.788] | 0.825 [0.816, 0.835] | 0.267 / 0.961 |
| 90 | | XGBoost | 0.764 [0.752, 0.777] | 0.819 [0.810, 0.828] | 0.270 / 0.971 |

Precision/recall/F1 at the validation-chosen threshold, confusion matrices, per-class metrics, risk-level
distributions and subgroup audits are in the full report.

## Findings

1. **Signal improves with time**: PR-AUC rises from ~0.66 (day 30) to ~0.77 (day 90) — consistent with RQ1.
2. **Models are close**: at every cutoff the three models' test CIs overlap. Selection used validation
   data only: best validation PR-AUC, then the most interpretable model within 0.01 (logistic
   regression at days 30 and 90; at day 60 logistic regression was 0.015 behind, so XGBoost was chosen).
3. **Class imbalance is mild** (36–48% positive). Balanced class weights never improved validation
   PR-AUC by more than 0.005, so unweighted training was kept everywhere. SMOTE was not used.
4. **Distribution shift**: validation (2014B) scores are 0.08–0.11 PR-AUC higher than test (2014J);
   prevalence also differs (e.g. 0.457 vs 0.381 at day 60). A model tuned on one cohort does not transfer
   perfectly to the next — even within the same institution.
5. **Calibration did not transfer**: Platt (sigmoid) calibration fitted on 2014B made test calibration
   *worse* for every model and cutoff (e.g. day 60 XGBoost ECE 0.079 → 0.086; day 30 LR 0.060 → 0.091).
   Probabilities should not be interpreted as exact likelihoods; risk *levels* (rank-based) are the
   intended output. Recalibration on the most recent completed cohort is required before any use.
6. **Stability**: seed-to-seed validation PR-AUC std ≤ 0.001. Mean pairwise Jaccard overlap of the
   top-5 SHAP feature sets across 5 seeds was 1.00 for 6 of the 9 model/cutoff runs; it was 0.80 for
   XGBoost at days 30 and 90 and 0.77 for random forest at day 90, so the lower-ranked factors can differ
   between retrainings.
7. **Most influential features** (selected models): course-relative score, mean score, assignment
   completion, submission timing, recent VLE activity. These are associations, not causes.

## Limitations

Benchmark UK data only; nominal dates; assumed score-release lag; calibration/threshold fitted on the same
validation split; validation overlaps the end of 2013J in calendar time; subgroup audit attributes
(gender, age band, disability, IMD band) are UK-specific and not transferable categories.
