"""Evaluation metrics for binary early-warning models.

Accuracy is deliberately not reported: with class imbalance and capacity-limited follow-up it
is misleading. Reported instead: ranking quality (ROC-AUC, PR-AUC as average precision),
threshold metrics (precision, recall, F1, confusion matrix, per-class metrics), capacity
metrics (precision/recall when the top k% are flagged), and calibration (Brier score,
expected calibration error, reliability table). Uncertainty: cluster bootstrap over students.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    precision_recall_curve,
    precision_recall_fscore_support,
    roc_auc_score,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
MetricFn = Callable[[IntArray, FloatArray], float]


def _check(y: IntArray, p: FloatArray) -> None:
    if y.shape != p.shape or y.ndim != 1 or y.size == 0:
        raise ValueError("y and p must be non-empty 1-D arrays of equal length")
    if not np.isin(y, (0, 1)).all():
        raise ValueError("y must contain only 0 and 1")
    if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError("p must be finite probabilities in [0, 1]")


def _bin_index(p: FloatArray, n_bins: int) -> IntArray:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    return np.clip(np.searchsorted(edges, p, side="right") - 1, 0, n_bins - 1).astype(np.int64)


def calibration_table(y: IntArray, p: FloatArray, n_bins: int = 10) -> list[dict[str, float | int]]:
    """Equal-width reliability table: mean predicted vs observed rate per probability bin."""
    _check(y, p)
    idx = _bin_index(p, n_bins)
    rows: list[dict[str, float | int]] = []
    for b in range(n_bins):
        mask = idx == b
        count = int(mask.sum())
        if count == 0:
            continue
        rows.append(
            {
                "bin_lower": b / n_bins,
                "bin_upper": (b + 1) / n_bins,
                "count": count,
                "mean_predicted": float(p[mask].mean()),
                "observed_rate": float(y[mask].mean()),
            }
        )
    return rows


def expected_calibration_error(y: IntArray, p: FloatArray, n_bins: int = 10) -> float:
    """Count-weighted mean |observed rate - mean predicted| over equal-width bins."""
    table = calibration_table(y, p, n_bins)
    n = y.size
    return float(sum(abs(r["observed_rate"] - r["mean_predicted"]) * r["count"] / n for r in table))


def best_f1_threshold(y: IntArray, p: FloatArray) -> float:
    """Probability threshold maximising F1. Choose it on VALIDATION data only."""
    _check(y, p)
    precision, recall, thresholds = precision_recall_curve(y, p)
    precision, recall = precision[:-1], recall[:-1]
    denom = precision + recall
    f1 = np.divide(2 * precision * recall, denom, out=np.zeros_like(denom), where=denom > 0)
    return float(thresholds[int(np.argmax(f1))])


def threshold_metrics(y: IntArray, p: FloatArray, threshold: float) -> dict[str, Any]:
    _check(y, p)
    y_hat = (p >= threshold).astype(np.int64)
    tn, fp, fn, tp = (int(v) for v in confusion_matrix(y, y_hat, labels=[0, 1]).ravel())
    prec, rec, f1, support = precision_recall_fscore_support(y, y_hat, labels=[0, 1], zero_division=0)
    return {
        "threshold": float(threshold),
        "precision": float(prec[1]),
        "recall": float(rec[1]),
        "f1": float(f1[1]),
        "false_positive_rate": fp / (fp + tn) if (fp + tn) else 0.0,
        "flagged_rate": float(y_hat.mean()),
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
        "per_class": {
            str(label): {
                "precision": float(prec[i]),
                "recall": float(rec[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i, label in enumerate((0, 1))
        },
    }


def top_fraction_metrics(y: IntArray, p: FloatArray, fraction: float) -> dict[str, float | int]:
    """Precision/recall when the ``fraction`` highest-risk units are flagged (capacity view)."""
    _check(y, p)
    if not 0 < fraction < 1:
        raise ValueError("fraction must be in (0, 1)")
    k = max(1, math.ceil(fraction * y.size))
    order = np.argsort(-p, kind="stable")[:k]
    tp = int(y[order].sum())
    positives = int(y.sum())
    return {
        "fraction": fraction,
        "flagged": k,
        "precision": tp / k,
        "recall": tp / positives if positives else 0.0,
    }


def evaluate(
    y: IntArray,
    p: FloatArray,
    *,
    threshold: float,
    top_fractions: Sequence[float],
    n_bins: int = 10,
) -> dict[str, Any]:
    """All headline metrics for one set of predictions."""
    _check(y, p)
    both_classes = 0 < int(y.sum()) < y.size
    return {
        "n": int(y.size),
        "positives": int(y.sum()),
        "prevalence": float(y.mean()),
        "mean_predicted": float(p.mean()),
        "roc_auc": float(roc_auc_score(y, p)) if both_classes else None,
        "pr_auc": float(average_precision_score(y, p)) if both_classes else None,
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, np.clip(p, 1e-15, 1 - 1e-15), labels=[0, 1])),
        "ece": expected_calibration_error(y, p, n_bins),
        "at_threshold": threshold_metrics(y, p, threshold),
        "top_fraction": [top_fraction_metrics(y, p, f) for f in top_fractions],
        "calibration_table": calibration_table(y, p, n_bins),
    }


def bootstrap_ci(
    y: IntArray,
    p: FloatArray,
    clusters: Sequence[str] | NDArray[Any],
    metrics: Mapping[str, MetricFn],
    *,
    iterations: int,
    seed: int,
    alpha: float = 0.05,
) -> dict[str, dict[str, float]]:
    """Percentile CIs from a cluster bootstrap (resampling students, not rows)."""
    _check(y, p)
    cluster_arr = np.asarray(clusters)
    if cluster_arr.shape != y.shape:
        raise ValueError("clusters must align with y")
    uniques, inverse = np.unique(cluster_arr, return_inverse=True)
    order = np.argsort(inverse, kind="stable")
    boundaries = np.searchsorted(inverse[order], np.arange(uniques.size + 1))
    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {name: [] for name in metrics}
    for _ in range(iterations):
        chosen = rng.integers(0, uniques.size, uniques.size)
        idx = np.concatenate([order[boundaries[c] : boundaries[c + 1]] for c in chosen])
        y_b, p_b = y[idx], p[idx]
        if y_b.min() == y_b.max():
            continue
        for name, fn in metrics.items():
            samples[name].append(fn(y_b, p_b))
    result: dict[str, dict[str, float]] = {}
    for name, values in samples.items():
        if len(values) < iterations * 0.9:
            raise RuntimeError(f"too many degenerate bootstrap resamples for {name}")
        arr = np.asarray(values)
        result[name] = {
            "low": float(np.quantile(arr, alpha / 2)),
            "high": float(np.quantile(arr, 1 - alpha / 2)),
            "resamples": int(arr.size),
        }
    return result


def subgroup_metrics(
    y: IntArray,
    p: FloatArray,
    groups: Sequence[str] | NDArray[Any],
    *,
    threshold: float,
    min_size: int = 100,
    min_positives: int = 10,
) -> list[dict[str, Any]]:
    """Disaggregated metrics per subgroup (audit only). Small groups are reported without metrics."""
    _check(y, p)
    group_arr = np.asarray(groups).astype(str)
    rows: list[dict[str, Any]] = []
    for value in sorted(set(group_arr.tolist())):
        mask = group_arr == value
        y_g, p_g = y[mask], p[mask]
        row: dict[str, Any] = {"group": value, "n": int(mask.sum()), "positives": int(y_g.sum())}
        if row["n"] < min_size or row["positives"] < min_positives or row["positives"] == row["n"]:
            row["insufficient_data"] = True
            rows.append(row)
            continue
        m = threshold_metrics(y_g, p_g, threshold)
        row.update(
            {
                "insufficient_data": False,
                "prevalence": float(y_g.mean()),
                "mean_predicted": float(p_g.mean()),
                "recall": m["recall"],
                "precision": m["precision"],
                "false_positive_rate": m["false_positive_rate"],
                "false_negative_rate": 1.0 - m["recall"],
                "flagged_rate": m["flagged_rate"],
                "pr_auc": float(average_precision_score(y_g, p_g)),
                "calibration_gap": float(p_g.mean() - y_g.mean()),
                "ece": expected_calibration_error(y_g, p_g),
            }
        )
        rows.append(row)
    return rows


DISPARITY_METRICS = (
    "recall",
    "precision",
    "false_positive_rate",
    "false_negative_rate",
    "pr_auc",
    "calibration_gap",
    "ece",
)


def disparity_summary(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Max - min of each metric across groups with sufficient data (None if fewer than two such groups)."""
    usable = [r for r in rows if not r.get("insufficient_data")]
    summary: dict[str, dict[str, Any]] = {}
    for metric in DISPARITY_METRICS:
        if len(usable) < 2:
            summary[metric] = {"gap": None, "min_group": None, "max_group": None}
            continue
        low = min(usable, key=lambda r: r[metric])
        high = max(usable, key=lambda r: r[metric])
        summary[metric] = {
            "gap": float(high[metric] - low[metric]),
            "min_group": low["group"],
            "max_group": high["group"],
        }
    return summary
