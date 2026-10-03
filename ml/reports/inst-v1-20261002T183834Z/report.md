# Institutional training — inst-v1-20261002T183834Z

> **Data provenance: SYNTHETIC.** Generated data (sews_services.training.synthetic). These numbers prove that the pipeline runs end to end; they say nothing about real students, and this model can never be approved for production (database rule).

- Dataset `inst-14ce9fd121318edc`; feature set `inst-fs-1.0.0`
- Target `academic`: withdrew from, or received F/Ab in, any course of the term (published results); horizon: end of the term (publication of results)
- Out-of-time split by term: train ['2024-25-odd', '2024-25-even'], validation ['2025-26-odd'], test ['2025-26-even']
- Calibration check: {'train': ['2024-25-odd'], 'calibrate': ['2024-25-even'], 'evaluate': ['2025-26-odd']}
- Availability by event time (docs/ml/institutional-training.md); temporal leakage guard: day 30 passed (4 terms); day 60 passed (4 terms); day 90 passed (4 terms)

## Terms

| Term | Students | Labelled | Used |
|---|---:|---:|---|
| 2024-25-odd | 400 | 400 | yes |
| 2024-25-even | 370 | 370 | yes |
| 2025-26-odd | 351 | 351 | yes |
| 2025-26-even | 332 | 332 | yes |

## Decision point: day 30 of the term

| Split | Terms | Students | Adverse | Prevalence |
|---|---|---:|---:|---:|
| train | 2024-25-even, 2024-25-odd | 770 | 156 | 0.203 |
| validation | 2025-26-odd | 351 | 65 | 0.185 |
| test | 2025-26-even | 332 | 56 | 0.169 |

| Model | Validation PR-AUC | Test PR-AUC [95% CI] | Test ROC-AUC | Test Brier | Test ECE | Calibrated |
|---|---:|---|---:|---:|---:|---|
| logistic_regression | 0.647 | 0.679 [0.552, 0.807] | 0.905 | 0.083 | 0.039 | no |
| random_forest (**selected**) | 0.668 | 0.709 [0.583, 0.810] | 0.914 | 0.083 | 0.028 | no |
| xgboost | 0.593 | 0.645 [0.512, 0.759] | 0.885 | 0.094 | 0.065 | yes |

Selection: Validation PR-AUC best = 0.6681 (random_forest). Models within 0.010 of it: random_forest. Selected the most interpretable of these (random_forest; validation PR-AUC 0.6681, Brier 0.0952, seed PR-AUC std 0.0019).

## Decision point: day 60 of the term

| Split | Terms | Students | Adverse | Prevalence |
|---|---|---:|---:|---:|
| train | 2024-25-even, 2024-25-odd | 770 | 156 | 0.203 |
| validation | 2025-26-odd | 351 | 65 | 0.185 |
| test | 2025-26-even | 332 | 56 | 0.169 |

| Model | Validation PR-AUC | Test PR-AUC [95% CI] | Test ROC-AUC | Test Brier | Test ECE | Calibrated |
|---|---:|---|---:|---:|---:|---|
| logistic_regression | 0.614 | 0.675 [0.551, 0.793] | 0.911 | 0.089 | 0.041 | no |
| random_forest (**selected**) | 0.687 | 0.705 [0.587, 0.806] | 0.919 | 0.082 | 0.041 | no |
| xgboost | 0.622 | 0.654 [0.523, 0.770] | 0.902 | 0.097 | 0.063 | no |

Selection: Validation PR-AUC best = 0.6868 (random_forest). Models within 0.010 of it: random_forest. Selected the most interpretable of these (random_forest; validation PR-AUC 0.6868, Brier 0.0910, seed PR-AUC std 0.0019).

## Decision point: day 90 of the term

| Split | Terms | Students | Adverse | Prevalence |
|---|---|---:|---:|---:|
| train | 2024-25-even, 2024-25-odd | 770 | 156 | 0.203 |
| validation | 2025-26-odd | 351 | 65 | 0.185 |
| test | 2025-26-even | 332 | 56 | 0.169 |

| Model | Validation PR-AUC | Test PR-AUC [95% CI] | Test ROC-AUC | Test Brier | Test ECE | Calibrated |
|---|---:|---|---:|---:|---:|---|
| logistic_regression | 0.720 | 0.702 [0.566, 0.802] | 0.906 | 0.086 | 0.045 | yes |
| random_forest (**selected**) | 0.742 | 0.719 [0.592, 0.814] | 0.909 | 0.082 | 0.037 | no |
| xgboost | 0.723 | 0.659 [0.519, 0.768] | 0.879 | 0.095 | 0.062 | yes |

Selection: Validation PR-AUC best = 0.7423 (random_forest). Models within 0.010 of it: random_forest. Selected the most interpretable of these (random_forest; validation PR-AUC 0.7423, Brier 0.0866, seed PR-AUC std 0.0024).

## Registered (status `development`)

- `inst-v1-20261002T183834Z-acad-rf-d30`
- `inst-v1-20261002T183834Z-acad-rf-d60`
- `inst-v1-20261002T183834Z-acad-rf-d90`

## Limitations

- Training replays history by event time; if live data is recorded late, live features lag (monitoring).
- The schema stores no withdrawal date: a student who withdrew before a decision point is still counted.
- No subgroup audit: the institutional schema holds no audit attributes (docs/ml/fairness.md).
- PR-AUC must be read against prevalence; feature contributions are associations, not causes.
