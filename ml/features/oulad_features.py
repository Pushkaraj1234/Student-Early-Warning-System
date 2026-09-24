"""Leakage-safe, as-of feature construction for OULAD.

For cutoff day ``t`` (days since presentation start):

* Population: registrations that exist and are still active at ``t``
  (registered on/before ``t`` or registration day unknown; not unregistered on/before ``t``).
  Students who already withdrew before ``t`` are excluded — there is nothing left to predict.
* VLE features use rows with ``date <= t`` only.
* Submission features use submissions with ``date_submitted <= t`` only.
* Scores are used only when ``date_submitted + score_release_lag_days <= t``. OULAD has no
  grade-release date, so the lag is an explicit, configurable ASSUMPTION.
* Banked results (carried over from an earlier attempt) count only as prior record.
* ``final_result`` is used ONLY for the target. ``date_unregistration`` is used ONLY for the
  population filter above. Demographics go to ``audit_*`` columns and are never features.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ml.data.contract import AUDIT_PREFIX, ID_COLUMNS, TARGET_COLUMN
from ml.data.oulad import OuladTables, nominal_presentation_start
from ml.features.definitions import (
    BASELINE_MIN_DAYS,
    BASELINE_RECENT_DAYS,
    FEATURE_VERSION,
    FEATURE_VERSION_V2,
    TREND_WINDOWS_DAYS,
    feature_names,
)
from ml.features.targets import target_values

KEY = ["code_module", "code_presentation", "id_student"]
PRESENTATION_KEY = ["code_module", "code_presentation"]
AUDIT_ATTRIBUTES = ("gender", "age_band", "disability", "imd_band")


def _population(tables: OuladTables, t: int) -> pd.DataFrame:
    reg = tables.registration
    active = reg[
        (reg["date_registration"].isna() | (reg["date_registration"] <= t))
        & (reg["date_unregistration"].isna() | (reg["date_unregistration"] > t))
    ]
    long_enough = tables.courses[tables.courses["module_presentation_length"] > t][PRESENTATION_KEY]
    active = active.merge(long_enough, on=PRESENTATION_KEY, how="inner")
    info_cols = [*KEY, "num_of_prev_attempts", "studied_credits", "final_result", *AUDIT_ATTRIBUTES]
    return active.merge(tables.student_info[info_cols], on=KEY, how="inner", validate="one_to_one")


def _sum_by_key(frame: pd.DataFrame, column: str) -> pd.Series:
    return frame.groupby(KEY, sort=False)[column].sum()


def _engagement(tables: OuladTables, t: int) -> tuple[pd.DataFrame, int]:
    """Per-student VLE aggregates at ``t`` and the length of the baseline window in days."""
    vle = tables.student_vle_daily
    v = vle[vle["date"] <= t]
    grouped = v.groupby(KEY, sort=False)
    out = pd.DataFrame(
        {
            "clicks_to_date": grouped["sum_click"].sum(),
            "active_days_to_date": grouped["date"].nunique(),
            "last_active_day": grouped["date"].max(),
        }
    )
    for w in TREND_WINDOWS_DAYS:
        current = _sum_by_key(v[v["date"] > t - w], "sum_click")
        previous = _sum_by_key(v[(v["date"] > t - 2 * w) & (v["date"] <= t - w)], "sum_click")
        out[f"clicks_last_{w}d"] = current
        out[f"_clicks_prev_{w}d"] = previous

    baseline_end = t - BASELINE_RECENT_DAYS
    baseline_days = baseline_end + 1  # days 0..baseline_end inclusive
    if baseline_days >= BASELINE_MIN_DAYS:
        out["_baseline_clicks"] = _sum_by_key(v[(v["date"] >= 0) & (v["date"] <= baseline_end)], "sum_click")
    return out, baseline_days


def _assessments(tables: OuladTables, t: int, lag: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_assessments = tables.assessments
    graded = all_assessments[(all_assessments["assessment_type"] != "Exam") & all_assessments["date"].notna()]

    due_counts = (
        graded[graded["date"] <= t]
        .groupby(PRESENTATION_KEY, sort=False)
        .size()
        .rename("assessments_due_to_date")
    )

    sa = tables.student_assessment
    banked = sa[sa["is_banked"] == 1].merge(
        all_assessments[["id_assessment", *PRESENTATION_KEY]], on="id_assessment", how="inner"
    )

    own = sa[sa["is_banked"] == 0].merge(
        graded[["id_assessment", *PRESENTATION_KEY, "date"]], on="id_assessment", how="inner"
    )
    submitted = own[own["date_submitted"].notna() & (own["date_submitted"] <= t)].copy()
    submitted["_delay"] = submitted["date_submitted"] - submitted["date"]
    submitted["_late"] = (submitted["_delay"] > 0).astype(float)
    by_student = submitted.groupby(KEY, sort=False)

    scored = own[
        own["score"].notna() & own["date_submitted"].notna() & (own["date_submitted"] + lag <= t)
    ].sort_values(["date_submitted", "id_assessment"])
    by_scored = scored.groupby(KEY, sort=False)

    # Outer-join all per-student aggregates so no student is dropped by index alignment.
    per_student = pd.concat(
        {
            "banked_assessment_count": banked.groupby(KEY, sort=False).size(),
            "_submitted_due": submitted[submitted["date"] <= t].groupby(KEY, sort=False).size(),
            "late_submission_rate": by_student["_late"].mean(),
            "mean_submission_delay_days": by_student["_delay"].mean(),
            "mean_score_to_date": by_scored["score"].mean(),
            "last_score": by_scored["score"].last(),
        },
        axis=1,
    )
    per_student.index.names = KEY
    return per_student, due_counts.reset_index()


def build_oulad_features(
    tables: OuladTables,
    cutoff_day: int,
    *,
    score_release_lag_days: int,
    target: str = "academic",
    feature_version: str = FEATURE_VERSION,
) -> pd.DataFrame:
    """Return the contract-compliant feature table for one cutoff day."""
    if cutoff_day < 1:
        raise ValueError("cutoff_day must be >= 1")
    if score_release_lag_days < 0:
        raise ValueError("score_release_lag_days must be >= 0")
    t = int(cutoff_day)

    base = _population(tables, t)
    engagement, baseline_days = _engagement(tables, t)
    per_student, due_counts = _assessments(tables, t, score_release_lag_days)

    df = base.merge(engagement, left_on=KEY, right_index=True, how="left")
    df = df.merge(per_student, left_on=KEY, right_index=True, how="left")
    df = df.merge(due_counts, on=PRESENTATION_KEY, how="left")

    # Absence of VLE/submission rows at t is a known zero, not a missing value.
    zero_fill = [
        "clicks_to_date",
        "active_days_to_date",
        "assessments_due_to_date",
        "banked_assessment_count",
        "_submitted_due",
    ]
    zero_fill += [f"clicks_last_{w}d" for w in TREND_WINDOWS_DAYS]
    zero_fill += [f"_clicks_prev_{w}d" for w in TREND_WINDOWS_DAYS]
    for col in zero_fill:
        df[col] = df[col].fillna(0).astype(float)

    for w in TREND_WINDOWS_DAYS:
        df[f"clicks_trend_{w}d"] = (df[f"clicks_last_{w}d"] - df[f"_clicks_prev_{w}d"]) / w

    if "_baseline_clicks" in df.columns:
        baseline_rate = df["_baseline_clicks"].fillna(0) / baseline_days
        df["clicks_change_from_baseline"] = df["clicks_last_14d"] / BASELINE_RECENT_DAYS - baseline_rate
    else:
        df["clicks_change_from_baseline"] = np.nan

    df["days_since_last_activity"] = t - df["last_active_day"]
    # Missing (NaN) when nothing is due yet — a rate over zero assessments is undefined.
    df["assignment_completion_rate"] = df["_submitted_due"] / df["assessments_due_to_date"].where(
        df["assessments_due_to_date"] > 0
    )
    cohort_mean = df.groupby(PRESENTATION_KEY, sort=False)["mean_score_to_date"].transform("mean")
    df["course_relative_score"] = df["mean_score_to_date"] - cohort_mean
    df["registration_lead_days"] = -df["date_registration"]
    if feature_version == FEATURE_VERSION_V2:
        df = _add_v2_features(df, tables, t, score_release_lag_days)
    names = feature_names(feature_version)

    out = pd.DataFrame(
        {
            "student_id": df["id_student"].astype(str),
            "context_id": df["code_module"].astype(str) + "-" + df["code_presentation"].astype(str),
            "prediction_date": [
                nominal_presentation_start(p) + pd.Timedelta(days=t) for p in df["code_presentation"]
            ],
            "cutoff_day": np.full(len(df), t, dtype=np.int64),
            "split_group": df["code_presentation"].astype(str),
        }
    )
    out["prediction_date"] = pd.to_datetime(out["prediction_date"])
    for name in names:
        out[name] = df[name].astype(float).to_numpy()
    out[TARGET_COLUMN] = target_values(df, tables, t, target)
    for attr in AUDIT_ATTRIBUTES:
        out[f"{AUDIT_PREFIX}{attr}"] = df[attr].astype("str").fillna("unknown").to_numpy()

    ordered = [*ID_COLUMNS, *names, TARGET_COLUMN, *[f"{AUDIT_PREFIX}{a}" for a in AUDIT_ATTRIBUTES]]
    return out[ordered].sort_values(["context_id", "student_id"]).reset_index(drop=True)


def _window(frame: pd.DataFrame, lo_exclusive: int, hi_inclusive: int) -> pd.DataFrame:
    return frame[(frame["date"] > lo_exclusive) & (frame["date"] <= hi_inclusive)]


def _add_v2_features(df: pd.DataFrame, tables: OuladTables, t: int, lag: int) -> pd.DataFrame:
    """Feature set v2 additions. Every input is filtered to information available at ``t``."""
    groups = tables.student_vle_daily_groups
    if groups is None:  # hand-built tables without activity detail: all activity counts as content
        groups = tables.student_vle_daily.assign(activity_group="content")
    g = groups[groups["date"] <= t]
    extra: dict[str, pd.Series] = {}
    for group in ("quiz", "forum", "content"):
        gi = g[g["activity_group"] == group]
        extra[f"{group}_clicks_to_date"] = _sum_by_key(gi, "sum_click")
        for w in (7, 14, 30):
            extra[f"{group}_clicks_last_{w}d"] = _sum_by_key(_window(gi, t - w, t), "sum_click")
        extra[f"_{group}_prev_14d"] = _sum_by_key(_window(gi, t - 28, t - 14), "sum_click")

    vle = tables.student_vle_daily
    extra["active_days_last_14d"] = _window(vle, t - 14, t).groupby(KEY, sort=False)["date"].nunique()

    assessments = tables.assessments
    graded = assessments[(assessments["assessment_type"] != "Exam") & assessments["date"].notna()]
    sa = tables.student_assessment
    own = sa[sa["is_banked"] == 0].merge(
        graded[["id_assessment", *PRESENTATION_KEY, "date"]].rename(columns={"date": "due"}),
        on="id_assessment",
        how="inner",
    )
    submitted = own[own["date_submitted"].notna() & (own["date_submitted"] <= t)]
    extra["submissions_last_30d"] = (
        submitted[submitted["date_submitted"] > t - 30].groupby(KEY, sort=False).size().astype(float)
    )
    recent_due = submitted[(submitted["due"] > t - 30) & (submitted["due"] <= t)]
    extra["_submitted_recent_due"] = recent_due.groupby(KEY, sort=False).size().astype(float)

    scored = own[own["score"].notna() & own["date_submitted"].notna() & (own["date_submitted"] + lag <= t)]
    scored = scored.assign(_x=scored["date_submitted"].astype(float), _y=scored["score"].astype(float))
    scored = scored.assign(_xx=scored["_x"] ** 2, _xy=scored["_x"] * scored["_y"])
    agg = scored.groupby(KEY, sort=False).agg(
        _n=("_x", "size"), _sx=("_x", "sum"), _sy=("_y", "sum"), _sxx=("_xx", "sum"), _sxy=("_xy", "sum")
    )
    denom = agg["_n"] * agg["_sxx"] - agg["_sx"] ** 2
    slope = (agg["_n"] * agg["_sxy"] - agg["_sx"] * agg["_sy"]) / denom.where(denom > 0)
    extra["score_trend_per_30d"] = (slope * 30).where(agg["_n"] >= 2)
    ordered_scores = scored.sort_values(["date_submitted", "id_assessment"]).groupby(KEY, sort=False)["score"]
    change = ordered_scores.last() - ordered_scores.first()
    extra["score_change_from_first"] = change.where(agg["_n"].reindex(change.index) >= 2)

    frame = pd.concat(extra, axis=1)
    frame.index.names = KEY
    df = df.merge(frame, left_on=KEY, right_index=True, how="left")

    due_recent = (
        graded[(graded["date"] > t - 30) & (graded["date"] <= t)]
        .groupby(PRESENTATION_KEY, sort=False)
        .size()
        .rename("_due_recent")
        .reset_index()
    )
    df = df.merge(due_recent, on=PRESENTATION_KEY, how="left")

    # Absent activity / submissions are known zeros; rates and slopes stay missing when undefined.
    zero_fill = [
        f"{group}_clicks_{suffix}"
        for group in ("quiz", "forum", "content")
        for suffix in ("to_date", "last_7d", "last_14d", "last_30d")
    ]
    zero_fill += [f"_{group}_prev_14d" for group in ("quiz", "forum", "content")]
    zero_fill += ["active_days_last_14d", "submissions_last_30d", "_submitted_recent_due", "_due_recent"]
    for col in zero_fill:
        df[col] = df[col].fillna(0).astype(float)
    for group in ("quiz", "forum", "content"):
        df[f"{group}_trend_14d"] = (df[f"{group}_clicks_last_14d"] - df[f"_{group}_prev_14d"]) / 14
    df["completion_rate_last_30d"] = df["_submitted_recent_due"] / df["_due_recent"].where(
        df["_due_recent"] > 0
    )
    df["clicks_last_7d_vs_30d_rate"] = df["clicks_last_7d"] / 7 - df["clicks_last_30d"] / 30
    return df
