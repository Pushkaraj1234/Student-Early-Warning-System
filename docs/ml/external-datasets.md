# External benchmark datasets — results

Status 2026-10-08. Run `external-v1-20261007T184644Z` ([report](../../ml/reports/external-v1-20261007T184644Z/report.md),
`results.json`). Design, feature policy and comparisons were fixed beforehand in
[external-datasets-plan.md](../research/external-datasets-plan.md). Reproduce:
`ml/.venv/Scripts/python -m ml.external.experiment --config ml/configs/external_v1.json` (code `ml/external/`,
tests `ml/tests/test_external.py`).

> **Provenance: BENCHMARK (Portugal, CC BY 4.0).** These results show how the SEWS method behaves on two more
> datasets. They are not evidence about Indian students, and no model trained here is approved for real students.

## 1. University dropout (UCI 697, 4,424 students, dropout rate 0.321)

Stratified hold-out (train 3,096 / validation 664 / test 664). **Not out-of-time:** the dataset has no enrolment
year. 95% intervals from 2,000 student bootstrap resamples.

| Decision point | Inputs | XGBoost test PR-AUC | L1 logistic | Random forest | Chance (dropout rate) |
|---|---:|---:|---:|---:|---:|
| D0 — enrolment | 59 | 0.555 [0.483, 0.627] | 0.561 [0.488, 0.630] | 0.516 | 0.321 |
| D1 — after semester 1 | 67 | **0.797** [0.745, 0.844] | 0.785 [0.729, 0.835] | 0.767 | 0.318 |
| D2 — after semester 2 | 76 | **0.836** [0.791, 0.878] | 0.830 [0.783, 0.875] | 0.811 | 0.318 |

**Pre-specified comparisons (Holm-corrected):**

| ID | Comparison | Effect [95% CI] | Holm p | Result |
|---|---|---|---:|---|
| E1 | semester-1 results added (D1 vs D0, XGBoost, 635 test students) | **+0.241** [0.181, 0.298] | 0.001 | supported |
| E2 | semester-2 results added (D2 vs D1) | **+0.040** [0.014, 0.067] | 0.004 | supported |
| E3 | L1 logistic vs XGBoost at D1 | −0.012 [−0.032, 0.009] | 0.252 | not supported |

What this means:

1. **The first semester's results are the strongest early signal** (E1: +0.24 PR-AUC). At D1 the most important
   inputs (SHAP) are the semester-1 approval rate and the **number of units failed** — the direct analogue of
   backlogs/KTs in Indian colleges. At the F1 threshold the D1 model finds 63% of later dropouts with 76% precision.
2. **The same pattern as OULAD:** later decision points are more accurate (OULAD H1; here E1, E2). An institution
   chooses between acting early with a weaker signal and acting later with a stronger one.
3. **A simple, explainable model is enough here.** LASSO logistic regression is statistically indistinguishable
   from XGBoost at D1 (E3), and close at D0 and D2.
4. **Calibration:** XGBoost's raw probabilities were already the best calibrated at D1 (ECE 0.038); Platt (0.057)
   and isotonic (0.053) made it worse on test, so no calibration would be applied (the SEWS rule).
5. **Class weights did not help** XGBoost or logistic regression on validation (they were not selected).
6. **Unseen cohort (exploratory):** trained without one of the 10 enrolment cohorts, XGBoost at D1 scores 0.77–0.87
   on the held-out cohort (mean 0.82) — the model is not tied to one intake.
7. **Financial variables (sensitivity only):** adding debtor / fees up to date / scholarship raises D0 PR-AUC from
   0.555 to **0.733**. Because their recording time is undocumented and 87% of fee defaulters are dropouts, this
   gain may come from information recorded after students left. They are **not** used in any SEWS result.
8. **Not graduated on time** (dropout or still enrolled, 50% of students; descriptive): XGBoost at D1 PR-AUC 0.911.

**Fairness at D1** (XGBoost, F1 threshold, test; recall = share of later dropouts flagged):

| Attribute | Recall by group | False-positive rate |
|---|---|---|
| Gender | female 0.561 (n 414) · male 0.702 (n 221) | 0.089 · 0.111 |
| Age at enrolment | ≤ 20: 0.419 · 21–25: 0.638 · > 25: 0.827 | 0.070 · 0.111 · 0.194 |
| Displaced (lives away from home) | no 0.766 · yes 0.484 | 0.140 · 0.058 |
| International, special needs | too few students (9 and 8) to report | — |

As in OULAD (week 6, H5), **at-risk women are missed more often than men**, and here so are younger and displaced
students. These gaps must be audited and addressed (e.g. per-group thresholds, as evaluated in the v3 study)
before any institutional model is approved; the attributes are never model inputs.

## 2. Secondary-school failure (UCI 320; exploratory, 5 × 5 repeated cross-validation)

Final grade below 10/20. PR-AUC mean (range over the 5 repeats).

| Decision point | Portuguese (649 students, fail 15.4%) | Math replication (395 students, fail 32.9%) |
|---|---|---|
| P0 — start of year (study time, past failures, support, plans) | 0.473 (L1) · 0.441 (XGBoost) | 0.539 (L1) · 0.559 (XGBoost) |
| P1 — after the first-period grade | **0.725** (L1) · 0.689 (XGBoost) | **0.822** (L1) · 0.812 (XGBoost) |
| P2 — after the second-period grade | 0.856 (L1) · **0.869** (XGBoost) | 0.932 (L1) · 0.930 (XGBoost) · 0.944 (RF) |
| P2 + absences (sensitivity) | 0.853 (L1) · 0.871 (XGBoost) | 0.939 (L1) · 0.937 (XGBoost) |

- Again, **each new assessment result is the strongest signal**; background information alone is weak.
- On these small datasets the **L1 logistic model is as good as or better than the tree models** before the last
  period.
- **Absences add nothing** once grades are known (≤ 0.007 PR-AUC). The dataset records only a yearly total, so
  this says nothing about the value of weekly attendance tracking in SEWS.
- Exploratory fairness at P1 (threshold chosen on the same out-of-fold predictions): recall gap between the sexes
  0.14 (boys lower) in Portuguese, 0.004 in Math — not consistent, and too small a sample to conclude anything.

## 3. Limitations

- Both datasets are Portuguese; one is secondary school. No out-of-time evaluation was possible (no year in either).
- Dataset B results are exploratory (no hypothesis tests, small n); the Portuguese and Math files share 382
  students and are therefore not independent replications.
- Neither dataset has weekly activity, so the v3 sequence models (GRU/LSTM/TCN) cannot be trained on them; the
  decision-point models are the part of SEWS these datasets can test.
- Datasets with documented terms and weekly data for a second institution were not found (XuetangX/KDD Cup 2015:
  terms not stated). A real Indian institutional dataset remains the only way to answer RQ5.
