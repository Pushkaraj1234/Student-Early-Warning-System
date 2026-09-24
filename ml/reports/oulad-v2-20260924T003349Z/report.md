# SEWS baseline evaluation — oulad-v2-20260924T003349Z

> **Data provenance: BENCHMARK.** Open University Learning Analytics Dataset (United Kingdom, 2013-2014; CC BY 4.0; UCI id 349). NOT Indian data.
> These results describe method behaviour on this benchmark dataset. They are **not** evidence about Indian students and must not be presented as such. No model here is approved to score real students: that requires validation on institutional data (see docs/ml/ml-strategy.md §5).

- Dataset version: `oulad-f853d3b6b35de756`
- Feature version: `oulad-fs-2.0.0` (37 features)
- Targets: academic: final_result is Fail or Withdrawn; dropout: final_result is Withdrawn; course_failure: final_result is Fail (students who later withdraw count as 0); engagement: no VLE activity at all in the 14 days after the cutoff
- Temporal leakage guard (features from full data == features from data truncated at the cutoff): day 30 passed (27450 rows, 37 features); day 60 passed (26353 rows, 37 features); day 90 passed (25558 rows, 37 features)
- Score release lag assumption: 14 days (OULAD has no grade-release dates)
- Split (out-of-time): {'train': ['2013B', '2013J'], 'validation': ['2014B'], 'test': ['2014J']}
- Created: 2026-09-24T00:33:49+00:00; git commit: none (no commits yet)
- Libraries: {'python': '3.13.2', 'numpy': '2.5.3', 'pandas': '3.0.6', 'scikit-learn': '1.9.1', 'xgboost': '3.4.1', 'shap': '0.52.0'}
- Active model (primary decision point): `oulad-v2-20260924T003349Z-acad-xgb-d60`

Attendance features are absent because OULAD contains no attendance data.

## Target: academic — decision point day 30

Definition: final_result is Fail or Withdrawn. Horizon: end of the module presentation.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11759 | 5193 | 0.442 |
| validation | 2014B | 6493 | 3136 | 0.483 |
| test | 2014J | 9198 | 3742 | 0.407 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.735 | 0.731 | 0.209 |
| Logistic Regression | balanced | 0.735 | 0.731 | 0.209 |
| Random Forest | none (selected) | 0.748 | 0.740 | 0.205 |
| Random Forest | balanced | 0.748 | 0.740 | 0.206 |
| XGBoost | none (selected) | 0.738 | 0.733 | 0.209 |
| XGBoost | balanced | 0.736 | 0.731 | 0.211 |

- Logistic Regression: 'balanced' improved validation PR-AUC by only 0.0001 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- Random Forest: 'balanced' improved validation PR-AUC by only 0.0001 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- XGBoost: no re-weighting had the best validation PR-AUC.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.643 [0.628, 0.657] | 0.704 [0.693, 0.714] | 0.217 -> 0.217 | 0.075 -> 0.091 | 0.308 | 0.461 | 0.918 | 0.614 |
| Random Forest | 0.671 [0.657, 0.686] | 0.728 [0.718, 0.738] | 0.205 -> 0.207 | 0.058 -> 0.070 | 0.323 | 0.495 | 0.870 | 0.631 |
| XGBoost | 0.649 [0.634, 0.664] | 0.715 [0.706, 0.725] | 0.216 -> 0.214 | 0.073 -> 0.073 | 0.316 | 0.492 | 0.858 | 0.625 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.797 / 0.196 | 0.672 / 0.331 | 0.611 / 0.450 |
| Random Forest | 0.846 / 0.208 | 0.721 / 0.354 | 0.644 / 0.475 |
| XGBoost | 0.805 / 0.198 | 0.672 / 0.331 | 0.623 / 0.459 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.824 / 0.264 / 0.400 (5456) | 0.461 / 0.918 / 0.614 (3742) | 1441 | 4015 | 307 | 3435 |
| Random Forest | 0.814 / 0.392 / 0.529 (5456) | 0.495 / 0.870 / 0.631 (3742) | 2137 | 3319 | 488 | 3254 |
| XGBoost | 0.801 / 0.392 / 0.526 (5456) | 0.492 / 0.858 / 0.625 (3742) | 2137 | 3319 | 530 | 3212 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.447 / 0.622 / 0.811 | 4342 (0.47), obs 0.26 | 2603 (0.28), obs 0.45 | 1588 (0.17), obs 0.54 | 665 (0.07), obs 0.87 |
| Random Forest | 0.456 / 0.639 / 0.814 | 4574 (0.50), obs 0.25 | 2521 (0.27), obs 0.44 | 1408 (0.15), obs 0.61 | 695 (0.08), obs 0.88 |
| XGBoost | 0.449 / 0.651 / 0.792 | 4554 (0.50), obs 0.25 | 2311 (0.25), obs 0.48 | 1551 (0.17), obs 0.54 | 782 (0.09), obs 0.84 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.7347 | 0.0000 | 1.00 |
| Random Forest | 0.7483 | 0.0005 | 1.00 |
| XGBoost | 0.7329 | 0.0017 | 1.00 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | course_relative_score, last_score, late_submission_rate, active_days_to_date, quiz_clicks_last_30d |
| Random Forest | Tree SHAP (probability); 300 trees | mean_submission_delay_days, completion_rate_last_30d, assignment_completion_rate, active_days_to_date, days_since_last_activity |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | assignment_completion_rate, mean_submission_delay_days, days_since_last_activity, active_days_to_date, course_relative_score |

### Model selection

**Selected: Random Forest** (`oulad-v2-20260924T003349Z-acad-rf-d30`).

Validation PR-AUC best = 0.7482 (random_forest). Models within 0.010 of it: random_forest. Selected the most interpretable of these (random_forest; validation PR-AUC 0.7482, Brier 0.2047, seed PR-AUC std 0.0005).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.225 -> 0.217 | 0.081 -> 0.045 | yes |
| Random Forest | 2013B / 2013J / 2014B | 0.227 -> 0.222 | 0.087 -> 0.058 | yes |
| XGBoost | 2013B / 2013J / 2014B | 0.245 -> 0.227 | 0.120 -> 0.054 | yes |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3869 | 0.384 | 0.460 | 0.076 | 0.077 | 0.851 | 0.149 | 0.455 | 0.635 |
| M | 5329 | 0.423 | 0.485 | 0.062 | 0.066 | 0.882 | 0.118 | 0.524 | 0.588 |

Largest gaps between groups (max - min): recall 0.030 (M vs F); precision 0.069 (M vs F); false_positive_rate 0.047 (F vs M); false_negative_rate 0.030 (F vs M); pr_auc 0.085 (M vs F); calibration_gap 0.014 (F vs M); ece 0.011 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 6303 | 0.421 | 0.486 | 0.065 | 0.068 | 0.883 | 0.117 | 0.504 | 0.633 |
| 35-55 | 2808 | 0.376 | 0.450 | 0.074 | 0.077 | 0.840 | 0.160 | 0.474 | 0.560 |
| 55<= | 87 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.043 (0-35 vs 35-55); precision 0.029 (0-35 vs 35-55); false_positive_rate 0.073 (0-35 vs 35-55); false_negative_rate 0.043 (35-55 vs 0-35); pr_auc 0.023 (0-35 vs 35-55); calibration_gap 0.009 (35-55 vs 0-35); ece 0.009 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 8346 | 0.395 | 0.472 | 0.077 | 0.080 | 0.870 | 0.130 | 0.484 | 0.605 |
| Y | 852 | 0.526 | 0.497 | -0.029 | 0.070 | 0.864 | 0.136 | 0.595 | 0.651 |

Largest gaps between groups (max - min): recall 0.007 (N vs Y); precision 0.111 (Y vs N); false_positive_rate 0.046 (Y vs N); false_negative_rate 0.007 (Y vs N); pr_auc 0.090 (Y vs N); calibration_gap 0.106 (N vs Y); ece 0.009 (N vs Y)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 820 | 0.493 | 0.489 | -0.004 | 0.035 | 0.876 | 0.124 | 0.574 | 0.632 |
| 10-20 | 910 | 0.475 | 0.482 | 0.007 | 0.030 | 0.882 | 0.118 | 0.576 | 0.588 |
| 20-30% | 970 | 0.458 | 0.469 | 0.011 | 0.029 | 0.887 | 0.113 | 0.561 | 0.586 |
| 30-40% | 979 | 0.416 | 0.473 | 0.058 | 0.067 | 0.862 | 0.138 | 0.506 | 0.598 |
| 40-50% | 921 | 0.407 | 0.481 | 0.074 | 0.080 | 0.843 | 0.157 | 0.478 | 0.632 |
| 50-60% | 920 | 0.403 | 0.475 | 0.072 | 0.076 | 0.871 | 0.129 | 0.498 | 0.594 |
| 60-70% | 886 | 0.376 | 0.457 | 0.081 | 0.084 | 0.826 | 0.174 | 0.459 | 0.586 |
| 70-80% | 870 | 0.387 | 0.478 | 0.090 | 0.092 | 0.914 | 0.086 | 0.494 | 0.591 |
| 80-90% | 809 | 0.354 | 0.476 | 0.122 | 0.125 | 0.857 | 0.143 | 0.422 | 0.641 |
| 90-100% | 747 | 0.332 | 0.470 | 0.138 | 0.143 | 0.875 | 0.125 | 0.402 | 0.647 |
| unknown | 366 | 0.287 | 0.459 | 0.172 | 0.172 | 0.857 | 0.143 | 0.364 | 0.602 |

