"""Loaders and decision-point feature sets for two external benchmark datasets (Portugal, CC BY 4.0).

A. UCI 697 "Predict Students' Dropout and Academic Success" (Realinho et al., doi:10.24432/C5MC89): one row
   per university student; enrolment data, first-year semester results, outcome at the end of the normal
   duration.
B. UCI 320 "Student Performance" (Cortez & Silva 2008, doi:10.24432/C5TG7T): one row per secondary-school
   student; period grades G1, G2 and final grade G3.

Feature policy (docs/research/external-datasets-plan.md): demographic, family and lifestyle attributes are
never model inputs; some are kept as ``audit_*`` columns for fairness checks. Variables whose recording time
is not documented (fees/debt/scholarship in A, absences in B) are only used in labelled sensitivity runs.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import numpy as np
import pandas as pd

from ml.data.contract import AUDIT_PREFIX, DataContractError

DATASET_A = "uci-697-dropout"
DATASET_B = "uci-320-student-performance"
PROVENANCE = "benchmark"

# ------------------------------------------------------------------ dataset A (UCI 697)
A_COLUMNS = (
    "Marital status", "Application mode", "Application order", "Course", "Daytime/evening attendance",
    "Previous qualification", "Previous qualification (grade)", "Nacionality", "Mother's qualification",
    "Father's qualification", "Mother's occupation", "Father's occupation", "Admission grade", "Displaced",
    "Educational special needs", "Debtor", "Tuition fees up to date", "Gender", "Scholarship holder",
    "Age at enrollment", "International",
    *(f"Curricular units {s} sem ({k})" for s in ("1st", "2nd")
      for k in ("credited", "enrolled", "evaluations", "approved", "grade", "without evaluations")),
    "Unemployment rate", "Inflation rate", "GDP", "Target",
)  # fmt: skip
A_TARGETS = frozenset({"Dropout", "Enrolled", "Graduate"})
# Nominal codes become one-hot columns named "<name>_code_<value>".
A_NOMINAL = {
    "Application mode": "application_mode",
    "Course": "course",
    "Previous qualification": "prev_qual",
}
A_NUMERIC_D0 = {
    "Application order": "application_order",
    "Daytime/evening attendance": "daytime",
    "Previous qualification (grade)": "prev_qual_grade",
    "Admission grade": "admission_grade",
    "Unemployment rate": "unemployment_rate",
    "Inflation rate": "inflation_rate",
    "GDP": "gdp",
}
A_FINANCIAL = {
    "Debtor": "debtor",
    "Tuition fees up to date": "fees_up_to_date",
    "Scholarship holder": "scholarship",
}
SEMESTER_FIELDS = ("credited", "enrolled", "evaluations", "approved", "grade", "without evaluations")
FINANCIAL_FEATURES: tuple[str, ...] = tuple(A_FINANCIAL.values())

# ------------------------------------------------------------------ dataset B (UCI 320)
B_COLUMNS = (
    "school", "sex", "age", "address", "famsize", "Pstatus", "Medu", "Fedu", "Mjob", "Fjob", "reason",
    "guardian", "traveltime", "studytime", "failures", "schoolsup", "famsup", "paid", "activities", "nursery",
    "higher", "internet", "romantic", "famrel", "freetime", "goout", "Dalc", "Walc", "health", "absences",
    "G1", "G2", "G3",
)  # fmt: skip
B_YES_NO = ("schoolsup", "famsup", "paid", "activities", "higher")
B_P0 = ("school_ms", "studytime", "failures", "schoolsup", "famsup", "paid", "activities", "higher")
PERFORMANCE_POINTS: dict[str, tuple[str, ...]] = {"P0": B_P0, "P1": (*B_P0, "g1"), "P2": (*B_P0, "g1", "g2")}
PASS_MARK = 10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verified(path: Path, expected_sha256: str | None) -> Path:
    if not path.is_file():
        raise DataContractError(f"missing dataset file: {path}")
    if expected_sha256 is not None and sha256(path) != expected_sha256:
        raise DataContractError(f"{path.name}: SHA-256 differs from the recorded download")
    return path


def _snake(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# ------------------------------------------------------------------ A: loading and features
def load_dropout(path: Path, *, expected_sha256: str | None) -> pd.DataFrame:
    raw = pd.read_csv(_verified(path, expected_sha256), sep=";", encoding="utf-8-sig")
    raw.columns = [c.strip() for c in raw.columns]
    if tuple(raw.columns) != A_COLUMNS:
        raise DataContractError(f"unexpected columns in {path.name}")
    if raw.isna().any().any():
        raise DataContractError(f"{path.name} has missing values")
    if not set(raw["Target"].unique()) <= A_TARGETS:
        raise DataContractError(f"unexpected Target values in {path.name}")
    return raw


def _age_band(age: pd.Series) -> np.ndarray:
    return np.select([age <= 20, age <= 25], ["<=20", "21-25"], ">25")


def dropout_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Model-ready frame: numeric inputs, one-hot nominal codes, semester features, targets, audit columns."""
    parts: dict[str, pd.Series | np.ndarray] = {"student_id": np.array([f"a{i}" for i in range(len(raw))])}
    for source, name in A_NUMERIC_D0.items():
        parts[name] = raw[source].astype(float)
    for source, name in A_FINANCIAL.items():
        parts[name] = raw[source].astype(float)
    for number, label in ((1, "1st"), (2, "2nd")):
        for field in SEMESTER_FIELDS:
            parts[f"sem{number}_{_snake(field)}"] = raw[f"Curricular units {label} sem ({field})"].astype(
                float
            )
        enrolled = pd.Series(parts[f"sem{number}_enrolled"])
        approved = pd.Series(parts[f"sem{number}_approved"])
        parts[f"sem{number}_approval_rate"] = approved / enrolled.where(enrolled > 0)
        parts[f"sem{number}_failed"] = enrolled - approved
    parts["approval_rate_change"] = pd.Series(parts["sem2_approval_rate"]) - pd.Series(
        parts["sem1_approval_rate"]
    )
    parts["y_dropout"] = (raw["Target"] == "Dropout").astype(np.int64)
    parts["y_not_graduated"] = (raw["Target"] != "Graduate").astype(np.int64)
    macro = raw[["Unemployment rate", "Inflation rate", "GDP"]].astype(str).agg("|".join, axis=1)
    parts["cohort"] = np.array([f"c{c}" for c in pd.factorize(macro, sort=True)[0]])
    parts[f"{AUDIT_PREFIX}gender"] = np.where(raw["Gender"] == 1, "male", "female")
    parts[f"{AUDIT_PREFIX}age_band"] = _age_band(raw["Age at enrollment"])
    for source, name in (("International", "international"), ("Displaced", "displaced"),
                         ("Educational special needs", "special_needs")):  # fmt: skip
        parts[f"{AUDIT_PREFIX}{name}"] = np.where(raw[source] == 1, "yes", "no")
    out = pd.DataFrame(parts, index=raw.index)
    codes = [
        pd.get_dummies(raw[source].astype(int), prefix=f"{name}_code", dtype=float)
        for source, name in A_NOMINAL.items()
    ]
    return pd.concat([out, *codes], axis=1)


