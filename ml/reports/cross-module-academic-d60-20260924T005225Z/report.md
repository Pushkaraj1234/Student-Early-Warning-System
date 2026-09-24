# Cross-group check — cross-module-academic-d60-20260924T005225Z

> **Cross-MODULE proxy within ONE institution (Open University, UK). This is NOT cross-institution validation and does not show that any model generalises to other institutions or to Indian students.**
> Data provenance: BENCHMARK (oulad-f853d3b6b35de756).

- Target: academic (final_result is Fail or Withdrawn)
- Decision point: day 60; model: logistic_regression (raw probabilities)
- Training presentations: 2013B, 2013J, 2014B; evaluation presentations: 2014J
- Groups evaluated: 7; skipped: 0

Degradation = reference (group seen in training) minus held-out (group unseen) for PR-AUC, ROC-AUC and recall at top 20%; held-out minus reference for Brier and ECE. Positive = worse on the unseen group.

| Group | n | PR-AUC ref -> held-out | ROC-AUC ref -> held-out | Brier ref -> held-out | ECE ref -> held-out | Recall@20% ref -> held-out |
|---|---:|---|---|---|---|---|
| AAA | 340 | 0.556 -> 0.552 | 0.758 -> 0.758 | 0.193 -> 0.209 | 0.172 -> 0.213 | 0.437 -> 0.425 |
| BBB | 1741 | 0.593 -> 0.591 | 0.683 -> 0.681 | 0.327 -> 0.333 | 0.320 -> 0.324 | 0.360 -> 0.367 |
| CCC | 1859 | 0.785 -> 0.740 | 0.800 -> 0.769 | 0.188 -> 0.209 | 0.077 -> 0.083 | 0.380 -> 0.361 |
| DDD | 1407 | 0.804 -> 0.802 | 0.823 -> 0.822 | 0.181 -> 0.183 | 0.092 -> 0.101 | 0.397 -> 0.393 |
| EEE | 995 | 0.769 -> 0.765 | 0.838 -> 0.835 | 0.151 -> 0.217 | 0.114 -> 0.265 | 0.511 -> 0.518 |
| FFF | 1779 | 0.784 -> 0.753 | 0.826 -> 0.793 | 0.159 -> 0.191 | 0.061 -> 0.128 | 0.455 -> 0.435 |
| GGG | 695 | 0.700 -> 0.686 | 0.772 -> 0.764 | 0.174 -> 0.183 | 0.039 -> 0.076 | 0.438 -> 0.434 |

Mean / worst degradation across evaluated groups:

- pr_auc: mean 0.015, worst 0.045, best 0.002
- roc_auc: mean 0.011, worst 0.033, best 0.000
- brier: mean 0.022, worst 0.066, best 0.003
- ece: mean 0.045, worst 0.151, best 0.005
- recall_at_top_20pct: mean 0.006, worst 0.020, best -0.007

Limitations: one institution only; modules differ in size, subject and assessment design; a single time split; no confidence intervals per group. Do not cite these numbers as cross-institution performance.
