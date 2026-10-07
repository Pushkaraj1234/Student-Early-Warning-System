# Pre-registered hypothesis tests — 20261003T095318Z

> **Provenance: BENCHMARK** (OULAD, UK). Hypotheses, tests and decision rules: docs/research/week04-research-design.md (fixed before this run). Holm correction across all tests, alpha = 0.05; 2000 cluster-bootstrap resamples (students), seed 20261003.

Sanity check: the saved V2 models reproduce the published test PR-AUC exactly (lr_d30 0.6426, xgb_d30 0.6493, lr_d60 0.6903, xgb_d60 0.7044, lr_d90 0.7690, xgb_d90 0.7601).

| ID | Hypothesis | Status | Effect | 95% interval | p | Holm p | Supported | Note |
|---|---|---|---:|---|---:|---:|---|---|
| H1a | ROC-AUC higher at day 60 than at day 30 (same students) | confirmatory (estimate seen) | 0.0661 (roc_auc) | [0.0568, 0.0761] | 5.00e-04 | 4.00e-03 | yes |  |
| H1b | ROC-AUC higher at day 90 than at day 60 (same students) | confirmatory (estimate seen) | 0.0479 (roc_auc) | [0.0413, 0.0544] | 5.00e-04 | 4.00e-03 | yes |  |
| H2a | removing the engagement family lowers PR-AUC at day 30 | pre-registered | 0.0194 (pr_auc) | [0.0115, 0.0272] | 5.00e-04 | 4.00e-03 | yes |  |
| H2b | removing the assignment family lowers PR-AUC at day 30 | pre-registered | 0.0358 (pr_auc) | [0.0250, 0.0468] | 5.00e-04 | 4.00e-03 | yes |  |
| H2c | removing the academic family lowers PR-AUC at day 90 | pre-registered | 0.0431 (pr_auc) | [0.0346, 0.0517] | 5.00e-04 | 4.00e-03 | yes |  |
| H3 | XGBoost and logistic regression differ in PR-AUC at day 60 | confirmatory (estimate seen) | 0.0141 (pr_auc) | [0.0078, 0.0201] | 1.00e-03 | 4.00e-03 | yes |  |
| H4 | ECE is higher on an unseen module than on the same module seen in training | confirmatory (estimate seen) | 0.0375 (ece_degradation_median) | [0.0049, 0.1509] | 7.81e-03 | 7.81e-03 | yes |  |
| H5 | recall at day 60 differs between female and male students | confirmatory (estimate seen) | -0.0666 (recall_gap_female_minus_male) | [-0.0956, -0.0402] | 1.00e-03 | 4.00e-03 | yes |  |
| H6a | active_days_to_date at day 30 is negatively associated with the adverse outcome | pre-registered | -0.2907 (spearman_rho) | [-0.3080, -0.2731] | 5.26e-228 | 4.74e-227 | yes |  |
| H6b | assignment_completion_rate at day 30 is negatively associated with the adverse outcome | pre-registered | -0.3362 (spearman_rho) | [-0.3517, -0.3203] | 1.31e-260 | 1.31e-259 | yes |  |

## Details

### H1a — one-sided paired DeLong and cluster bootstrap; larger p (XGBoost)

```json
{
  "n_registrations": 8528,
  "n_students": 8237,
  "roc_auc_day30": 0.7037404825727028,
  "roc_auc_day60": 0.7698539666765946,
  "delong_z": 13.286273667823092,
  "p_delong": 1.3904297970749884e-40,
  "p_bootstrap": 0.0004997501249375312,
  "robustness_logistic_regression_delta": 0.041756757659762944
}
```

### H1b — one-sided paired DeLong and cluster bootstrap; larger p (XGBoost)

```json
{
  "n_registrations": 8528,
  "n_students": 8237,
  "roc_auc_day60": 0.7698539666765946,
  "roc_auc_day90": 0.8177441907418438,
  "delong_z": 14.266168464636115,
  "p_delong": 1.7779286840920526e-46,
  "p_bootstrap": 0.0004997501249375312,
  "robustness_logistic_regression_delta": 0.08774328744539661
}
```

### H2a — one-sided paired cluster bootstrap (XGBoost, retrained without the family)

```json
{
  "family_size": 17,
  "pr_auc_full": 0.649263736181283,
  "pr_auc_without_family": 0.6298745920846025,
  "n_test": 9198,
  "prevalence": 0.40682757121113283,
  "robustness_logistic_regression_delta": 0.02437850832127153
}
```

### H2b — one-sided paired cluster bootstrap (XGBoost, retrained without the family)

```json
{
  "family_size": 6,
  "pr_auc_full": 0.649263736181283,
  "pr_auc_without_family": 0.6134934513205683,
  "n_test": 9198,
  "prevalence": 0.40682757121113283,
  "robustness_logistic_regression_delta": 0.032956055795685724
}
```

### H2c — one-sided paired cluster bootstrap (XGBoost, retrained without the family)

```json
{
  "family_size": 5,
  "pr_auc_full": 0.7601141475251255,
  "pr_auc_without_family": 0.7170341334069162,
  "n_test": 8532,
  "prevalence": 0.36040787623066106,
  "robustness_logistic_regression_delta": 0.05295927879910867
}
```

### H3 — two-sided paired cluster bootstrap

```json
{
  "pr_auc_xgboost": 0.7043590346521823,
  "pr_auc_logistic_regression": 0.6903045317639801,
  "roc_auc_delta": 0.03414644565051406,
  "roc_auc_delong_p_two_sided": 3.0221593791593354e-26
}
```

### H4 — one-sided exact Wilcoxon signed-rank over modules (interval = min..max across modules, not a CI)

```json
{
  "modules": 7,
  "per_module": {
    "AAA": 0.04166560209806772,
    "BBB": 0.004891860341986132,
    "CCC": 0.006434316959228428,
    "DDD": 0.008736943683954196,
    "EEE": 0.1509067978057142,
    "FFF": 0.06715880003145426,
    "GGG": 0.037505318495207336
  },
  "source": "cross-module-academic-d60-20260924T005225Z"
}
```

### H5 — two-sided cluster bootstrap (active model, XGBoost day 60, at its decision threshold)

```json
{
  "threshold": 0.30575780561330135,
  "recall_female": 0.763001485884101,
  "recall_male": 0.8296075509190264,
  "positives_female": 1346,
  "positives_male": 2013
}
```

### H6a — one-sided Spearman correlation (training presentations)

```json
{
  "n": 11759,
  "missing_excluded": 0,
  "note": "p assumes independent rows; the interval is a student-level cluster bootstrap"
}
```

### H6b — one-sided Spearman correlation (training presentations)

```json
{
  "n": 9908,
  "missing_excluded": 1851,
  "note": "p assumes independent rows; the interval is a student-level cluster bootstrap"
}
```
