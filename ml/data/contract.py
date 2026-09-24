"""Data contract for prediction-time feature tables.

One row is one prediction unit — a student in a course context — at one prediction date.

Column            Type             Meaning
----------------  ---------------  -----------------------------------------------------------
student_id        str              Pseudonymous student identifier from the source dataset.
context_id        str              Course/term context of the prediction (OULAD: module-presentation).
prediction_date   datetime64[ns]   The cutoff. Every feature uses ONLY information available on or
                                   before this date. For OULAD, which records days relative to the
                                   presentation start, this is a NOMINAL date (see ml.data.oulad).
cutoff_day        int              Days since the context start at prediction_date.
split_group       str              Time-ordered group used for out-of-time splitting (OULAD: presentation).
<feature columns> float            Model inputs. NaN means "not available at prediction time".
target            int (0/1)        1 = adverse outcome (v1: Fail or Withdrawn), 0 = otherwise.
audit_<attr>      str              Subgroup attributes for fairness audits ONLY — never model inputs.

The contract is enforced by :func:`validate_feature_table` before any training or evaluation.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

ID_COLUMNS: tuple[str, ...] = ("student_id", "context_id", "prediction_date", "cutoff_day", "split_group")
KEY_COLUMNS: tuple[str, ...] = ("student_id", "context_id", "prediction_date")
TARGET_COLUMN = "target"
AUDIT_PREFIX = "audit_"


class DataContractError(ValueError):
    """Raised when a table does not satisfy the data contract."""


def validate_feature_table(
    df: pd.DataFrame,
    feature_names: Sequence[str],
    *,
    require_target: bool = True,
) -> None:
    """Validate ``df`` against the contract; raise :class:`DataContractError` on the first violation."""
    required = [*ID_COLUMNS, *feature_names]
    if require_target:
        required.append(TARGET_COLUMN)
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataContractError(f"missing required columns: {missing}")

    if df.empty:
        raise DataContractError("feature table is empty")

    overlap = [f for f in feature_names if f.startswith(AUDIT_PREFIX) or f in ID_COLUMNS or f == TARGET_COLUMN]
    if overlap:
        raise DataContractError(f"identifier, target or audit columns used as features: {overlap}")

    if df["student_id"].isna().any() or df["context_id"].isna().any():
        raise DataContractError("student_id and context_id must not be null")

    if not pd.api.types.is_datetime64_any_dtype(df["prediction_date"]):
        raise DataContractError("prediction_date must be a datetime64 column")
    if df["prediction_date"].isna().any():
        raise DataContractError("prediction_date must not be null")

    if not pd.api.types.is_integer_dtype(df["cutoff_day"]) or (df["cutoff_day"] < 0).any():
        raise DataContractError("cutoff_day must be a non-negative integer column")

    if df.duplicated(list(KEY_COLUMNS)).any():
        raise DataContractError("duplicate (student_id, context_id, prediction_date) rows")

    for name in feature_names:
        col = df[name]
        if pd.api.types.is_bool_dtype(col) or not pd.api.types.is_numeric_dtype(col):
            raise DataContractError(f"feature {name!r} must be numeric (got {col.dtype})")
        if np.isinf(col.to_numpy(dtype=float)).any():
            raise DataContractError(f"feature {name!r} contains infinite values")

    if require_target:
        target = df[TARGET_COLUMN]
        if target.isna().any() or not set(target.unique()).issubset({0, 1}):
            raise DataContractError("target must contain only 0 and 1")
