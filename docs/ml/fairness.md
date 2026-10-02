# Fairness audit notes (benchmark)

> **Provenance: BENCHMARK (OULAD, United Kingdom, 2013–2014).** These are facts about models trained and tested
> on UK data with UK audit categories. They say nothing about Indian students or Indian social categories.

Source: `subgroups_test` in `ml/reports/oulad-v2-20260924T003349Z/metrics.json` (selected model per target and
decision point, test presentation 2014J). Code: `ml/evaluation/metrics.py` (`subgroup_metrics`,
`disparity_summary`); tests: `ml/tests/test_monitoring_and_fairness.py`.

## Method

- **Audit attributes are never model inputs.** OULAD's `gender`, `age_band`, `disability` and `imd_band`
  (Index of Multiple Deprivation band of the student's area) are used only to disaggregate test results.
  None of the 37 features is a protected attribute.
- Per group: recall, false-negative rate, false-positive rate, precision (at the validation-chosen threshold),
  PR-AUC, mean predicted probability vs observed rate (calibration gap) and ECE. Disparity = largest minus
  smallest value across groups with enough data.
- Groups with fewer than 100 students or fewer than 10 adverse outcomes are reported **without metrics**
  (OULAD's `55<=` age band — 81 students at day 60 — is excluded at every academic decision point).
- No fairness threshold has been agreed and **no mitigation was applied**. This is an audit, not a certificate.

## Active benchmark model (academic, day 60, XGBoost), test

| Attribute | Group | n | Observed rate | Mean predicted | Recall | False-positive rate | PR-AUC | ECE |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| gender | F | 3,730 | 0.361 | 0.471 | 0.763 | 0.428 | 0.618 | 0.114 |
| gender | M | 5,086 | 0.396 | 0.453 | 0.830 | 0.399 | 0.769 | 0.059 |
| age_band | 0-35 | 6,029 | 0.395 | 0.471 | 0.815 | 0.431 | 0.724 | 0.080 |
| age_band | 35-55 | 2,706 | 0.352 | 0.439 | 0.776 | 0.374 | 0.659 | 0.088 |
| disability | N | 8,013 | 0.369 | 0.456 | 0.802 | 0.408 | 0.697 | 0.088 |
| disability | Y | 803 | 0.497 | 0.505 | 0.807 | 0.463 | 0.768 | 0.064 |

IMD band (11 groups including `unknown`): PR-AUC from 0.616 (`unknown`, 359 students) and 0.624 (80-90%) to
0.763 (20-30%); ECE from 0.067 (20-30%) to 0.133 (90-100%); recall from 0.755 (`unknown`) to 0.831 (20-30%).

What this shows for the active model:

1. **Women are served worse.** Lower recall (0.763 vs 0.830: more at-risk women are missed), much lower PR-AUC
   (0.618 vs 0.769), and about twice the over-prediction (predicted 0.471 vs observed 0.361; men 0.453 vs
   0.396).
2. **Students with a declared disability get more false alarms** (FPR 0.463 vs 0.408) at similar recall.
3. **Ranking and calibration are worst for the least-deprived areas and for missing IMD data**, i.e. the
   model's errors are not uniform across socio-economic groups.

## Across all 12 selected models

The eight largest disparities all involve IMD band: PR-AUC gaps up to 0.259 (engagement, day 30: `unknown` vs
0-10%) and recall gaps up to 0.213 (dropout, day 90: 80-90% vs 40-50%). For the academic target, the gaps per
attribute (recall / FPR / PR-AUC / ECE) stay below 0.11 / 0.10 / 0.22 / 0.15 at days 30, 60 and 90.

## Consequences for SEWS

- A benchmark model must not be deployed to Indian students; any institutional model needs its own audit on the
  institution's data before approval (docs/ml/ml-strategy.md §5).
- Relevant Indian audit categories (e.g. gender, social category, disability, rural/urban, first-generation
  learner) need a lawful basis and restricted access (docs/ml/data-dictionary.md). The institutional schema
  does not hold audit attributes today, so **live subgroup monitoring is not possible yet**
  (docs/ml/monitoring.md).
- Because the system only suggests support and every suggestion needs human review, a missed student (false
  negative) is the costlier error; per-group recall should be the first metric any approval checks.
- Agreeing acceptable disparity limits, and what happens when they are exceeded, is an owner/institution
  decision that has not been made.
