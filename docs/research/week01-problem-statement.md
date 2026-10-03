# Week 1 — Problem identification and research planning

Project: **SEWS — Student Early Warning & Intervention System**. Domain: education, artificial intelligence
(machine learning), mobile and cloud software. Status 2026-10-03.

## 1. The real-world problem

Indian higher education is very large: the Ministry of Education's All India Survey on Higher Education (AISHE)
2021-22, released on 25 January 2024, reports about **4.33 crore students** enrolled and a gross enrolment ratio of
**28.4** [MoE-AISHE]. At this scale a mentor or class teacher cannot follow every student closely.

Students who end up failing or withdrawing usually show earlier, observable signals: falling attendance, missed or late
submissions, low early marks and less activity on the learning platform. In most institutions these signals sit in
separate registers and systems, and the problem becomes visible only when semester results are published — too late
for a cheap, supportive intervention such as a mentor meeting.

## 2. From the practical problem to a research problem

| | |
|---|---|
| **Practical question** (mentor) | "Which of my students need help now, and why?" |
| **Research problem** | Can a model that uses **only the information available at a given day of the semester** identify students at risk of failing or withdrawing **early enough to act**, with **calibrated** probabilities, **explanations** a mentor can check, and **comparable performance across student groups** — and can it work inside a **human-in-the-loop** intervention workflow? |

Why this is a research problem and not just an app: published early-warning results can be inflated by information
leaks (using data that would not exist yet at prediction time) and by random rather than time-ordered test splits
[Kaufman2012, Le2026]; models trained on one cohort or course lose calibration on another (our own cross-module result:
expected calibration error worsened by up to 0.151, [results-v2](../ml/results-v2.md)); and most of the evidence we
found comes from UK, US and MOOC settings rather than Indian institutions ([week 2](week02-literature-review.md)).

## 3. Problem statement

Higher-education institutions need to identify students at academic risk early in a semester, while support is still
cheap and effective. Existing records (attendance, assessments, learning-platform activity, prior results) contain
early signals, but they are scattered, checked late, and — when used for prediction — easily misused through data
leakage, poorly calibrated scores and unexplained or biased flags. **This project designs, builds and evaluates SEWS:
a leakage-safe, explainable and auditable early-warning system that estimates each student's risk of failing or
withdrawing at fixed points in the semester, explains the estimate, and routes it to a mentor who decides on support.**

## 4. Objectives

| # | Objective | Measured by |
|---|---|---|
| O1 | Build an **as-of** feature pipeline that uses only information available at the decision point (attendance, assessments, learning-platform activity, prior record), with an automatic leakage check | The leakage guard passes at every decision point; features unchanged when future data is removed |
| O2 | Train and compare **logistic regression, random forest and XGBoost** at days 30, 60 and 90 of a term, evaluated **out of time** (train on earlier cohorts, test on a later one) | PR-AUC, ROC-AUC, Brier score, expected calibration error, each with 95% bootstrap confidence intervals, against the base rate |
| O3 | **Explain** each estimate in language suited to students, mentors and administrators | SHAP-based factors; stability of the top factors across training seeds |
| O4 | **Audit fairness**: compare errors and calibration across student groups | Per-group recall, false-positive rate, PR-AUC, calibration; disparity between groups |
| O5 | Build a **working prototype**: mobile app (student, mentor, admin), secure database, batch jobs, and training from an institution's own records with human approval before use | End-to-end demo on the hosted testing project; automated tests |
| O6 | Record **interventions and their outcomes** (offered, accepted, completed) for later descriptive analysis | Complete intervention workflow with outcome measures |

## 5. Scope

**In scope:** higher-education students in India (18+), semester system with UGC CBCS 10-point grades; academic
risk = fail or withdraw in the term; decision points days 30, 60 and 90; human review of every suggestion;
benchmark data (OULAD, UK) for method development; synthetic data for software testing.

**Out of scope:** school students (different consent rules under the DPDP Act 2023 [DPDP2023]); diagnosing
mental health or ability; causal claims about interventions; automatic action without a human; any claim about
Indian students before institutional data is available and approved. Full scope: [project-scope.md](project-scope.md).

## 6. Expected outcomes

1. A reproducible, leakage-safe ML method with out-of-time results, confidence intervals, calibration and a fairness
   audit on public benchmark data — **achieved** on OULAD: day-60 XGBoost PR-AUC 0.704 [0.689, 0.720] against a base
   rate of 0.381 ([results-v2](../ml/results-v2.md)).
2. A working prototype at **TRL 4** (validated in a laboratory environment) — **achieved** on the hosted testing project
   with synthetic data (week 7); the technology readiness assessment is done in week 9.
3. A training pipeline that learns from an institution's own records, ready for a pilot once data and ethics
   approval exist — **built and proven on synthetic data** ([institutional-training](../ml/institutional-training.md)).
4. Research outputs: literature review, IEEE-format paper, poster and presentation (weeks 2, 8, 10).

## 7. Stakeholders and design thinking

| Stage | What was done |
|---|---|
| Empathise | Needs of three users: students (support without stigma), mentors (limited time, need reasons they can check), administrators (oversight of models) |
| Define | Ranking under limited mentor capacity, not just yes/no classification; a human decides ([problem-definition.md](problem-definition.md) §2) |
| Ideate | Risk *signal* with plain-language reasons, suggested support options, the student can accept or decline |
| Prototype | Flutter app + Supabase + Python ML and batch jobs (week 7) |
| Test | Driven end to end on an Android emulator against the testing project; bugs found and fixed |

## References

- [MoE-AISHE] Ministry of Education, Government of India, *All India Survey on Higher Education 2021-22*, released
  25 Jan 2024 (press release: https://www.pib.gov.in/PressReleasePage.aspx?PRID=1999713).
- [Kaufman2012] S. Kaufman, S. Rosset, C. Perlich, O. Stitelman, "Leakage in data mining: Formulation, detection, and
  avoidance," *ACM Trans. Knowl. Discov. Data*, vol. 6, no. 4, 2012, doi:10.1145/2382577.2382579.
- [Le2026] N. L. Le, M.-H. Abel, B. Laforge, "When Can We Trust Early Warnings? Leakage-Excluded Early Outcome
  Prediction from LMS Interaction Logs," arXiv:2605.25794, 2026 (preprint, not peer-reviewed).
- [DPDP2023] Digital Personal Data Protection Act, 2023 (India), Section 9 (personal data of children).

Full, verified reference list: [week02-literature-review.md](week02-literature-review.md).
