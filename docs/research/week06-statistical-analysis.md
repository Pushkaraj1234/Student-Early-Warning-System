# Week 6 — Statistical analysis and validation

Status 2026-10-03. The hypotheses, tests and decision rules were fixed in [week 4](week04-research-design.md) (with
clarifications logged there **before** this run). One confirmatory run:
[`ml/reports/hypotheses-20261003T095318Z/`](../../ml/reports/hypotheses-20261003T095318Z/report.md) (`report.md`,
`results.json`). Reproduce: `ml/.venv/Scripts/python -m ml.analysis.hypotheses --config ml/configs/oulad_v2.json`
(code `ml/analysis/hypotheses.py`; the statistics are unit-tested against known references in
`ml/tests/test_hypotheses_stats.py`).

> **Provenance: BENCHMARK** (OULAD, UK, 2013–14). These results describe the method on this dataset. They are not
> evidence about Indian students.

**Sanity check before testing:** the saved V2 models reproduce the published test PR-AUC exactly (all six logistic
regression and XGBoost models at days 30, 60, 90), and the retrained full models in H2 reproduce them too — the tests
analyse the same models the results document reports.

## 1. Results (Holm-corrected across all 10 tests, α = 0.05; 2,000 student-level bootstrap resamples)

| ID | Hypothesis | Status | Effect [95% interval] | Holm p | Result |
|---|---|---|---|---:|---|
| H1a | ROC-AUC higher at day 60 than day 30 (same 8,528 registrations) | confirmatory | gain **0.066** [0.057, 0.076] (0.704 → 0.770) | 0.004 | supported |
| H1b | ROC-AUC higher at day 90 than day 60 (same registrations) | confirmatory | gain **0.048** [0.041, 0.054] (0.770 → 0.818) | 0.004 | supported |
| H2a | Removing **engagement** (17 features) lowers PR-AUC at day 30 | **pre-registered** | drop **0.019** [0.012, 0.027] (0.649 → 0.630) | 0.004 | supported |
| H2b | Removing **assignment** (6 features) lowers PR-AUC at day 30 | **pre-registered** | drop **0.036** [0.025, 0.047] (0.649 → 0.614) | 0.004 | supported |
| H2c | Removing **scores** (5 features) lowers PR-AUC at day 90 | **pre-registered** | drop **0.043** [0.035, 0.052] (0.760 → 0.717) | 0.004 | supported |
| H3 | XGBoost and logistic regression differ in PR-AUC at day 60 | confirmatory | XGBoost higher by **0.014** [0.008, 0.020] (0.704 vs 0.690) | 0.004 | supported |
| H4 | Calibration error is higher on an unseen module | confirmatory | median ECE increase **0.038**; worse in **7 of 7** modules (range 0.005–0.151) | 0.008 | supported |
| H5 | Recall at day 60 differs between women and men | confirmatory | women lower by **0.067** [0.040, 0.096] (0.763 vs 0.830) | 0.004 | supported |
| H6a | Active days on the platform (day 30) ↔ adverse outcome | **pre-registered** | Spearman ρ = **−0.29** [−0.31, −0.27], n = 11,759 | < 0.001 | supported |
| H6b | Assignment completion rate (day 30) ↔ adverse outcome | **pre-registered** | Spearman ρ = **−0.34** [−0.35, −0.32], n = 9,908 | < 0.001 | supported |

No result is "practically negligible" under the week 4 thresholds (the smallest, H3, is 0.014 > 0.01).
Robustness: logistic regression shows the same direction for every H1 and H2 effect (H1: +0.042, +0.088; H2 drops:
0.024, 0.033, 0.053).

## 2. What the results mean

1. **Earlier warnings cost accuracy (RQ1).** On exactly the same students, ROC-AUC rises from 0.704 (day 30) to 0.770
   (day 60) to 0.818 (day 90). An institution must choose: act early with a weaker signal, or later with a stronger one
   but less time to help. SEWS therefore keeps a separate model per decision point.
2. **Every tested signal family adds information (RQ2).** At day 30, **assignment behaviour (6 features) contributes
   almost twice as much as all 17 engagement features** (PR-AUC drop 0.036 vs 0.019). At day 90, removing the 5
   released-score features costs 0.043. Week 5 explains why scores were tested at day 90: 84% are missing at day 30.
3. **XGBoost beats logistic regression, but only slightly (H3).** 0.014 PR-AUC is real (the interval excludes 0) but
   small; logistic regression remains a defensible, more explainable alternative. The separate 95% intervals of the two
   models overlap ([results-v2](../ml/results-v2.md)) — the **paired** test, on the same students, is what resolves the
   difference. Judging by overlapping intervals would have wrongly suggested "no difference".
4. **Calibration does not transfer (H4, RQ5 proxy).** Expected calibration error worsened on all 7 unseen modules.
   Probabilities from one setting cannot be trusted in another without recalibration — the strongest argument for
   training and calibrating on each institution's own data (in-app training).
5. **The active model misses more at-risk women than men (H5, RQ4).** Recall 0.763 vs 0.830: about 7 percentage points
   more at-risk women go unflagged at the chosen threshold. This is now a statistically supported finding. No
   mitigation was applied; an institutional model must be audited before approval ([fairness.md](../ml/fairness.md)).
6. **Early behaviour is associated with outcomes (H6).** Fewer active days and lower assignment completion in the first
   30 days go with failing or withdrawing (ρ = −0.29 and −0.34: moderate). These are associations, not causes.

## 3. Methods used (course week 6 topics)

| Topic | Where |
|---|---|
| Correlation | Spearman rank correlation (H6; feature–feature correlation in week 5) |
| Regression | Logistic regression as a model and as the baseline (H2 robustness, H3) |
| Hypothesis testing | DeLong test for correlated ROC curves; paired cluster bootstrap; exact Wilcoxon signed-rank; Spearman test; Holm family-wise correction |
| Performance metrics | PR-AUC (read with prevalence), ROC-AUC, Brier score, expected calibration error, recall by group |
| Validation | Out-of-time split; same-student paired comparisons; student-level resampling; reproduction of published numbers; leakage guard |

## 4. Caveats (state these in the paper)

- **Bootstrap floor.** With 2,000 resamples the smallest one-sided bootstrap p-value is 1/2001 ≈ 0.0005. Five tests
  (H1a, H1b, H2a–c) sit at that floor and two two-sided tests (H3, H5) at twice it, so their true p-values are *at
  most* these values. After Holm all are ≤ 0.004. The DeLong p-values for H1 are far smaller (z = 13.3 and 14.3).
- **H4 has only 7 modules.** 0.0078 = 1/128 is the smallest p-value an exact one-sided Wilcoxon test can give with 7
  observations: every module degraded.
- **Confirmatory ≠ blind.** For H1, H3, H4 and H5 the direction was known before testing (week 4 honesty note); the
  genuinely new findings are the pre-registered H2 and H6.
- **Independence.** The H6 p-values assume independent rows; the intervals resample students and are the safer
  statement.
- **Ablation measures unique contribution.** Removing a family shows what the *other* families cannot replace;
  correlated families (e.g. engagement and quiz activity) share information, so a family's total importance can be
  larger than its ablation effect.
- **One dataset.** Everything here is about one UK distance-learning university in 2013–14.
