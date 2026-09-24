# SEWS baseline evaluation — oulad-baseline-v1-20260923T222002Z

> **Data provenance: BENCHMARK.** Open University Learning Analytics Dataset (United Kingdom, 2013-2014; CC BY 4.0; UCI id 349). NOT Indian data.
> These results describe method behaviour on this benchmark dataset. They are **not** evidence about Indian students and must not be presented as such. No model here is approved to score real students: that requires validation on institutional data (see docs/ml/ml-strategy.md §5).

- Dataset version: `oulad-f853d3b6b35de756`
- Feature version: `oulad-fs-1.0.0` (21 features)
- Target: 1 = final_result in {Fail, Withdrawn}; 0 = {Pass, Distinction} (OULAD)
- Score release lag assumption: 14 days (OULAD has no grade-release dates)
- Split (out-of-time): {'train': ['2013B', '2013J'], 'validation': ['2014B'], 'test': ['2014J']}
- Created: 2026-09-23T22:20:02+00:00; git commit: none (no commits yet)
- Libraries: {'python': '3.13.2', 'numpy': '2.5.3', 'pandas': '3.0.6', 'scikit-learn': '1.9.1', 'xgboost': '3.4.1', 'shap': '0.52.0'}
- Active model (primary decision point): `oulad-baseline-v1-20260923T222002Z-xgb-d60`

Attendance features are absent because OULAD contains no attendance data.

## Decision point: day 30 of the presentation

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
| Logistic Regression | none (selected) | 0.744 | 0.736 | 0.206 |
| Logistic Regression | balanced | 0.744 | 0.736 | 0.206 |
| Random Forest | none (selected) | 0.747 | 0.739 | 0.205 |
| Random Forest | balanced | 0.746 | 0.739 | 0.206 |
| XGBoost | none (selected) | 0.744 | 0.735 | 0.206 |
| XGBoost | balanced | 0.745 | 0.736 | 0.206 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: no re-weighting had the best validation PR-AUC.
- XGBoost: 'balanced' improved validation PR-AUC by only 0.0006 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time, calibrated probabilities)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

