# External benchmark datasets — external-v1-20261007T184644Z

> **Provenance: BENCHMARK (Portugal, CC BY 4.0).** Not Indian data; models are never approved for real
> students. Plan and pre-specified comparisons: `docs/research/external-datasets-plan.md`.

## A. University dropout (UCI 697): 4,424 students, dropout rate 0.321

Split {'train': 3096, 'validation': 664, 'test': 664}: stratified random split; no enrolment year exists, so no out-of-time split is possible.

| Point | Model | Validation PR-AUC | Test PR-AUC [95% CI] | Test ROC-AUC | Test Brier |
|---|---|---:|---:|---:|---:|
| D0 | xgboost | 0.542 | 0.555 [0.483, 0.627] | 0.735 | 0.187 |
| D0 | l1_logistic | 0.568 | 0.561 [0.488, 0.630] | 0.724 | 0.208 |
| D0 | random_forest | 0.490 | 0.516 [0.449, 0.584] | 0.704 | 0.198 |
| D0 | prevalence_baseline | 0.321 | 0.321 [0.286, 0.355] | 0.500 | 0.218 |
| D1 | xgboost | 0.848 | 0.797 [0.745, 0.844] | 0.873 | 0.129 |
| D1 | l1_logistic | 0.822 | 0.785 [0.729, 0.835] | 0.874 | 0.131 |
| D1 | random_forest | 0.808 | 0.767 [0.708, 0.823] | 0.856 | 0.147 |
| D1 | prevalence_baseline | 0.315 | 0.318 [0.282, 0.354] | 0.500 | 0.217 |
| D2 | xgboost | 0.882 | 0.836 [0.791, 0.878] | 0.898 | 0.116 |
| D2 | l1_logistic | 0.874 | 0.830 [0.783, 0.875] | 0.894 | 0.115 |
| D2 | random_forest | 0.867 | 0.811 [0.756, 0.860] | 0.889 | 0.121 |
| D2 | prevalence_baseline | 0.315 | 0.318 [0.282, 0.354] | 0.500 | 0.217 |

| ID | Comparison | Effect [95% CI] | p | Holm p | Result |
|---|---|---|---:|---:|---|
| E1 | xgboost at D1 minus xgboost at D0, test PR-AUC on 635 students (one-sided) | 0.2412 [0.1807, 0.2977] | < 0.001 | 0.001 | supported |
| E2 | xgboost at D2 minus xgboost at D1, test PR-AUC on 635 students (one-sided) | 0.0397 [0.0143, 0.0666] | 0.002 | 0.004 | supported |
| E3 | l1_logistic at D1 minus xgboost at D1, test PR-AUC on 635 students (two-sided) | -0.0120 [-0.0317, 0.0091] | 0.252 | 0.252 | not supported |

- D0: selected l1_logistic; at the F1 threshold recall 0.746, precision 0.417; top SHAP (XGBoost): course_code_9500, application_mode_code_1, application_mode_code_39, prev_qual_grade, gdp.
- D1: selected xgboost; at the F1 threshold recall 0.634, precision 0.757; top SHAP (XGBoost): sem1_approval_rate, sem1_failed, sem1_approved, sem1_grade, sem1_credited.
- D2: selected xgboost; at the F1 threshold recall 0.723, precision 0.730; top SHAP (XGBoost): sem2_failed, sem2_approval_rate, sem1_approval_rate, sem2_approved, sem2_grade.

**Financial variables (sensitivity; recording time undocumented; a gain may be leakage (e.g. fees recorded after students left)):** D0: 0.555 -> 0.733 (difference CI [0.124, 0.234]); D1: 0.797 -> 0.850 (difference CI [0.028, 0.083])

**Leave-one-cohort-out at D1 (exploratory):** xgboost mean 0.818 (range 0.769 to 0.866); l1_logistic mean 0.810 (range 0.757 to 0.868)