def dropout_decision_points(frame: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    """Feature names per decision point (the one-hot columns depend on the codes present)."""
    prefixes = tuple(f"{name}_code_" for name in A_NOMINAL.values())
    d0 = (*A_NUMERIC_D0.values(), *(c for c in frame.columns if c.startswith(prefixes)))
    sem1 = (*(f"sem1_{_snake(f)}" for f in SEMESTER_FIELDS), "sem1_approval_rate", "sem1_failed")
    sem2 = (*(f"sem2_{_snake(f)}" for f in SEMESTER_FIELDS), "sem2_approval_rate", "sem2_failed")
    return {"D0": tuple(d0), "D1": (*d0, *sem1), "D2": (*d0, *sem1, *sem2, "approval_rate_change")}


def dropout_population(frame: pd.DataFrame, point: str) -> pd.Series:
    """D0: everyone; D1/D2: students with at least one unit enrolled in that semester."""
    if point == "D0":
        return pd.Series(True, index=frame.index)
    semester = {"D1": "sem1_enrolled", "D2": "sem2_enrolled"}[point]
    return frame[semester] > 0


# ------------------------------------------------------------------ B: loading and features
def load_performance(path: Path, *, expected_sha256: str | None) -> pd.DataFrame:
    raw = pd.read_csv(_verified(path, expected_sha256), sep=";")
    if tuple(raw.columns) != B_COLUMNS:
        raise DataContractError(f"unexpected columns in {path.name}")
    if raw.isna().any().any():
        raise DataContractError(f"{path.name} has missing values")
    for grade in ("G1", "G2", "G3"):
        raw[grade] = pd.to_numeric(raw[grade], errors="raise")
        if not raw[grade].between(0, 20).all():
            raise DataContractError(f"{grade} outside 0-20 in {path.name}")
    return raw


def performance_frame(raw: pd.DataFrame) -> pd.DataFrame:
    parts: dict[str, pd.Series | np.ndarray] = {
        "student_id": np.array([f"b{i}" for i in range(len(raw))]),
        "school_ms": (raw["school"] == "MS").astype(float),
    }
    for col in ("studytime", "failures", "absences"):
        parts[col] = raw[col].astype(float)
    for col in B_YES_NO:
        parts[col] = (raw[col] == "yes").astype(float)
    parts["g1"] = raw["G1"].astype(float)
    parts["g2"] = raw["G2"].astype(float)
    parts["y_fail"] = (raw["G3"] < PASS_MARK).astype(np.int64)
    parts[f"{AUDIT_PREFIX}sex"] = raw["sex"].astype(str)
    parts[f"{AUDIT_PREFIX}age_band"] = np.where(raw["age"] <= 17, "<=17", ">=18")
    parts[f"{AUDIT_PREFIX}address"] = np.where(raw["address"] == "U", "urban", "rural")
    return pd.DataFrame(parts, index=raw.index)
