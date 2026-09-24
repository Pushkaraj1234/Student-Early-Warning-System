# Problem Definition

> Status: **DRAFT v0.1**. The label and horizon choices in §3–§4 are **[OPEN]** and must be confirmed before any model is trained.

## 1. Problem statement

Students who later struggle academically often show earlier, observable signals: falling attendance, missed or late submissions, low early assessment scores and reduced engagement with learning platforms. Institutions usually find out at the end of the term, when it is too late for a low-cost intervention.

SEWS aims to surface these signals **early enough to act**. It explains them in terms a mentor can check, and it records which interventions were tried and what followed.

## 2. Decision context

- A mentor or counsellor has **limited capacity** (for example, they can meet *k* students per week).
  The practical task is therefore **ranking and prioritisation under a capacity constraint**, not just binary classification.
- A human always reviews a flagged student before any intervention.
- A false negative (a missed student) and a false positive (an unnecessary check-in) have different costs.
  A supportive check-in is usually low-cost, but repeated flagging can stigmatise a student.

## 3. Formal prediction task

For student *s*, enrolled in term *T*, at decision point (cutoff) *t*:

- **Inputs:** only information whose *event time* is ≤ *t* and which would have been **available in the system at *t***. Late-arriving data counts only from the moment it arrives, not from the event date.
- **Output:** p̂(s, t) = the estimated probability that the adverse outcome *Y* occurs in the outcome window (*t*, *t* + *h*].
- **Label *Y*** — candidate definitions (**[OPEN]**, choose one primary label):

  | Candidate | Definition | Notes |
  |---|---|---|
  | Y1 course failure | Fails ≥ 1 enrolled course at the end of term *T* | Needs final results per course |
  | Y2 term GPA drop | Term GPA below an institution-defined threshold | The threshold must come from institution policy, not be chosen after seeing results |
  | Y3 attendance shortfall | Final attendance below the institution's eligibility threshold | The threshold is institution-specific. The label is close to the attendance features, so leakage controls are critical |
  | Y4 withdrawal | Withdraws or de-registers before the end of term | Rarer; class imbalance |

- **Horizon *h*:** normally "until the end of term *T*". **[OPEN]**
- **Decision points *t*:** a fixed schedule, for example weeks 2, 4, 6 and 8 of the term. **[OPEN]** One model per decision point, or one model with "weeks elapsed" as a feature, will be decided by experiment (see the ML strategy).

## 4. Leakage definition (applies to every experiment)

A feature leaks if it uses information that would **not** have been available at the cutoff *t*. Examples:

- Final marks, end-of-term attendance, or any aggregate computed over the whole term.
- Registration or unregistration dates that fall after *t*. For example, an unregistration date directly reveals withdrawal.
- Assessments whose submission or grading date is after *t*, including grades that were *released* after *t*.
- Normalisation statistics or imputation values fitted on the full dataset, including test data.
- Random row-level splits in which the same student, or a later term, appears in training while an earlier term is tested.

The required control is to compute features through a single **as-of** feature function that takes `(student, cutoff)` as input. Evaluation must be **out-of-time**: train on earlier cohorts or terms and test on later ones.

## 5. What the system is not

- It is not a diagnosis of ability, motivation or character.
- It is not a causal model. It does **not** show that changing a feature (e.g. attendance) will change the outcome.
- It does not establish intervention effectiveness. Observational intervention logs are confounded, because students chosen for intervention differ from those who were not. See RQ6.

## 6. Constraints

| Constraint | Consequence |
|---|---|
| Privacy (DPDP Act, 2023; institutional policy) | Data minimisation; purpose limitation; consent records; restricted access to protected attributes |
| Fairness | Performance and calibration must be reported per subgroup, where lawful and where the data exists |
| Interpretability | Mentors must be able to check each flagged factor against source data |
| Class imbalance | Use PR-AUC, recall at capacity and calibration. Accuracy alone is not acceptable |
| Distribution shift | Benchmark datasets differ from Indian institutions in curriculum, grading, attendance rules and platform usage |

## 7. Ethical risks

- **Self-fulfilling prophecy and labelling.** Mentors may treat flagged students differently. Mitigations: supportive framing; no score shown without explanation and context; "signal" wording.
- **Feedback loops.** Interventions change outcomes, which contaminates future training labels. Intervention status must be recorded so it can be modelled or excluded.
- **Proxy discrimination.** Features such as region or socio-economic indicators can act as proxies for protected characteristics. Protected attributes are excluded from model inputs by default; fairness audits use them only under restricted access.
- **Student-facing scores (**[OPEN]**).** These can motivate some students and demoralise others. Default: students are not shown a raw probability.

## 8. Success criteria for the ML component

Success is defined **before** any results are seen, and applies to held-out, out-of-time data:

1. It beats the baselines (prevalence, a simple attendance/marks rule, and logistic regression) on PR-AUC and on recall at the capacity *k*.
2. It is calibrated, with reported Brier score and reliability curve. A calibration step is applied if needed.
3. Subgroup gaps in recall at capacity and in calibration are reported. Whether they are acceptable is judged against thresholds agreed with stakeholders.
4. Explanations are stable: similar students receive similar top factors (see RQ3).
