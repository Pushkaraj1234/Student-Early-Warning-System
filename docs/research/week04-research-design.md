# Week 4 — Hypotheses, research design, sampling and data collection

Status 2026-10-03. **These hypotheses, tests and decision rules are fixed here, before the week 6 tests are run**, and
must not be changed after seeing the test results. Any later change is recorded in §7 with its reason.

Honesty note: the point estimates for H1, H3, H4 and H5 were already published in [results-v2](../ml/results-v2.md),
[fairness](../ml/fairness.md) and the cross-module report, so for those the **formal statistical test** is new but the
direction of the effect was known — they are labelled **confirmatory (estimate seen)**. H2 and H6 have not been
examined at all — **pre-registered**. The paper must report this distinction.

## 1. Hypotheses

All hypotheses concern the **academic** target (Fail or Withdrawn) on the **OULAD benchmark** (UK), test presentation
2014J, unless stated. They say nothing about Indian students (RQ5 needs institutional data).

| ID | RQ | Hypothesis (H₁) | Null (H₀) | Status | Test |
|---|---|---|---|---|---|
| H1a | RQ1 | On the same students, ROC-AUC is higher at day 60 than at day 30 | ROC-AUC(60) ≤ ROC-AUC(30) | confirmatory (estimate seen) | one-sided paired DeLong test; paired cluster bootstrap of the difference |
| H1b | RQ1 | On the same students, ROC-AUC is higher at day 90 than at day 60 | ROC-AUC(90) ≤ ROC-AUC(60) | confirmatory (estimate seen) | as H1a |
| H2a | RQ2 | Removing the **engagement** family (17 VLE features) lowers PR-AUC at day 30 | ΔPR-AUC (full − ablated) ≤ 0 | **pre-registered** | one-sided paired cluster bootstrap |
| H2b | RQ2 | Removing the **assignment** family (6 features) lowers PR-AUC at day 30 | as H2a | **pre-registered** | as H2a |
| H2c | RQ2 | Removing the **academic-score** family (5 features) lowers PR-AUC at day 90 | as H2a | **pre-registered** | as H2a |
| H3 | — | At day 60, XGBoost and logistic regression differ in test PR-AUC | difference = 0 | confirmatory (estimate seen) | two-sided paired cluster bootstrap; DeLong for ROC-AUC |
| H4 | RQ5 (proxy) | Expected calibration error is higher on a module the model never saw than on the same module seen in training | median ECE degradation ≤ 0 | confirmatory (estimate seen) | one-sided exact Wilcoxon signed-rank over the 7 modules |
| H5 | RQ4 | At day 60, the active model's recall differs between female and male students | recall(F) = recall(M) | confirmatory (estimate seen) | two-sided bootstrap of the recall difference (clustered by student) |
| H6a | RQ2 | At day 30, VLE active days to date are negatively associated with the adverse outcome | Spearman ρ ≥ 0 | **pre-registered** | one-sided Spearman correlation on the training presentations |
| H6b | RQ2 | At day 30, assignment completion rate is negatively associated with the adverse outcome | Spearman ρ ≥ 0 | **pre-registered** | as H6a |

Secondary (reported with confidence intervals, no hypothesis test): ablation of every family at every decision point;
all model pairs at every decision point; every subgroup in [fairness](../ml/fairness.md).

## 2. Decision rules (fixed in advance)

- **Family-wise error:** the 10 tests above form one family; **Holm's step-down correction** [Holm1979] at α = 0.05.
  A hypothesis is supported only if its Holm-adjusted p-value < 0.05.
- **Effect sizes first:** every result is reported as an effect size with a 95% confidence interval, whether or not it
  is significant. A significant but tiny effect (|ΔPR-AUC| < 0.01, |ΔROC-AUC| < 0.01, recall gap < 0.02) is reported as
  "statistically detectable but practically negligible".
- **Resampling:** 2,000 bootstrap resamples, **clustered by student** (a student may have several module
  registrations), fixed seed 20261003. ROC-AUC comparisons also use DeLong's test for correlated curves [DeLong1988].
- **Same students:** H1 uses only students still registered at day 90 (the day-90 test population), so every decision
  point is compared on identical students.
- **Ablation protocol (H2):** retrain XGBoost with the same hyperparameters, imbalance strategy, split and seed,
  dropping only the family under test; no re-tuning (re-tuning would favour the ablated model). Logistic regression is
  repeated as a robustness check.
- **No re-selection:** none of these tests changes which model is selected or approved. The test presentation is used
  for evaluation only.

## 3. Experimental design

