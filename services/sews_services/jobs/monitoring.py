"""Model monitoring: per-window snapshots, drift alerts and label-time performance.

For one registered model and a window [start, end] of prediction dates:
  * snapshot   n, risk-level distribution, probability quantiles, per-feature aggregates
               (ml.monitoring.drift.monitoring_snapshot; aggregates only, never identifiers)
  * drift      compared with a reference window: feature PSI and missingness, prediction PSI,
               outcome-rate change -> public.drift_alerts (thresholds in ml/monitoring/drift.py)
  * labels     institutional academic label, known only once results are published: 1 if the student
               withdrew from, or received F/Ab in, any course of the term containing the prediction;
               0 if every course of that term has a published passing result. Performance (PR-AUC,
               ROC-AUC, Brier, ECE) is computed when >= MIN_LABELS labels with both classes exist and
               compared with the registry's validation PR-AUC (performance_drop alerts).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ml.evaluation.metrics import expected_calibration_error
from ml.monitoring.drift import (
    DriftAlert,
    clean_for_json,
    feature_drift,
    monitoring_snapshot,
    outcome_drift,
    performance_drop,
    prediction_drift,
)
from sews_services.db import Connection, record_system_event

MIN_LABELS = 50

WINDOW_SQL = """
select p.student_id::text as student_id, p.prediction_date, p.risk_probability::float8 as risk_probability,
       p.risk_level, fs.features
from public.risk_predictions p
left join private.ml_subject_map m on m.student_id = p.student_id
left join private.feature_snapshots fs
  on fs.ml_subject_id = m.ml_subject_id and fs.as_of = p.scored_at and fs.feature_version = p.feature_version
where p.model_registry_id = %(model)s and p.prediction_date between %(start)s and %(end)s
"""

LABEL_SQL = """
select sc.student_id::text as student_id,
       bool_or(sc.status = 'withdrawn' or (sc.result_published_at is not null and sc.grade in ('F', 'Ab')))
         as adverse,
       bool_and(sc.status = 'withdrawn' or sc.result_published_at is not null) as all_known
from public.student_courses sc
join public.academic_terms t
  on t.institution_id = sc.institution_id and t.academic_year = sc.academic_year
 and t.term in ('odd', 'even') and (sc.semester %% 2 = 1) = (t.term = 'odd')