| Model | PR-AUC | ROC-AUC | Brier (uncal -> cal) | ECE (uncal -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.656 [0.641, 0.672] | 0.712 [0.702, 0.722] | 0.211 -> 0.214 [0.211, 0.218] | 0.060 -> 0.091 | 0.330 | 0.473 | 0.894 | 0.619 |
| Random Forest | 0.668 [0.652, 0.682] | 0.726 [0.716, 0.735] | 0.205 -> 0.208 [0.205, 0.211] | 0.048 -> 0.068 | 0.307 | 0.489 | 0.878 | 0.628 |
| XGBoost | 0.649 [0.634, 0.666] | 0.718 [0.708, 0.728] | 0.211 -> 0.214 [0.211, 0.218] | 0.059 -> 0.078 | 0.307 | 0.486 | 0.878 | 0.626 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.825 / 0.203 | 0.692 / 0.340 | 0.625 / 0.461 |
| Random Forest | 0.834 / 0.205 | 0.716 / 0.352 | 0.649 / 0.478 |
| XGBoost | 0.778 / 0.191 | 0.674 / 0.331 | 0.630 / 0.465 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.814 / 0.317 / 0.457 (5456) | 0.473 / 0.894 / 0.619 (3742) | 1731 | 3725 | 396 | 3346 |
| Random Forest | 0.816 / 0.371 / 0.510 (5456) | 0.489 / 0.878 / 0.628 (3742) | 2026 | 3430 | 457 | 3285 |
| XGBoost | 0.814 / 0.364 / 0.503 (5456) | 0.486 / 0.878 / 0.626 (3742) | 1985 | 3471 | 455 | 3287 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.452 / 0.615 / 0.839 | 4338 (0.47), obs 0.26 | 2618 (0.28), obs 0.44 | 1600 (0.17), obs 0.57 | 642 (0.07), obs 0.89 |
| Random Forest | 0.457 / 0.640 / 0.804 | 4560 (0.50), obs 0.26 | 2564 (0.28), obs 0.43 | 1383 (0.15), obs 0.61 | 691 (0.08), obs 0.88 |
| XGBoost | 0.449 / 0.645 / 0.811 | 4434 (0.48), obs 0.25 | 2264 (0.25), obs 0.45 | 1728 (0.19), obs 0.56 | 772 (0.08), obs 0.82 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.7444 | 0.0000 | 1.00 |
| Random Forest | 0.7476 | 0.0002 | 1.00 |
| XGBoost | 0.7448 | 0.0008 | 0.80 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | course_relative_score, mean_score_to_date, assignment_completion_rate, active_days_to_date, late_submission_rate |
| Random Forest | Tree SHAP (probability); 300 trees | mean_submission_delay_days, assignment_completion_rate, active_days_to_date, days_since_last_activity, late_submission_rate |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | assignment_completion_rate, mean_submission_delay_days, days_since_last_activity, active_days_to_date, course_relative_score |

### Model selection

**Selected: Logistic Regression** (`oulad-baseline-v1-20260923T222002Z-lr-d30`).

Validation PR-AUC best = 0.7474 (random_forest). Models within 0.010 of it: logistic_regression, random_forest, xgboost. Selected the most interpretable of these (logistic_regression; validation PR-AUC 0.7444, Brier 0.2050, seed PR-AUC std 0.0000).

### Subgroup audit of the selected model (test; audit attributes are not model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| F | 3869 | 0.384 | 0.460 | 0.869 | 0.438 | 0.695 |
| M | 5329 | 0.423 | 0.482 | 0.910 | 0.498 | 0.674 |

**age_band**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| 0-35 | 6303 | 0.421 | 0.484 | 0.907 | 0.483 | 0.706 |
| 35-55 | 2808 | 0.376 | 0.450 | 0.863 | 0.449 | 0.638 |
| 55<= | 87 | too few rows for reliable metrics | | | | |

**disability**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| N | 8346 | 0.395 | 0.470 | 0.895 | 0.462 | 0.679 |
| Y | 852 | 0.526 | 0.499 | 0.891 | 0.575 | 0.730 |

**imd_band**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| 0-10% | 820 | 0.493 | 0.483 | 0.894 | 0.555 | 0.695 |
| 10-20 | 910 | 0.475 | 0.475 | 0.900 | 0.551 | 0.663 |
| 20-30% | 970 | 0.458 | 0.468 | 0.892 | 0.532 | 0.662 |
| 30-40% | 979 | 0.416 | 0.477 | 0.902 | 0.474 | 0.713 |
| 40-50% | 921 | 0.407 | 0.478 | 0.875 | 0.456 | 0.716 |
| 50-60% | 920 | 0.403 | 0.472 | 0.868 | 0.472 | 0.656 |
| 60-70% | 886 | 0.376 | 0.458 | 0.856 | 0.434 | 0.673 |
| 70-80% | 870 | 0.387 | 0.476 | 0.958 | 0.487 | 0.638 |
| 80-90% | 809 | 0.354 | 0.475 | 0.906 | 0.407 | 0.723 |
| 90-100% | 747 | 0.332 | 0.470 | 0.907 | 0.397 | 0.685 |
| unknown | 366 | 0.287 | 0.461 | 0.867 | 0.336 | 0.690 |

## Decision point: day 60 of the presentation

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
| Logistic Regression | none (selected) | 0.809 | 0.803 | 0.175 |
| Logistic Regression | balanced | 0.809 | 0.803 | 0.176 |
| Random Forest | none (selected) | 0.822 | 0.818 | 0.169 |
| Random Forest | balanced | 0.822 | 0.819 | 0.171 |
| XGBoost | none (selected) | 0.825 | 0.823 | 0.167 |
| XGBoost | balanced | 0.825 | 0.824 | 0.169 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: 'balanced' improved validation PR-AUC by only 0.0001 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- XGBoost: no re-weighting had the best validation PR-AUC.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time, calibrated probabilities)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

