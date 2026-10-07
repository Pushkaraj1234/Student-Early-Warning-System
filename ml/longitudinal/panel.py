"""Student-week panel (feature set ``oulad-ts-1.0.0``) for the v3 longitudinal study.

One row = one registration (student x module presentation) at the end of week ``k`` (cutoff day ``7k``),
for every week in which the registration is still active (the v2 population rule, ``_population``).

Features = the 37 v2 features rebuilt at each weekly cutoff (``build_oulad_features``) + 18 longitudinal
features computed here from weekly series. Every value at week ``k`` uses only records dated on or before
day ``7k`` (scores only once released: submission + release lag); ``assert_panel_no_leakage`` checks this by
rebuilding a week from tables truncated at the cutoff.

Week numbering: week ``j`` >= 1 covers days ``7(j-1)+1 .. 7j``; activity on or before day 0 (before the
presentation starts) is week 0, which the weekly series (weeks 1..k) do not include.

Labels (never features):
  ``y_academic``     final_result is Fail or Withdrawn (course end).
  ``y_withdraw_<h>w`` unregisters within ``h`` weeks after the cutoff
                     (``7k < date_unregistration <= 7(k+h)``).
                     Missing (NaN) for registrations recorded as Withdrawn without an unregistration date: the
                     withdrawal week is unknown. An unregistration date with another final result still counts
                     as leaving.
"""

from __future__ import annotations

import pickle
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from ml.data.contract import AUDIT_PREFIX, ID_COLUMNS, KEY_COLUMNS, TARGET_COLUMN
from ml.data.oulad import OuladTables, truncate_at
from ml.features.definitions import FEATURE_VERSION_V2, FeatureSpec, feature_names
from ml.features.leakage import TemporalLeakageError
from ml.features.oulad_features import AUDIT_ATTRIBUTES, KEY, PRESENTATION_KEY, build_oulad_features

FloatMatrix = NDArray[np.float64]

FEATURE_VERSION_TS = "oulad-ts-1.0.0"
DAYS_PER_WEEK = 7
# Longest OULAD presentation is 269 days (39 weeks); activity after week 40 is ignored.
PANEL_MAX_WEEK = 40
ROLL_SHORT_WEEKS = 3
ROLL_LONG_WEEKS = 6
SLOPE_MIN_WEEKS = 3
RECENT_WEEKS = 4
CUSUM_ALLOWANCE = 0.5
CUSUM_THRESHOLD = 3.0
CUSUM_MIN_SD = 0.5
HORIZON_WEEKS: dict[str, int] = {"withdraw_1w": 1, "withdraw_4w": 4, "withdraw_8w": 8}
PANEL_TARGETS: tuple[str, ...] = ("academic", *HORIZON_WEEKS)

