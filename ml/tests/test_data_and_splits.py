"""Loader, data contract and out-of-time split tests (synthetic data only)."""

from __future__ import annotations

import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.data.contract import DataContractError, validate_feature_table
from ml.data.oulad import dataset_version, load_oulad, nominal_presentation_start, presentation_sort_key
from ml.features.definitions import FEATURE_NAMES
from ml.features.oulad_features import build_oulad_features
from ml.training.splits import SplitError, TemporalSplit, split_frame

# ------------------------------------------------------------------------ loader


def test_loader_parses_question_marks_as_missing(synthetic_dir: Path) -> None:
    tables = load_oulad(synthetic_dir)
    assert tables.assessments.loc[tables.assessments["assessment_type"] == "Exam", "date"].isna().all()
    assert tables.registration["date_unregistration"].isna().any()
    assert tables.student_info["imd_band"].isna().any()
    assert tables.student_vle_daily["sum_click"].dtype == np.int64


def test_dataset_version_is_content_addressed(synthetic_dir: Path, tmp_path: Path) -> None:
    copy = tmp_path / "copy"
    shutil.copytree(synthetic_dir, copy)
    assert dataset_version(copy) == dataset_version(synthetic_dir)
    with (copy / "courses.csv").open("a", encoding="utf-8") as handle:
        handle.write('"SYN","2015B","200"\n')
    assert dataset_version(copy) != dataset_version(synthetic_dir)


def test_loader_rejects_missing_file_and_wrong_header(synthetic_dir: Path, tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    shutil.copytree(synthetic_dir, missing)
    (missing / "studentVle.csv").unlink()
    with pytest.raises(DataContractError):
        load_oulad(missing)
    bad = tmp_path / "bad"
    shutil.copytree(synthetic_dir, bad)
    (bad / "courses.csv").write_text('"a","b","c"\n', encoding="utf-8")
    with pytest.raises(DataContractError):
        load_oulad(bad)
    with pytest.raises(DataContractError):
        load_oulad(tmp_path / "does-not-exist")


def test_presentation_ordering_and_nominal_dates() -> None:
    assert presentation_sort_key("2013B") < presentation_sort_key("2013J") < presentation_sort_key("2014B")
    assert nominal_presentation_start("2014J") == pd.Timestamp("2014-10-01")
    assert nominal_presentation_start("2013B") == pd.Timestamp("2013-02-01")
    with pytest.raises(DataContractError):
        presentation_sort_key("2014X")


# ---------------------------------------------------------------------- contract


@pytest.fixture(scope="module")
def feature_table(synthetic_dir: Path) -> pd.DataFrame:
    return build_oulad_features(load_oulad(synthetic_dir), 60, score_release_lag_days=14)


def test_synthetic_feature_table_satisfies_contract(feature_table: pd.DataFrame) -> None:
    validate_feature_table(feature_table, FEATURE_NAMES)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda df: df.drop(columns=["student_id"]),
        lambda df: df.drop(columns=[FEATURE_NAMES[0]]),
        lambda df: df.iloc[0:0],
        lambda df: pd.concat([df, df.iloc[[0]]]),
        lambda df: df.assign(**{FEATURE_NAMES[0]: math.inf}),
        lambda df: df.assign(**{FEATURE_NAMES[0]: True}),
        lambda df: df.assign(**{FEATURE_NAMES[0]: "high"}),
        lambda df: df.assign(target=2),
        lambda df: df.assign(prediction_date="2014-01-01"),
        lambda df: df.assign(cutoff_day=-1),
    ],
    ids=[
        "no-id",
        "no-feature",
        "empty",
        "duplicate-key",
        "inf",
        "bool",
        "string",
        "bad-target",
        "date-not-datetime",
        "negative-cutoff",
    ],
)
def test_contract_violations_are_rejected(feature_table: pd.DataFrame, mutate: object) -> None:
    with pytest.raises(DataContractError):
        validate_feature_table(mutate(feature_table.copy()), FEATURE_NAMES)  # type: ignore[operator]


def test_audit_column_cannot_be_a_feature(feature_table: pd.DataFrame) -> None:
    with pytest.raises(DataContractError):
        validate_feature_table(feature_table, (*FEATURE_NAMES, "audit_gender"))


# ------------------------------------------------------------------------- splits


def test_out_of_time_split_assigns_groups(feature_table: pd.DataFrame) -> None:
    frames = split_frame(feature_table, TemporalSplit(("2013B", "2013J"), ("2014B",), ("2014J",)))
    assert set(frames.train["split_group"]) == {"2013B", "2013J"}
    assert set(frames.validation["split_group"]) == {"2014B"}
    assert set(frames.test["split_group"]) == {"2014J"}
    assert frames.unassigned_rows == 0
    assert len(frames.train) + len(frames.validation) + len(frames.test) == len(feature_table)


@pytest.mark.parametrize(
    "split",
    [
        TemporalSplit(("2014B",), ("2013J",), ("2014J",)),  # validation before train
        TemporalSplit(("2013B",), ("2014J",), ("2014B",)),  # test before validation
        TemporalSplit(("2013B", "2014B"), ("2014B",), ("2014J",)),  # overlap
        TemporalSplit(("2013B", "2014J"), ("2014B",), ("2014J",)),  # future group in training
        TemporalSplit((), ("2014B",), ("2014J",)),  # empty
    ],
)
def test_non_temporal_splits_are_rejected(feature_table: pd.DataFrame, split: TemporalSplit) -> None:
    with pytest.raises(SplitError):
        split_frame(feature_table, split)


def test_split_with_no_rows_for_a_group_is_rejected(feature_table: pd.DataFrame) -> None:
    with pytest.raises(SplitError):
        split_frame(feature_table, TemporalSplit(("2011B",), ("2012B",), ("2014J",)))
