"""Evaluation helpers for the v3 experiment: headline metrics, metrics by week, fast cluster-bootstrap
PR-AUC (average precision) and paired comparisons, and equal-opportunity thresholds.

The cluster bootstrap resamples STUDENTS (a student contributes many student-weeks and may have several
registrations), using ``ml.analysis.hypotheses.cluster_weights``; p-values use ``bootstrap_p``
(definition fixed in the week 4 change log).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ml.analysis.hypotheses import bootstrap_p, cluster_weights
from ml.evaluation.metrics import expected_calibration_error

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
ALPHA = 0.05


class RankedScores:
    """Average precision for many row-weight vectors over fixed predictions (sorted once).

    Equals ``sklearn.metrics.average_precision_score(y, p, sample_weight=w)``: thresholds at distinct
    scores, AP = sum over thresholds of (recall increase) x precision.
    """

    def __init__(self, y: IntArray, p: FloatArray) -> None:
        if y.shape != p.shape:
            raise ValueError("y and p must align")
        self._order = np.argsort(-p, kind="stable")
        self._y = y[self._order].astype(np.float64)
        sorted_p = p[self._order]
        self._last = np.r_[np.flatnonzero(np.diff(sorted_p) != 0), sorted_p.size - 1]

    def ap(self, w: FloatArray) -> float:
        ws = w[self._order]
        tp = np.cumsum(ws * self._y)[self._last]
        fp = np.cumsum(ws * (1.0 - self._y))[self._last]
        positives = tp[-1]
        if positives <= 0:
            return float("nan")
        flagged = tp + fp
        precision = np.divide(tp, flagged, out=np.zeros_like(tp), where=flagged > 0)
        recall_gain = np.diff(np.r_[0.0, tp / positives])
        return float(np.sum(recall_gain * precision))


def headline(y: IntArray, p: FloatArray) -> dict[str, Any]:
    both = 0 < int(y.sum()) < y.size
    return {
        "n": int(y.size),
        "positives": int(y.sum()),
        "prevalence": float(y.mean()),
        "pr_auc": float(average_precision_score(y, p)) if both else None,
        "roc_auc": float(roc_auc_score(y, p)) if both else None,
        "brier": float(brier_score_loss(y, p)),
        "ece": expected_calibration_error(y, p),
    }


def by_week(weeks: IntArray, y: IntArray, p: FloatArray) -> list[dict[str, Any]]:
    rows = []
    for week in np.unique(weeks):
        mask = weeks == week
        yw = y[mask]
        both = 0 < int(yw.sum()) < yw.size
        rows.append(
            {
                "week": int(week),
                "n": int(mask.sum()),
                "prevalence": float(yw.mean()),
                "pr_auc": float(average_precision_score(yw, p[mask])) if both else None,
                "roc_auc": float(roc_auc_score(yw, p[mask])) if both else None,
            }
        )
    return rows


def bootstrap_ap(
    y: IntArray, predictions: Mapping[str, FloatArray], clusters: NDArray[Any], *, resamples: int, seed: int
) -> dict[str, FloatArray]:
    """Bootstrap AP samples per model, all models on the SAME resamples (so differences are paired)."""
    ranked = {name: RankedScores(y, p) for name, p in predictions.items()}
    samples: dict[str, list[float]] = {name: [] for name in predictions}
    for w in cluster_weights(np.asarray(clusters), resamples, seed):
        for name, r in ranked.items():
            samples[name].append(r.ap(w))
    return {name: np.asarray(v, dtype=np.float64) for name, v in samples.items()}


def interval(samples: FloatArray) -> tuple[float, float]:
    low, high = np.nanquantile(samples, [ALPHA / 2, 1 - ALPHA / 2])
    return float(low), float(high)


def paired_comparison(
    observed: float, samples_a: FloatArray, samples_b: FloatArray, *, two_sided: bool
) -> dict[str, Any]:
    """Effect a - b with a bootstrap CI and p-value (H0: effect <= 0, or = 0 if two-sided)."""
    effects = samples_a - samples_b
    low, high = interval(effects)
    return {
        "effect": float(observed),
        "ci_low": low,
        "ci_high": high,
        "p_value": bootstrap_p(effects, two_sided=two_sided),
        "two_sided": two_sided,
        "resamples": int(effects.size),
    }


def student_rate_bootstrap(
    outcome_a: NDArray[np.bool_],
    outcome_b: NDArray[np.bool_],
    eligible: NDArray[np.bool_],
    clusters: NDArray[Any],
    *,
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    """Paired bootstrap of the difference of two rates (e.g. false-alarm rates of two alert policies) over the
    ``eligible`` registrations; one-sided H0: rate_a - rate_b <= 0."""
    a = outcome_a.astype(np.float64) * eligible
    b = outcome_b.astype(np.float64) * eligible
    e = eligible.astype(np.float64)
    observed = float(a.sum() / e.sum() - b.sum() / e.sum())
    effects = []
    for w in cluster_weights(np.asarray(clusters), resamples, seed):
        denom = float(w @ e)
        effects.append((float(w @ a) - float(w @ b)) / denom)
    arr = np.asarray(effects)
    low, high = interval(arr)
    return {
        "rate_a": float(a.sum() / e.sum()),
        "rate_b": float(b.sum() / e.sum()),
        "effect": observed,
        "ci_low": low,
        "ci_high": high,
        "p_value": bootstrap_p(arr, two_sided=False),
        "two_sided": False,
        "resamples": int(arr.size),
    }


def equal_opportunity_thresholds(
    y: IntArray, p: FloatArray, groups: Sequence[str] | NDArray[Any], target_recall: float
) -> dict[str, float]:
    """Per-group thresholds giving each group (approximately) ``target_recall`` on these rows (validation)."""
    g = np.asarray(groups).astype(str)
    out: dict[str, float] = {}
    for value in sorted(set(g.tolist())):
        positives = p[(g == value) & (y == 1)]
        if positives.size == 0:
            continue
        out[value] = float(np.quantile(positives, 1.0 - target_recall, method="lower"))
    return out


def group_recall_gap(
    y: IntArray, flagged: NDArray[np.bool_], groups: NDArray[Any], a: str, b: str
) -> dict[str, float]:
    """Recall and false-positive rate of groups ``a`` and ``b`` and the recall gap (b - a)."""
    g = np.asarray(groups).astype(str)
    recall = {v: float(flagged[(g == v) & (y == 1)].mean()) for v in (a, b)}
    fpr = {v: float(flagged[(g == v) & (y == 0)].mean()) for v in (a, b)}
    return {
        f"recall_{a}": recall[a],
        f"recall_{b}": recall[b],
        "recall_gap": recall[b] - recall[a],
        f"fpr_{a}": fpr[a],
        f"fpr_{b}": fpr[b],
        "precision": float(y[flagged].mean()) if flagged.any() else float("nan"),
        "flagged_rate": float(flagged.mean()),
    }
