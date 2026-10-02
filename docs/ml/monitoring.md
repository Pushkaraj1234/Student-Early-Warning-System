# Model monitoring and drift

Status: statistics in `ml/monitoring/drift.py`; database job in `services/sews_services/jobs/monitoring.py`;
tables in migration `20260925001100_v4_registry_privacy_monitoring.sql`. Verified by `ml/tests/test_monitoring_and_fairness.py`,
`services/tests/test_jobs.py` and `supabase/tests/database/110_v4_registry_privacy_monitoring.sql`.

**Not yet scheduled:** the job runs from the command line
(`python -m sews_services.jobs monitor --model-registry-id <uuid>`, docs/architecture/deployment.md), but no
scheduler calls it yet. See "Remaining work".

## What is monitored

| Signal | Statistic | Warning | Critical |
|---|---|---:|---:|
| Feature distribution | Population stability index (PSI), 10 bins at reference quantiles, missing values ignored | ≥ 0.10 | ≥ 0.25 |
| Feature missingness | absolute change in the share of missing values | ≥ 0.05 | ≥ 0.15 |
| Prediction distribution | PSI of predicted probabilities | ≥ 0.10 | ≥ 0.25 |
| Outcome rate | absolute change in the adverse-outcome rate (labels only) | ≥ 0.05 | ≥ 0.10 |
| Performance | absolute PR-AUC drop vs the registry's validation PR-AUC (labels only) | ≥ 0.05 | ≥ 0.10 |

These thresholds are conventional heuristics (the PSI 0.10/0.25 rule of thumb), **not** validated SEWS limits.
They are constants in `ml/monitoring/drift.py`, used by both training reports and the database job.

A constant reference feature is compared as "equal to the reference value" vs "different", so PSI stays defined.

## Two places monitoring runs

1. **At training time** (`ml/training/train.py`): every model's report has a "Drift, training period vs test period"
   section and a `monitoring_snapshot_test` in `metrics.json`. This shows how much the benchmark itself shifts over
   time; it is not live monitoring.
2. **Live** (`monitor_window`): for one registered model and a window of **prediction dates in the institution's
   time zone** (the scoring job dates predictions in that zone; callers must use it too).

## The live job, step by step

1. Load the window's predictions and, where present, their feature snapshots. Snapshots are joined through
   `private.ml_subject_map` and contain no identity fields; predictions without a snapshot still count.
2. Snapshot (aggregates only): number of predictions, count per risk level, probability quantiles
   (p10/p25/p50/p75/p90) and per-feature missing rate, mean, standard deviation, p10/p50/p90.
   Written to `public.model_monitoring_snapshots` (unique per model and window; a window is monitored once).
3. Labels (label-time performance). A prediction's academic label is known only when results are published:
   - `1` if the student withdrew from, or received F/Ab in, any course of the term containing the prediction;
   - `0` if every course of that term has a published result and none is adverse;
   - unknown otherwise (never guessed). Summer terms are not labelled.
4. Performance (PR-AUC, ROC-AUC, Brier, ECE) when at least **50** labels with both classes exist, compared with
   `validation_metrics.validation.pr_auc` in the model registry → `performance_drop` alerts.
5. With a reference window: feature PSI and missingness, prediction PSI, and (with ≥ 50 labels in both windows)
   outcome-rate change → `public.drift_alerts`, linked to the snapshot.
6. Any critical alert also writes a `public.system_events` row (`component = monitoring`,
   `event_type = drift_alert`) with counts only.

## Who sees what

| Object | Access |
|---|---|
| `model_monitoring_snapshots`, `drift_alerts` | Readable by authenticated users who can see the model's registry row (admins of the model's institution, and global models). Written only by the service role. |
| `system_events` | Admins only, for their institution or global events. The database rejects identity keys in `details`. |
| Acknowledging an alert | `public.acknowledge_drift_alert(id)`: admin of the model's institution; only `open` alerts; records who and when. |
| Mobile admin screen | Registered models, open alerts with Acknowledge, recent windows (counts only). |

## What monitoring does not do

- It does not retrain, recalibrate, roll back or retire a model. Those are human decisions recorded in the
  model registry (lifecycle enforced by the database).
- It does not look at individual students; every stored statistic is an aggregate.
- It cannot detect problems in groups smaller than the window's sample, and thresholds are not validated.

## Remaining work

- A schedule for the command-line runner (its defaults: a 7-day window ending yesterday in the institution's time
  zone, with the previous 7 days as reference). Where it runs is an owner decision (it needs the service-role
  database connection).
- Subgroup (fairness) monitoring on live data needs audit attributes that the institutional schema does not hold yet.
