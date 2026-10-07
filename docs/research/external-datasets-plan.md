# External benchmark datasets: search, choice and pre-specified analysis

Status 2026-10-08. Question from the team: "is there any other dataset to train this model on?" This document records
the search, why two datasets were chosen, and — **before any model is trained on them** — the design, feature policy
and comparisons, so the results cannot steer the analysis. Results: [docs/ml/external-datasets.md](../ml/external-datasets.md).

> **Provenance: BENCHMARK (Portugal).** Neither dataset is Indian. Results describe the SEWS method on these data and
> are never evidence about Indian students; models trained on them are never approved for real students.

## 1. Search (2026-10-08)

| Candidate | Decision | Reason |
|---|---|---|
| UCI 697 "Predict Students' Dropout and Academic Success" — Polytechnic Institute of Portalegre, 4,424 students, 36 attributes, CC BY 4.0, doi:10.24432/C5MC89 | **Used (primary)** | Higher education, semester-based; "curricular units not approved" is the closest public analogue of backlogs/KTs |
| UCI 320 "Student Performance" — two Portuguese secondary schools, 649 (Portuguese) + 395 (Math) students, CC BY 4.0, doi:10.24432/C5TG7T | **Used (secondary)** | Period grades G1/G2 allow early prediction; small; secondary school |
| XuetangX / KDD Cup 2015 MOOC clickstream | Not used | Licence terms not stated; the original download site is gone. SEWS requires documented dataset terms |
| Indian college datasets in published papers (e.g. a 165-record cohort, VBS Purvanchal University) | Not used | Never published; not obtainable |
| HarvardX–MITx person-course | Not used | Engagement counts are end-of-course totals: unusable for early warning without leakage |

Downloaded with the team's approval on 2026-10-08 into the git-ignored `ml/data/raw/`:

| File | Source | SHA-256 |
|---|---|---|
| `uci_dropout/data.csv` (4,424 rows) | archive.ics.uci.edu, dataset 697 | `3ef126de5cefff26eb11fbb4237f1a1401cb64b488e2f1d598c23cedeb4c45ae` |
| `uci_student_performance/student-por.csv` (649 rows) | archive.ics.uci.edu, dataset 320 | `a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f` |
| `uci_student_performance/student-mat.csv` (395 rows) | archive.ics.uci.edu, dataset 320 | `e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80` |

Profiling before design (no model trained): no missing values; Target = Graduate 2,209 / Dropout 1,421 / Enrolled 794;
the same 180 students have 0 units enrolled in both semesters (75 of them graduated, so "0 enrolled" is not
"already left"); 10 distinct (unemployment, inflation, GDP) tuples, i.e. 10 enrolment cohorts, but no year column;
students "not up to date with tuition fees" are 87% dropouts (457 of 528).

## 2. Dataset A — university dropout (UCI 697)

**Target:** `dropout` = Target is "Dropout" (status at the end of the normal course duration). Secondary,
descriptive only: `not_graduated` = Dropout or Enrolled.

**Decision points and populations** (a prediction uses only what is known at that point):

| Point | Features | Population |
|---|---|---|
| D0 — enrolment | application mode, application order, course, daytime/evening, previous qualification and its grade, admission grade, unemployment rate, inflation rate, GDP | all students |
| D1 — end of semester 1 | D0 + semester-1 units credited, enrolled, evaluations, approved, grade, without evaluations; derived: semester-1 approval rate, semester-1 units failed (enrolled − approved, the backlog analogue) | students with ≥ 1 unit enrolled in semester 1 |
| D2 — end of semester 2 | D1 + the same semester-2 variables and derived features + change in approval rate (2 − 1) | students with ≥ 1 unit enrolled in semester 2 |

**Not model inputs (policy):** gender, age at enrolment, marital status, nationality, international, displaced,
educational special needs, parents' qualifications and occupations. Gender, age band (≤ 20, 21–25, > 25),
international, displaced and special needs are **audit attributes** for the fairness check.

**Timing not verified → sensitivity analysis only:** `Debtor`, `Tuition fees up to date`, `Scholarship holder`. The
dataset documentation says only that it contains "information known at the time of student enrolment"; it does
not state when these three were recorded, and the 87% dropout share among fee defaulters is consistent with
recording after students left. They are added in one labelled sensitivity run at D0; any gain is reported as
possibly leakage, not as a result.

**Splits:** no enrolment year, so **no out-of-time split is possible**. Stratified random split 70 / 15 / 15
(train / validation / test, seed 20261008); validation for tuning, thresholds and calibration; test used once.
Exploratory robustness: **leave-one-cohort-out** over the 10 macro-economic cohorts (XGBoost and L1 at D1).

**Models:** prevalence baseline, L1 logistic (C on validation), random forest, XGBoost (12-setting random search,
early stopping on validation). Imbalance: none vs class weights (chosen on validation). Calibration: Platt vs
isotonic on validation. Thresholds: F1 and F2 on validation. SHAP for XGBoost; subgroup metrics on the audit
attributes.

**Pre-specified comparisons** (test set, paired student bootstrap, 2,000 resamples, seed 20261008; Holm over
E1–E3; |ΔPR-AUC| < 0.01 is "practically negligible"):

| ID | Comparison | Test |
|---|---|---|
| E1 | XGBoost PR-AUC at D1 > at D0, on the D1 test students | one-sided |
| E2 | XGBoost PR-AUC at D2 > at D1, on the D2 test students | one-sided |
| E3 | L1 logistic and XGBoost differ in PR-AUC at D1 | two-sided |

## 3. Dataset B — secondary-school failure (UCI 320, Portuguese course; Math as replication)

**Target:** `fail` = final grade G3 < 10 (the Portuguese pass mark on the 0–20 scale).

| Point | Features |
|---|---|
| P0 — start of year | school, weekly study time, past class failures, extra school support, family support, paid classes, extra-curricular activities, wants higher education |
| P1 — after period 1 | P0 + G1 |
| P2 — after period 2 | P1 + G2 |

**Not model inputs (policy):** sex, age, address, family size, parents' cohabitation, education and jobs, guardian,
reason for school choice, travel time, nursery, internet, romantic relationship, family relations, free time,
going out, alcohol use, health — demographic, family or sensitive lifestyle data. Sex, age band (≤ 17, ≥ 18) and
address are audit attributes. `absences` has no recording date (it is most likely the year's total): sensitivity
at P2 only.

**Evaluation:** n = 649 is too small for a single hold-out, so **5 × 5 repeated stratified cross-validation**
(seed 20261008); out-of-fold PR-AUC per repeat, reported as mean and range. L1 logistic with C chosen by inner
5-fold CV; random forest and XGBoost with fixed, conservative settings (XGBoost: depth 3, learning rate 0.05,
200 trees, subsample 0.8, column sample 0.8, min child weight 5). **Exploratory only — no hypothesis tests.** The
Math file (n = 395; 382 students also appear in the Portuguese file) is analysed separately as a replication and
never pooled.

## 4. Change log

| Date | Change | Reason |
|---|---|---|
| 2026-10-08 | Initial version, after download and profiling, before any training | — |
| 2026-10-08 (before any training) | Dataset B random forest fixed: 300 trees, minimum 5 students per leaf, √features per split, full bootstrap sample. Dataset A nominal codes are one-hot encoded (59 / 67 / 76 inputs at D0 / D1 / D2); D1 and D2 populations are identical (4,244 students active in semester 1) | The plan did not specify these details |