## B. uci-320-student-performance-portuguese: 649 students, fail rate 0.154 (5 x 5 repeated stratified cross-validation (exploratory))

| Point | Model | PR-AUC mean (range) | ROC-AUC mean | Brier mean |
|---|---|---:|---:|---:|
| P0 | l1_logistic | 0.473 (0.464 to 0.484) | 0.821 | 0.104 |
| P0 | random_forest | 0.455 (0.439 to 0.471) | 0.829 | 0.102 |
| P0 | xgboost | 0.441 (0.421 to 0.462) | 0.823 | 0.103 |
| P0 | prevalence_baseline | 0.154 (0.154 to 0.154) | 0.499 | 0.130 |
| P1 | l1_logistic | 0.725 (0.708 to 0.738) | 0.943 | 0.067 |
| P1 | random_forest | 0.690 (0.660 to 0.723) | 0.939 | 0.068 |
| P1 | xgboost | 0.689 (0.671 to 0.710) | 0.939 | 0.069 |
| P1 | prevalence_baseline | 0.154 (0.154 to 0.154) | 0.499 | 0.130 |
| P2 | l1_logistic | 0.856 (0.825 to 0.870) | 0.964 | 0.051 |
| P2 | random_forest | 0.867 (0.862 to 0.878) | 0.966 | 0.049 |
| P2 | xgboost | 0.869 (0.865 to 0.874) | 0.966 | 0.051 |
| P2 | prevalence_baseline | 0.154 (0.154 to 0.154) | 0.499 | 0.130 |
| P2_with_absences | l1_logistic | 0.853 (0.823 to 0.870) | 0.963 | 0.052 |
| P2_with_absences | random_forest | 0.869 (0.864 to 0.878) | 0.966 | 0.049 |
| P2_with_absences | xgboost | 0.871 (0.866 to 0.874) | 0.965 | 0.051 |
| P2_with_absences | prevalence_baseline | 0.154 (0.154 to 0.154) | 0.499 | 0.130 |

## B. uci-320-student-performance-math: 395 students, fail rate 0.329 (5 x 5 repeated stratified cross-validation (exploratory))

| Point | Model | PR-AUC mean (range) | ROC-AUC mean | Brier mean |
|---|---|---:|---:|---:|
| P0 | l1_logistic | 0.539 (0.533 to 0.542) | 0.672 | 0.196 |
| P0 | random_forest | 0.570 (0.564 to 0.574) | 0.685 | 0.193 |
| P0 | xgboost | 0.559 (0.550 to 0.583) | 0.690 | 0.194 |
| P0 | prevalence_baseline | 0.329 (0.329 to 0.329) | 0.500 | 0.221 |
| P1 | l1_logistic | 0.822 (0.800 to 0.836) | 0.915 | 0.112 |
| P1 | random_forest | 0.816 (0.797 to 0.830) | 0.913 | 0.112 |
| P1 | xgboost | 0.812 (0.790 to 0.821) | 0.915 | 0.111 |
| P1 | prevalence_baseline | 0.329 (0.329 to 0.329) | 0.500 | 0.221 |
| P2 | l1_logistic | 0.932 (0.924 to 0.939) | 0.967 | 0.070 |
| P2 | random_forest | 0.944 (0.939 to 0.948) | 0.972 | 0.065 |
| P2 | xgboost | 0.930 (0.924 to 0.938) | 0.969 | 0.064 |
| P2 | prevalence_baseline | 0.329 (0.329 to 0.329) | 0.500 | 0.221 |
| P2_with_absences | l1_logistic | 0.939 (0.928 to 0.947) | 0.969 | 0.067 |
| P2_with_absences | random_forest | 0.946 (0.943 to 0.950) | 0.972 | 0.064 |
| P2_with_absences | xgboost | 0.937 (0.933 to 0.942) | 0.971 | 0.063 |
| P2_with_absences | prevalence_baseline | 0.329 (0.329 to 0.329) | 0.500 | 0.221 |