| Element | Value |
|---|---|
| Unit of analysis | One student registration on one module presentation at one decision point |
| Independent variables | Decision point (day 30, 60, 90); model family (logistic regression, random forest, XGBoost); feature set (full, or one family removed) |
| Dependent variables | PR-AUC, ROC-AUC, Brier score, expected calibration error, recall / false-positive rate (overall and by group) |
| Controls | Same out-of-time split, same features (except the ablated family), same seed, same preprocessing; temporal leakage guard at every decision point |
| Split (out-of-time) | train 2013B + 2013J · validation 2014B · test 2014J |
| Baselines | Prevalence (random ranking); logistic regression |
| Threats to validity | *Internal:* leakage (controlled by the as-of builder and guard); selection on test (avoided: test used once per model). *External:* one UK distance-learning university, 2013–14; no attendance data; results do not transfer to Indian institutions without institutional data. *Construct:* "Fail or Withdrawn" mixes two different outcomes (separate dropout and course-failure targets are reported in results-v2) |

## 4. Sampling

OULAD is not a random sample: it is the complete record of 7 modules over four presentations (22 module presentations,
32,593 registrations) at the Open University, UK [Kuzilek2017]. The population the results describe is therefore
**Open University registrations in 2013–14**. At each decision point, registrations that had already withdrawn are
excluded (they are no longer at risk to be predicted).

| Decision point | Train (n / adverse / rate) | Validation | Test |
|---|---|---|---|
| day 30 | 11,759 / 5,193 / 0.442 | 6,493 / 3,136 / 0.483 | 9,198 / 3,742 / 0.407 |
| day 60 | 11,353 / 4,785 / 0.421 | 6,184 / 2,827 / 0.457 | 8,816 / 3,359 / 0.381 |
| day 90 | 11,052 / 4,483 / 0.406 | 5,974 / 2,616 / 0.438 | 8,532 / 3,075 / 0.360 |

**Precision instead of a power calculation:** the test set is fixed, so the useful question is how small a difference it
can resolve. The day-60 XGBoost PR-AUC interval is [0.689, 0.720], half-width ≈ 0.015; paired differences have narrower
intervals because both models are scored on the same students. Differences below about 0.01 should be treated as not
resolvable with these data.

## 5. Data collection

| Dataset | How obtained | Terms | Version / integrity | Used for |
|---|---|---|---|---|
| OULAD (UK, 2013–14) | Downloaded from the Open University / UCI repository | CC BY 4.0 (attribution) | content hash `oulad-f853d3b6b35de756`; download SHA-256 recorded in [baseline-results-v1](../ml/baseline-results-v1.md) | All model training and hypothesis tests |
| NSS 75th round (India, 2017–18) | Supplied by the team (MoSPI microdata) | Not supplied | Profile report `nss75-profile-20260924T225037Z` | Descriptive context only |
| Synthetic history | Generated by `sews_services.training.synthetic` (seeded) | Project code | seed and generator version in the run report | Proving the software and in-app training only — never as evidence |
| Team's enrolment file (`Dataset.csv`) | Supplied by the team | Source and year not stated | — | **Excluded**: institution-level totals, no student outcomes (week 3, example 5) |
| Institutional records | **Not collected** | Needs approval, ethics review, data-sharing agreement, DPDP Act basis | — | Future pilot ([institutional-training](../ml/institutional-training.md), [data-dictionary](../ml/data-dictionary.md)) |

### Planned questionnaire (not conducted — needs ethics approval)

For RQ3 (are explanations useful to mentors?), after a pilot: a Google Forms survey of mentors who used SEWS.

1. **System Usability Scale** — the standard 10 items, 5-point agreement scale [Brooke1996].
2. **Explanation usefulness** (5-point agreement): (a) I understood why a student was flagged; (b) I could check the
   reasons against the student's records; (c) the reasons helped me decide what support to offer; (d) the wording was
   respectful to the student; (e) I would have missed this student without SEWS.
3. Open questions: one thing that helped; one thing that misled or confused you.

Rules: voluntary, informed consent on the first page, no student names or identifiers collected, responses analysed in
aggregate only.

## 6. References

- [DeLong1988] E. R. DeLong, D. M. DeLong, and D. L. Clarke-Pearson, "Comparing the areas under two or more correlated
  receiver operating characteristic curves: A nonparametric approach," *Biometrics*, vol. 44, no. 3, pp. 837–845, 1988.
- [Holm1979] S. Holm, "A simple sequentially rejective multiple test procedure," *Scandinavian J. Statistics*, vol. 6,
  pp. 65–70, 1979.
- [Brooke1996] J. Brooke, "SUS — A quick and dirty usability scale," in *Usability Evaluation in Industry*, Taylor &
  Francis, 1996, pp. 189–194.
- [Kuzilek2017] J. Kuzilek, M. Hlosta, and Z. Zdrahal, "Open University Learning Analytics dataset," *Scientific Data*,
  vol. 4, art. 170171, 2017, doi: 10.1038/sdata.2017.171.

## 7. Change log (after this point, only with a reason)

| Date | Change | Reason |
|---|---|---|
| 2026-10-03 | Initial version | — |
