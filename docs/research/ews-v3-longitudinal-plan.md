# EWS v3 — Longitudinal early-warning study: plan, gap analysis and pre-specified comparisons

Status 2026-10-06. Source: the team's report "Robust longitudinal EWS" (executive summary, data schema, feature
engineering, labelling, models, training protocol, metrics, 12-week Gantt chart). This document maps every item
of that report onto SEWS, records what is already built, what v3 adds, and what cannot be done with the data
available — and **fixes the v3 comparisons and decision rules before any v3 result is seen** (the same
discipline as [week 4](week04-research-design.md)). Results go to [docs/ml/longitudinal-v3.md](../ml/longitudinal-v3.md).

> **Provenance: BENCHMARK** (OULAD, Open University UK, 2013–14). v3 results describe the method on this
> dataset, not Indian students. Benchmark-trained models are never approved for real students
> ([ml-strategy](../ml/ml-strategy.md) §5); what transfers to an institution is the *procedure*.

## 1. Gap analysis: the report against SEWS

| Report item | Already in SEWS (v2) | Added in v3 | Not possible / changed, and why |
|---|---|---|---|
| Demographics as features | Kept as **audit attributes only** (gender, age band, disability, deprivation band) | One **sensitivity experiment** with demographics as inputs, to measure the accuracy gain and the fairness cost | Policy stays: demographics are not model inputs in SEWS (a model must not raise risk *because* of who a student is). Race/ethnicity is not in OULAD; for Indian institutions, caste/community data is sensitive personal data and is not requested. CENEVAL is a Mexican exam — not applicable |
| Academic history (prior GPA, backlogs/KTs, credits) | Prior attempts, credits, banked results (OULAD); `academic_records`, backlogs in the institutional schema | — | OULAD has no prior GPA |
| Attendance, library, tutoring, counselling, discipline | Attendance tables and features exist for **institutional** data | — | **Not in OULAD.** Never fabricated; cannot be studied on the benchmark |
| Prior interventions + outcomes | Intervention workflow and outcome measures in the app/DB | — | Not in OULAD |
| Weekly granularity | Snapshots at days 30/60/90 | **Student-week panel**: a prediction every week, weeks 1–30 | — |
| Trend, rolling, volatility features | 7/14/30-day windows, click trends, score slope | Weekly rolling means (3 and 6 weeks), 6-week slope, volatility (CV), own-baseline change, inactivity streaks | — |
| Change-point indicators (CUSUM) | — | One-sided **CUSUM** drop statistic on weekly activity; weeks since the last detected drop | Bayesian change-point detection not used (CUSUM is transparent and cheap; one method is enough) |
| Submission punctuality | Late rate, mean delay, completion rates | On-time ratio, missed deadlines in the last 4 weeks, change in lateness | Exact submission *time of day* (11:59 pm) — OULAD records days only |
| Difficulty-adjusted score | Course-relative mean score | Score minus the cohort mean **of the same assessment** (released results only) | — |
| Feature selection (LASSO) | SHAP importance | **L1 (LASSO) logistic regression** as a model and as feature selection | — |
| Multi-horizon labels | End-of-course targets (academic, dropout, failure) and 14-day disengagement | **Withdrawal within 4 weeks** and **within 8 weeks**, per student-week | Course *failure* has no date in OULAD, so it has only the end-of-course horizon |
| Label smoothing / sustained decline | — | **Alert smoothing**: an alert only after the risk stays above threshold for 2 consecutive weeks; and an exponentially smoothed risk. Compared with raw alerts on false alarms and lead time | Soft labels near the pass mark need the numeric final mark — OULAD has only the result category |
| Risk tiers | Four levels (stable/watch/elevated/high) from validation quantiles | Tier stability week to week (flip rate) | — |
| Teacher-verified labels | — | — | Need a pilot (mentor feedback in the app exists, no data yet) |
| Time-to-event labels | — | Withdrawal week with censoring at course end | — |
| LSTM/GRU, TCN | — | **GRU, LSTM and TCN** (causal: the output for week *k* uses weeks ≤ *k* only), PyTorch | — |
| Transformer | — | — | Not built: the report itself rates it overkill at this data size |
| Survival analysis | — | **Kaplan–Meier** retention curves; **discrete-time hazard model** (person-week), C-index | Cox PH not used: weekly time has many ties; the discrete-time model is the standard choice for it |
| Hierarchical Bayesian model | Cross-module (unseen module) evaluation | — | Not built (needs Bayesian tooling and time); module effects are examined by leave-one-module-out instead |
| Ensembles | LR / RF / XGBoost compared, one selected | **Average of XGBoost and the best sequence model** | — |
| MC-dropout uncertainty | — | MC dropout on the sequence model; checked whether uncertain predictions are less accurate | — |
| Temporal CV | One out-of-time split (train 2013B+2013J, validation 2014B, test 2014J) | **Rolling-origin CV**: 2013B→2013J, 2013B+J→2014B, 2013B+J+2014B→2014J | — |
| Imbalance (SMOTE, weights) | None vs class weights | **SMOTE** added to the comparison (short-horizon withdrawal is rare per week) | — |
| Calibration (Platt, isotonic) | Platt, applied only if an out-of-time check improves it | Platt vs isotonic compared | — |
| Metrics | PR-AUC, ROC-AUC, Brier, ECE, F1, top-k%, subgroup metrics | **F2**, **cost-based threshold** (FN cost = 5 × FP, sensitivity 2/5/10), **time-to-detection (lead time)**, false alarms per student | — |
| Fairness | Subgroup audit with disparity summary | **Per-group thresholds** (equal opportunity) as an evaluated mitigation | Using a protected attribute at decision time is an ethical and legal choice for the institution; reported as analysis, not switched on |
| Explainability | SHAP (global and per student) | **Counterfactuals** on actionable features ("which change would bring the risk below the threshold") | Counterfactuals show what the *model* is sensitive to, not what *causes* success |
| Concept-drift indicators | PSI feature/prediction drift, performance-drop alerts | Drift across rolling-origin folds; whether simple models degrade less (P5) | — |
| Deployment, retraining, monitoring | Batch jobs, in-app institutional training, drift monitoring, model approval workflow | Versioned v3 artifacts + weekly batch scoring with the smoothed alert policy (prototype, benchmark only) | Wiring a benchmark-trained v3 model into the app is **not allowed** by the approval rule; production needs institutional weekly data (phase 2, §6) |