| Model | PR-AUC | ROC-AUC | Brier (uncal -> cal) | ECE (uncal -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.707 [0.693, 0.722] | 0.756 [0.746, 0.767] | 0.198 -> 0.197 [0.192, 0.201] | 0.082 -> 0.095 | 0.378 | 0.570 | 0.725 | 0.638 |
| Random Forest | 0.716 [0.702, 0.731] | 0.783 [0.774, 0.793] | 0.185 -> 0.190 [0.185, 0.195] | 0.060 -> 0.073 | 0.340 | 0.567 | 0.778 | 0.656 |
| XGBoost | 0.711 [0.696, 0.726] | 0.781 [0.771, 0.791] | 0.195 -> 0.196 [0.191, 0.201] | 0.079 -> 0.086 | 0.366 | 0.570 | 0.764 | 0.653 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.924 / 0.243 | 0.752 / 0.395 | 0.659 / 0.519 |
| Random Forest | 0.908 / 0.238 | 0.726 / 0.381 | 0.677 / 0.533 |
| XGBoost | 0.897 / 0.235 | 0.725 / 0.381 | 0.675 / 0.532 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.797 / 0.663 / 0.724 (5457) | 0.570 / 0.725 / 0.638 (3359) | 3618 | 1839 | 924 | 2435 |
| Random Forest | 0.823 / 0.633 / 0.716 (5457) | 0.567 / 0.778 / 0.656 (3359) | 3457 | 2000 | 745 | 2614 |
| XGBoost | 0.816 / 0.644 / 0.720 (5457) | 0.570 / 0.764 / 0.653 (3359) | 3517 | 1940 | 792 | 2567 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.377 / 0.646 / 0.928 | 4533 (0.51), obs 0.20 | 1896 (0.22), obs 0.43 | 1664 (0.19), obs 0.56 | 723 (0.08), obs 0.95 |
| Random Forest | 0.370 / 0.726 / 0.907 | 4442 (0.50), obs 0.18 | 2121 (0.24), obs 0.46 | 1630 (0.18), obs 0.59 | 623 (0.07), obs 0.95 |
| XGBoost | 0.359 / 0.752 / 0.904 | 4272 (0.48), obs 0.18 | 2150 (0.24), obs 0.43 | 1721 (0.20), obs 0.59 | 673 (0.08), obs 0.95 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.8093 | 0.0000 | 1.00 |
| Random Forest | 0.8224 | 0.0002 | 1.00 |
| XGBoost | 0.8247 | 0.0005 | 1.00 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | course_relative_score, mean_score_to_date, assignment_completion_rate, clicks_last_30d, late_submission_rate |
| Random Forest | Tree SHAP (probability); 300 trees | assignment_completion_rate, course_relative_score, mean_score_to_date, clicks_last_7d, mean_submission_delay_days |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | course_relative_score, assignment_completion_rate, mean_submission_delay_days, clicks_last_7d, late_submission_rate |

### Model selection

**Selected: XGBoost** (`oulad-baseline-v1-20260923T222002Z-xgb-d60`).

Validation PR-AUC best = 0.8247 (xgboost). Models within 0.010 of it: random_forest, xgboost. Selected the most interpretable of these (xgboost; validation PR-AUC 0.8247, Brier 0.1682, seed PR-AUC std 0.0005).

### Subgroup audit of the selected model (test; audit attributes are not model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| F | 3730 | 0.361 | 0.472 | 0.723 | 0.516 | 0.383 |
| M | 5086 | 0.396 | 0.460 | 0.792 | 0.608 | 0.334 |

**age_band**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| 0-35 | 6029 | 0.395 | 0.479 | 0.783 | 0.577 | 0.375 |
| 35-55 | 2706 | 0.352 | 0.437 | 0.718 | 0.553 | 0.315 |
| 55<= | 81 | too few rows for reliable metrics | | | | |

**disability**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| N | 8013 | 0.369 | 0.461 | 0.760 | 0.558 | 0.353 |
| Y | 803 | 0.497 | 0.513 | 0.792 | 0.667 | 0.391 |

**imd_band**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| 0-10% | 779 | 0.466 | 0.491 | 0.747 | 0.636 | 0.373 |
| 10-20 | 866 | 0.448 | 0.495 | 0.781 | 0.642 | 0.354 |
| 20-30% | 935 | 0.437 | 0.478 | 0.795 | 0.666 | 0.310 |
| 30-40% | 939 | 0.390 | 0.478 | 0.760 | 0.567 | 0.370 |
| 40-50% | 875 | 0.376 | 0.474 | 0.766 | 0.542 | 0.390 |
| 50-60% | 885 | 0.380 | 0.471 | 0.756 | 0.543 | 0.390 |
| 60-70% | 853 | 0.352 | 0.443 | 0.743 | 0.544 | 0.338 |
| 70-80% | 834 | 0.361 | 0.451 | 0.754 | 0.558 | 0.338 |
| 80-90% | 776 | 0.326 | 0.458 | 0.767 | 0.483 | 0.398 |
| 90-100% | 715 | 0.302 | 0.436 | 0.796 | 0.513 | 0.327 |
| unknown | 359 | 0.273 | 0.394 | 0.694 | 0.472 | 0.291 |

## Decision point: day 90 of the presentation

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
| Logistic Regression | none (selected) | 0.861 | 0.864 | 0.143 |
| Logistic Regression | balanced | 0.860 | 0.864 | 0.145 |
| Random Forest | none (selected) | 0.864 | 0.865 | 0.143 |
| Random Forest | balanced | 0.864 | 0.865 | 0.147 |
| XGBoost | none (selected) | 0.864 | 0.866 | 0.142 |
| XGBoost | balanced | 0.865 | 0.867 | 0.144 |

- Logistic Regression: no re-weighting had the best validation PR-AUC.
- Random Forest: 'balanced' improved validation PR-AUC by only 0.0002 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.
- XGBoost: 'balanced' improved validation PR-AUC by only 0.0010 (<= 0.005); unweighted training is kept because re-weighting distorts probability estimates.

SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts probability calibration; class re-weighting was compared instead.

### Held-out test performance (out-of-time, calibrated probabilities)

95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the F1-optimal threshold chosen on validation.

| Model | PR-AUC | ROC-AUC | Brier (uncal -> cal) | ECE (uncal -> cal) | Threshold | Precision | Recall | F1 |
|---|---|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.766 [0.753, 0.780] | 0.820 [0.811, 0.829] | 0.159 -> 0.161 [0.156, 0.165] | 0.033 -> 0.045 | 0.370 | 0.602 | 0.740 | 0.664 |
| Random Forest | 0.775 [0.763, 0.788] | 0.825 [0.816, 0.835] | 0.159 -> 0.164 [0.159, 0.169] | 0.058 -> 0.066 | 0.419 | 0.615 | 0.728 | 0.667 |
| XGBoost | 0.764 [0.752, 0.777] | 0.819 [0.810, 0.828] | 0.167 -> 0.173 [0.167, 0.177] | 0.058 -> 0.077 | 0.381 | 0.602 | 0.733 | 0.661 |

#### Capacity view (test): flag the top k% highest-risk registrations

| Model | top 10% precision / recall | top 20% precision / recall | top 30% precision / recall |
|---|---|---|---|
| Logistic Regression | 0.963 / 0.267 | 0.825 / 0.458 | 0.717 / 0.597 |
| Random Forest | 0.961 / 0.267 | 0.843 / 0.468 | 0.709 / 0.590 |
| XGBoost | 0.971 / 0.270 | 0.804 / 0.446 | 0.701 / 0.583 |

#### Class-specific performance and confusion matrices (test, at threshold)

| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |
|---|---|---|---:|---:|---:|---:|
| Logistic Regression | 0.832 / 0.725 / 0.775 (5457) | 0.602 / 0.740 / 0.664 (3075) | 3956 | 1501 | 801 | 2274 |
| Random Forest | 0.829 / 0.743 / 0.784 (5457) | 0.615 / 0.728 / 0.667 (3075) | 4056 | 1401 | 837 | 2238 |
| XGBoost | 0.829 / 0.727 / 0.775 (5457) | 0.602 / 0.733 / 0.661 (3075) | 3967 | 1490 | 820 | 2255 |

#### Risk levels on test (thresholds = validation quantiles of calibrated probability)

| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |
|---|---|---|---|---|---|
| Logistic Regression | 0.323 / 0.725 / 0.970 | 4384 (0.51), obs 0.16 | 2480 (0.29), obs 0.40 | 1179 (0.14), obs 0.77 | 489 (0.06), obs 0.99 |
| Random Forest | 0.318 / 0.784 / 0.938 | 4338 (0.51), obs 0.15 | 2586 (0.30), obs 0.40 | 1091 (0.13), obs 0.80 | 517 (0.06), obs 0.99 |
| XGBoost | 0.301 / 0.810 / 0.931 | 4307 (0.50), obs 0.15 | 2393 (0.28), obs 0.41 | 1274 (0.15), obs 0.69 | 558 (0.07), obs 0.99 |

### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)

| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |
|---|---:|---:|---:|
| Logistic Regression | 0.8607 | 0.0000 | 1.00 |
| Random Forest | 0.8639 | 0.0003 | 0.77 |
| XGBoost | 0.8649 | 0.0006 | 0.80 |

### Interpretability

| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |
|---|---|---|
| Logistic Regression | Linear SHAP (log-odds); coefficients are directly inspectable | assignment_completion_rate, course_relative_score, clicks_last_30d, days_since_last_activity, clicks_to_date |
| Random Forest | Tree SHAP (probability); 300 trees | assignment_completion_rate, course_relative_score, mean_score_to_date, clicks_last_30d, last_score |
| XGBoost | Tree SHAP (log-odds); 400 boosted trees | assignment_completion_rate, course_relative_score, days_since_last_activity, clicks_last_30d, mean_score_to_date |

### Model selection

**Selected: Logistic Regression** (`oulad-baseline-v1-20260923T222002Z-lr-d90`).

Validation PR-AUC best = 0.8643 (xgboost). Models within 0.010 of it: logistic_regression, random_forest, xgboost. Selected the most interpretable of these (logistic_regression; validation PR-AUC 0.8607, Brier 0.1426, seed PR-AUC std 0.0000).

### Subgroup audit of the selected model (test; audit attributes are not model inputs)

**gender**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| F | 3627 | 0.343 | 0.407 | 0.716 | 0.524 | 0.339 |
| M | 4905 | 0.373 | 0.402 | 0.755 | 0.667 | 0.225 |

**age_band**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| 0-35 | 5831 | 0.375 | 0.418 | 0.760 | 0.619 | 0.280 |
| 35-55 | 2621 | 0.331 | 0.376 | 0.691 | 0.561 | 0.267 |
| 55<= | 80 | too few rows for reliable metrics | | | | |

**disability**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| N | 7771 | 0.350 | 0.397 | 0.733 | 0.592 | 0.272 |
| Y | 761 | 0.469 | 0.479 | 0.793 | 0.687 | 0.319 |

**imd_band**

| Group | n | Prevalence | Mean predicted | Recall | Precision | FPR |
|---|---:|---:|---:|---:|---:|---:|
| 0-10% | 741 | 0.439 | 0.439 | 0.760 | 0.671 | 0.291 |
| 10-20 | 830 | 0.424 | 0.444 | 0.764 | 0.651 | 0.301 |
| 20-30% | 893 | 0.411 | 0.429 | 0.771 | 0.680 | 0.253 |
| 30-40% | 901 | 0.364 | 0.414 | 0.756 | 0.592 | 0.298 |
| 40-50% | 846 | 0.355 | 0.412 | 0.750 | 0.571 | 0.310 |
| 50-60% | 860 | 0.362 | 0.399 | 0.727 | 0.598 | 0.277 |
| 60-70% | 834 | 0.337 | 0.386 | 0.690 | 0.559 | 0.277 |
| 70-80% | 820 | 0.350 | 0.399 | 0.728 | 0.602 | 0.259 |
| 80-90% | 759 | 0.311 | 0.382 | 0.703 | 0.539 | 0.272 |
| 90-100% | 696 | 0.283 | 0.365 | 0.751 | 0.546 | 0.246 |
| unknown | 352 | 0.259 | 0.323 | 0.648 | 0.518 | 0.211 |

## Limitations

- Trained and evaluated on benchmark data only; performance on Indian institutions is unknown (RQ5).
- OULAD dates are relative; prediction dates are nominal (presentation start + cutoff).
- Score availability depends on an assumed release lag; results may change with the true lag.
- Validation (2014B) overlaps in calendar time with the end of 2013J; this can make validation slightly optimistic. The test split (2014J) starts after all training/validation presentations.
- The calibrator and thresholds are fitted on the same validation split.
- SHAP values are associations with the model output, not causal effects.