ACTIVITY_FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("clicks_this_week", "engagement", "VLE clicks in week k."),
    FeatureSpec("active_days_this_week", "engagement", "Days with VLE activity in week k."),
    FeatureSpec(
        "clicks_roll3w_mean", "engagement", "Mean weekly clicks over the last 3 weeks (fewer if k < 3)."
    ),
    FeatureSpec(
        "clicks_roll6w_mean", "engagement", "Mean weekly clicks over the last 6 weeks (fewer if k < 6)."
    ),
    FeatureSpec(
        "clicks_slope_6w",
        "engagement",
        "Least-squares slope of log(1+weekly clicks) over the last 6 weeks (>= 3).",
    ),
    FeatureSpec("clicks_cv_6w", "engagement", "Coefficient of variation of weekly clicks, last 6 weeks."),
    FeatureSpec(
        "clicks_recent_vs_own_mean",
        "engagement",
        "log(1+mean clicks, last 3 weeks) - log(1+mean clicks, earlier weeks); needs >= 1 earlier week.",
    ),
    FeatureSpec("inactive_week_streak", "engagement", "Consecutive weeks up to k without VLE activity."),
    FeatureSpec("inactive_weeks_last_6w", "engagement", "Weeks without VLE activity among the last 6."),
    FeatureSpec(
        "cusum_drop_stat",
        "engagement",
        "One-sided lower CUSUM of log(1+weekly clicks) against the student's own running mean/SD of earlier "
        "weeks.",
    ),
    FeatureSpec(
        "weeks_since_change_point",
        "engagement",
        "Weeks since the CUSUM statistic last crossed above the threshold; missing if it never did.",
    ),
)
ASSESSMENT_FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        "on_time_ratio_to_date", "assignment", "Due assessments submitted on time / due assessments."
    ),
    FeatureSpec(
        "missed_due_last_4w", "assignment", "Assessments due in the last 4 weeks not submitted by the cutoff."
    ),
    FeatureSpec(
        "delay_change_recent",
        "assignment",
        "Mean submission delay in the last 4 weeks minus the mean delay before (both needed).",
    ),
    FeatureSpec(
        "difficulty_adjusted_score",
        "academic",
        "Mean of (score - cohort mean for the same assessment), released results only.",
    ),
    FeatureSpec("score_rolling2_mean", "academic", "Mean of the last 2 released scores."),
    FeatureSpec("score_drop_from_best", "academic", "Best released score minus the latest (>= 2 scores)."),
    FeatureSpec("score_volatility", "academic", "Standard deviation of released scores (>= 3)."),
)
LONGITUDINAL_FEATURES: tuple[FeatureSpec, ...] = ACTIVITY_FEATURES + ASSESSMENT_FEATURES
V2_FEATURE_NAMES: tuple[str, ...] = feature_names(FEATURE_VERSION_V2)
TS_FEATURE_NAMES: tuple[str, ...] = V2_FEATURE_NAMES + tuple(s.name for s in LONGITUDINAL_FEATURES)


def label_column(target: str) -> str:
    if target not in PANEL_TARGETS:
        raise ValueError(f"unknown panel target: {target}")
    return f"y_{target}"


