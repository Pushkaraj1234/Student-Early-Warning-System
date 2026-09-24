"""Prediction targets (V3). Each target has an explicit definition, horizon and population.

Population for every target: registrations still active at the cutoff (see oulad_features).
Attendance risk is NOT defined: OULAD has no attendance data, and no model is created for it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ml.data.oulad import OuladTables

KEY = ["code_module", "code_presentation", "id_student"]
ENGAGEMENT_HORIZON_DAYS = 14


@dataclass(frozen=True)
class TargetSpec:
    name: str
    definition: str
    horizon: str


TARGETS: dict[str, TargetSpec] = {
    "academic": TargetSpec("academic", "final_result is Fail or Withdrawn", "end of the module presentation"),
    "dropout": TargetSpec("dropout", "final_result is Withdrawn", "end of the module presentation"),
    "course_failure": TargetSpec(
        "course_failure",
        "final_result is Fail (students who later withdraw count as 0)",
        "end of the module presentation",
    ),
    "engagement": TargetSpec(
        "engagement",
        f"no VLE activity at all in the {ENGAGEMENT_HORIZON_DAYS} days after the cutoff",
        f"{ENGAGEMENT_HORIZON_DAYS} days",
    ),
}


def target_values(population: pd.DataFrame, tables: OuladTables, cutoff_day: int, target: str) -> np.ndarray:
    """0/1 labels aligned with ``population`` (which carries KEY columns and ``final_result``)."""
    if target == "academic":
        return population["final_result"].isin({"Fail", "Withdrawn"}).astype(np.int64).to_numpy()
    if target == "dropout":
        return (population["final_result"] == "Withdrawn").astype(np.int64).to_numpy()
    if target == "course_failure":
        return (population["final_result"] == "Fail").astype(np.int64).to_numpy()
    if target == "engagement":
        vle = tables.student_vle_daily
        future = vle[(vle["date"] > cutoff_day) & (vle["date"] <= cutoff_day + ENGAGEMENT_HORIZON_DAYS)]
        active = future.groupby(KEY, sort=False)["sum_click"].sum() > 0
        joined = population[KEY].merge(active.rename("_active").reset_index(), on=KEY, how="left")
        return (~joined["_active"].fillna(False).astype(bool)).astype(np.int64).to_numpy()
    raise ValueError(f"unknown target: {target}")