**Corrections to the report before it is cited:**
- "~90% accuracy" from clickstream studies and "Qiu & Shi (2025)" are **not verified** by us; do not cite them
  without reading the papers. Accuracy is not a suitable headline metric for imbalanced outcomes (SEWS reports
  PR-AUC, recall, calibration).
- "Simple models generalise better under drift" is a **hypothesis** here (P5), not a premise.
- The SHAP-importance table in the report is illustrative, not a result; v3 reports its own importance.

## 2. Study design (v3)

| Element | Value |
|---|---|
| Unit | One registration (student × module presentation) at the end of week *k* (cutoff day 7*k*), *k* = 1…30, while still registered |
| Features | `oulad-ts-1.0.0` = the 37 v2 features rebuilt at each weekly cutoff + 18 longitudinal features (§3), 55 in total. All as of the cutoff; the temporal-leakage guard is run on the longitudinal features as well |
| Targets | `academic` (Fail or Withdrawn at course end), `withdraw_4w`, `withdraw_8w` (unregisters within 4 / 8 weeks after the cutoff). Registrations recorded as Withdrawn without an unregistration date (93) are excluded from the horizon targets only |
| Hold-out split | train 2013B+2013J · validation 2014B · test 2014J (as v2) |
| Rolling-origin CV | 2013B→2013J · 2013B+2013J→2014B · 2013B+2013J+2014B→2014J (hyperparameters fixed from the hold-out validation; fold 2 is therefore optimistic) |
| Models | Prevalence baseline · L1 logistic regression · random forest · XGBoost · GRU · LSTM · TCN · ensemble (XGBoost + best sequence model) · discrete-time hazard (withdrawal) |
| Tuning | On validation only: XGBoost random search (12 settings), L1 strength (5 values), sequence models hidden size {32, 64} × dropout {0.1, 0.3}, early stopping on validation loss |
| Imbalance | none · class weights · SMOTE (on training rows only) |
| Thresholds | Chosen on validation: F1-best, F2-best, minimum expected cost (FN:FP = 5:1; 2:1 and 10:1 as sensitivity) |
| Alert policies | raw (risk ≥ threshold this week) · 2 consecutive weeks · exponentially smoothed risk (α = 0.5) |
| Student-level metrics | recall (adverse students alerted at least once before the outcome), false-alarm rate (passing students ever alerted), lead time (weeks between the first alert and withdrawal; for failures, weeks before course end), alert flips per student |
| Uncertainty | Cluster bootstrap over students, 2,000 resamples, seed 20261006 |

## 3. Longitudinal features (`oulad-ts-1.0.0` additions)

