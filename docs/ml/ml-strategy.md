# ML Strategy

> Status: **PROPOSED v0.1**. No model has been trained. No performance numbers exist, and none may be quoted until produced by the evaluation protocol below.

## 1. Data tiers and their permitted use

| Tier | Candidate sources | Use | Forbidden |
|---|---|---|---|
| `benchmark` | Open University Learning Analytics Dataset (OULAD, **UK**); UCI "Student Performance" (**Portugal**, secondary schools); UCI "Predict Students' Dropout and Academic Success" (**Portugal**, higher education) | Developing and comparing methods; testing the leakage-safe pipeline | Describing these as Indian data; claiming results transfer to Indian students |
| `synthetic` | A project generator driven by explicit, documented assumptions | Pipeline tests; UI development; RLS and load testing | Reporting as model performance; describing as real student data |
| `institutional` | A partner Indian institution, under a data-sharing agreement, ethics approval and consent | Institution-specific models; RQ5 | Use before governance prerequisites are met (see the security model) |

Each dataset is registered in `dataset_versions` with its provenance, a source description (including URL and access date), its licence and a content hash **at acquisition time**. Licence terms and dataset sizes must be checked against the source when downloaded, not assumed from this document.

**Suitability notes:**
- **OULAD** has dated VLE clicks and assessment submissions. This makes it the best benchmark for **as-of / decision-point** experiments.
- The **UCI Student Performance** data has no within-term timestamps. It can only support a coarse "before term / after first-period grade" setup, and it must **not** be used for earliness claims.

## 2. Target and decision points

Per `problem-definition.md` §3: one primary label (**[OPEN]**), decision points *t* ∈ {e.g. week 2, 4, 6, 8}, horizon = end of term.

For OULAD the proposed mapping is: `final_result ∈ {Fail, Withdrawn}` → 1, `{Pass, Distinction}` → 0, with cutoffs measured in days from the module start. Withdrawn students whose `date_unregistration` ≤ *t* are **excluded** at that cutoff, because they have already left and there is nothing left to predict.

## 3. Leakage controls (mandatory)

1. **A single as-of feature function** `build_features(entity, cutoff, sources) -> FeatureVector`, shared between training and serving.
2. Only records with `available_time ≤ cutoff` are used. For assessment results, `available_time = max(submitted, released)` where both are known.
3. **Out-of-time split:** train on earlier presentations or terms, validate on the next one, test on the latest. For OULAD, for example, train on the 2013 presentations and test on the 2014 presentations of the same modules.
4. **Grouping:** no student appears in both train and test in a way that lets a later outcome inform an earlier prediction.
5. Preprocessing (imputers, scalers, encoders, calibrators) is fitted **inside** the training fold only, using `sklearn.pipeline.Pipeline`.
6. Hyperparameters are tuned on the validation period only. **The test period is touched once**, for the final report.
7. **Automated leakage tests:**
   - Unit tests assert that no feature changes when records dated after the cutoff are added.
   - A "shuffled-future" test: replace all post-cutoff data with noise and check that the features are identical.
8. **Label-proximity audit:** flag any single feature with implausibly high univariate AUC, then investigate it before use.

## 4. Models

| Model | Role |
|---|---|
| Prevalence (constant) | Floor baseline |
| Rule baseline (e.g. attendance below the institution threshold, or failed first assessment) | The "what institutions already do" baseline. The threshold comes from institution policy |
| Logistic regression (regularised) | Interpretable baseline |
| XGBoost (`XGBClassifier`) | Primary candidate |
| Calibrated wrapper (`CalibratedClassifierCV`, isotonic or sigmoid, fitted on the validation period) | Applied if the reliability curve shows miscalibration |

Class imbalance is handled with `scale_pos_weight` or class weights, and threshold choice happens **after** calibration. Resampling (e.g. SMOTE) is not the default. If used, it must happen strictly inside training folds.

## 5. Evaluation protocol

Reported on the held-out, out-of-time **test** period, for each decision point:

- **Ranking:** PR-AUC (primary, because of imbalance) and ROC-AUC (secondary).
- **Operational:** recall and precision at capacity *k* (the top *k* %), which matches mentor capacity.
- **Calibration:** Brier score, reliability diagram and expected calibration error (binning documented).
- **Uncertainty:** 95 % bootstrap confidence intervals, resampling students.
- **Subgroups:** the metrics above per subgroup where lawful and available (RQ4), with uncertainty intervals.
- **Baselines:** always reported next to the candidate model.

A model may be set to `approved` in `model_versions` only when:
1. It beats the rule baseline and logistic regression on PR-AUC and recall at capacity, **with non-overlapping or clearly separated confidence intervals**. The criterion is agreed before testing.
2. Calibration is acceptable.
3. Subgroup gaps have been reviewed and documented.
4. A model card is written.
5. It was evaluated on data of the **same provenance tier** it will score. A model validated only on benchmark data is never approved to score real students.

## 6. Risk bands

(Implemented v1: four levels `stable`, `watch`, `elevated`, `high`, at the 50th/75th/90th percentiles of
validation-period calibrated probability — see docs/ml/baseline-results-v1.md.)

A calibrated probability is mapped to a risk level using thresholds that are:
- chosen on the **validation** period, from capacity and cost considerations agreed with the institution;
- stored with the model version, not hard-coded in the app.

The app shows the band and the explanation. Showing a raw probability to staff is **[OPEN]**. Students are not shown one by default.

## 7. Explanations

- **SHAP:** `TreeExplainer` for XGBoost, computed on the model's raw margin output. For each prediction, store the top-k factors as `{feature, value, direction, contribution}` in `risk_predictions.explanation`.
- Every factor maps to human-readable text and to a source value the mentor can check. For example, "Attendance in last 14 days: 45 % (threshold used by model: none; this is an association)".
- Explanations are described as **associations with the model output**, never as causes.
- **Stability checks** (RQ3): top-k overlap across retraining seeds.

## 8. Interventions: recommendation logic

- The intervention recommendations are **rule-based**. They map explanation factor categories (attendance, assessment, engagement) to catalogue entries in `intervention_types.related_factors`.
- A mentor always chooses. Recommendations are suggestions only.
- Effectiveness claims require a designed study (RQ6).

## 9. Versioning and reproducibility

Each training run records:
- `model_version`, `dataset_version` (with content hash), `feature_version` (with definition hash);
- `trained_at` (UTC), the git commit SHA, the Python and library versions;
- random seeds, the hyperparameters, and the split definition (the date ranges or presentations used).

The artifacts are the serialised pipeline, a JSON metrics file, and the model card (intended use, data, metrics, subgroup results, limitations, ethical considerations).

## 10. Monitoring (after deployment)

- Input drift, per feature, compared with the training distribution.
- Score distribution drift, and the share of students in each band.
- Delayed label feedback: realised outcomes at term end → recalibration check.
- Intervention contamination: flagged students who received interventions are tracked separately in performance monitoring.
- Any retraining creates a new version and goes through the approval criteria again.
