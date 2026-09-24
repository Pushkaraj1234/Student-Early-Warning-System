# Research Questions

> Status: **DRAFT v0.1**. Each question lists the data it needs. A question must not be reported as answered using a data class that cannot support it (see `project-scope.md` §6).

## RQ1 — Earliness vs accuracy

**How early in a term can the model provide a useful risk signal?**

- Method: evaluate the model at each decision point *t* (e.g. weeks 2, 4, 6 and 8) on out-of-time test cohorts. Plot PR-AUC and recall at capacity against *t*.
- Data: `benchmark` (method development); `institutional` (for any claim about the institution).
- Cannot claim: that earliness curves from benchmark data apply to Indian institutions.

## RQ2 — Feature family contribution

**Which families of signals add predictive value over prior academic record alone?**
The families are attendance, assessment, engagement (LMS) and prior academic record.

- Method: ablation of each feature family, measured on the same out-of-time split. Report confidence intervals, e.g. using a bootstrap over students.
- Cannot claim: that a family is *causally* important.

## RQ3 — Explanation quality and stability

**Are SHAP-based explanations stable, and do mentors find them actionable?**

- Method: measure the stability of each student's top-k factors under retraining with different seeds, and under small input perturbations. Then run a small usability study with mentors, only with ethics approval.
- Cannot claim: that attributions reflect causal mechanisms.

## RQ4 — Fairness

**Do recall at capacity and calibration differ across subgroups?**
Subgroups could include gender, first-generation status or rural/urban origin, where lawful and available.

- Method: disaggregated metrics with uncertainty intervals, then evaluation of mitigations (e.g. group-aware thresholds) with their trade-offs documented.
- Data: subgroup attributes accessed only under the restricted-access rules in `security-model.md`.

## RQ5 — Transfer to the Indian institutional context

**How much does a model developed on non-Indian benchmark data degrade when applied to Indian institutional data, and how much does local retraining recover?**

- Method: train on benchmark data and evaluate on institutional data. Compare with training and evaluating on institutional data using an out-of-time split. Note: the feature spaces will differ, so only a shared feature subset can be compared.
- Data: requires `institutional` data. **This question cannot be answered, or partly answered, without it.**

## RQ6 — Intervention outcomes (observational)

**What outcomes follow the logged interventions?**

- Method: descriptive analysis only, unless a designed study is approved. Examples of designed studies: randomised encouragement, or a stepped-wedge rollout.
- Cannot claim: that an intervention *caused* an improvement, based on observational logs alone.

## RQ7 — Student-facing feedback (conditional)

**If students are shown their own signals, how does that affect engagement and wellbeing?**

- Only pursued if the project owner decides students may see their own signals, and ethics approval covers it.

## Reporting rules

- Always state the data class (`benchmark`, `synthetic` or `institutional`) next to every number.
- Always state the split type (out-of-time, and grouped by student) and the decision point.
- Report baselines alongside every model result.
- Results on `synthetic` data are never reported as model performance.