Weekly activity series *x*₁…*x*ₖ = VLE clicks in each week (days 7(*j*−1)+1 … 7*j*):
`clicks_this_week`, `active_days_this_week`, `clicks_roll3w_mean`, `clicks_roll6w_mean`,
`clicks_slope_6w` (least-squares slope of log(1+clicks) over the last 6 weeks, ≥ 3 weeks),
`clicks_cv_6w` (coefficient of variation over the last 6 weeks), `clicks_recent_vs_own_mean`
(log(1+mean of the last 3 weeks) − log(1+mean of the weeks before), ≥ 1 earlier week),
`inactive_week_streak`, `inactive_weeks_last_6w`,
`cusum_drop_stat` (one-sided lower CUSUM of log(1+clicks) against the student's own running mean and standard
deviation of earlier weeks, allowance 0.5, standard deviation floored at 0.5),
`weeks_since_change_point` (weeks since the CUSUM statistic last exceeded 3; missing if never).

Assessments (non-exam, with a due date; scores only once released, as in v2):
`on_time_ratio_to_date`, `missed_due_last_4w`, `delay_change_recent` (mean delay of submissions in the last 4
weeks − mean delay before), `difficulty_adjusted_score` (mean of score − cohort mean for the same assessment, both
from results released by the cutoff), `score_rolling2_mean`, `score_drop_from_best`, `score_volatility`
(standard deviation of released scores, ≥ 3).

## 4. Pre-specified comparisons (fixed 2026-10-06, before any v3 result)

Primary metric: test PR-AUC (2014J), all eligible student-weeks, paired cluster bootstrap over students.
Family: P1, P2, P4, P5 — **Holm** correction at α = 0.05. Everything else is reported with confidence intervals
as exploratory. Effects below |ΔPR-AUC| 0.01 or a false-alarm reduction below 0.02 are "practically negligible".

| ID | Comparison | Test |
|---|---|---|
| P1 | XGBoost with `oulad-ts-1.0.0` has higher PR-AUC than XGBoost with the v2 features, on identical student-weeks (target `academic`) | one-sided paired bootstrap |
| P2 | The best sequence model (chosen on validation) and XGBoost (`oulad-ts-1.0.0`) differ in PR-AUC (`academic`) | two-sided paired bootstrap |
| P4 | The 2-consecutive-week alert policy has a lower student-level false-alarm rate than raw alerts, same model and threshold (`academic`, F1 threshold) | one-sided paired bootstrap over students |
| P5 | Under an unseen module (leave-one-module-out, 7 modules), L1 logistic regression loses less PR-AUC than XGBoost relative to training with the module included (`academic`) | one-sided exact Wilcoxon signed-rank over the 7 modules |

## 5. Plan against the 12-week Gantt chart

| Gantt stage (dates from the chart) | v3 deliverable | Status |
|---|---|---|
| Schema design & feature selection (11–18 Oct) | §1 gap analysis, §3 feature set | done 2026-10-06 |
| Data collection & cleaning (18 Oct–1 Nov) | OULAD (already validated, [week 5](week05-eda.md)); student-week panel builder + leakage guard | done (guard passed at 6 weeks) |
| Feature engineering & aggregation (1–8 Nov) | `ml/longitudinal/panel.py` | done |
| Exploratory analysis & baselines (1–8 Nov) | panel description, Kaplan–Meier curves, prevalence and L1 baselines | done |
| Advanced prototyping — LSTM, XGBoost (8–22 Nov) | GRU / LSTM / TCN, XGBoost, RF, ensemble, hazard model | done |
| Refinement & cross-validation (15–22 Nov) | tuning on validation, rolling-origin CV, leave-one-module-out | done |
| Metrics & threshold tuning (15–29 Nov) | F2, cost thresholds, lead time, alert smoothing | done |
| Fairness & explainability (22 Nov–6 Dec) | subgroup audit, per-group thresholds, demographics sensitivity, SHAP, counterfactuals | done |
| Stakeholder feedback (29 Nov–6 Dec) | needs mentors/guide — not something code can do | owner |
| Prototype deployment & monitoring (6–20 Dec) | versioned artifacts, weekly batch scoring with alert policy, drift report; phase 2 below | done (benchmark prototype, `ml/longitudinal/score.py`) |

## 6. Phase 2 (after v3, needs institutional data)

Weekly institutional features (attendance by week, internal marks, submissions) built from the SEWS database by
the in-app training service, using the v3 feature definitions where the signal exists; trained per institution,
audited and approved through the existing model-approval workflow. Not started: it depends on real data access
(ethics approval, data-sharing agreement, DPDP Act basis).

## 7. Change log

| Date | Change | Reason |
|---|---|---|
| 2026-10-06 | Initial version, before any v3 code was run | — |
| 2026-10-06 (before any result) | Feature count corrected: 18 longitudinal features (11 activity + 7 assessment), not 19 | Counting error; the list in §3 is unchanged |
| 2026-10-08 | Status column updated after the run; results in [longitudinal-v3.md](../ml/longitudinal-v3.md) | — |