Largest gaps between groups (max - min): recall 0.088 (70-80% vs 60-70%); precision 0.211 (10-20 vs unknown); false_positive_rate 0.062 (90-100% vs 20-30%); false_negative_rate 0.088 (60-70% vs 70-80%); pr_auc 0.211 (10-20 vs unknown); calibration_gap 0.176 (unknown vs 0-10%); ece 0.143 (unknown vs 20-30%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | mean_submission_delay_days | psi | 0.221 | 0.100 | warning |
| feature_drift | mean_score_to_date | psi | 1.131 | 0.250 | critical |
| feature_drift | last_score | psi | 1.104 | 0.250 | critical |
| feature_drift | course_relative_score | psi | 1.059 | 0.250 | critical |
| feature_drift | quiz_clicks_to_date | psi | 0.171 | 0.100 | warning |
| feature_drift | quiz_clicks_last_14d | psi | 0.107 | 0.100 | warning |
| feature_drift | quiz_clicks_last_30d | psi | 0.151 | 0.100 | warning |
| feature_drift | quiz_trend_14d | psi | 0.154 | 0.100 | warning |
| feature_drift | forum_clicks_to_date | psi | 0.151 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.155 | 0.100 | warning |
| feature_drift | score_trend_per_30d | psi | 0.446 | 0.250 | critical |
| feature_drift | score_change_from_first | psi | 0.475 | 0.250 | critical |
| performance_drop | pr_auc | metric_drop | 0.077 | 0.050 | warning |

## Target: academic — decision point day 60

Definition: final_result is Fail or Withdrawn. Horizon: end of the module presentation.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11353 | 4785 | 0.421 |
| validation | 2014B | 6184 | 2827 | 0.457 |
| test | 2014J | 8816 | 3359 | 0.381 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.808 | 0.803 | 0.176 |
| Logistic Regression | balanced | 0.808 | 0.803 | 0.176 |
| Random Forest | none (selected) | 0.819 | 0.819 | 0.169 |
| Random Forest | balanced | 0.819 | 0.819 | 0.171 |
| XGBoost | none (selected) | 0.814 | 0.817 | 0.173 |
| XGBoost | balanced | 0.816 | 0.819 | 0.174 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: no re-weighting had the best validation PR-AUC.
- XGBoost: 'balanced' improved validation PR-AUC by only 0.0014 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.690 [0.675, 0.706] | 0.743 [0.733, 0.754] | 0.205 -> 0.204 | 0.095 -> 0.100 | 0.411 | 0.573 | 0.694 | 0.627 |
| Random Forest | 0.722 [0.707, 0.737] | 0.784 [0.775, 0.794] | 0.183 -> 0.189 | 0.059 -> 0.074 | 0.315 | 0.546 | 0.806 | 0.651 |
| XGBoost | 0.704 [0.689, 0.720] | 0.777 [0.767, 0.787] | 0.198 -> 0.196 | 0.084 -> 0.081 | 0.306 | 0.545 | 0.803 | 0.650 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.916 / 0.241 | 0.727 / 0.382 | 0.652 / 0.513 |
| Random Forest | 0.907 / 0.238 | 0.753 / 0.396 | 0.675 / 0.532 |
| XGBoost | 0.881 / 0.231 | 0.719 / 0.377 | 0.667 / 0.525 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.783 / 0.682 / 0.729 (5457) | 0.573 / 0.694 / 0.627 (3359) | 3719 | 1738 | 1029 | 2330 |
| Random Forest | 0.831 / 0.588 / 0.689 (5457) | 0.546 / 0.806 / 0.651 (3359) | 3209 | 2248 | 652 | 2707 |
| XGBoost | 0.829 / 0.588 / 0.688 (5457) | 0.545 / 0.803 / 0.650 (3359) | 3209 | 2248 | 662 | 2697 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.385 / 0.643 / 0.917 | 4499 (0.51), obs 0.21 | 1817 (0.21), obs 0.42 | 1791 (0.20), obs 0.55 | 709 (0.08), obs 0.94 |
| Random Forest | 0.365 / 0.724 / 0.916 | 4368 (0.50), obs 0.18 | 2228 (0.25), obs 0.46 | 1597 (0.18), obs 0.60 | 623 (0.07), obs 0.96 |
| XGBoost | 0.357 / 0.751 / 0.886 | 4328 (0.49), obs 0.18 | 2146 (0.24), obs 0.45 | 1656 (0.19), obs 0.58 | 686 (0.08), obs 0.93 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.8082 | 0.0000 | 1.00 |
| Random Forest | 0.8190 | 0.0007 | 1.00 |
| XGBoost | 0.8133 | 0.0010 | 1.00 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | course_relative_score, mean_score_to_date, score_trend_per_30d, last_score, assessments_due_to_date |
| Random Forest | Tree SHAP (probability); 300 trees | course_relative_score, assignment_completion_rate, mean_score_to_date, completion_rate_last_30d, last_score |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | course_relative_score, assignment_completion_rate, completion_rate_last_30d, mean_submission_delay_days, active_days_last_14d |

### Model selection

**Selected: XGBoost** (`oulad-v2-20260924T003349Z-acad-xgb-d60`).

Validation PR-AUC best = 0.8195 (random_forest). Models within 0.010 of it: random_forest, xgboost. Selected the most interpretable of these (xgboost; validation PR-AUC 0.8144, Brier 0.1730, seed PR-AUC std 0.0010).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.190 -> 0.186 | 0.068 -> 0.058 | yes |
| Random Forest | 2013B / 2013J / 2014B | 0.187 -> 0.182 | 0.081 -> 0.049 | yes |
| XGBoost | 2013B / 2013J / 2014B | 0.205 -> 0.191 | 0.105 -> 0.060 | yes |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3730 | 0.361 | 0.471 | 0.111 | 0.114 | 0.763 | 0.237 | 0.501 | 0.428 |
| M | 5086 | 0.396 | 0.453 | 0.057 | 0.059 | 0.830 | 0.170 | 0.576 | 0.399 |

Largest gaps between groups (max - min): recall 0.067 (M vs F); precision 0.075 (M vs F); false_positive_rate 0.029 (F vs M); false_negative_rate 0.067 (F vs M); pr_auc 0.151 (M vs F); calibration_gap 0.054 (F vs M); ece 0.055 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 6029 | 0.395 | 0.471 | 0.076 | 0.080 | 0.815 | 0.185 | 0.553 | 0.431 |
| 35-55 | 2706 | 0.352 | 0.439 | 0.087 | 0.088 | 0.776 | 0.224 | 0.530 | 0.374 |
| 55<= | 81 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.039 (0-35 vs 35-55); precision 0.023 (0-35 vs 35-55); false_positive_rate 0.057 (0-35 vs 35-55); false_negative_rate 0.039 (35-55 vs 0-35); pr_auc 0.065 (0-35 vs 35-55); calibration_gap 0.011 (35-55 vs 0-35); ece 0.008 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 8013 | 0.369 | 0.456 | 0.087 | 0.088 | 0.802 | 0.198 | 0.535 | 0.408 |
| Y | 803 | 0.497 | 0.505 | 0.008 | 0.064 | 0.807 | 0.193 | 0.633 | 0.463 |

Largest gaps between groups (max - min): recall 0.005 (Y vs N); precision 0.097 (Y vs N); false_positive_rate 0.055 (Y vs N); false_negative_rate 0.005 (N vs Y); pr_auc 0.071 (Y vs N); calibration_gap 0.079 (N vs Y); ece 0.024 (N vs Y)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 779 | 0.466 | 0.485 | 0.019 | 0.074 | 0.799 | 0.201 | 0.616 | 0.435 |
| 10-20 | 866 | 0.448 | 0.488 | 0.040 | 0.082 | 0.814 | 0.186 | 0.625 | 0.397 |
| 20-30% | 935 | 0.437 | 0.479 | 0.041 | 0.067 | 0.831 | 0.169 | 0.638 | 0.367 |
| 30-40% | 939 | 0.390 | 0.476 | 0.086 | 0.090 | 0.787 | 0.213 | 0.534 | 0.438 |
| 40-50% | 875 | 0.376 | 0.468 | 0.092 | 0.095 | 0.812 | 0.188 | 0.527 | 0.440 |
| 50-60% | 885 | 0.380 | 0.466 | 0.086 | 0.089 | 0.804 | 0.196 | 0.533 | 0.432 |
| 60-70% | 853 | 0.352 | 0.436 | 0.085 | 0.103 | 0.770 | 0.230 | 0.520 | 0.385 |
| 70-80% | 834 | 0.361 | 0.443 | 0.082 | 0.086 | 0.797 | 0.203 | 0.538 | 0.386 |
| 80-90% | 776 | 0.326 | 0.452 | 0.126 | 0.126 | 0.798 | 0.202 | 0.467 | 0.442 |
| 90-100% | 715 | 0.302 | 0.433 | 0.131 | 0.133 | 0.829 | 0.171 | 0.472 | 0.401 |
| unknown | 359 | 0.273 | 0.395 | 0.122 | 0.123 | 0.755 | 0.245 | 0.411 | 0.406 |

Largest gaps between groups (max - min): recall 0.076 (20-30% vs unknown); precision 0.227 (20-30% vs unknown); false_positive_rate 0.075 (80-90% vs 20-30%); false_negative_rate 0.076 (unknown vs 20-30%); pr_auc 0.147 (20-30% vs unknown); calibration_gap 0.111 (90-100% vs 0-10%); ece 0.066 (90-100% vs 20-30%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | assessments_due_to_date | psi | 3.335 | 0.250 | critical |
| feature_drift | late_submission_rate | psi | 0.692 | 0.250 | critical |
| feature_drift | mean_score_to_date | psi | 0.342 | 0.250 | critical |
| feature_drift | last_score | psi | 0.384 | 0.250 | critical |
| feature_drift | course_relative_score | psi | 0.211 | 0.100 | warning |
| feature_drift | quiz_clicks_to_date | psi | 0.525 | 0.250 | critical |
| feature_drift | quiz_clicks_last_14d | psi | 0.158 | 0.100 | warning |
| feature_drift | quiz_clicks_last_30d | psi | 0.257 | 0.250 | critical |
| feature_drift | quiz_trend_14d | psi | 0.146 | 0.100 | warning |
| feature_drift | forum_clicks_to_date | psi | 0.195 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.102 | 0.100 | warning |
| feature_drift | forum_trend_14d | psi | 0.225 | 0.100 | warning |
| feature_drift | submissions_last_30d | psi | 0.490 | 0.250 | critical |
| feature_drift | score_trend_per_30d | psi | 0.541 | 0.250 | critical |
| feature_drift | score_change_from_first | psi | 0.281 | 0.250 | critical |
| performance_drop | pr_auc | metric_drop | 0.110 | 0.100 | critical |

## Target: academic — decision point day 90

Definition: final_result is Fail or Withdrawn. Horizon: end of the module presentation.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11052 | 4483 | 0.406 |
| validation | 2014B | 5974 | 2616 | 0.438 |
| test | 2014J | 8532 | 3075 | 0.360 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.862 | 0.866 | 0.142 |
| Logistic Regression | balanced | 0.861 | 0.866 | 0.145 |
| Random Forest | none (selected) | 0.866 | 0.867 | 0.142 |
| Random Forest | balanced | 0.866 | 0.867 | 0.145 |
| XGBoost | none (selected) | 0.862 | 0.864 | 0.144 |
| XGBoost | balanced | 0.863 | 0.866 | 0.147 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: 'balanced' improved validation PR-AUC by only 0.0001 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- XGBoost: 'balanced' improved validation PR-AUC by only 0.0011 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.769 [0.756, 0.783] | 0.822 [0.813, 0.832] | 0.157 -> 0.159 | 0.032 -> 0.043 | 0.384 | 0.620 | 0.729 | 0.670 |
| Random Forest | 0.779 [0.767, 0.792] | 0.827 [0.818, 0.837] | 0.157 -> 0.161 | 0.065 -> 0.062 | 0.388 | 0.588 | 0.777 | 0.670 |
| XGBoost | 0.760 [0.747, 0.773] | 0.818 [0.808, 0.828] | 0.170 -> 0.173 | 0.067 -> 0.075 | 0.372 | 0.601 | 0.749 | 0.667 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.964 / 0.268 | 0.832 / 0.462 | 0.721 / 0.601 |
| Random Forest | 0.954 / 0.265 | 0.853 / 0.473 | 0.725 / 0.604 |
| XGBoost | 0.970 / 0.269 | 0.791 / 0.439 | 0.699 / 0.582 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.831 / 0.748 / 0.787 (5457) | 0.620 / 0.729 / 0.670 (3075) | 4083 | 1374 | 833 | 2242 |
| Random Forest | 0.847 / 0.694 / 0.762 (5457) | 0.588 / 0.777 / 0.670 (3075) | 3785 | 1672 | 686 | 2389 |
| XGBoost | 0.836 / 0.720 / 0.773 (5457) | 0.601 / 0.749 / 0.667 (3075) | 3928 | 1529 | 773 | 2302 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.331 / 0.726 / 0.968 | 4456 (0.52), obs 0.16 | 2471 (0.29), obs 0.41 | 1105 (0.13), obs 0.78 | 500 (0.06), obs 0.99 |
| Random Forest | 0.349 / 0.682 / 0.943 | 4147 (0.49), obs 0.14 | 2889 (0.34), obs 0.40 | 1005 (0.12), obs 0.84 | 491 (0.06), obs 0.99 |
| XGBoost | 0.308 / 0.810 / 0.920 | 4277 (0.50), obs 0.15 | 2425 (0.28), obs 0.42 | 1317 (0.15), obs 0.69 | 513 (0.06), obs 0.99 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.8615 | 0.0000 | 1.00 |
| Random Forest | 0.8659 | 0.0001 | 1.00 |
| XGBoost | 0.8641 | 0.0006 | 1.00 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | assignment_completion_rate, course_relative_score, score_change_from_first, days_since_last_activity, clicks_last_30d |
| Random Forest | Tree SHAP (probability); 300 trees | assignment_completion_rate, course_relative_score, mean_score_to_date, clicks_last_30d, completion_rate_last_30d |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | assignment_completion_rate, course_relative_score, mean_score_to_date, days_since_last_activity, mean_submission_delay_days |

### Model selection

**Selected: Logistic Regression** (`oulad-v2-20260924T003349Z-acad-lr-d90`).

Validation PR-AUC best = 0.8662 (random_forest). Models within 0.010 of it: logistic_regression, random_forest, xgboost. Selected the most interpretable of these (logistic_regression; validation PR-AUC 0.8615, Brier 0.1419, seed PR-AUC std 0.0000).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.240 -> 0.182 | 0.196 -> 0.069 | yes |
| Random Forest | 2013B / 2013J / 2014B | 0.152 -> 0.152 | 0.066 -> 0.067 | no |
| XGBoost | 2013B / 2013J / 2014B | 0.154 -> 0.153 | 0.062 -> 0.055 | yes |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3627 | 0.343 | 0.396 | 0.054 | 0.063 | 0.695 | 0.305 | 0.550 | 0.297 |
| M | 4905 | 0.373 | 0.407 | 0.034 | 0.034 | 0.752 | 0.248 | 0.674 | 0.217 |

Largest gaps between groups (max - min): recall 0.057 (M vs F); precision 0.125 (M vs F); false_positive_rate 0.080 (F vs M); false_negative_rate 0.057 (F vs M); pr_auc 0.097 (M vs F); calibration_gap 0.020 (F vs M); ece 0.029 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 5831 | 0.375 | 0.416 | 0.042 | 0.042 | 0.746 | 0.254 | 0.633 | 0.259 |
| 35-55 | 2621 | 0.331 | 0.373 | 0.042 | 0.045 | 0.686 | 0.314 | 0.587 | 0.238 |
| 55<= | 80 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.060 (0-35 vs 35-55); precision 0.046 (0-35 vs 35-55); false_positive_rate 0.021 (0-35 vs 35-55); false_negative_rate 0.060 (35-55 vs 0-35); pr_auc 0.062 (0-35 vs 35-55); calibration_gap 0.001 (35-55 vs 0-35); ece 0.003 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 7771 | 0.350 | 0.395 | 0.046 | 0.047 | 0.723 | 0.277 | 0.611 | 0.248 |
| Y | 761 | 0.469 | 0.476 | 0.007 | 0.037 | 0.779 | 0.221 | 0.695 | 0.302 |

Largest gaps between groups (max - min): recall 0.056 (Y vs N); precision 0.084 (Y vs N); false_positive_rate 0.054 (Y vs N); false_negative_rate 0.056 (N vs Y); pr_auc 0.077 (Y vs N); calibration_gap 0.039 (N vs Y); ece 0.009 (N vs Y)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 741 | 0.439 | 0.440 | 0.001 | 0.042 | 0.751 | 0.249 | 0.678 | 0.279 |
| 10-20 | 830 | 0.424 | 0.441 | 0.017 | 0.042 | 0.753 | 0.247 | 0.662 | 0.282 |
| 20-30% | 893 | 0.411 | 0.427 | 0.016 | 0.027 | 0.749 | 0.251 | 0.681 | 0.245 |
| 30-40% | 901 | 0.364 | 0.411 | 0.047 | 0.064 | 0.753 | 0.247 | 0.605 | 0.281 |
| 40-50% | 846 | 0.355 | 0.409 | 0.054 | 0.055 | 0.737 | 0.263 | 0.602 | 0.267 |
| 50-60% | 860 | 0.362 | 0.396 | 0.035 | 0.044 | 0.707 | 0.293 | 0.629 | 0.237 |
| 60-70% | 834 | 0.337 | 0.383 | 0.047 | 0.052 | 0.680 | 0.320 | 0.577 | 0.253 |
| 70-80% | 820 | 0.350 | 0.397 | 0.047 | 0.057 | 0.725 | 0.275 | 0.627 | 0.233 |
| 80-90% | 759 | 0.311 | 0.380 | 0.069 | 0.070 | 0.695 | 0.305 | 0.556 | 0.250 |
| 90-100% | 696 | 0.283 | 0.364 | 0.081 | 0.081 | 0.751 | 0.249 | 0.569 | 0.224 |
| unknown | 352 | 0.259 | 0.330 | 0.072 | 0.090 | 0.648 | 0.352 | 0.541 | 0.192 |

Largest gaps between groups (max - min): recall 0.105 (30-40% vs unknown); precision 0.139 (20-30% vs unknown); false_positive_rate 0.091 (10-20 vs unknown); false_negative_rate 0.105 (unknown vs 30-40%); pr_auc 0.138 (20-30% vs 80-90%); calibration_gap 0.080 (90-100% vs 0-10%); ece 0.062 (unknown vs 20-30%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | clicks_last_7d | psi | 0.114 | 0.100 | warning |
| feature_drift | clicks_last_14d | psi | 0.158 | 0.100 | warning |
| feature_drift | clicks_trend_7d | psi | 0.104 | 0.100 | warning |
| feature_drift | clicks_trend_14d | psi | 0.183 | 0.100 | warning |
| feature_drift | clicks_change_from_baseline | psi | 0.114 | 0.100 | warning |
| feature_drift | days_since_last_activity | psi | 0.102 | 0.100 | warning |
| feature_drift | assessments_due_to_date | psi | 1.892 | 0.250 | critical |
| feature_drift | late_submission_rate | psi | 0.514 | 0.250 | critical |
| feature_drift | mean_submission_delay_days | psi | 0.152 | 0.100 | warning |
| feature_drift | mean_score_to_date | psi | 0.136 | 0.100 | warning |
| feature_drift | last_score | psi | 0.153 | 0.100 | warning |
| feature_drift | course_relative_score | psi | 0.168 | 0.100 | warning |
| feature_drift | active_days_last_14d | psi | 0.156 | 0.100 | warning |
| feature_drift | quiz_clicks_to_date | psi | 0.326 | 0.250 | critical |
| feature_drift | quiz_clicks_last_7d | psi | 0.107 | 0.100 | warning |
| feature_drift | quiz_clicks_last_14d | psi | 0.275 | 0.250 | critical |
| feature_drift | quiz_clicks_last_30d | psi | 0.371 | 0.250 | critical |
| feature_drift | quiz_trend_14d | psi | 0.261 | 0.250 | critical |
| feature_drift | forum_clicks_to_date | psi | 0.199 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.161 | 0.100 | warning |
| feature_drift | forum_trend_14d | psi | 0.112 | 0.100 | warning |
| feature_drift | content_trend_14d | psi | 0.139 | 0.100 | warning |
| feature_drift | submissions_last_30d | psi | 0.170 | 0.100 | warning |
| missingness_drift | completion_rate_last_30d | missing_rate_change | 0.083 | 0.050 | warning |
| feature_drift | score_trend_per_30d | psi | 0.161 | 0.100 | warning |
| feature_drift | score_change_from_first | psi | 0.174 | 0.100 | warning |
| feature_drift | clicks_last_7d_vs_30d_rate | psi | 0.123 | 0.100 | warning |
| performance_drop | pr_auc | metric_drop | 0.093 | 0.050 | warning |

## Target: dropout — decision point day 30

Definition: final_result is Withdrawn. Horizon: end of the module presentation.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11759 | 1961 | 0.167 |
| validation | 2014B | 6493 | 1306 | 0.201 |
| test | 2014J | 9198 | 1767 | 0.192 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.333 | 0.681 | 0.151 |
| Logistic Regression | balanced | 0.328 | 0.680 | 0.232 |
| Random Forest | none (selected) | 0.334 | 0.675 | 0.151 |
| Random Forest | balanced | 0.332 | 0.675 | 0.210 |
| XGBoost | none (selected) | 0.311 | 0.657 | 0.155 |
| XGBoost | balanced | 0.312 | 0.655 | 0.204 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: no re-weighting had the best validation PR-AUC.
- XGBoost: 'balanced' improved validation PR-AUC by only 0.0009 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.331 [0.310, 0.353] | 0.672 [0.656, 0.685] | 0.146 -> 0.146 | 0.018 -> 0.017 | 0.155 | 0.272 | 0.677 | 0.388 |
| Random Forest | 0.344 [0.323, 0.362] | 0.676 [0.661, 0.691] | 0.145 -> 0.145 | 0.019 -> 0.018 | 0.181 | 0.288 | 0.648 | 0.398 |
| XGBoost | 0.331 [0.312, 0.352] | 0.665 [0.651, 0.678] | 0.147 -> 0.146 | 0.028 -> 0.017 | 0.178 | 0.273 | 0.647 | 0.384 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.415 / 0.216 | 0.364 / 0.379 | 0.321 / 0.501 |
| Random Forest | 0.425 / 0.221 | 0.364 / 0.379 | 0.323 / 0.505 |
| XGBoost | 0.401 / 0.209 | 0.350 / 0.364 | 0.312 / 0.487 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.881 / 0.569 / 0.692 (7431) | 0.272 / 0.677 / 0.388 (1767) | 4229 | 3202 | 571 | 1196 |
| Random Forest | 0.881 / 0.618 / 0.727 (7431) | 0.288 / 0.648 / 0.398 (1767) | 4595 | 2836 | 622 | 1145 |
| XGBoost | 0.876 / 0.590 / 0.705 (7431) | 0.273 / 0.647 / 0.384 (1767) | 4388 | 3043 | 623 | 1144 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.139 / 0.253 / 0.342 | 4005 (0.44), obs 0.11 | 3172 (0.34), obs 0.19 | 1320 (0.14), obs 0.31 | 701 (0.08), obs 0.43 |
| Random Forest | 0.164 / 0.235 / 0.297 | 4566 (0.50), obs 0.11 | 2618 (0.28), obs 0.20 | 1301 (0.14), obs 0.31 | 713 (0.08), obs 0.45 |
| XGBoost | 0.174 / 0.232 / 0.322 | 4742 (0.52), obs 0.12 | 2405 (0.26), obs 0.21 | 1312 (0.14), obs 0.29 | 739 (0.08), obs 0.42 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.3328 | 0.0000 | 1.00 |
| Random Forest | 0.3347 | 0.0017 | 1.00 |
| XGBoost | 0.3113 | 0.0045 | 0.78 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | last_score, course_relative_score, quiz_clicks_last_30d, mean_score_to_date, studied_credits |
| Random Forest | Tree SHAP (probability); 300 trees | studied_credits, completion_rate_last_30d, assignment_completion_rate, mean_submission_delay_days, late_submission_rate |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | studied_credits, mean_submission_delay_days, assignment_completion_rate, clicks_trend_7d, days_since_last_activity |

### Model selection

**Selected: Logistic Regression** (`oulad-v2-20260924T003349Z-drop-lr-d30`).

Validation PR-AUC best = 0.3341 (random_forest). Models within 0.010 of it: logistic_regression, random_forest. Selected the most interpretable of these (logistic_regression; validation PR-AUC 0.3328, Brier 0.1510, seed PR-AUC std 0.0000).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.152 -> 0.152 | 0.026 -> 0.026 | no |
| Random Forest | 2013B / 2013J / 2014B | 0.158 -> 0.159 | 0.020 -> 0.041 | no |
| XGBoost | 2013B / 2013J / 2014B | 0.166 -> 0.161 | 0.067 -> 0.041 | yes |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3869 | 0.180 | 0.163 | -0.017 | 0.026 | 0.617 | 0.383 | 0.254 | 0.398 |
| M | 5329 | 0.201 | 0.185 | -0.016 | 0.018 | 0.715 | 0.285 | 0.283 | 0.456 |

Largest gaps between groups (max - min): recall 0.098 (M vs F); precision 0.030 (M vs F); false_positive_rate 0.058 (M vs F); false_negative_rate 0.098 (F vs M); pr_auc 0.033 (M vs F); calibration_gap 0.001 (M vs F); ece 0.008 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 6303 | 0.194 | 0.181 | -0.013 | 0.016 | 0.685 | 0.315 | 0.268 | 0.450 |
| 35-55 | 2808 | 0.187 | 0.164 | -0.023 | 0.023 | 0.661 | 0.339 | 0.282 | 0.386 |
| 55<= | 87 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.024 (0-35 vs 35-55); precision 0.014 (35-55 vs 0-35); false_positive_rate 0.064 (0-35 vs 35-55); false_negative_rate 0.024 (35-55 vs 0-35); pr_auc 0.012 (35-55 vs 0-35); calibration_gap 0.009 (0-35 vs 35-55); ece 0.007 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 8346 | 0.184 | 0.175 | -0.009 | 0.012 | 0.675 | 0.325 | 0.262 | 0.428 |
| Y | 852 | 0.271 | 0.184 | -0.087 | 0.087 | 0.688 | 0.312 | 0.356 | 0.464 |

Largest gaps between groups (max - min): recall 0.013 (Y vs N); precision 0.093 (Y vs N); false_positive_rate 0.036 (Y vs N); false_negative_rate 0.013 (N vs Y); pr_auc 0.123 (Y vs N); calibration_gap 0.078 (N vs Y); ece 0.075 (Y vs N)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 820 | 0.221 | 0.177 | -0.044 | 0.044 | 0.696 | 0.304 | 0.304 | 0.451 |
| 10-20 | 910 | 0.213 | 0.176 | -0.037 | 0.039 | 0.670 | 0.330 | 0.301 | 0.422 |
| 20-30% | 970 | 0.220 | 0.174 | -0.046 | 0.055 | 0.615 | 0.385 | 0.292 | 0.419 |
| 30-40% | 979 | 0.200 | 0.175 | -0.026 | 0.040 | 0.643 | 0.357 | 0.275 | 0.425 |
| 40-50% | 921 | 0.193 | 0.178 | -0.015 | 0.021 | 0.685 | 0.315 | 0.269 | 0.447 |
| 50-60% | 920 | 0.187 | 0.175 | -0.012 | 0.026 | 0.709 | 0.291 | 0.291 | 0.397 |
| 60-70% | 886 | 0.179 | 0.167 | -0.012 | 0.027 | 0.616 | 0.384 | 0.257 | 0.389 |
| 70-80% | 870 | 0.169 | 0.176 | 0.007 | 0.017 | 0.707 | 0.293 | 0.248 | 0.436 |
| 80-90% | 809 | 0.168 | 0.176 | 0.008 | 0.019 | 0.684 | 0.316 | 0.227 | 0.470 |
| 90-100% | 747 | 0.178 | 0.181 | 0.003 | 0.018 | 0.737 | 0.263 | 0.264 | 0.445 |
| unknown | 366 | 0.158 | 0.188 | 0.030 | 0.033 | 0.793 | 0.207 | 0.240 | 0.474 |

Largest gaps between groups (max - min): recall 0.178 (unknown vs 20-30%); precision 0.077 (0-10% vs 80-90%); false_positive_rate 0.085 (unknown vs 60-70%); false_negative_rate 0.178 (20-30% vs unknown); pr_auc 0.104 (20-30% vs unknown); calibration_gap 0.076 (unknown vs 20-30%); ece 0.038 (20-30% vs 70-80%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | mean_submission_delay_days | psi | 0.221 | 0.100 | warning |
| feature_drift | mean_score_to_date | psi | 1.131 | 0.250 | critical |
| feature_drift | last_score | psi | 1.104 | 0.250 | critical |
| feature_drift | course_relative_score | psi | 1.059 | 0.250 | critical |
| feature_drift | quiz_clicks_to_date | psi | 0.171 | 0.100 | warning |
| feature_drift | quiz_clicks_last_14d | psi | 0.107 | 0.100 | warning |
| feature_drift | quiz_clicks_last_30d | psi | 0.151 | 0.100 | warning |
| feature_drift | quiz_trend_14d | psi | 0.154 | 0.100 | warning |
| feature_drift | forum_clicks_to_date | psi | 0.151 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.155 | 0.100 | warning |
| feature_drift | score_trend_per_30d | psi | 0.446 | 0.250 | critical |
| feature_drift | score_change_from_first | psi | 0.475 | 0.250 | critical |
| prediction_drift | prediction | psi | 0.113 | 0.100 | warning |

## Target: dropout — decision point day 60

Definition: final_result is Withdrawn. Horizon: end of the module presentation.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11353 | 1552 | 0.137 |
| validation | 2014B | 6184 | 995 | 0.161 |
| test | 2014J | 8816 | 1384 | 0.157 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.305 | 0.693 | 0.127 |
| Logistic Regression | balanced | 0.302 | 0.693 | 0.225 |
| Random Forest | none (selected) | 0.304 | 0.694 | 0.126 |
| Random Forest | balanced | 0.300 | 0.695 | 0.196 |
| XGBoost | none | 0.298 | 0.688 | 0.127 |
| XGBoost | balanced (selected) | 0.303 | 0.687 | 0.179 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: no re-weighting had the best validation PR-AUC.
- XGBoost: 'balanced' improved validation PR-AUC by more than 0.005 over no re-weighting.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.255 [0.239, 0.275] | 0.669 [0.654, 0.683] | 0.131 -> 0.128 | 0.047 -> 0.028 | 0.159 | 0.254 | 0.616 | 0.360 |
| Random Forest | 0.246 [0.233, 0.262] | 0.678 [0.663, 0.691] | 0.127 -> 0.128 | 0.020 -> 0.028 | 0.175 | 0.273 | 0.572 | 0.369 |
| XGBoost | 0.255 [0.241, 0.275] | 0.680 [0.666, 0.695] | 0.185 -> 0.126 | 0.205 -> 0.015 | 0.179 | 0.261 | 0.556 | 0.355 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.239 / 0.152 | 0.281 / 0.358 | 0.273 / 0.522 |
| Random Forest | 0.271 / 0.173 | 0.281 / 0.358 | 0.274 / 0.523 |
| XGBoost | 0.305 / 0.194 | 0.299 / 0.382 | 0.268 / 0.512 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.903 / 0.663 / 0.764 (7432) | 0.254 / 0.616 / 0.360 (1384) | 4926 | 2506 | 531 | 853 |
| Random Forest | 0.900 / 0.716 / 0.797 (7432) | 0.273 / 0.572 / 0.369 (1384) | 5322 | 2110 | 593 | 791 |
| XGBoost | 0.895 / 0.707 / 0.790 (7432) | 0.261 / 0.556 / 0.355 (1384) | 5253 | 2179 | 614 | 770 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.135 / 0.198 / 0.284 | 4440 (0.50), obs 0.09 | 2006 (0.23), obs 0.17 | 1144 (0.13), obs 0.29 | 1226 (0.14), obs 0.27 |
| Random Forest | 0.117 / 0.204 / 0.289 | 4086 (0.46), obs 0.08 | 2286 (0.26), obs 0.17 | 1279 (0.15), obs 0.27 | 1165 (0.13), obs 0.27 |
| XGBoost | 0.128 / 0.216 / 0.309 | 4475 (0.51), obs 0.09 | 2066 (0.23), obs 0.18 | 1194 (0.14), obs 0.25 | 1081 (0.12), obs 0.31 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.3052 | 0.0000 | 1.00 |
| Random Forest | 0.3024 | 0.0015 | 0.78 |
| XGBoost | 0.3040 | 0.0037 | 1.00 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | mean_score_to_date, last_score, course_relative_score, active_days_last_14d, clicks_to_date |
| Random Forest | Tree SHAP (probability); 300 trees | course_relative_score, mean_score_to_date, completion_rate_last_30d, assignment_completion_rate, last_score |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | course_relative_score, assignment_completion_rate, mean_score_to_date, forum_clicks_to_date, studied_credits |

### Model selection

**Selected: Logistic Regression** (`oulad-v2-20260924T003349Z-drop-lr-d60`).

Validation PR-AUC best = 0.3052 (logistic_regression). Models within 0.010 of it: logistic_regression, random_forest, xgboost. Selected the most interpretable of these (logistic_regression; validation PR-AUC 0.3052, Brier 0.1261, seed PR-AUC std 0.0000).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.129 -> 0.128 | 0.033 -> 0.029 | yes |
| Random Forest | 2013B / 2013J / 2014B | 0.127 -> 0.126 | 0.014 -> 0.018 | no |
| XGBoost | 2013B / 2013J / 2014B | 0.184 -> 0.131 | 0.193 -> 0.028 | yes |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3730 | 0.149 | 0.166 | 0.017 | 0.058 | 0.541 | 0.459 | 0.225 | 0.325 |
| M | 5086 | 0.163 | 0.167 | 0.004 | 0.021 | 0.667 | 0.333 | 0.273 | 0.346 |

Largest gaps between groups (max - min): recall 0.127 (M vs F); precision 0.048 (M vs F); false_positive_rate 0.021 (M vs F); false_negative_rate 0.127 (F vs M); pr_auc 0.072 (M vs F); calibration_gap 0.013 (F vs M); ece 0.037 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 6029 | 0.158 | 0.169 | 0.011 | 0.033 | 0.639 | 0.361 | 0.256 | 0.348 |
| 35-55 | 2706 | 0.156 | 0.162 | 0.006 | 0.035 | 0.566 | 0.434 | 0.249 | 0.315 |
| 55<= | 81 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.073 (0-35 vs 35-55); precision 0.007 (0-35 vs 35-55); false_positive_rate 0.033 (0-35 vs 35-55); false_negative_rate 0.073 (35-55 vs 0-35); pr_auc 0.014 (0-35 vs 35-55); calibration_gap 0.005 (0-35 vs 35-55); ece 0.002 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 8013 | 0.150 | 0.166 | 0.016 | 0.030 | 0.613 | 0.387 | 0.244 | 0.335 |
| Y | 803 | 0.227 | 0.174 | -0.052 | 0.058 | 0.637 | 0.363 | 0.340 | 0.362 |

Largest gaps between groups (max - min): recall 0.024 (Y vs N); precision 0.096 (Y vs N); false_positive_rate 0.027 (Y vs N); false_negative_rate 0.024 (N vs Y); pr_auc 0.106 (Y vs N); calibration_gap 0.068 (N vs Y); ece 0.028 (Y vs N)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 779 | 0.180 | 0.167 | -0.012 | 0.043 | 0.629 | 0.371 | 0.300 | 0.321 |
| 10-20 | 866 | 0.173 | 0.177 | 0.004 | 0.052 | 0.580 | 0.420 | 0.242 | 0.381 |
| 20-30% | 935 | 0.190 | 0.169 | -0.021 | 0.036 | 0.657 | 0.343 | 0.311 | 0.342 |
| 30-40% | 939 | 0.165 | 0.172 | 0.007 | 0.050 | 0.587 | 0.413 | 0.243 | 0.362 |
| 40-50% | 875 | 0.151 | 0.169 | 0.018 | 0.035 | 0.629 | 0.371 | 0.248 | 0.339 |
| 50-60% | 885 | 0.155 | 0.167 | 0.012 | 0.033 | 0.613 | 0.387 | 0.247 | 0.342 |
| 60-70% | 853 | 0.148 | 0.158 | 0.010 | 0.031 | 0.611 | 0.389 | 0.256 | 0.308 |
| 70-80% | 834 | 0.133 | 0.164 | 0.031 | 0.046 | 0.631 | 0.369 | 0.227 | 0.331 |
| 80-90% | 776 | 0.133 | 0.165 | 0.032 | 0.035 | 0.602 | 0.398 | 0.209 | 0.348 |
| 90-100% | 715 | 0.141 | 0.161 | 0.019 | 0.035 | 0.653 | 0.347 | 0.249 | 0.324 |
| unknown | 359 | 0.142 | 0.151 | 0.009 | 0.020 | 0.549 | 0.451 | 0.257 | 0.263 |

Largest gaps between groups (max - min): recall 0.108 (20-30% vs unknown); precision 0.102 (20-30% vs 80-90%); false_positive_rate 0.118 (10-20 vs unknown); false_negative_rate 0.108 (unknown vs 20-30%); pr_auc 0.104 (20-30% vs 80-90%); calibration_gap 0.054 (80-90% vs 20-30%); ece 0.032 (10-20 vs unknown)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | assessments_due_to_date | psi | 3.335 | 0.250 | critical |
| feature_drift | late_submission_rate | psi | 0.692 | 0.250 | critical |
| feature_drift | mean_score_to_date | psi | 0.342 | 0.250 | critical |
| feature_drift | last_score | psi | 0.384 | 0.250 | critical |
| feature_drift | course_relative_score | psi | 0.211 | 0.100 | warning |
| feature_drift | quiz_clicks_to_date | psi | 0.525 | 0.250 | critical |
| feature_drift | quiz_clicks_last_14d | psi | 0.158 | 0.100 | warning |
| feature_drift | quiz_clicks_last_30d | psi | 0.257 | 0.250 | critical |
| feature_drift | quiz_trend_14d | psi | 0.146 | 0.100 | warning |
| feature_drift | forum_clicks_to_date | psi | 0.195 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.102 | 0.100 | warning |
| feature_drift | forum_trend_14d | psi | 0.225 | 0.100 | warning |
| feature_drift | submissions_last_30d | psi | 0.490 | 0.250 | critical |
| feature_drift | score_trend_per_30d | psi | 0.541 | 0.250 | critical |
| feature_drift | score_change_from_first | psi | 0.281 | 0.250 | critical |
| performance_drop | pr_auc | metric_drop | 0.050 | 0.050 | warning |

## Target: dropout — decision point day 90

Definition: final_result is Withdrawn. Horizon: end of the module presentation.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11052 | 1250 | 0.113 |
| validation | 2014B | 5974 | 783 | 0.131 |
| test | 2014J | 8532 | 1099 | 0.129 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.289 | 0.720 | 0.105 |
| Logistic Regression | balanced | 0.282 | 0.719 | 0.219 |
| Random Forest | none (selected) | 0.302 | 0.728 | 0.104 |
| Random Forest | balanced | 0.291 | 0.727 | 0.177 |
| XGBoost | none (selected) | 0.291 | 0.723 | 0.105 |
| XGBoost | balanced | 0.264 | 0.699 | 0.155 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: no re-weighting had the best validation PR-AUC.
- XGBoost: no re-weighting had the best validation PR-AUC.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.253 [0.233, 0.278] | 0.700 [0.684, 0.716] | 0.106 -> 0.106 | 0.018 -> 0.014 | 0.124 | 0.224 | 0.575 | 0.323 |
| Random Forest | 0.246 [0.223, 0.270] | 0.695 [0.679, 0.710] | 0.106 -> 0.107 | 0.006 -> 0.016 | 0.188 | 0.250 | 0.404 | 0.309 |
| XGBoost | 0.234 [0.214, 0.257] | 0.682 [0.665, 0.697] | 0.108 -> 0.108 | 0.026 -> 0.019 | 0.125 | 0.215 | 0.581 | 0.314 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.308 / 0.239 | 0.258 / 0.401 | 0.230 / 0.536 |
| Random Forest | 0.285 / 0.221 | 0.254 / 0.394 | 0.231 / 0.538 |
| XGBoost | 0.262 / 0.204 | 0.252 / 0.391 | 0.225 / 0.523 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.918 / 0.706 / 0.798 (7433) | 0.224 / 0.575 / 0.323 (1099) | 5248 | 2185 | 467 | 632 |
| Random Forest | 0.903 / 0.821 / 0.860 (7433) | 0.250 / 0.404 / 0.309 (1099) | 6099 | 1334 | 655 | 444 |
| XGBoost | 0.917 / 0.686 / 0.785 (7433) | 0.215 / 0.581 / 0.314 (1099) | 5100 | 2333 | 460 | 639 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.085 / 0.160 / 0.255 | 3928 (0.46), obs 0.06 | 2780 (0.33), obs 0.14 | 1295 (0.15), obs 0.22 | 529 (0.06), obs 0.34 |
| Random Forest | 0.086 / 0.169 / 0.253 | 3537 (0.41), obs 0.06 | 2809 (0.33), obs 0.14 | 1512 (0.18), obs 0.21 | 674 (0.08), obs 0.28 |
| XGBoost | 0.091 / 0.142 / 0.242 | 3464 (0.41), obs 0.06 | 2712 (0.32), obs 0.12 | 1587 (0.19), obs 0.22 | 769 (0.09), obs 0.26 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.2888 | 0.0000 | 1.00 |
| Random Forest | 0.3016 | 0.0014 | 0.78 |
| XGBoost | 0.2788 | 0.0026 | 0.67 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | mean_score_to_date, assignment_completion_rate, score_change_from_first, score_trend_per_30d, late_submission_rate |
| Random Forest | Tree SHAP (probability); 300 trees | assignment_completion_rate, course_relative_score, mean_score_to_date, completion_rate_last_30d, mean_submission_delay_days |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | assignment_completion_rate, mean_score_to_date, course_relative_score, studied_credits, forum_clicks_to_date |

### Model selection

**Selected: Random Forest** (`oulad-v2-20260924T003349Z-drop-rf-d90`).

Validation PR-AUC best = 0.3018 (random_forest). Models within 0.010 of it: random_forest. Selected the most interpretable of these (random_forest; validation PR-AUC 0.3018, Brier 0.1040, seed PR-AUC std 0.0014).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.108 -> 0.108 | 0.023 -> 0.029 | no |
| Random Forest | 2013B / 2013J / 2014B | 0.105 -> 0.105 | 0.009 -> 0.013 | no |
| XGBoost | 2013B / 2013J / 2014B | 0.109 -> 0.108 | 0.043 -> 0.028 | yes |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3627 | 0.125 | 0.131 | 0.006 | 0.017 | 0.389 | 0.611 | 0.204 | 0.216 |
| M | 4905 | 0.132 | 0.117 | -0.015 | 0.018 | 0.414 | 0.586 | 0.293 | 0.152 |

Largest gaps between groups (max - min): recall 0.025 (M vs F); precision 0.088 (M vs F); false_positive_rate 0.064 (F vs M); false_negative_rate 0.025 (F vs M); pr_auc 0.078 (M vs F); calibration_gap 0.021 (F vs M); ece 0.002 (M vs F)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 5831 | 0.129 | 0.124 | -0.005 | 0.006 | 0.422 | 0.578 | 0.255 | 0.183 |
| 35-55 | 2621 | 0.128 | 0.120 | -0.008 | 0.012 | 0.366 | 0.634 | 0.237 | 0.173 |
| 55<= | 80 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.056 (0-35 vs 35-55); precision 0.017 (0-35 vs 35-55); false_positive_rate 0.010 (0-35 vs 35-55); false_negative_rate 0.056 (35-55 vs 0-35); pr_auc 0.012 (0-35 vs 35-55); calibration_gap 0.003 (0-35 vs 35-55); ece 0.006 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 7771 | 0.123 | 0.121 | -0.002 | 0.006 | 0.387 | 0.613 | 0.236 | 0.177 |
| Y | 761 | 0.184 | 0.138 | -0.046 | 0.046 | 0.521 | 0.479 | 0.360 | 0.209 |

Largest gaps between groups (max - min): recall 0.135 (Y vs N); precision 0.124 (Y vs N); false_positive_rate 0.033 (Y vs N); false_negative_rate 0.135 (N vs Y); pr_auc 0.152 (Y vs N); calibration_gap 0.043 (N vs Y); ece 0.039 (Y vs N)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 741 | 0.138 | 0.130 | -0.008 | 0.022 | 0.480 | 0.520 | 0.297 | 0.182 |
| 10-20 | 830 | 0.137 | 0.134 | -0.003 | 0.020 | 0.421 | 0.579 | 0.223 | 0.233 |
| 20-30% | 893 | 0.152 | 0.128 | -0.024 | 0.026 | 0.478 | 0.522 | 0.319 | 0.184 |
| 30-40% | 901 | 0.130 | 0.126 | -0.004 | 0.019 | 0.359 | 0.641 | 0.209 | 0.203 |
| 40-50% | 846 | 0.122 | 0.127 | 0.005 | 0.013 | 0.495 | 0.505 | 0.250 | 0.206 |
| 50-60% | 860 | 0.130 | 0.120 | -0.010 | 0.021 | 0.357 | 0.643 | 0.242 | 0.167 |
| 60-70% | 834 | 0.128 | 0.118 | -0.011 | 0.027 | 0.290 | 0.710 | 0.200 | 0.171 |
| 70-80% | 820 | 0.118 | 0.121 | 0.002 | 0.020 | 0.485 | 0.515 | 0.272 | 0.174 |
| 80-90% | 759 | 0.112 | 0.116 | 0.004 | 0.014 | 0.282 | 0.718 | 0.186 | 0.156 |
| 90-100% | 696 | 0.118 | 0.115 | -0.003 | 0.020 | 0.390 | 0.610 | 0.264 | 0.145 |
| unknown | 352 | 0.125 | 0.104 | -0.021 | 0.021 | 0.341 | 0.659 | 0.326 | 0.101 |

Largest gaps between groups (max - min): recall 0.213 (40-50% vs 80-90%); precision 0.140 (unknown vs 80-90%); false_positive_rate 0.133 (10-20 vs unknown); false_negative_rate 0.213 (80-90% vs 40-50%); pr_auc 0.163 (20-30% vs 60-70%); calibration_gap 0.029 (40-50% vs 20-30%); ece 0.013 (60-70% vs 40-50%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | clicks_last_7d | psi | 0.114 | 0.100 | warning |
| feature_drift | clicks_last_14d | psi | 0.158 | 0.100 | warning |
| feature_drift | clicks_trend_7d | psi | 0.104 | 0.100 | warning |
| feature_drift | clicks_trend_14d | psi | 0.183 | 0.100 | warning |
| feature_drift | clicks_change_from_baseline | psi | 0.114 | 0.100 | warning |
| feature_drift | days_since_last_activity | psi | 0.102 | 0.100 | warning |
| feature_drift | assessments_due_to_date | psi | 1.892 | 0.250 | critical |
| feature_drift | late_submission_rate | psi | 0.514 | 0.250 | critical |
| feature_drift | mean_submission_delay_days | psi | 0.152 | 0.100 | warning |
| feature_drift | mean_score_to_date | psi | 0.136 | 0.100 | warning |
| feature_drift | last_score | psi | 0.153 | 0.100 | warning |
| feature_drift | course_relative_score | psi | 0.168 | 0.100 | warning |
| feature_drift | active_days_last_14d | psi | 0.156 | 0.100 | warning |
| feature_drift | quiz_clicks_to_date | psi | 0.326 | 0.250 | critical |
| feature_drift | quiz_clicks_last_7d | psi | 0.107 | 0.100 | warning |
| feature_drift | quiz_clicks_last_14d | psi | 0.275 | 0.250 | critical |
| feature_drift | quiz_clicks_last_30d | psi | 0.371 | 0.250 | critical |
| feature_drift | quiz_trend_14d | psi | 0.261 | 0.250 | critical |
| feature_drift | forum_clicks_to_date | psi | 0.199 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.161 | 0.100 | warning |
| feature_drift | forum_trend_14d | psi | 0.112 | 0.100 | warning |
| feature_drift | content_trend_14d | psi | 0.139 | 0.100 | warning |
| feature_drift | submissions_last_30d | psi | 0.170 | 0.100 | warning |
| missingness_drift | completion_rate_last_30d | missing_rate_change | 0.083 | 0.050 | warning |
| feature_drift | score_trend_per_30d | psi | 0.161 | 0.100 | warning |
| feature_drift | score_change_from_first | psi | 0.174 | 0.100 | warning |
| feature_drift | clicks_last_7d_vs_30d_rate | psi | 0.123 | 0.100 | warning |
| prediction_drift | prediction | psi | 0.100 | 0.100 | warning |
| performance_drop | pr_auc | metric_drop | 0.056 | 0.050 | warning |

## Target: course_failure — decision point day 30

Definition: final_result is Fail (students who later withdraw count as 0). Horizon: end of the module presentation.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11759 | 3232 | 0.275 |
| validation | 2014B | 6493 | 1830 | 0.282 |
| test | 2014J | 9198 | 1975 | 0.215 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.467 | 0.680 | 0.185 |
| Logistic Regression | balanced | 0.470 | 0.682 | 0.231 |
| Random Forest | none (selected) | 0.479 | 0.693 | 0.182 |
| Random Forest | balanced | 0.480 | 0.694 | 0.223 |
| XGBoost | none | 0.435 | 0.675 | 0.191 |
| XGBoost | balanced (selected) | 0.452 | 0.679 | 0.233 |

- Logistic Regression: 'balanced' improved validation PR-AUC by only 0.0023 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- Random Forest: 'balanced' improved validation PR-AUC by only 0.0015 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- XGBoost: 'balanced' improved validation PR-AUC by more than 0.005 over no re-weighting.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.337 [0.320, 0.357] | 0.648 [0.633, 0.661] | 0.170 -> 0.167 | 0.087 -> 0.076 | 0.261 | 0.276 | 0.708 | 0.398 |
| Random Forest | 0.368 [0.350, 0.388] | 0.672 [0.658, 0.684] | 0.163 -> 0.161 | 0.078 -> 0.058 | 0.241 | 0.290 | 0.700 | 0.410 |
| XGBoost | 0.331 [0.316, 0.351] | 0.651 [0.637, 0.665] | 0.242 -> 0.166 | 0.254 -> 0.063 | 0.293 | 0.300 | 0.625 | 0.405 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.426 / 0.198 | 0.360 / 0.336 | 0.325 / 0.454 |
| Random Forest | 0.429 / 0.200 | 0.371 / 0.345 | 0.340 / 0.475 |
| XGBoost | 0.400 / 0.186 | 0.342 / 0.319 | 0.328 / 0.458 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.861 / 0.493 / 0.627 (7223) | 0.276 / 0.708 / 0.398 (1975) | 3564 | 3659 | 577 | 1398 |
| Random Forest | 0.866 / 0.530 / 0.658 (7223) | 0.290 / 0.700 / 0.410 (1975) | 3829 | 3394 | 592 | 1383 |
| XGBoost | 0.854 / 0.601 / 0.705 (7223) | 0.300 / 0.625 / 0.405 (1975) | 4338 | 2885 | 740 | 1235 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.272 / 0.361 / 0.458 | 4478 (0.49), obs 0.14 | 2349 (0.26), obs 0.23 | 1545 (0.17), obs 0.28 | 826 (0.09), obs 0.44 |
| Random Forest | 0.251 / 0.347 / 0.470 | 4719 (0.51), obs 0.14 | 2302 (0.25), obs 0.24 | 1405 (0.15), obs 0.30 | 772 (0.08), obs 0.46 |
| XGBoost | 0.277 / 0.372 / 0.467 | 4730 (0.51), obs 0.14 | 2087 (0.23), obs 0.24 | 1553 (0.17), obs 0.29 | 828 (0.09), obs 0.42 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.4674 | 0.0000 | 1.00 |
| Random Forest | 0.4784 | 0.0007 | 0.51 |
| XGBoost | 0.4362 | 0.0080 | 1.00 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | course_relative_score, active_days_to_date, last_score, late_submission_rate, mean_submission_delay_days |
| Random Forest | Tree SHAP (probability); 300 trees | active_days_to_date, mean_submission_delay_days, forum_clicks_to_date, days_since_last_activity, active_days_last_14d |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | active_days_to_date, mean_submission_delay_days, days_since_last_activity, course_relative_score, quiz_trend_14d |

### Model selection

**Selected: Random Forest** (`oulad-v2-20260924T003349Z-fail-rf-d30`).

Validation PR-AUC best = 0.4788 (random_forest). Models within 0.010 of it: random_forest. Selected the most interpretable of these (random_forest; validation PR-AUC 0.4788, Brier 0.1819, seed PR-AUC std 0.0007).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.195 -> 0.189 | 0.067 -> 0.021 | yes |
| Random Forest | 2013B / 2013J / 2014B | 0.193 -> 0.186 | 0.080 -> 0.015 | yes |
| XGBoost | 2013B / 2013J / 2014B | 0.244 -> 0.190 | 0.206 -> 0.026 | yes |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3869 | 0.204 | 0.275 | 0.071 | 0.071 | 0.707 | 0.293 | 0.269 | 0.493 |
| M | 5329 | 0.222 | 0.271 | 0.049 | 0.049 | 0.696 | 0.304 | 0.305 | 0.453 |

Largest gaps between groups (max - min): recall 0.011 (F vs M); precision 0.036 (M vs F); false_positive_rate 0.040 (F vs M); false_negative_rate 0.011 (M vs F); pr_auc 0.036 (M vs F); calibration_gap 0.022 (F vs M); ece 0.022 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 6303 | 0.227 | 0.279 | 0.052 | 0.052 | 0.711 | 0.289 | 0.301 | 0.485 |
| 35-55 | 2808 | 0.189 | 0.260 | 0.072 | 0.072 | 0.668 | 0.332 | 0.260 | 0.442 |
| 55<= | 87 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.043 (0-35 vs 35-55); precision 0.041 (0-35 vs 35-55); false_positive_rate 0.043 (0-35 vs 35-55); false_negative_rate 0.043 (35-55 vs 0-35); pr_auc 0.055 (0-35 vs 35-55); calibration_gap 0.020 (35-55 vs 0-35); ece 0.020 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 8346 | 0.211 | 0.271 | 0.061 | 0.061 | 0.700 | 0.300 | 0.287 | 0.464 |
| Y | 852 | 0.255 | 0.288 | 0.034 | 0.054 | 0.700 | 0.300 | 0.310 | 0.534 |

Largest gaps between groups (max - min): recall 0.000 (Y vs N); precision 0.022 (Y vs N); false_positive_rate 0.070 (Y vs N); false_negative_rate 0.000 (N vs Y); pr_auc 0.032 (Y vs N); calibration_gap 0.027 (N vs Y); ece 0.007 (N vs Y)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 820 | 0.272 | 0.286 | 0.014 | 0.039 | 0.682 | 0.318 | 0.342 | 0.489 |
| 10-20 | 910 | 0.262 | 0.282 | 0.021 | 0.034 | 0.756 | 0.244 | 0.359 | 0.479 |
| 20-30% | 970 | 0.238 | 0.273 | 0.034 | 0.045 | 0.714 | 0.286 | 0.322 | 0.470 |
| 30-40% | 979 | 0.216 | 0.274 | 0.058 | 0.069 | 0.673 | 0.327 | 0.282 | 0.470 |
| 40-50% | 921 | 0.214 | 0.275 | 0.061 | 0.061 | 0.701 | 0.299 | 0.281 | 0.488 |
| 50-60% | 920 | 0.216 | 0.275 | 0.059 | 0.059 | 0.714 | 0.286 | 0.292 | 0.479 |
| 60-70% | 886 | 0.196 | 0.263 | 0.066 | 0.067 | 0.661 | 0.339 | 0.261 | 0.456 |
| 70-80% | 870 | 0.218 | 0.272 | 0.053 | 0.063 | 0.742 | 0.258 | 0.321 | 0.438 |
| 80-90% | 809 | 0.185 | 0.272 | 0.087 | 0.087 | 0.640 | 0.360 | 0.231 | 0.486 |
| 90-100% | 747 | 0.154 | 0.267 | 0.113 | 0.113 | 0.713 | 0.287 | 0.213 | 0.479 |
| unknown | 366 | 0.128 | 0.247 | 0.119 | 0.119 | 0.638 | 0.362 | 0.190 | 0.401 |

Largest gaps between groups (max - min): recall 0.118 (10-20 vs unknown); precision 0.169 (10-20 vs unknown); false_positive_rate 0.088 (0-10% vs unknown); false_negative_rate 0.118 (unknown vs 10-20); pr_auc 0.149 (70-80% vs 80-90%); calibration_gap 0.105 (unknown vs 0-10%); ece 0.085 (unknown vs 10-20)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | mean_submission_delay_days | psi | 0.221 | 0.100 | warning |
| feature_drift | mean_score_to_date | psi | 1.131 | 0.250 | critical |
| feature_drift | last_score | psi | 1.104 | 0.250 | critical |
| feature_drift | course_relative_score | psi | 1.059 | 0.250 | critical |
| feature_drift | quiz_clicks_to_date | psi | 0.171 | 0.100 | warning |
| feature_drift | quiz_clicks_last_14d | psi | 0.107 | 0.100 | warning |
| feature_drift | quiz_clicks_last_30d | psi | 0.151 | 0.100 | warning |
| feature_drift | quiz_trend_14d | psi | 0.154 | 0.100 | warning |
| feature_drift | forum_clicks_to_date | psi | 0.151 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.155 | 0.100 | warning |
| feature_drift | score_trend_per_30d | psi | 0.446 | 0.250 | critical |
| feature_drift | score_change_from_first | psi | 0.475 | 0.250 | critical |
| outcome_drift | outcome | rate_change | 0.060 | 0.050 | warning |
| performance_drop | pr_auc | metric_drop | 0.111 | 0.100 | critical |

## Target: course_failure — decision point day 60

Definition: final_result is Fail (students who later withdraw count as 0). Horizon: end of the module presentation.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11353 | 3233 | 0.285 |
| validation | 2014B | 6184 | 1832 | 0.296 |
| test | 2014J | 8816 | 1975 | 0.224 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.601 | 0.770 | 0.166 |
| Logistic Regression | balanced | 0.597 | 0.770 | 0.191 |
| Random Forest | none (selected) | 0.614 | 0.778 | 0.164 |
| Random Forest | balanced | 0.615 | 0.780 | 0.192 |
| XGBoost | none | 0.598 | 0.771 | 0.167 |
| XGBoost | balanced (selected) | 0.608 | 0.778 | 0.192 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: 'balanced' improved validation PR-AUC by only 0.0007 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- XGBoost: 'balanced' improved validation PR-AUC by more than 0.005 over no re-weighting.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.410 [0.390, 0.436] | 0.696 [0.683, 0.710] | 0.166 -> 0.166 | 0.071 -> 0.075 | 0.266 | 0.345 | 0.648 | 0.451 |
| Random Forest | 0.449 [0.426, 0.474] | 0.736 [0.725, 0.749] | 0.158 -> 0.157 | 0.072 -> 0.057 | 0.282 | 0.381 | 0.622 | 0.473 |
| XGBoost | 0.431 [0.410, 0.456] | 0.730 [0.718, 0.743] | 0.207 -> 0.160 | 0.196 -> 0.055 | 0.334 | 0.389 | 0.599 | 0.472 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.541 / 0.242 | 0.448 / 0.401 | 0.389 / 0.521 |
| Random Forest | 0.562 / 0.251 | 0.468 / 0.418 | 0.401 / 0.537 |
| XGBoost | 0.529 / 0.236 | 0.455 / 0.407 | 0.408 / 0.546 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.864 / 0.645 / 0.739 (6841) | 0.345 / 0.648 / 0.451 (1975) | 4414 | 2427 | 695 | 1280 |
| Random Forest | 0.867 / 0.709 / 0.780 (6841) | 0.381 / 0.622 / 0.473 (1975) | 4848 | 1993 | 746 | 1229 |
| XGBoost | 0.863 / 0.728 / 0.790 (6841) | 0.389 / 0.599 / 0.472 (1975) | 4980 | 1861 | 791 | 1184 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.231 / 0.403 / 0.642 | 4556 (0.52), obs 0.13 | 1968 (0.22), obs 0.23 | 1610 (0.18), obs 0.35 | 682 (0.08), obs 0.55 |
| Random Forest | 0.213 / 0.386 / 0.707 | 4454 (0.51), obs 0.11 | 2250 (0.26), obs 0.24 | 1536 (0.17), obs 0.39 | 576 (0.07), obs 0.58 |
| XGBoost | 0.223 / 0.460 / 0.647 | 4570 (0.52), obs 0.11 | 2310 (0.26), obs 0.26 | 1269 (0.14), obs 0.38 | 667 (0.08), obs 0.55 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.6006 | 0.0000 | 1.00 |
| Random Forest | 0.6143 | 0.0002 | 0.67 |
| XGBoost | 0.6051 | 0.0007 | 0.59 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | course_relative_score, mean_score_to_date, score_trend_per_30d, clicks_to_date, completion_rate_last_30d |
| Random Forest | Tree SHAP (probability); 300 trees | course_relative_score, mean_score_to_date, assignment_completion_rate, mean_submission_delay_days, completion_rate_last_30d |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | course_relative_score, mean_submission_delay_days, assignment_completion_rate, score_trend_per_30d, active_days_to_date |

### Model selection

**Selected: XGBoost** (`oulad-v2-20260924T003349Z-fail-xgb-d60`).

Validation PR-AUC best = 0.6143 (random_forest). Models within 0.010 of it: random_forest, xgboost. Selected the most interpretable of these (xgboost; validation PR-AUC 0.6076, Brier 0.1653, seed PR-AUC std 0.0007).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.168 -> 0.167 | 0.026 -> 0.021 | yes |
| Random Forest | 2013B / 2013J / 2014B | 0.174 -> 0.167 | 0.080 -> 0.021 | yes |
| XGBoost | 2013B / 2013J / 2014B | 0.209 -> 0.173 | 0.169 -> 0.028 | yes |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3730 | 0.212 | 0.274 | 0.062 | 0.069 | 0.571 | 0.429 | 0.362 | 0.271 |
| M | 5086 | 0.233 | 0.282 | 0.049 | 0.050 | 0.618 | 0.382 | 0.407 | 0.273 |

Largest gaps between groups (max - min): recall 0.047 (M vs F); precision 0.045 (M vs F); false_positive_rate 0.002 (M vs F); false_negative_rate 0.047 (F vs M); pr_auc 0.068 (M vs F); calibration_gap 0.013 (F vs M); ece 0.019 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 6029 | 0.237 | 0.290 | 0.053 | 0.053 | 0.615 | 0.385 | 0.399 | 0.288 |
| 35-55 | 2706 | 0.196 | 0.256 | 0.060 | 0.060 | 0.560 | 0.440 | 0.360 | 0.243 |
| 55<= | 81 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.055 (0-35 vs 35-55); precision 0.040 (0-35 vs 35-55); false_positive_rate 0.045 (0-35 vs 35-55); false_negative_rate 0.055 (35-55 vs 0-35); pr_auc 0.044 (0-35 vs 35-55); calibration_gap 0.008 (35-55 vs 0-35); ece 0.008 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 8013 | 0.219 | 0.276 | 0.056 | 0.056 | 0.601 | 0.399 | 0.390 | 0.265 |
| Y | 803 | 0.270 | 0.310 | 0.040 | 0.084 | 0.585 | 0.415 | 0.381 | 0.352 |

Largest gaps between groups (max - min): recall 0.016 (N vs Y); precision 0.008 (N vs Y); false_positive_rate 0.087 (Y vs N); false_negative_rate 0.016 (Y vs N); pr_auc 0.017 (Y vs N); calibration_gap 0.016 (N vs Y); ece 0.028 (Y vs N)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 779 | 0.286 | 0.294 | 0.008 | 0.061 | 0.561 | 0.439 | 0.424 | 0.306 |
| 10-20 | 866 | 0.275 | 0.300 | 0.025 | 0.053 | 0.630 | 0.370 | 0.445 | 0.298 |
| 20-30% | 935 | 0.247 | 0.289 | 0.042 | 0.054 | 0.636 | 0.364 | 0.424 | 0.284 |
| 30-40% | 939 | 0.225 | 0.290 | 0.065 | 0.072 | 0.607 | 0.393 | 0.370 | 0.299 |
| 40-50% | 875 | 0.225 | 0.281 | 0.056 | 0.056 | 0.594 | 0.406 | 0.389 | 0.271 |
| 50-60% | 885 | 0.225 | 0.281 | 0.056 | 0.069 | 0.623 | 0.377 | 0.385 | 0.289 |
| 60-70% | 853 | 0.204 | 0.266 | 0.062 | 0.062 | 0.569 | 0.431 | 0.368 | 0.250 |
| 70-80% | 834 | 0.228 | 0.270 | 0.042 | 0.052 | 0.579 | 0.421 | 0.414 | 0.242 |
| 80-90% | 776 | 0.193 | 0.271 | 0.078 | 0.078 | 0.607 | 0.393 | 0.351 | 0.268 |
| 90-100% | 715 | 0.161 | 0.258 | 0.097 | 0.097 | 0.574 | 0.426 | 0.310 | 0.245 |
| unknown | 359 | 0.131 | 0.236 | 0.105 | 0.108 | 0.574 | 0.426 | 0.300 | 0.202 |

Largest gaps between groups (max - min): recall 0.076 (20-30% vs 0-10%); precision 0.145 (10-20 vs unknown); false_positive_rate 0.104 (0-10% vs unknown); false_negative_rate 0.076 (0-10% vs 20-30%); pr_auc 0.112 (20-30% vs unknown); calibration_gap 0.097 (unknown vs 0-10%); ece 0.055 (unknown vs 70-80%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | assessments_due_to_date | psi | 3.335 | 0.250 | critical |
| feature_drift | late_submission_rate | psi | 0.692 | 0.250 | critical |
| feature_drift | mean_score_to_date | psi | 0.342 | 0.250 | critical |
| feature_drift | last_score | psi | 0.384 | 0.250 | critical |
| feature_drift | course_relative_score | psi | 0.211 | 0.100 | warning |
| feature_drift | quiz_clicks_to_date | psi | 0.525 | 0.250 | critical |
| feature_drift | quiz_clicks_last_14d | psi | 0.158 | 0.100 | warning |
| feature_drift | quiz_clicks_last_30d | psi | 0.257 | 0.250 | critical |
| feature_drift | quiz_trend_14d | psi | 0.146 | 0.100 | warning |
| feature_drift | forum_clicks_to_date | psi | 0.195 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.102 | 0.100 | warning |
| feature_drift | forum_trend_14d | psi | 0.225 | 0.100 | warning |
| feature_drift | submissions_last_30d | psi | 0.490 | 0.250 | critical |
| feature_drift | score_trend_per_30d | psi | 0.541 | 0.250 | critical |
| feature_drift | score_change_from_first | psi | 0.281 | 0.250 | critical |
| outcome_drift | outcome | rate_change | 0.061 | 0.050 | warning |
| performance_drop | pr_auc | metric_drop | 0.177 | 0.100 | critical |

## Target: course_failure — decision point day 90

Definition: final_result is Fail (students who later withdraw count as 0). Horizon: end of the module presentation.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11052 | 3233 | 0.293 |
| validation | 2014B | 5974 | 1833 | 0.307 |
| test | 2014J | 8532 | 1976 | 0.232 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.680 | 0.831 | 0.149 |
| Logistic Regression | balanced | 0.674 | 0.830 | 0.172 |
| Random Forest | none (selected) | 0.697 | 0.826 | 0.149 |
| Random Forest | balanced | 0.698 | 0.827 | 0.172 |
| XGBoost | none | 0.659 | 0.814 | 0.157 |
| XGBoost | balanced (selected) | 0.672 | 0.817 | 0.180 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: 'balanced' improved validation PR-AUC by only 0.0013 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- XGBoost: 'balanced' improved validation PR-AUC by more than 0.005 over no re-weighting.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.511 [0.491, 0.536] | 0.784 [0.773, 0.796] | 0.147 -> 0.147 | 0.044 -> 0.038 | 0.247 | 0.431 | 0.705 | 0.535 |
| Random Forest | 0.534 [0.511, 0.559] | 0.789 [0.777, 0.801] | 0.147 -> 0.146 | 0.070 -> 0.052 | 0.318 | 0.470 | 0.654 | 0.547 |
| XGBoost | 0.506 [0.486, 0.532] | 0.775 [0.765, 0.787] | 0.195 -> 0.152 | 0.189 -> 0.054 | 0.308 | 0.429 | 0.697 | 0.531 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.636 / 0.275 | 0.549 / 0.474 | 0.477 / 0.618 |
| Random Forest | 0.660 / 0.285 | 0.554 / 0.478 | 0.484 / 0.628 |
| XGBoost | 0.617 / 0.267 | 0.529 / 0.457 | 0.464 / 0.601 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.890 / 0.719 / 0.796 (6556) | 0.431 / 0.705 / 0.535 (1976) | 4717 | 1839 | 582 | 1394 |
| Random Forest | 0.882 / 0.778 / 0.826 (6556) | 0.470 / 0.654 / 0.547 (1976) | 5098 | 1458 | 683 | 1293 |
| XGBoost | 0.888 / 0.720 / 0.795 (6556) | 0.429 / 0.697 / 0.531 (1976) | 4719 | 1837 | 598 | 1378 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.209 / 0.420 / 0.787 | 4641 (0.54), obs 0.09 | 2268 (0.27), obs 0.28 | 1092 (0.13), obs 0.52 | 531 (0.06), obs 0.65 |
| Random Forest | 0.207 / 0.426 / 0.814 | 4340 (0.51), obs 0.09 | 2407 (0.28), obs 0.26 | 1261 (0.15), obs 0.50 | 524 (0.06), obs 0.66 |
| XGBoost | 0.223 / 0.511 / 0.711 | 4528 (0.53), obs 0.10 | 2287 (0.27), obs 0.27 | 1172 (0.14), obs 0.47 | 545 (0.06), obs 0.65 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.6802 | 0.0000 | 1.00 |
| Random Forest | 0.6974 | 0.0001 | 0.78 |
| XGBoost | 0.6761 | 0.0017 | 0.78 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | course_relative_score, clicks_last_30d, assignment_completion_rate, quiz_clicks_last_30d, days_since_last_activity |
| Random Forest | Tree SHAP (probability); 300 trees | course_relative_score, assignment_completion_rate, clicks_last_30d, mean_score_to_date, mean_submission_delay_days |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | course_relative_score, assignment_completion_rate, mean_score_to_date, clicks_last_30d, mean_submission_delay_days |

### Model selection

**Selected: Random Forest** (`oulad-v2-20260924T003349Z-fail-rf-d90`).

Validation PR-AUC best = 0.6971 (random_forest). Models within 0.010 of it: random_forest. Selected the most interpretable of these (random_forest; validation PR-AUC 0.6971, Brier 0.1487, seed PR-AUC std 0.0001).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.202 -> 0.173 | 0.156 -> 0.055 | yes |
| Random Forest | 2013B / 2013J / 2014B | 0.160 -> 0.155 | 0.089 -> 0.050 | yes |
| XGBoost | 2013B / 2013J / 2014B | 0.187 -> 0.158 | 0.149 -> 0.041 | yes |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3627 | 0.218 | 0.295 | 0.077 | 0.077 | 0.668 | 0.332 | 0.432 | 0.245 |
| M | 4905 | 0.242 | 0.275 | 0.034 | 0.034 | 0.646 | 0.354 | 0.501 | 0.205 |

Largest gaps between groups (max - min): recall 0.022 (F vs M); precision 0.069 (M vs F); false_positive_rate 0.040 (F vs M); false_negative_rate 0.022 (M vs F); pr_auc 0.048 (M vs F); calibration_gap 0.043 (F vs M); ece 0.043 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 5831 | 0.245 | 0.295 | 0.049 | 0.049 | 0.672 | 0.328 | 0.479 | 0.238 |
| 35-55 | 2621 | 0.203 | 0.260 | 0.058 | 0.058 | 0.603 | 0.397 | 0.442 | 0.193 |
| 55<= | 80 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.070 (0-35 vs 35-55); precision 0.037 (0-35 vs 35-55); false_positive_rate 0.045 (0-35 vs 35-55); false_negative_rate 0.070 (35-55 vs 0-35); pr_auc 0.072 (0-35 vs 35-55); calibration_gap 0.009 (35-55 vs 0-35); ece 0.009 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 7771 | 0.226 | 0.278 | 0.052 | 0.052 | 0.646 | 0.354 | 0.469 | 0.214 |
| Y | 761 | 0.285 | 0.335 | 0.049 | 0.055 | 0.719 | 0.281 | 0.474 | 0.318 |

Largest gaps between groups (max - min): recall 0.073 (Y vs N); precision 0.005 (Y vs N); false_positive_rate 0.104 (Y vs N); false_negative_rate 0.073 (N vs Y); pr_auc 0.009 (Y vs N); calibration_gap 0.003 (N vs Y); ece 0.003 (Y vs N)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 741 | 0.301 | 0.317 | 0.016 | 0.030 | 0.655 | 0.345 | 0.497 | 0.286 |
| 10-20 | 830 | 0.287 | 0.316 | 0.030 | 0.061 | 0.723 | 0.277 | 0.539 | 0.248 |
| 20-30% | 893 | 0.259 | 0.304 | 0.045 | 0.046 | 0.688 | 0.312 | 0.492 | 0.248 |
| 30-40% | 901 | 0.234 | 0.289 | 0.055 | 0.064 | 0.673 | 0.327 | 0.469 | 0.233 |
| 40-50% | 846 | 0.233 | 0.293 | 0.060 | 0.061 | 0.624 | 0.376 | 0.446 | 0.236 |
| 50-60% | 860 | 0.231 | 0.280 | 0.049 | 0.062 | 0.673 | 0.327 | 0.506 | 0.198 |
| 60-70% | 834 | 0.209 | 0.269 | 0.060 | 0.066 | 0.609 | 0.391 | 0.444 | 0.202 |
| 70-80% | 820 | 0.232 | 0.274 | 0.042 | 0.057 | 0.605 | 0.395 | 0.462 | 0.213 |
| 80-90% | 759 | 0.199 | 0.262 | 0.063 | 0.063 | 0.589 | 0.411 | 0.410 | 0.211 |
| 90-100% | 696 | 0.165 | 0.255 | 0.090 | 0.099 | 0.678 | 0.322 | 0.415 | 0.189 |
| unknown | 352 | 0.134 | 0.213 | 0.079 | 0.080 | 0.617 | 0.383 | 0.372 | 0.161 |

Largest gaps between groups (max - min): recall 0.133 (10-20 vs 80-90%); precision 0.167 (10-20 vs unknown); false_positive_rate 0.125 (0-10% vs unknown); false_negative_rate 0.133 (80-90% vs 10-20); pr_auc 0.174 (0-10% vs unknown); calibration_gap 0.074 (90-100% vs 0-10%); ece 0.069 (90-100% vs 0-10%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | clicks_last_7d | psi | 0.114 | 0.100 | warning |
| feature_drift | clicks_last_14d | psi | 0.158 | 0.100 | warning |
| feature_drift | clicks_trend_7d | psi | 0.104 | 0.100 | warning |
| feature_drift | clicks_trend_14d | psi | 0.183 | 0.100 | warning |
| feature_drift | clicks_change_from_baseline | psi | 0.114 | 0.100 | warning |
| feature_drift | days_since_last_activity | psi | 0.102 | 0.100 | warning |
| feature_drift | assessments_due_to_date | psi | 1.892 | 0.250 | critical |
| feature_drift | late_submission_rate | psi | 0.514 | 0.250 | critical |
| feature_drift | mean_submission_delay_days | psi | 0.152 | 0.100 | warning |
| feature_drift | mean_score_to_date | psi | 0.136 | 0.100 | warning |
| feature_drift | last_score | psi | 0.153 | 0.100 | warning |
| feature_drift | course_relative_score | psi | 0.168 | 0.100 | warning |
| feature_drift | active_days_last_14d | psi | 0.156 | 0.100 | warning |
| feature_drift | quiz_clicks_to_date | psi | 0.326 | 0.250 | critical |
| feature_drift | quiz_clicks_last_7d | psi | 0.107 | 0.100 | warning |
| feature_drift | quiz_clicks_last_14d | psi | 0.275 | 0.250 | critical |
| feature_drift | quiz_clicks_last_30d | psi | 0.371 | 0.250 | critical |
| feature_drift | quiz_trend_14d | psi | 0.261 | 0.250 | critical |
| feature_drift | forum_clicks_to_date | psi | 0.199 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.161 | 0.100 | warning |
| feature_drift | forum_trend_14d | psi | 0.112 | 0.100 | warning |
| feature_drift | content_trend_14d | psi | 0.139 | 0.100 | warning |
| feature_drift | submissions_last_30d | psi | 0.170 | 0.100 | warning |
| missingness_drift | completion_rate_last_30d | missing_rate_change | 0.083 | 0.050 | warning |
| feature_drift | score_trend_per_30d | psi | 0.161 | 0.100 | warning |
| feature_drift | score_change_from_first | psi | 0.174 | 0.100 | warning |
| feature_drift | clicks_last_7d_vs_30d_rate | psi | 0.123 | 0.100 | warning |
| outcome_drift | outcome | rate_change | 0.061 | 0.050 | warning |
| performance_drop | pr_auc | metric_drop | 0.164 | 0.100 | critical |

## Target: engagement — decision point day 30

Definition: no VLE activity at all in the 14 days after the cutoff. Horizon: 14 days.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11759 | 1766 | 0.150 |
| validation | 2014B | 6493 | 1132 | 0.174 |
| test | 2014J | 9198 | 1268 | 0.138 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.678 | 0.891 | 0.089 |
| Logistic Regression | balanced | 0.678 | 0.891 | 0.131 |
| Random Forest | none (selected) | 0.684 | 0.894 | 0.087 |
| Random Forest | balanced | 0.681 | 0.894 | 0.129 |
| XGBoost | none (selected) | 0.680 | 0.892 | 0.088 |
| XGBoost | balanced | 0.684 | 0.893 | 0.118 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: no re-weighting had the best validation PR-AUC.
- XGBoost: 'balanced' improved validation PR-AUC by only 0.0041 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.605 [0.578, 0.632] | 0.881 [0.870, 0.889] | 0.080 -> 0.080 | 0.015 -> 0.011 | 0.297 | 0.527 | 0.640 | 0.578 |
| Random Forest | 0.611 [0.581, 0.639] | 0.893 [0.884, 0.901] | 0.078 -> 0.081 | 0.010 -> 0.037 | 0.315 | 0.573 | 0.588 | 0.580 |
| XGBoost | 0.587 [0.557, 0.617] | 0.882 [0.871, 0.891] | 0.081 -> 0.083 | 0.021 -> 0.028 | 0.335 | 0.578 | 0.549 | 0.563 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.637 / 0.462 | 0.483 / 0.701 | 0.376 / 0.818 |
| Random Forest | 0.650 / 0.472 | 0.483 / 0.701 | 0.385 / 0.838 |
| XGBoost | 0.640 / 0.465 | 0.477 / 0.692 | 0.371 / 0.808 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.940 / 0.908 / 0.924 (7930) | 0.527 / 0.640 / 0.578 (1268) | 7201 | 729 | 457 | 811 |
| Random Forest | 0.934 / 0.930 / 0.932 (7930) | 0.573 / 0.588 / 0.580 (1268) | 7373 | 557 | 522 | 746 |
| XGBoost | 0.928 / 0.936 / 0.932 (7930) | 0.578 / 0.549 / 0.563 (1268) | 7422 | 508 | 572 | 696 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.069 / 0.243 / 0.569 | 4947 (0.54), obs 0.02 | 2371 (0.26), obs 0.11 | 1253 (0.14), obs 0.35 | 627 (0.07), obs 0.73 |
| Random Forest | 0.058 / 0.234 / 0.555 | 4851 (0.53), obs 0.02 | 2581 (0.28), obs 0.12 | 1112 (0.12), obs 0.37 | 654 (0.07), obs 0.70 |
| XGBoost | 0.033 / 0.212 / 0.622 | 4907 (0.53), obs 0.02 | 2536 (0.28), obs 0.12 | 1125 (0.12), obs 0.37 | 630 (0.07), obs 0.70 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.6782 | 0.0000 | 1.00 |
| Random Forest | 0.6824 | 0.0010 | 1.00 |
| XGBoost | 0.6806 | 0.0020 | 1.00 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | active_days_to_date, active_days_last_14d, course_relative_score, forum_clicks_last_14d, quiz_clicks_to_date |
| Random Forest | Tree SHAP (probability); 300 trees | active_days_to_date, active_days_last_14d, clicks_last_7d, clicks_last_30d, clicks_to_date |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | active_days_to_date, active_days_last_14d, days_since_last_activity, clicks_last_30d, clicks_last_7d |

### Model selection

**Selected: Logistic Regression** (`oulad-v2-20260924T003349Z-eng-lr-d30`).

Validation PR-AUC best = 0.6843 (random_forest). Models within 0.010 of it: logistic_regression, random_forest, xgboost. Selected the most interpretable of these (logistic_regression; validation PR-AUC 0.6782, Brier 0.0887, seed PR-AUC std 0.0000).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.102 -> 0.098 | 0.051 -> 0.014 | yes |
| Random Forest | 2013B / 2013J / 2014B | 0.089 -> 0.089 | 0.024 -> 0.018 | no |
| XGBoost | 2013B / 2013J / 2014B | 0.095 -> 0.097 | 0.035 -> 0.027 | no |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3869 | 0.175 | 0.173 | -0.003 | 0.022 | 0.647 | 0.353 | 0.536 | 0.119 |
| M | 5329 | 0.111 | 0.129 | 0.018 | 0.019 | 0.632 | 0.368 | 0.516 | 0.074 |

Largest gaps between groups (max - min): recall 0.015 (F vs M); precision 0.020 (F vs M); false_positive_rate 0.045 (F vs M); false_negative_rate 0.015 (M vs F); pr_auc 0.020 (F vs M); calibration_gap 0.021 (M vs F); ece 0.004 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 6303 | 0.140 | 0.154 | 0.014 | 0.015 | 0.639 | 0.361 | 0.516 | 0.098 |
| 35-55 | 2808 | 0.135 | 0.134 | -0.001 | 0.020 | 0.637 | 0.363 | 0.553 | 0.081 |
| 55<= | 87 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.003 (0-35 vs 35-55); precision 0.037 (35-55 vs 0-35); false_positive_rate 0.017 (0-35 vs 35-55); false_negative_rate 0.003 (35-55 vs 0-35); pr_auc 0.027 (0-35 vs 35-55); calibration_gap 0.015 (0-35 vs 35-55); ece 0.004 (35-55 vs 0-35)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 8346 | 0.135 | 0.144 | 0.009 | 0.010 | 0.633 | 0.367 | 0.530 | 0.088 |
| Y | 852 | 0.163 | 0.178 | 0.015 | 0.042 | 0.691 | 0.309 | 0.503 | 0.133 |

Largest gaps between groups (max - min): recall 0.057 (Y vs N); precision 0.027 (N vs Y); false_positive_rate 0.045 (Y vs N); false_negative_rate 0.057 (N vs Y); pr_auc 0.067 (N vs Y); calibration_gap 0.006 (Y vs N); ece 0.032 (Y vs N)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 820 | 0.167 | 0.168 | 0.001 | 0.031 | 0.657 | 0.343 | 0.596 | 0.089 |
| 10-20 | 910 | 0.173 | 0.162 | -0.011 | 0.028 | 0.643 | 0.357 | 0.567 | 0.102 |
| 20-30% | 970 | 0.161 | 0.158 | -0.003 | 0.019 | 0.660 | 0.340 | 0.572 | 0.095 |
| 30-40% | 979 | 0.141 | 0.150 | 0.009 | 0.026 | 0.594 | 0.406 | 0.497 | 0.099 |
| 40-50% | 921 | 0.135 | 0.148 | 0.014 | 0.022 | 0.581 | 0.419 | 0.471 | 0.102 |
| 50-60% | 920 | 0.137 | 0.151 | 0.014 | 0.022 | 0.643 | 0.357 | 0.509 | 0.098 |
| 60-70% | 886 | 0.124 | 0.139 | 0.015 | 0.028 | 0.700 | 0.300 | 0.531 | 0.088 |
| 70-80% | 870 | 0.132 | 0.148 | 0.016 | 0.018 | 0.652 | 0.348 | 0.500 | 0.099 |
| 80-90% | 809 | 0.122 | 0.142 | 0.019 | 0.022 | 0.646 | 0.354 | 0.512 | 0.086 |
| 90-100% | 747 | 0.114 | 0.132 | 0.018 | 0.026 | 0.647 | 0.353 | 0.514 | 0.079 |
| unknown | 366 | 0.057 | 0.085 | 0.027 | 0.028 | 0.524 | 0.476 | 0.407 | 0.046 |

Largest gaps between groups (max - min): recall 0.176 (60-70% vs unknown); precision 0.189 (0-10% vs unknown); false_positive_rate 0.056 (10-20 vs unknown); false_negative_rate 0.176 (unknown vs 60-70%); pr_auc 0.259 (0-10% vs unknown); calibration_gap 0.038 (unknown vs 10-20); ece 0.013 (0-10% vs 70-80%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | mean_submission_delay_days | psi | 0.221 | 0.100 | warning |
| feature_drift | mean_score_to_date | psi | 1.131 | 0.250 | critical |
| feature_drift | last_score | psi | 1.104 | 0.250 | critical |
| feature_drift | course_relative_score | psi | 1.059 | 0.250 | critical |
| feature_drift | quiz_clicks_to_date | psi | 0.171 | 0.100 | warning |
| feature_drift | quiz_clicks_last_14d | psi | 0.107 | 0.100 | warning |
| feature_drift | quiz_clicks_last_30d | psi | 0.151 | 0.100 | warning |
| feature_drift | quiz_trend_14d | psi | 0.154 | 0.100 | warning |
| feature_drift | forum_clicks_to_date | psi | 0.151 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.155 | 0.100 | warning |
| feature_drift | score_trend_per_30d | psi | 0.446 | 0.250 | critical |
| feature_drift | score_change_from_first | psi | 0.475 | 0.250 | critical |
| performance_drop | pr_auc | metric_drop | 0.074 | 0.050 | warning |

## Target: engagement — decision point day 60

Definition: no VLE activity at all in the 14 days after the cutoff. Horizon: 14 days.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11353 | 2894 | 0.255 |
| validation | 2014B | 6184 | 1435 | 0.232 |
| test | 2014J | 8816 | 1863 | 0.211 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.763 | 0.893 | 0.108 |
| Logistic Regression | balanced | 0.758 | 0.892 | 0.158 |
| Random Forest | none (selected) | 0.765 | 0.892 | 0.109 |
| Random Forest | balanced | 0.765 | 0.893 | 0.156 |
| XGBoost | none (selected) | 0.764 | 0.891 | 0.109 |
| XGBoost | balanced | 0.764 | 0.891 | 0.149 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: no re-weighting had the best validation PR-AUC.
- XGBoost: no re-weighting had the best validation PR-AUC.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.725 [0.706, 0.744] | 0.891 [0.884, 0.898] | 0.105 -> 0.099 | 0.055 -> 0.012 | 0.505 | 0.648 | 0.663 | 0.655 |
| Random Forest | 0.710 [0.691, 0.729] | 0.879 [0.871, 0.887] | 0.107 -> 0.105 | 0.051 -> 0.022 | 0.506 | 0.670 | 0.586 | 0.625 |
| XGBoost | 0.711 [0.690, 0.732] | 0.880 [0.871, 0.887] | 0.107 -> 0.104 | 0.042 -> 0.022 | 0.517 | 0.658 | 0.600 | 0.628 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.831 / 0.393 | 0.671 / 0.635 | 0.552 / 0.784 |
| Random Forest | 0.820 / 0.388 | 0.647 / 0.613 | 0.531 / 0.754 |
| XGBoost | 0.815 / 0.386 | 0.651 / 0.616 | 0.534 / 0.758 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.909 / 0.903 / 0.906 (6953) | 0.648 / 0.663 / 0.655 (1863) | 6282 | 671 | 628 | 1235 |
| Random Forest | 0.893 / 0.922 / 0.907 (6953) | 0.670 / 0.586 / 0.625 (1863) | 6414 | 539 | 771 | 1092 |
| XGBoost | 0.895 / 0.917 / 0.906 (6953) | 0.658 / 0.600 / 0.628 (1863) | 6373 | 580 | 746 | 1117 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.171 / 0.468 / 0.839 | 4748 (0.54), obs 0.04 | 1994 (0.23), obs 0.20 | 1404 (0.16), obs 0.50 | 670 (0.08), obs 0.89 |
| Random Forest | 0.199 / 0.485 / 0.822 | 4878 (0.55), obs 0.04 | 2220 (0.25), obs 0.24 | 1080 (0.12), obs 0.52 | 638 (0.07), obs 0.88 |
| XGBoost | 0.155 / 0.495 / 0.834 | 4746 (0.54), obs 0.04 | 2289 (0.26), obs 0.22 | 1182 (0.13), obs 0.53 | 599 (0.07), obs 0.88 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.7627 | 0.0000 | 1.00 |
| Random Forest | 0.7654 | 0.0003 | 0.67 |
| XGBoost | 0.7645 | 0.0008 | 1.00 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | active_days_to_date, clicks_last_30d, clicks_last_7d_vs_30d_rate, course_relative_score, clicks_trend_7d |
| Random Forest | Tree SHAP (probability); 300 trees | active_days_to_date, clicks_last_30d, active_days_last_14d, clicks_to_date, days_since_last_activity |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | active_days_to_date, days_since_last_activity, active_days_last_14d, clicks_last_30d, assessments_due_to_date |

### Model selection

**Selected: Logistic Regression** (`oulad-v2-20260924T003349Z-eng-lr-d60`).

Validation PR-AUC best = 0.7651 (random_forest). Models within 0.010 of it: logistic_regression, random_forest, xgboost. Selected the most interpretable of these (logistic_regression; validation PR-AUC 0.7627, Brier 0.1078, seed PR-AUC std 0.0000).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.119 -> 0.119 | 0.062 -> 0.080 | no |
| Random Forest | 2013B / 2013J / 2014B | 0.116 -> 0.118 | 0.069 -> 0.080 | no |
| XGBoost | 2013B / 2013J / 2014B | 0.122 -> 0.121 | 0.063 -> 0.065 | no |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3730 | 0.264 | 0.340 | 0.076 | 0.076 | 0.695 | 0.305 | 0.614 | 0.157 |
| M | 5086 | 0.173 | 0.212 | 0.039 | 0.039 | 0.626 | 0.374 | 0.695 | 0.057 |

Largest gaps between groups (max - min): recall 0.069 (F vs M); precision 0.081 (M vs F); false_positive_rate 0.099 (F vs M); false_negative_rate 0.069 (M vs F); pr_auc 0.001 (M vs F); calibration_gap 0.037 (F vs M); ece 0.037 (F vs M)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 6029 | 0.218 | 0.276 | 0.058 | 0.058 | 0.660 | 0.340 | 0.643 | 0.102 |
| 35-55 | 2706 | 0.200 | 0.248 | 0.048 | 0.048 | 0.666 | 0.334 | 0.660 | 0.086 |
| 55<= | 81 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.006 (35-55 vs 0-35); precision 0.017 (35-55 vs 0-35); false_positive_rate 0.016 (0-35 vs 35-55); false_negative_rate 0.006 (0-35 vs 35-55); pr_auc 0.028 (0-35 vs 35-55); calibration_gap 0.010 (0-35 vs 35-55); ece 0.010 (0-35 vs 35-55)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 8013 | 0.207 | 0.263 | 0.055 | 0.055 | 0.672 | 0.328 | 0.652 | 0.094 |
| Y | 803 | 0.252 | 0.300 | 0.048 | 0.059 | 0.589 | 0.411 | 0.613 | 0.125 |

Largest gaps between groups (max - min): recall 0.083 (N vs Y); precision 0.038 (N vs Y); false_positive_rate 0.031 (Y vs N); false_negative_rate 0.083 (Y vs N); pr_auc 0.082 (N vs Y); calibration_gap 0.007 (N vs Y); ece 0.004 (Y vs N)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 779 | 0.250 | 0.312 | 0.061 | 0.061 | 0.667 | 0.333 | 0.631 | 0.130 |
| 10-20 | 866 | 0.260 | 0.305 | 0.046 | 0.046 | 0.693 | 0.307 | 0.706 | 0.101 |
| 20-30% | 935 | 0.261 | 0.296 | 0.036 | 0.043 | 0.676 | 0.324 | 0.685 | 0.110 |
| 30-40% | 939 | 0.218 | 0.273 | 0.054 | 0.058 | 0.644 | 0.356 | 0.653 | 0.095 |
| 40-50% | 875 | 0.232 | 0.276 | 0.044 | 0.045 | 0.635 | 0.365 | 0.648 | 0.104 |
| 50-60% | 885 | 0.207 | 0.270 | 0.064 | 0.064 | 0.667 | 0.333 | 0.639 | 0.098 |
| 60-70% | 853 | 0.197 | 0.250 | 0.053 | 0.053 | 0.655 | 0.345 | 0.659 | 0.083 |
| 70-80% | 834 | 0.183 | 0.254 | 0.071 | 0.072 | 0.680 | 0.320 | 0.608 | 0.098 |
| 80-90% | 776 | 0.175 | 0.240 | 0.064 | 0.066 | 0.684 | 0.316 | 0.646 | 0.080 |
| 90-100% | 715 | 0.164 | 0.225 | 0.062 | 0.065 | 0.650 | 0.350 | 0.603 | 0.084 |
| unknown | 359 | 0.095 | 0.147 | 0.052 | 0.052 | 0.529 | 0.471 | 0.474 | 0.062 |

Largest gaps between groups (max - min): recall 0.164 (10-20 vs unknown); precision 0.232 (10-20 vs unknown); false_positive_rate 0.069 (0-10% vs unknown); false_negative_rate 0.164 (unknown vs 10-20); pr_auc 0.244 (10-20 vs unknown); calibration_gap 0.035 (70-80% vs 20-30%); ece 0.029 (70-80% vs 20-30%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | assessments_due_to_date | psi | 3.335 | 0.250 | critical |
| feature_drift | late_submission_rate | psi | 0.692 | 0.250 | critical |
| feature_drift | mean_score_to_date | psi | 0.342 | 0.250 | critical |
| feature_drift | last_score | psi | 0.384 | 0.250 | critical |
| feature_drift | course_relative_score | psi | 0.211 | 0.100 | warning |
| feature_drift | quiz_clicks_to_date | psi | 0.525 | 0.250 | critical |
| feature_drift | quiz_clicks_last_14d | psi | 0.158 | 0.100 | warning |
| feature_drift | quiz_clicks_last_30d | psi | 0.257 | 0.250 | critical |
| feature_drift | quiz_trend_14d | psi | 0.146 | 0.100 | warning |
| feature_drift | forum_clicks_to_date | psi | 0.195 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.102 | 0.100 | warning |
| feature_drift | forum_trend_14d | psi | 0.225 | 0.100 | warning |
| feature_drift | submissions_last_30d | psi | 0.490 | 0.250 | critical |
| feature_drift | score_trend_per_30d | psi | 0.541 | 0.250 | critical |
| feature_drift | score_change_from_first | psi | 0.281 | 0.250 | critical |

## Target: engagement — decision point day 90

Definition: no VLE activity at all in the 14 days after the cutoff. Horizon: 14 days.

### Data and class distribution

| Split | Presentations | Registrations | Adverse outcomes | Prevalence |
|---|---|---:|---:|---:|
| train | 2013B, 2013J | 11052 | 2447 | 0.221 |
| validation | 2014B | 5974 | 1753 | 0.293 |
| test | 2014J | 8532 | 1720 | 0.202 |

Rows not assigned to any split: 0.

### Imbalance strategy comparison (validation, uncalibrated)

| Model | Strategy | PR-AUC | ROC-AUC | Brier |
|---|---|---:|---:|---:|
| Logistic Regression | none (selected) | 0.822 | 0.897 | 0.111 |
| Logistic Regression | balanced | 0.821 | 0.897 | 0.134 |
| Random Forest | none (selected) | 0.828 | 0.896 | 0.109 |
| Random Forest | balanced | 0.829 | 0.898 | 0.126 |
| XGBoost | none | 0.813 | 0.889 | 0.114 |
| XGBoost | balanced (selected) | 0.821 | 0.893 | 0.127 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: 'balanced' improved validation PR-AUC by only 0.0008 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- XGBoost: 'balanced' improved validation PR-AUC by more than 0.005 over no re-weighting.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses calibration only where the out-of-time check below showed it helps.

| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.707 [0.684, 0.725] | 0.875 [0.865, 0.883] | 0.101 -> 0.102 | 0.021 -> 0.035 | 0.357 | 0.567 | 0.659 | 0.609 |
| Random Forest | 0.742 [0.720, 0.760] | 0.890 [0.881, 0.899] | 0.094 -> 0.096 | 0.027 -> 0.042 | 0.332 | 0.622 | 0.669 | 0.645 |
| XGBoost | 0.728 [0.708, 0.746] | 0.883 [0.874, 0.891] | 0.121 -> 0.103 | 0.114 -> 0.048 | 0.587 | 0.604 | 0.659 | 0.630 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.834 / 0.414 | 0.615 / 0.610 | 0.499 / 0.742 |
| Random Forest | 0.865 / 0.430 | 0.650 / 0.645 | 0.515 / 0.766 |
| XGBoost | 0.857 / 0.426 | 0.636 / 0.631 | 0.511 / 0.760 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.910 / 0.873 / 0.891 (6812) | 0.567 / 0.659 / 0.609 (1720) | 5945 | 867 | 587 | 1133 |
| Random Forest | 0.915 / 0.897 / 0.906 (6812) | 0.622 / 0.669 / 0.645 (1720) | 6113 | 699 | 569 | 1151 |
| XGBoost | 0.912 / 0.891 / 0.901 (6812) | 0.604 / 0.659 / 0.630 (1720) | 6069 | 743 | 587 | 1133 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.169 / 0.447 / 0.897 | 4914 (0.58), obs 0.05 | 2078 (0.24), obs 0.23 | 1070 (0.13), obs 0.52 | 470 (0.06), obs 0.95 |
| Random Forest | 0.151 / 0.379 / 0.884 | 4728 (0.55), obs 0.04 | 2248 (0.26), obs 0.22 | 1076 (0.13), obs 0.55 | 480 (0.06), obs 0.97 |
| XGBoost | 0.274 / 0.691 / 0.971 | 4979 (0.58), obs 0.05 | 2073 (0.24), obs 0.23 | 1000 (0.12), obs 0.54 | 480 (0.06), obs 0.97 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.8217 | 0.0000 | 1.00 |
| Random Forest | 0.8284 | 0.0004 | 0.78 |
| XGBoost | 0.8213 | 0.0023 | 0.78 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | active_days_to_date, assignment_completion_rate, clicks_to_date, active_days_last_14d, course_relative_score |
| Random Forest | Tree SHAP (probability); 300 trees | assignment_completion_rate, clicks_last_30d, active_days_to_date, content_clicks_last_14d, clicks_last_7d |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | active_days_to_date, assignment_completion_rate, days_since_last_activity, forum_clicks_last_14d, clicks_last_30d |

### Model selection

**Selected: Logistic Regression** (`oulad-v2-20260924T003349Z-eng-lr-d90`).

Validation PR-AUC best = 0.8282 (random_forest). Models within 0.010 of it: logistic_regression, random_forest, xgboost. Selected the most interpretable of these (logistic_regression; validation PR-AUC 0.8217, Brier 0.1104, seed PR-AUC std 0.0000).

### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)

| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |
|---|---|---|---|---|
| Logistic Regression | 2013B / 2013J / 2014B | 0.153 -> 0.140 | 0.107 -> 0.104 | yes |
| Random Forest | 2013B / 2013J / 2014B | 0.116 -> 0.126 | 0.060 -> 0.103 | no |
| XGBoost | 2013B / 2013J / 2014B | 0.136 -> 0.131 | 0.109 -> 0.110 | no |

### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F | 3627 | 0.222 | 0.229 | 0.007 | 0.019 | 0.603 | 0.397 | 0.598 | 0.115 |
| M | 4905 | 0.187 | 0.241 | 0.054 | 0.054 | 0.707 | 0.293 | 0.545 | 0.136 |

Largest gaps between groups (max - min): recall 0.104 (M vs F); precision 0.053 (F vs M); false_positive_rate 0.020 (M vs F); false_negative_rate 0.104 (F vs M); pr_auc 0.025 (M vs F); calibration_gap 0.047 (M vs F); ece 0.035 (M vs F)

**age_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-35 | 5831 | 0.215 | 0.251 | 0.036 | 0.036 | 0.666 | 0.334 | 0.559 | 0.144 |
| 35-55 | 2621 | 0.174 | 0.205 | 0.031 | 0.033 | 0.638 | 0.362 | 0.587 | 0.095 |
| 55<= | 80 | too few rows for reliable metrics | | | | | | | |

Largest gaps between groups (max - min): recall 0.028 (0-35 vs 35-55); precision 0.027 (35-55 vs 0-35); false_positive_rate 0.049 (0-35 vs 35-55); false_negative_rate 0.028 (35-55 vs 0-35); pr_auc 0.002 (35-55 vs 0-35); calibration_gap 0.005 (0-35 vs 35-55); ece 0.003 (0-35 vs 35-55)

**disability**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N | 7771 | 0.195 | 0.231 | 0.036 | 0.037 | 0.661 | 0.339 | 0.564 | 0.124 |
| Y | 761 | 0.265 | 0.281 | 0.016 | 0.040 | 0.644 | 0.356 | 0.583 | 0.166 |

Largest gaps between groups (max - min): recall 0.017 (N vs Y); precision 0.019 (Y vs N); false_positive_rate 0.043 (Y vs N); false_negative_rate 0.017 (Y vs N); pr_auc 0.010 (N vs Y); calibration_gap 0.020 (N vs Y); ece 0.003 (Y vs N)

**imd_band**

| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0-10% | 741 | 0.251 | 0.254 | 0.003 | 0.018 | 0.640 | 0.360 | 0.647 | 0.117 |
| 10-20 | 830 | 0.240 | 0.264 | 0.024 | 0.033 | 0.688 | 0.312 | 0.623 | 0.132 |
| 20-30% | 893 | 0.253 | 0.255 | 0.002 | 0.020 | 0.668 | 0.332 | 0.648 | 0.123 |
| 30-40% | 901 | 0.199 | 0.238 | 0.039 | 0.039 | 0.648 | 0.352 | 0.547 | 0.133 |
| 40-50% | 846 | 0.206 | 0.243 | 0.037 | 0.041 | 0.649 | 0.351 | 0.533 | 0.147 |
| 50-60% | 860 | 0.202 | 0.239 | 0.037 | 0.042 | 0.707 | 0.293 | 0.591 | 0.124 |
| 60-70% | 834 | 0.185 | 0.226 | 0.041 | 0.042 | 0.682 | 0.318 | 0.571 | 0.116 |
| 70-80% | 820 | 0.187 | 0.238 | 0.051 | 0.056 | 0.673 | 0.327 | 0.510 | 0.148 |
| 80-90% | 759 | 0.155 | 0.215 | 0.059 | 0.059 | 0.627 | 0.373 | 0.481 | 0.125 |
| 90-100% | 696 | 0.174 | 0.206 | 0.032 | 0.051 | 0.562 | 0.438 | 0.511 | 0.113 |
| unknown | 352 | 0.102 | 0.172 | 0.069 | 0.071 | 0.667 | 0.333 | 0.414 | 0.108 |

Largest gaps between groups (max - min): recall 0.145 (50-60% vs 90-100%); precision 0.234 (20-30% vs unknown); false_positive_rate 0.041 (70-80% vs unknown); false_negative_rate 0.145 (90-100% vs 50-60%); pr_auc 0.184 (20-30% vs unknown); calibration_gap 0.068 (unknown vs 20-30%); ece 0.053 (unknown vs 0-10%)

### Drift, training period vs test period (selected model)

| Type | Subject | Statistic | Value | Threshold | Severity |
|---|---|---|---:|---:|---|
| feature_drift | clicks_last_7d | psi | 0.114 | 0.100 | warning |
| feature_drift | clicks_last_14d | psi | 0.158 | 0.100 | warning |
| feature_drift | clicks_trend_7d | psi | 0.104 | 0.100 | warning |
| feature_drift | clicks_trend_14d | psi | 0.183 | 0.100 | warning |
| feature_drift | clicks_change_from_baseline | psi | 0.114 | 0.100 | warning |
| feature_drift | days_since_last_activity | psi | 0.102 | 0.100 | warning |
| feature_drift | assessments_due_to_date | psi | 1.892 | 0.250 | critical |
| feature_drift | late_submission_rate | psi | 0.514 | 0.250 | critical |
| feature_drift | mean_submission_delay_days | psi | 0.152 | 0.100 | warning |
| feature_drift | mean_score_to_date | psi | 0.136 | 0.100 | warning |
| feature_drift | last_score | psi | 0.153 | 0.100 | warning |
| feature_drift | course_relative_score | psi | 0.168 | 0.100 | warning |
| feature_drift | active_days_last_14d | psi | 0.156 | 0.100 | warning |
| feature_drift | quiz_clicks_to_date | psi | 0.326 | 0.250 | critical |
| feature_drift | quiz_clicks_last_7d | psi | 0.107 | 0.100 | warning |
| feature_drift | quiz_clicks_last_14d | psi | 0.275 | 0.250 | critical |
| feature_drift | quiz_clicks_last_30d | psi | 0.371 | 0.250 | critical |
| feature_drift | quiz_trend_14d | psi | 0.261 | 0.250 | critical |
| feature_drift | forum_clicks_to_date | psi | 0.199 | 0.100 | warning |
| feature_drift | forum_clicks_last_14d | psi | 0.161 | 0.100 | warning |
| feature_drift | forum_trend_14d | psi | 0.112 | 0.100 | warning |
| feature_drift | content_trend_14d | psi | 0.139 | 0.100 | warning |
| feature_drift | submissions_last_30d | psi | 0.170 | 0.100 | warning |
| missingness_drift | completion_rate_last_30d | missing_rate_change | 0.083 | 0.050 | warning |
| feature_drift | score_trend_per_30d | psi | 0.161 | 0.100 | warning |
| feature_drift | score_change_from_first | psi | 0.174 | 0.100 | warning |
| feature_drift | clicks_last_7d_vs_30d_rate | psi | 0.123 | 0.100 | warning |
| performance_drop | pr_auc | metric_drop | 0.115 | 0.100 | critical |

## Limitations

- Trained and evaluated on benchmark data only; performance on Indian institutions is unknown (RQ5).
- OULAD dates are relative; prediction dates are nominal (presentation start + cutoff).
- Score availability depends on an assumed release lag; results may change with the true lag.
- Validation (2014B) overlaps in calendar time with the end of 2013J; this can make validation slightly optimistic. The test split (2014J) starts after all training/validation presentations.
- The calibrator (when applied) and thresholds are fitted on the same validation split; whether calibration is applied is decided on a separate out-of-time check, not on the test split.
- Subgroup audit attributes are never model inputs; differences are reported, not corrected, and small groups are not reported.
- Drift thresholds are conventional heuristics, not validated limits.
- SHAP values are associations with the model output, not causal effects.