where sc.student_id = any(%(students)s::uuid[]) and %(day)s between t.starts_on and t.ends_on
group by sc.student_id
"""


@dataclass
class MonitoringResult:
    snapshot_id: str | None
    n_predictions: int
    labels_available: int
    alerts: list[DriftAlert]


def _window(conn: Connection, model_id: str, start: date, end: date, names: list[str] | None = None) -> pd.DataFrame:
    """Predictions of the window with their feature vectors; ``names`` defaults to every feature seen."""
    rows = conn.execute(WINDOW_SQL, {"model": model_id, "start": start, "end": end}).fetchall()
    frame = pd.DataFrame(rows, columns=["student_id", "prediction_date", "risk_probability", "risk_level", "features"])
    if names is None:
        names = sorted({k for f in frame["features"] if f for k in f})
    feats = pd.DataFrame([{n: (f or {}).get(n) for n in names} for f in frame["features"]], columns=names, dtype=float)
    out = pd.concat([frame.drop(columns="features").reset_index(drop=True), feats], axis=1)
    out.attrs["feature_names"] = names
    return out


def _labels(conn: Connection, window: pd.DataFrame) -> pd.Series:
    """Label per prediction row (NaN while unknown)."""
    labels = pd.Series(np.nan, index=window.index)
    for day, group in window.groupby("prediction_date"):
        rows = conn.execute(LABEL_SQL, {"students": group["student_id"].tolist(), "day": day}).fetchall()
        known = {r["student_id"]: float(r["adverse"]) for r in rows if r["adverse"] or r["all_known"]}
        labels.loc[group.index] = group["student_id"].map(known).astype(float)
    return labels


def _performance(y: np.ndarray, p: np.ndarray) -> dict[str, float] | None:
    if y.size < MIN_LABELS or y.min() == y.max():
        return None
    return {
        "n": float(y.size),
        "pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "ece": expected_calibration_error(y, p),
    }


def monitor_window(
    conn: Connection,
    *,
    model_registry_id: str,
    window: tuple[date, date],
    reference: tuple[date, date] | None = None,
) -> MonitoringResult:
    """``window`` and ``reference`` are inclusive ranges of prediction dates, which the scoring job
    records in the institution's local time zone; callers must derive them in that zone too."""
    model = conn.execute(
        "select id::text as id, feature_version, validation_metrics, institution_id::text as institution_id "
        "from public.model_registry where id = %s",
        (model_registry_id,),
    ).fetchone()
    if model is None:
        raise LookupError("model is not registered")
    current = _window(conn, model_registry_id, window[0], window[1])
    names: list[str] = current.attrs["feature_names"]
    if current.empty:
        return MonitoringResult(None, 0, 0, [])

    probs = current["risk_probability"].to_numpy(dtype=float)
    snap = monitoring_snapshot(probs, current["risk_level"].tolist(), current, names)
    labels = _labels(conn, current)
    known = labels.notna().to_numpy()
    perf = _performance(labels[known].to_numpy(dtype=int), probs[known])

    alerts: list[DriftAlert] = []
    if perf is not None:
        reference_pr_auc = ((model["validation_metrics"] or {}).get("validation") or {}).get("pr_auc")
        if reference_pr_auc is not None:
            alerts += performance_drop(float(reference_pr_auc), perf["pr_auc"])
    if reference is not None:
        ref = _window(conn, model_registry_id, reference[0], reference[1], names)
        if not ref.empty:
            alerts += feature_drift(ref, current, names)[1]
            alerts += prediction_drift(ref["risk_probability"].to_numpy(dtype=float), probs)[1]
            ref_labels = _labels(conn, ref).dropna()
            if len(ref_labels) >= MIN_LABELS and known.sum() >= MIN_LABELS:
                alerts += outcome_drift(float(ref_labels.mean()), float(labels[known].mean()))

    inserted = conn.execute(
        """insert into public.model_monitoring_snapshots
             (model_registry_id, window_start, window_end, n_predictions, level_distribution,
              probability_quantiles, feature_stats, labels_available, performance)
           values (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb)
           on conflict (model_registry_id, window_start, window_end) do nothing
           returning id::text as id""",
        (
            model_registry_id,
            window[0],
            window[1],
            snap["n_predictions"],
            json.dumps(snap["level_distribution"]),
            json.dumps(snap["probability_quantiles"]),
            json.dumps(clean_for_json(snap["feature_stats"])),
            int(known.sum()),
            json.dumps(perf) if perf is not None else None,
        ),
    ).fetchone()
    if inserted is None:  # this window was already monitored; do not duplicate alerts
        conn.rollback()
        return MonitoringResult(None, snap["n_predictions"], int(known.sum()), [])
    for a in alerts:
        conn.execute(
            """insert into public.drift_alerts
                 (model_registry_id, monitoring_snapshot_id, alert_type, subject, statistic, value, threshold, severity)
               values (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                model_registry_id,
                inserted["id"],
                a.alert_type,
                a.subject,
                a.statistic,
                a.value,
                a.threshold,
                a.severity,
            ),
        )
    critical = sum(a.severity == "critical" for a in alerts)
    if critical:
        record_system_event(
            conn,
            "monitoring",
            "drift_alert",
            "critical",
            {"alerts": len(alerts), "critical": critical, "window_end": window[1].isoformat()},
            model["institution_id"],
        )
    conn.commit()
    return MonitoringResult(inserted["id"], snap["n_predictions"], int(known.sum()), alerts)


def summary(result: MonitoringResult) -> dict[str, Any]:
    return {
        "n_predictions": result.n_predictions,
        "labels_available": result.labels_available,
        "alerts": [a.as_dict() for a in result.alerts],
    }
