"""Test fixtures. ALL DATA HERE IS SYNTHETIC — generated in OULAD's file format so the pipeline
can be exercised end to end without real student records. Nothing here is a benchmark result."""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.data.oulad import EXPECTED_COLUMNS, OuladTables

SYN_PRESENTATIONS = ("2013B", "2013J", "2014B", "2014J")
SYN_MODULE = "SYN"
DUE_DAYS = (20, 50, 80, 110)


def _write(path: Path, header: tuple[str, ...], rows: Sequence[Sequence[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        writer.writerows(["?" if v is None else v for v in row] for row in rows)


def write_synthetic_oulad(root: Path, *, per_presentation: int = 80, seed: int = 7) -> Path:
    """Write a small synthetic dataset in OULAD format. Outcomes depend on a latent risk that
    also drives engagement and submissions, so models have signal to learn."""
    rng = np.random.default_rng(seed)
    root.mkdir(parents=True, exist_ok=True)
    courses, assessments, vle_sites, info, registration, student_assessment, student_vle = (
        [] for _ in range(7)
    )
    assessment_id = 5000
    site_id = 9000
    for p_index, pres in enumerate(SYN_PRESENTATIONS):
        courses.append([SYN_MODULE, pres, 200])
        ids = []
        for due in DUE_DAYS:
            assessments.append([SYN_MODULE, pres, assessment_id, "TMA", due, 25.0])
            ids.append((assessment_id, due))
            assessment_id += 1
        assessments.append([SYN_MODULE, pres, assessment_id, "Exam", None, 100.0])
        assessment_id += 1
        vle_sites.append([site_id, SYN_MODULE, pres, "resource", None, None])
        for i in range(per_presentation):
            student = 100000 + p_index * 1000 + i
            risk = float(rng.uniform())
            adverse = risk + rng.normal(0, 0.15) > 0.6
            withdrawn = bool(adverse and rng.uniform() < 0.4)
            result = (
                ("Withdrawn" if withdrawn else "Fail")
                if adverse
                else ("Distinction" if risk < 0.1 else "Pass")
            )
            unreg = int(rng.integers(15, 150)) if withdrawn else None
            info.append(
                [
                    SYN_MODULE,
                    pres,
                    student,
                    "F" if i % 2 else "M",
                    "Synthetic Region",
                    "A Level or Equivalent",
                    None if i % 7 == 0 else "20-30%",
                    "0-35",
                    int(rng.uniform() < 0.2),
                    60,
                    "N",
                    result,
                ]
            )
            registration.append([SYN_MODULE, pres, student, int(rng.integers(-40, -1)), unreg])
            last_day = unreg if unreg is not None else 199
            for day in range(-5, last_day):
                if rng.uniform() < 0.75 - 0.6 * risk:
                    student_vle.append([SYN_MODULE, pres, student, site_id, day, int(rng.integers(1, 6))])
            for aid, due in ids:
                if (unreg is None or due < unreg) and rng.uniform() < 0.95 - 0.6 * risk:
                    delay = int(rng.integers(-5, 3)) + (int(rng.integers(0, 10)) if risk > 0.5 else 0)
                    score = (
                        None
                        if rng.uniform() < 0.02
                        else round(float(np.clip(90 - 60 * risk + rng.normal(0, 8), 0, 100)))
                    )
                    student_assessment.append([aid, student, due + delay, 0, score])
        site_id += 1
    # One banked result carried over from an earlier attempt.
    student_assessment.append([5000, 101000, -10, 1, 70])

    _write(root / "courses.csv", EXPECTED_COLUMNS["courses.csv"], courses)
    _write(root / "assessments.csv", EXPECTED_COLUMNS["assessments.csv"], assessments)
    _write(root / "vle.csv", EXPECTED_COLUMNS["vle.csv"], vle_sites)
    _write(root / "studentInfo.csv", EXPECTED_COLUMNS["studentInfo.csv"], info)
    _write(root / "studentRegistration.csv", EXPECTED_COLUMNS["studentRegistration.csv"], registration)
    _write(root / "studentAssessment.csv", EXPECTED_COLUMNS["studentAssessment.csv"], student_assessment)
    _write(root / "studentVle.csv", EXPECTED_COLUMNS["studentVle.csv"], student_vle)
    return root


@pytest.fixture(scope="session")
def synthetic_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_synthetic_oulad(tmp_path_factory.mktemp("synthetic_oulad"))


def make_tables(
    *,
    vle: Sequence[tuple[int, int, int]] | None = None,
    submissions: Sequence[tuple[int, int, float | None, float | None, int]] | None = None,
    registrations: Sequence[tuple[int, float | None, float | None]] | None = None,
    results: dict[int, str] | None = None,
) -> OuladTables:
    """Hand-built minimal tables for exact leakage tests (module 'SYN', presentation '2014J').

    vle:          (id_student, date, clicks)
    submissions:  (id_assessment, id_student, date_submitted, score, is_banked)
    registrations:(id_student, date_registration, date_unregistration)
    Assessments: 1 due day 20, 2 due day 50, 3 due day 90 (TMA); 4 = Exam (no date).
    """
    registrations = registrations or [(1, -10.0, None), (2, -5.0, None)]
    results = results or {s: "Pass" for s, _, _ in registrations}
    key = {"code_module": "SYN", "code_presentation": "2014J"}
    return OuladTables(
        courses=pd.DataFrame([{**key, "module_presentation_length": 200}]),
        assessments=pd.DataFrame(
            [
                {**key, "id_assessment": 1, "assessment_type": "TMA", "date": 20.0, "weight": 25.0},
                {**key, "id_assessment": 2, "assessment_type": "TMA", "date": 50.0, "weight": 25.0},
                {**key, "id_assessment": 3, "assessment_type": "TMA", "date": 90.0, "weight": 25.0},
                {**key, "id_assessment": 4, "assessment_type": "Exam", "date": np.nan, "weight": 100.0},
            ]
        ),
        student_info=pd.DataFrame(
            [
                {
                    **key,
                    "id_student": s,
                    "gender": "F",
                    "region": "R",
                    "highest_education": "HE",
                    "imd_band": "20-30%",
                    "age_band": "0-35",
                    "num_of_prev_attempts": 0,
                    "studied_credits": 60,
                    "disability": "N",
                    "final_result": results[s],
                }
                for s, _, _ in registrations
            ]
        ),
        registration=pd.DataFrame(
            [
                {**key, "id_student": s, "date_registration": r, "date_unregistration": u}
                for s, r, u in registrations
            ]
        ).astype({"date_registration": "float64", "date_unregistration": "float64"}),
        student_assessment=pd.DataFrame(
            [
                {"id_assessment": a, "id_student": s, "date_submitted": d, "is_banked": b, "score": sc}
                for a, s, d, sc, b in (submissions or [])
            ],
            columns=["id_assessment", "id_student", "date_submitted", "is_banked", "score"],
        ).astype({"date_submitted": "float64", "score": "float64", "is_banked": "int64"}),
        student_vle_daily=pd.DataFrame(
            [{**key, "id_student": s, "date": d, "sum_click": c} for s, d, c in (vle or [])],
            columns=["code_module", "code_presentation", "id_student", "date", "sum_click"],
        ).astype({"id_student": "int64", "date": "int64", "sum_click": "int64"}),
    )
