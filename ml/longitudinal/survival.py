"""Time-to-withdrawal analysis: Kaplan-Meier retention curves and Harrell's concordance index.

The weekly withdrawal hazard itself is modelled as a discrete-time hazard model: a classifier on person-weeks
with the label "withdraws in the next week" (``y_withdraw_1w``), the standard choice for weekly event times
with many ties. Under the simplifying assumption that the hazard stays at its current value, the probability
of withdrawing within ``h`` weeks is ``1 - (1 - hazard)^h``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.typing import NDArray

CHUNK = 2000


def kaplan_meier(durations: NDArray[np.float64], events: NDArray[np.bool_]) -> pd.DataFrame:
    """Product-limit estimate S(t) at each distinct event time (durations in weeks; False = censored)."""
    if durations.shape != events.shape or durations.size == 0:
        raise ValueError("durations and events must be non-empty and aligned")
    times = np.unique(durations[events])
    rows = []
    survival = 1.0
    for t in times:
        at_risk = int(np.sum(durations >= t))
        d = int(np.sum((durations == t) & events))
        survival *= 1.0 - d / at_risk
        rows.append({"time": float(t), "at_risk": at_risk, "events": d, "survival": survival})
    return pd.DataFrame(rows, columns=["time", "at_risk", "events", "survival"])


def survival_at(curve: pd.DataFrame, t: float) -> float:
    """S(t) from a Kaplan-Meier table (1.0 before the first event)."""
    before = curve[curve["time"] <= t]
    return 1.0 if before.empty else float(before["survival"].iloc[-1])


def concordance_index(
    durations: NDArray[np.float64], events: NDArray[np.bool_], risk: NDArray[np.float64]
) -> float:
    """Harrell's C: among comparable pairs (the earlier time is an event), the share where the earlier
    event has the higher risk; ties in risk count one half."""
    if not (durations.shape == events.shape == risk.shape):
        raise ValueError("inputs must be aligned")
    concordant = 0.0
    comparable = 0
    event_idx = np.flatnonzero(events)
    for start in range(0, event_idx.size, CHUNK):
        i = event_idx[start : start + CHUNK]
        later = durations[None, :] > durations[i, None]
        comparable += int(later.sum())
        higher = risk[i, None] > risk[None, :]
        tied = risk[i, None] == risk[None, :]
        concordant += float(np.sum(later & higher) + 0.5 * np.sum(later & tied))
    if comparable == 0:
        raise ValueError("no comparable pairs")
    return concordant / comparable


def risk_within(hazard: NDArray[np.float64], weeks: int) -> NDArray[np.float64]:
    """P(withdraw within ``weeks``) from a constant weekly hazard."""
    return 1.0 - (1.0 - np.clip(hazard, 0.0, 1.0)) ** weeks
