# Federated learning — design note (no prototype)

Status 2026-10-02. Decision: **not built.** The plan asked for a design and a prototype only if justified;
it is not justified today. This note records why, and what a future design would have to satisfy.

## The question it would answer

Several institutions want a better model than any one of them can train alone, but must not pool raw student
records. Federated learning trains one model by sending model updates, not data, between institutions and a
coordinator.

## Why not now

1. **There is no institutional training data at all.** SEWS has no model trained on Indian institutional data
   (docs/ml/results-v2.md); the first step is one institution's own model, validated on its own cohorts.
   Federation solves a problem that only appears once two or more institutions have usable data.
2. **One institution at a time is the deployment model.** Every table, policy and job is scoped by
   `institution_id`, and registry models can be institution-specific. Nothing requires cross-institution
   training to work.
3. **Benefit is unproven.** On the benchmark, ranking transferred between modules of one university with
   small losses, but calibration did not (ECE worsened by up to 0.151; docs/ml/results-v2.md). Institutions
   differ more than modules do (attendance rules, grading, LMS use), so a shared model would still need
   per-institution calibration and validation — the part that federation does not remove.
4. **Cost and risk are high.** It needs a coordinator service, secure aggregation, update-level privacy
   protection (model updates can leak training data), agreements between institutions, and an evaluation
   protocol across non-identical data. Each is a new attack surface for a small expected gain.

## Lower-cost alternatives, in order

1. **Per-institution models** trained on the institution's own history with the existing pipeline, registry
   and approval lifecycle.
2. **Shared method, not shared data**: institutions reuse the feature definitions, training code, leakage
   guard and evaluation reports; only code and aggregate metrics cross institutional boundaries.
3. **Shared aggregate monitoring**: comparing identity-free monitoring snapshots (already aggregate-only) to
   see whether institutions behave alike before considering any joint model.

## If it is ever justified — minimum requirements

- At least two institutions with validated single-institution models and a written data-sharing/processing
  agreement; an owner decision on who runs the coordinator.
- Model families that federate simply: logistic regression (federated averaging of coefficients) first;
  gradient-boosted trees only with a vetted federated-GBDT library and a security review.
- Secure aggregation (the coordinator sees only the sum of updates) and differential-privacy noise on updates,
  with the privacy budget recorded in the model registry alongside the existing version fields.
- Same feature version at every site (the scoring job already refuses mismatched feature versions), and each
  site keeps its own held-out cohort for out-of-time validation, calibration and the subgroup audit
  (docs/ml/fairness.md) before its admin may approve the shared model for local use.
- Evaluation must compare the federated model with each site's own model on that site's data; adopt it only
  where it is better and no subgroup gets worse.
