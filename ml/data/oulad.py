"""Loader for the Open University Learning Analytics Dataset (OULAD).

PROVENANCE — benchmark data: The Open University, United Kingdom, presentations 2013–2014,
licensed CC BY 4.0 (UCI Machine Learning Repository, dataset id 349; verified 2026-09-24).
It is NOT Indian data. Results obtained on it must never be described as evidence about
Indian students.

Missing values are encoded as "?" in the source files. Dates are integers: days relative
to the start of the module presentation (negative = before the start).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ml.data.contract import DataContractError

DATASET_NAME = "OULAD"
DATA_PROVENANCE = "benchmark"

EXPECTED_COLUMNS: dict[str, tuple[str, ...]] = {
    "courses.csv": ("code_module", "code_presentation", "module_presentation_length"),
    "assessments.csv": ("code_module", "code_presentation", "id_assessment", "assessment_type", "date", "weight"),
    "vle.csv": ("id_site", "code_module", "code_presentation", "activity_type", "week_from", "week_to"),
    "studentInfo.csv": (
        "code_module", "code_presentation", "id_student", "gender", "region", "highest_education",
        "imd_band", "age_band", "num_of_prev_attempts", "studied_credits", "disability", "final_result",
    ),
    "studentRegistration.csv": (
        "code_module", "code_presentation", "id_student", "date_registration", "date_unregistration",
    ),
    "studentAssessment.csv": ("id_assessment", "id_student", "date_submitted", "is_banked", "score"),
    "studentVle.csv": ("code_module", "code_presentation", "id_student", "id_site", "date", "sum_click"),
}

_NA = ["?", ""]
_PRESENTATION_RE = re.compile(r"^(\d{4})([BJ])$")

# OULAD vle.activity_type → activity group. 'questionnaire' is a survey, not a quiz.
QUIZ_ACTIVITIES = frozenset({"quiz", "externalquiz"})
FORUM_ACTIVITIES = frozenset({"forumng", "oucollaborate", "ouwiki", "ouelluminate"})
ACTIVITY_GROUPS = ("quiz", "forum", "content")


def activity_group(activity_type: str) -> str:
    if activity_type in QUIZ_ACTIVITIES:
        return "quiz"
    if activity_type in FORUM_ACTIVITIES:
        return "forum"
    return "content"


@dataclass(frozen=True)
class OuladTables:
    """The OULAD tables needed for feature construction.

    ``student_vle_daily`` is studentVle aggregated to one row per student per day (sum of clicks).
    ``student_vle_daily_groups`` splits the same clicks by activity group (see ACTIVITY_GROUPS).
    """

    courses: pd.DataFrame
    assessments: pd.DataFrame
    student_info: pd.DataFrame
    registration: pd.DataFrame
    student_assessment: pd.DataFrame
    student_vle_daily: pd.DataFrame
    # Same aggregation split by activity group (quiz / forum / content); used by feature set v2.
    student_vle_daily_groups: pd.DataFrame | None = None


def presentation_sort_key(code_presentation: str) -> tuple[int, int]:
    """Chronological order of presentations: 'B' (February) precedes 'J' (October) in a year."""
    match = _PRESENTATION_RE.match(code_presentation)
    if match is None:
        raise DataContractError(f"invalid code_presentation: {code_presentation!r}")
    return int(match.group(1)), 0 if match.group(2) == "B" else 1


def nominal_presentation_start(code_presentation: str) -> pd.Timestamp:
    """NOMINAL calendar start of a presentation.

    OULAD only records days relative to the presentation start. Per OULAD.names, 'B'
    presentations start in February and 'J' presentations in October; the 1st of that month
    is used as a nominal start so prediction dates can be ordered. It is not the true date.
    """
    year, half = presentation_sort_key(code_presentation)
    return pd.Timestamp(year=year, month=2 if half == 0 else 10, day=1)


def dataset_version(root: Path) -> str:
    """Content hash of all source files, e.g. ``oulad-1a2b3c4d5e6f7a8b``."""
    digest = hashlib.sha256()
    for name in sorted(EXPECTED_COLUMNS):
        path = root / name
        if not path.is_file():
            raise DataContractError(f"missing OULAD file: {path}")
        digest.update(name.encode())
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    return f"oulad-{digest.hexdigest()[:16]}"


def _read(root: Path, name: str, dtype: dict[str, str], usecols: tuple[str, ...] | None = None) -> pd.DataFrame:
    path = root / name
    if not path.is_file():
        raise DataContractError(f"missing OULAD file: {path}")
    header = tuple(pd.read_csv(path, nrows=0).columns)
    if header != EXPECTED_COLUMNS[name]:
        raise DataContractError(f"unexpected columns in {name}: {header}")
    return pd.read_csv(
        path,
        dtype=dtype,
        usecols=list(usecols) if usecols else None,
        na_values=_NA,
        keep_default_na=False,
    )


def load_oulad(root: Path) -> OuladTables:
    """Load and type-check the OULAD CSV files from ``root``."""
    if not root.is_dir():
        raise DataContractError(f"dataset directory not found: {root}")

    courses = _read(root, "courses.csv", {"code_module": "str", "code_presentation": "str",
                                          "module_presentation_length": "int64"})
    assessments = _read(root, "assessments.csv", {
        "code_module": "str", "code_presentation": "str", "id_assessment": "int64",
        "assessment_type": "str", "date": "float64", "weight": "float64",
    })
    student_info = _read(root, "studentInfo.csv", {
        "code_module": "str", "code_presentation": "str", "id_student": "int64", "gender": "str",
        "region": "str", "highest_education": "str", "imd_band": "str", "age_band": "str",
        "num_of_prev_attempts": "int64", "studied_credits": "int64", "disability": "str",
        "final_result": "str",
    })
    registration = _read(root, "studentRegistration.csv", {
        "code_module": "str", "code_presentation": "str", "id_student": "int64",
        "date_registration": "float64", "date_unregistration": "float64",
    })
    student_assessment = _read(root, "studentAssessment.csv", {
        "id_assessment": "int64", "id_student": "int64", "date_submitted": "float64",
        "is_banked": "int64", "score": "float64",
    })
    vle = _read(
        root,
        "studentVle.csv",
        {"code_module": "category", "code_presentation": "category", "id_student": "int32",
         "id_site": "int32", "date": "int32", "sum_click": "int32"},
        usecols=("code_module", "code_presentation", "id_student", "id_site", "date", "sum_click"),
    )
    sites = _read(root, "vle.csv", {"id_site": "int32", "code_module": "str", "code_presentation": "str",
                                    "activity_type": "str", "week_from": "float64", "week_to": "float64"})
    site_groups = pd.Series(
        [activity_group(str(a)) for a in sites["activity_type"]], index=sites["id_site"].to_numpy(), dtype="category"
    )
    vle["activity_group"] = site_groups.reindex(vle["id_site"].to_numpy()).to_numpy()
    if vle["activity_group"].isna().any():
        raise DataContractError("studentVle references sites missing from vle.csv")
    student_vle_daily_groups = (
        vle.groupby(["code_module", "code_presentation", "id_student", "date", "activity_group"],
                    observed=True, sort=False)["sum_click"]
        .sum()
        .reset_index()
    )
    for col in ("code_module", "code_presentation", "activity_group"):
        student_vle_daily_groups[col] = student_vle_daily_groups[col].astype("str")
    for col in ("id_student", "date", "sum_click"):
        student_vle_daily_groups[col] = student_vle_daily_groups[col].astype("int64")
    student_vle_daily = (
        vle.groupby(["code_module", "code_presentation", "id_student", "date"], observed=True, sort=False)["sum_click"]
        .sum()
        .reset_index()
    )
    student_vle_daily["code_module"] = student_vle_daily["code_module"].astype("str")
    student_vle_daily["code_presentation"] = student_vle_daily["code_presentation"].astype("str")
    student_vle_daily["id_student"] = student_vle_daily["id_student"].astype("int64")
    student_vle_daily["date"] = student_vle_daily["date"].astype("int64")
    student_vle_daily["sum_click"] = student_vle_daily["sum_click"].astype("int64")

    valid_results = {"Pass", "Distinction", "Fail", "Withdrawn"}
    unexpected = set(student_info["final_result"].dropna().unique()) - valid_results
    if unexpected or student_info["final_result"].isna().any():
        raise DataContractError(f"unexpected final_result values: {sorted(unexpected)}")
    for code in pd.concat([courses["code_presentation"], student_info["code_presentation"]]).unique():
        presentation_sort_key(str(code))

    return OuladTables(
        courses=courses,
        assessments=assessments,
        student_info=student_info,
        registration=registration,
        student_assessment=student_assessment,
        student_vle_daily=student_vle_daily,
        student_vle_daily_groups=student_vle_daily_groups,
    )


def truncate_at(tables: OuladTables, cutoff_day: int) -> OuladTables:
    """A copy of the tables containing ONLY information available on or before ``cutoff_day``.

    Used by the leakage guard: features built from these tables must equal features built from the
    full tables. ``final_result`` is kept because it is the target, never a feature.
    """
    t = int(cutoff_day)
    reg = tables.registration.copy()
    reg.loc[reg["date_unregistration"] > t, "date_unregistration"] = float("nan")
    sa = tables.student_assessment
    groups = tables.student_vle_daily_groups
    return OuladTables(
        courses=tables.courses,
        assessments=tables.assessments,
        student_info=tables.student_info,
        registration=reg,
        student_assessment=sa[sa["date_submitted"].notna() & (sa["date_submitted"] <= t)].reset_index(drop=True),
        student_vle_daily=tables.student_vle_daily[tables.student_vle_daily["date"] <= t].reset_index(drop=True),
        student_vle_daily_groups=None if groups is None else groups[groups["date"] <= t].reset_index(drop=True),
    )
