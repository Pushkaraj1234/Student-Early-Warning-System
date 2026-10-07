"""Decision thresholds, weekly alert policies and student-level alert metrics.

Thresholds are chosen on VALIDATION data only. Alert policies turn a weekly risk series into alerts:
  ``raw``           alert in week k if risk_k >= threshold
  ``consecutive_2`` alert in week k if risk_k and risk_{k-1} are both >= threshold (a persistent signal)
  ``ewma``          alert in week k if the smoothed risk s_k = a*risk_k + (1-a)*s_{k-1} >= threshold
                    (s at a registration's first panel week = its risk)
Student-level view (one registration = one student-course): an adverse registration is detected if it is
alerted at least once while still in the panel (i.e. before withdrawing); a non-adverse registration that is
ever alerted is a false alarm. Lead time = weeks from the first alert to the withdrawal week (withdrawals) or
to the course's last week (failures).
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.metrics import precision_recall_curve

AlertPolicy = Literal["raw", "consecutive_2", "ewma"]
ALERT_POLICIES: tuple[AlertPolicy, ...] = ("raw", "consecutive_2", "ewma")
EWMA_ALPHA = 0.5
GROUP = ["context_id", "student_id"]


def fbeta_threshold(y: NDArray[np.int64], p: NDArray[np.float64], beta: float) -> float:
    """Threshold maximising F-beta (beta > 1 weighs recall more)."""
    precision, recall, thresholds = precision_recall_curve(y, p)
    precision, recall = precision[:-1], recall[:-1]
    b2 = beta**2
    denom = b2 * precision + recall
    score = np.divide((1 + b2) * precision * recall, denom, out=np.zeros_like(denom), where=denom > 0)
    return float(thresholds[int(np.argmax(score))])


def cost_threshold(y: NDArray[np.int64], p: NDArray[np.float64], *, cost_fn: float, cost_fp: float) -> float:
    """Threshold minimising cost_fn * FN + cost_fp * FP (flag when risk >= threshold)."""
    order = np.argsort(-p, kind="stable")
    p_sorted, y_sorted = p[order], y[order]
    # Flagging the top i rows: candidate thresholds at distinct risk values (ties flagged together).
    last_of_value = np.r_[np.flatnonzero(np.diff(p_sorted) != 0), p_sorted.size - 1]
    tp = np.cumsum(y_sorted)[last_of_value]
    fp = (last_of_value + 1) - tp
    fn = int(y.sum()) - tp
    cost = cost_fn * fn + cost_fp * fp
    flag_none = cost_fn * int(y.sum())
    best = int(np.argmin(cost))
    if flag_none <= cost[best]:
        return float(np.nextafter(p_sorted[0], np.inf))
    return float(p_sorted[last_of_value[best]])


def _week_order(frame: pd.DataFrame) -> tuple[NDArray[np.int64], NDArray[np.bool_]]:
    """Row order by (registration, week) and, in that order, whether a row is its registration's first."""
    groups = frame.groupby(GROUP, sort=False, observed=True).ngroup().to_numpy()
    order = np.lexsort((frame["week"].to_numpy(), groups))
    sorted_groups = groups[order]
    first = np.ones(len(order), dtype=bool)
    first[1:] = sorted_groups[1:] != sorted_groups[:-1]
    return order, first


def ewma_risk(
    frame: pd.DataFrame, risk: NDArray[np.float64], alpha: float = EWMA_ALPHA
) -> NDArray[np.float64]:
    """Exponentially smoothed risk per registration over weeks, aligned with ``frame``."""
    order, first = _week_order(frame)
    p = risk[order]
    smoothed = np.empty_like(p)
    for i in range(len(p)):
        smoothed[i] = p[i] if first[i] else alpha * p[i] + (1 - alpha) * smoothed[i - 1]
    out = np.empty_like(smoothed)
    out[order] = smoothed
    return out


def alert_flags(
    frame: pd.DataFrame, risk: NDArray[np.float64], threshold: float, policy: AlertPolicy
) -> NDArray[np.bool_]:
    """Alert per panel row. ``frame`` holds context_id, student_id, week (any order); ``risk`` aligns."""
    if policy == "ewma":
        return ewma_risk(frame, risk) >= threshold
    order, first = _week_order(frame)
    above = risk[order] >= threshold
    if policy == "raw":
        flags = above
    elif policy == "consecutive_2":
        flags = above & np.r_[False, above[:-1]] & ~first
    else:
        raise ValueError(f"unknown alert policy: {policy}")
    out = np.empty(len(order), dtype=bool)
    out[order] = flags
    return out


def mean_changes(frame: pd.DataFrame, values: NDArray[np.int64]) -> float:
    """Mean number of week-to-week changes of ``values`` (e.g. risk tier) per registration."""
    order, first = _week_order(frame)
    v = values[order]
    changed = np.r_[False, v[1:] != v[:-1]] & ~first
    registrations = int(first.sum())
    return float(changed.sum() / registrations) if registrations else 0.0


def student_alert_table(frame: pd.DataFrame, flags: NDArray[np.bool_]) -> pd.DataFrame:
    """One row per registration: outcome, first alert week, number of on/off switches, lead time."""
    data = frame[[*GROUP, "week", "y_academic", "withdraw_week", "course_end_week"]].assign(_flag=flags)
    data = data.sort_values([*GROUP, "week"], kind="stable")
    group = data.groupby(GROUP, sort=False, observed=True).ngroup().to_numpy()
    flag = data["_flag"].to_numpy().astype(np.int64)
    same = np.r_[False, group[1:] == group[:-1]]
    switches = np.where(same, np.abs(np.diff(flag, prepend=flag[:1])), 0)
    data = data.assign(_switch=switches, _alert_week=np.where(data["_flag"], data["week"], np.nan))
    table = data.groupby(GROUP, sort=False, observed=True).agg(
        adverse=("y_academic", "max"),
        withdraw_week=("withdraw_week", "first"),
        course_end_week=("course_end_week", "first"),
        first_alert_week=("_alert_week", "min"),
        flips=("_switch", "sum"),
    )
    alerted = table["first_alert_week"].notna()
    outcome_week = table["withdraw_week"].where(table["withdraw_week"].notna(), table["course_end_week"])
    table["alerted"] = alerted
    table["lead_time_weeks"] = (outcome_week - table["first_alert_week"]).where(
        alerted & (table["adverse"] == 1)
    )
    return table.reset_index()


def student_metrics(table: pd.DataFrame) -> dict[str, Any]:
    adverse = table["adverse"] == 1
    alerted = table["alerted"]
    lead = table.loc[adverse & alerted, "lead_time_weeks"].dropna()
    n_alerted = int(alerted.sum())
    return {
        "registrations": len(table),
        "adverse": int(adverse.sum()),
        "recall": float(alerted[adverse].mean()) if adverse.any() else None,
        "false_alarm_rate": float(alerted[~adverse].mean()) if (~adverse).any() else None,
        "precision": float(adverse[alerted].mean()) if n_alerted else None,
        "alerted": n_alerted,
        "lead_time_median_weeks": float(lead.median()) if len(lead) else None,
        "lead_time_share_4w_or_more": float((lead >= 4).mean()) if len(lead) else None,
        "mean_flips_per_registration": float(table["flips"].mean()),
    }
