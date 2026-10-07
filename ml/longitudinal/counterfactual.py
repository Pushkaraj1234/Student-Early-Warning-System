"""Counterfactual explanations on actionable features.

For a flagged student-week, search for the fewest changes to ACTIONABLE features (behaviour a student or
mentor can influence) that bring the model's risk below the threshold. Candidate values are the training
distribution's median, upper quartile and 90th percentile (lower quartile / 10th percentile for features
where lower is better), and only moves in the improving direction are tried. Up to two features are changed.

Limitation: features derived from the same records are changed independently (e.g. clicks this week without
the 14-day click count). A counterfactual shows what the MODEL is sensitive to; it is not a causal claim.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

Direction = Literal["increase", "decrease"]
ACTIONABLE: dict[str, Direction] = {
    "clicks_this_week": "increase",
    "active_days_this_week": "increase",
    "active_days_last_14d": "increase",
    "clicks_last_14d": "increase",
    "quiz_clicks_last_14d": "increase",
    "forum_clicks_last_14d": "increase",
    "assignment_completion_rate": "increase",
    "completion_rate_last_30d": "increase",
    "on_time_ratio_to_date": "increase",
    "days_since_last_activity": "decrease",
    "inactive_week_streak": "decrease",
    "missed_due_last_4w": "decrease",
    "late_submission_rate": "decrease",
}
QUANTILES: dict[Direction, tuple[float, ...]] = {"increase": (0.5, 0.75, 0.9), "decrease": (0.5, 0.25, 0.1)}
MAX_CHANGES = 2


@dataclass(frozen=True)
class Counterfactual:
    changes: tuple[tuple[str, float, float], ...]  # (feature, from, to)
    risk_before: float
    risk_after: float


def candidate_values(reference: pd.DataFrame, features: dict[str, Direction]) -> dict[str, tuple[float, ...]]:
    return {
        f: tuple(float(v) for v in np.nanquantile(reference[f].to_numpy(dtype=np.float64), QUANTILES[d]))
        for f, d in features.items()
    }


def _improves(current: float, target: float, direction: Direction) -> bool:
    if np.isnan(current):
        return True
    return target > current if direction == "increase" else target < current


def find_counterfactual(
    row: pd.DataFrame,
    predict: Callable[[pd.DataFrame], np.ndarray],
    threshold: float,
    candidates: dict[str, tuple[float, ...]],
    features: dict[str, Direction] = ACTIONABLE,
) -> Counterfactual | None:
    """Fewest changes (1, then 2) bringing the risk below ``threshold``; among those, the lowest risk."""
    if len(row) != 1:
        raise ValueError("expects exactly one row")
    risk_before = float(predict(row)[0])
    options = [
        (f, v)
        for f, values in candidates.items()
        for v in values
        if _improves(float(row[f].iloc[0]), v, features[f])
    ]
    for size in range(1, MAX_CHANGES + 1):
        combos = [c for c in itertools.combinations(options, size) if len({f for f, _ in c}) == size]
        if not combos:
            continue
        trial = pd.concat([row] * len(combos), ignore_index=True)
        for i, combo in enumerate(combos):
            for f, v in combo:
                trial.loc[i, f] = v
        risks = predict(trial)
        below = np.flatnonzero(risks < threshold)
        if below.size:
            best = int(below[np.argmin(risks[below])])
            return Counterfactual(
                changes=tuple((f, float(row[f].iloc[0]), v) for f, v in combos[best]),
                risk_before=risk_before,
                risk_after=float(risks[best]),
            )
    return None