def week_of_day(day: NDArray[np.int64]) -> NDArray[np.int64]:
    """Week index of a day relative to the presentation start (day <= 0 -> week 0)."""
    d = np.asarray(day, dtype=np.int64)
    return np.where(d <= 0, 0, (d + DAYS_PER_WEEK - 1) // DAYS_PER_WEEK).astype(np.int64)


@dataclass(frozen=True)
class WeeklyMatrices:
    """Weekly VLE series per registration: row i = ``keys`` row i, column j = week j (0 = before start)."""

    keys: pd.DataFrame
    clicks: FloatMatrix
    active_days: FloatMatrix


def weekly_matrices(tables: OuladTables, max_week: int = PANEL_MAX_WEEK) -> WeeklyMatrices:
    keys = tables.registration[KEY].drop_duplicates().reset_index(drop=True)
    if len(keys) != len(tables.registration):
        raise ValueError("registration keys must be unique")
    rows = keys.assign(_row=np.arange(len(keys), dtype=np.int64))
    vle = tables.student_vle_daily.merge(rows, on=KEY, how="inner")
    week = week_of_day(vle["date"].to_numpy())
    keep = week <= max_week
    r = vle["_row"].to_numpy()[keep]
    w = week[keep]
    clicks = np.zeros((len(keys), max_week + 1))
    active = np.zeros((len(keys), max_week + 1))
    np.add.at(clicks, (r, w), vle["sum_click"].to_numpy(dtype=np.float64)[keep])
    np.add.at(active, (r, w), (vle["sum_click"].to_numpy()[keep] > 0).astype(np.float64))
    return WeeklyMatrices(keys=keys, clicks=clicks, active_days=active)


def activity_feature_arrays(m: WeeklyMatrices) -> dict[str, FloatMatrix]:
    """Every activity feature for every week: array (registrations, max_week + 1); column k = week k.
    Column k depends only on weeks 0..k (verified by ``assert_panel_no_leakage``)."""
    x = m.clicks[:, 1:]
    a = m.active_days[:, 1:]
    n, weeks = x.shape
    out = {s.name: np.full((n, weeks + 1), np.nan) for s in ACTIVITY_FEATURES}
    logx = np.log1p(x)
    csum = np.cumsum(logx, axis=1)
    csum2 = np.cumsum(logx**2, axis=1)
    cusum = np.zeros(n)
    last_cross = np.full(n, np.nan)
    for k in range(1, weeks + 1):
        cur = x[:, :k]
        last_short = cur[:, -ROLL_SHORT_WEEKS:]
        last_long = cur[:, -ROLL_LONG_WEEKS:]
        out["clicks_this_week"][:, k] = x[:, k - 1]
        out["active_days_this_week"][:, k] = a[:, k - 1]
        out["clicks_roll3w_mean"][:, k] = last_short.mean(axis=1)
        mean_long = last_long.mean(axis=1)
        out["clicks_roll6w_mean"][:, k] = mean_long
        span = last_long.shape[1]
        if span >= SLOPE_MIN_WEEKS:
            centred = np.arange(span) - (span - 1) / 2
            out["clicks_slope_6w"][:, k] = np.log1p(last_long) @ centred / float(centred @ centred)
        out["clicks_cv_6w"][:, k] = np.divide(
            last_long.std(axis=1), mean_long, out=np.full(n, np.nan), where=mean_long > 0
        )
        if k > ROLL_SHORT_WEEKS:
            earlier = cur[:, :-ROLL_SHORT_WEEKS].mean(axis=1)
            out["clicks_recent_vs_own_mean"][:, k] = np.log1p(last_short.mean(axis=1)) - np.log1p(earlier)
        zero = cur == 0
        trailing = np.argmax(~zero[:, ::-1], axis=1)
        out["inactive_week_streak"][:, k] = np.where(zero.all(axis=1), k, trailing)
        out["inactive_weeks_last_6w"][:, k] = (last_long == 0).sum(axis=1)
        if k >= 2:
            j = k - 1  # earlier weeks available
            mean_prev = csum[:, j - 1] / j
            sd_prev = np.sqrt(np.maximum(csum2[:, j - 1] / j - mean_prev**2, 0.0))
            z = (mean_prev - logx[:, k - 1]) / np.maximum(sd_prev, CUSUM_MIN_SD)
            updated = np.maximum(0.0, cusum + z - CUSUM_ALLOWANCE)
            crossed = (cusum <= CUSUM_THRESHOLD) & (updated > CUSUM_THRESHOLD)
            last_cross = np.where(crossed, float(k), last_cross)
            cusum = updated
        out["cusum_drop_stat"][:, k] = cusum
        out["weeks_since_change_point"][:, k] = k - last_cross
    return out


def assessment_base(tables: OuladTables) -> pd.DataFrame:
    """One row per (registration, non-exam assessment with a due date) with the student's own submission."""
    a = tables.assessments
    graded = a[(a["assessment_type"] != "Exam") & a["date"].notna()]
    graded = graded[["id_assessment", *PRESENTATION_KEY, "date"]].rename(columns={"date": "due"})
    base = tables.registration[KEY].merge(graded, on=PRESENTATION_KEY, how="inner")
    sa = tables.student_assessment
    own = sa[sa["is_banked"] == 0][["id_assessment", "id_student", "date_submitted", "score"]]
    return base.merge(own, on=["id_assessment", "id_student"], how="left", validate="one_to_one")


def assessment_features(base: pd.DataFrame, cutoff_day: int, lag: int) -> pd.DataFrame:
    """Assessment features at ``cutoff_day`` indexed by KEY (registrations without assessments are absent)."""
    t = float(cutoff_day)
    recent_start = t - RECENT_WEEKS * DAYS_PER_WEEK
    s = base["date_submitted"]
    due = base["due"]
    submitted = s.notna() & (s <= t)
    is_due = due <= t
    flags = base[KEY].assign(
        _due=is_due.astype(float),
        _on_time=(submitted & (s <= due) & is_due).astype(float),
        _missed_recent=(is_due & (due > recent_start) & ~submitted).astype(float),
    )
    counts = flags.groupby(KEY, sort=False)[["_due", "_on_time", "_missed_recent"]].sum()
    out = pd.DataFrame(index=counts.index)
    out["on_time_ratio_to_date"] = counts["_on_time"] / counts["_due"].where(counts["_due"] > 0)
    out["missed_due_last_4w"] = counts["_missed_recent"]

    subs = base[submitted].assign(_delay=lambda f: f["date_submitted"] - f["due"])
    recent = subs["date_submitted"] > recent_start
    delay_recent = subs[recent].groupby(KEY, sort=False)["_delay"].mean()
    delay_before = subs[~recent].groupby(KEY, sort=False)["_delay"].mean()
    out["delay_change_recent"] = (delay_recent - delay_before).reindex(out.index)

    released = base[base["score"].notna() & s.notna() & (s + lag <= t)]
    released = released.sort_values(["date_submitted", "id_assessment"], kind="stable")
    adjusted = released["score"] - released.groupby("id_assessment")["score"].transform("mean")
    by_student = released.assign(_adj=adjusted).groupby(KEY, sort=False)
    n_scores = by_student["score"].size()
    scores = by_student["score"]
    out["difficulty_adjusted_score"] = by_student["_adj"].mean().reindex(out.index)
    out["score_rolling2_mean"] = (
        released.groupby(KEY, sort=False).tail(2).groupby(KEY)["score"].mean().reindex(out.index)
    )
    out["score_drop_from_best"] = (scores.max() - scores.last()).where(n_scores >= 2).reindex(out.index)
    out["score_volatility"] = scores.std(ddof=1).where(n_scores >= 3).reindex(out.index)
    return out


def _labels(info: pd.DataFrame, cutoff_day: int) -> dict[str, NDArray[np.float64]]:
    unreg = info["date_unregistration"].to_numpy(dtype=np.float64)
    withdrawn = (info["final_result"] == "Withdrawn").to_numpy()
    unknown_time = withdrawn & np.isnan(unreg)
    adverse = info["final_result"].isin({"Fail", "Withdrawn"}).to_numpy()
    labels: dict[str, NDArray[np.float64]] = {"y_academic": adverse.astype(np.float64)}
    for target, h in HORIZON_WEEKS.items():
        hit = (unreg > cutoff_day) & (unreg <= cutoff_day + h * DAYS_PER_WEEK)
        labels[label_column(target)] = np.where(unknown_time, np.nan, hit.astype(np.float64))
    return labels


def build_panel(
    tables: OuladTables,
    *,
    weeks: Sequence[int],
    score_release_lag_days: int,
    max_week: int = PANEL_MAX_WEEK,
) -> pd.DataFrame:
    """The student-week panel for the requested weeks (features float32; labels float, NaN = undefined)."""
    if not weeks or min(weeks) < 1 or max(weeks) > max_week:
        raise ValueError(f"weeks must be within 1..{max_week}")
    matrices = weekly_matrices(tables, max_week)
    activity = activity_feature_arrays(matrices)
    base = assessment_base(tables)
    row_index = matrices.keys.assign(_row=np.arange(len(matrices.keys), dtype=np.int64))
    info = (
        tables.registration[[*KEY, "date_unregistration"]]
        .merge(tables.student_info[[*KEY, "final_result"]], on=KEY, how="inner", validate="one_to_one")
        .merge(tables.courses, on=PRESENTATION_KEY, how="inner", validate="many_to_one")
    )
    frames: list[pd.DataFrame] = []
    for k in weeks:
        t = k * DAYS_PER_WEEK
        snap = build_oulad_features(
            tables,
            t,
            score_release_lag_days=score_release_lag_days,
            target="academic",
            feature_version=FEATURE_VERSION_V2,
        )
        module_presentation = snap["context_id"].str.split("-", n=1, expand=True)
        keyed = pd.DataFrame(
            {
                "code_module": module_presentation[0],
                "code_presentation": module_presentation[1],
                "id_student": snap["student_id"].astype(np.int64),
            }
        )
        keyed = keyed.merge(row_index, on=KEY, how="left", validate="one_to_one").merge(
            info, on=KEY, how="left", validate="one_to_one"
        )
        if keyed["_row"].isna().any() or keyed["final_result"].isna().any():
            raise ValueError(f"week {k}: population rows without a registration")
        rows = keyed["_row"].to_numpy(dtype=np.int64)
        week_frame = snap[list(ID_COLUMNS)].copy()
        for name in V2_FEATURE_NAMES:
            week_frame[name] = snap[name].to_numpy(dtype=np.float32)
        for spec in ACTIVITY_FEATURES:
            week_frame[spec.name] = activity[spec.name][rows, k].astype(np.float32)
        assess = assessment_features(base, t, score_release_lag_days)
        joined = keyed[KEY].merge(assess, left_on=KEY, right_index=True, how="left")
        for spec in ASSESSMENT_FEATURES:
            week_frame[spec.name] = joined[spec.name].to_numpy(dtype=np.float32)
        week_frame["missed_due_last_4w"] = week_frame["missed_due_last_4w"].fillna(0).astype(np.float32)
        for col, values in _labels(keyed, t).items():
            week_frame[col] = values
        if not np.array_equal(
            week_frame["y_academic"].to_numpy(), snap[TARGET_COLUMN].to_numpy(dtype=np.float64)
        ):
            raise ValueError(f"week {k}: academic label disagrees with the v2 target")
        week_frame["week"] = np.int64(k)
        week_frame["module"] = keyed["code_module"].to_numpy()
        unreg = keyed["date_unregistration"].to_numpy(dtype=np.float64)
        week_frame["withdraw_week"] = np.where(unreg > 0, np.ceil(unreg / DAYS_PER_WEEK), np.nan)
        week_frame["course_end_week"] = np.ceil(
            keyed["module_presentation_length"].to_numpy(dtype=np.float64) / DAYS_PER_WEEK
        )
        for attr in AUDIT_ATTRIBUTES:
            week_frame[f"{AUDIT_PREFIX}{attr}"] = snap[f"{AUDIT_PREFIX}{attr}"].to_numpy()
        frames.append(week_frame)
    panel = pd.concat(frames, ignore_index=True)
    # Repeated identifiers as categories: the full panel has ~750k rows.
    for col in (
        "student_id",
        "context_id",
        "split_group",
        "module",
        *(f"{AUDIT_PREFIX}{a}" for a in AUDIT_ATTRIBUTES),
    ):
        panel[col] = panel[col].astype("category")
    return panel.sort_values(["context_id", "student_id", "week"], kind="stable").reset_index(drop=True)


def assert_panel_no_leakage(tables: OuladTables, week: int, *, score_release_lag_days: int) -> int:
    """Rebuild ``week`` from tables truncated at its cutoff; every feature must be identical.

    Returns the number of rows compared."""
    full = build_panel(tables, weeks=[week], score_release_lag_days=score_release_lag_days)
    truncated = build_panel(
        truncate_at(tables, week * DAYS_PER_WEEK), weeks=[week], score_release_lag_days=score_release_lag_days
    )
    keys = list(KEY_COLUMNS)
    if not full[keys].equals(truncated[keys]):
        raise TemporalLeakageError(f"panel population at week {week} depends on future information")
    leaking = [
        name
        for name in TS_FEATURE_NAMES
        if not np.allclose(
            full[name].to_numpy(np.float64),
            truncated[name].to_numpy(np.float64),
            rtol=0,
            atol=1e-6,
            equal_nan=True,
        )
    ]
    if leaking:
        raise TemporalLeakageError(f"panel features use information after week {week}: {leaking}")
    return len(full)


def load_or_build_panel(
    tables: OuladTables,
    *,
    weeks: Sequence[int],
    score_release_lag_days: int,
    cache_dir: Path,
    dataset_version: str,
) -> pd.DataFrame:
    """Build the panel once per (dataset, feature version, weeks, lag) and cache it (git-ignored folder)."""
    span = f"w{min(weeks)}-{max(weeks)}-lag{score_release_lag_days}"
    name = f"panel-{dataset_version}-{FEATURE_VERSION_TS}-{span}.pkl"
    path = cache_dir / name
    if path.is_file():
        with path.open("rb") as handle:
            cached = pickle.load(handle)
        if not isinstance(cached, pd.DataFrame):
            raise TypeError(f"unexpected cache content in {path}")
        return cached
    panel = build_panel(tables, weeks=weeks, score_release_lag_days=score_release_lag_days)
    cache_dir.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        pickle.dump(panel, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return panel
