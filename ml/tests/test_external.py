"""External benchmark datasets: loaders, feature policy, derived features and an end-to-end run.
ALL DATA HERE IS SYNTHETIC, written in the exact UCI 697 / UCI 320 file formats. Not a result."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np
import pytest

from ml.data.contract import DataContractError
from ml.external import uci
from ml.external.experiment import ExternalConfig, run

POLICY_EXCLUDED_A = ("gender", "age", "marital", "nacionality", "nationality", "international", "displaced",
                     "special", "mother", "father", "debtor", "fees", "scholarship")  # fmt: skip


def _write_a(path: Path, n: int = 400, seed: int = 1) -> Path:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        risk = float(rng.uniform())
        enrolled = 0 if i % 25 == 0 else 6
        approved1 = int(np.clip(round(6 * (1 - risk) + rng.normal(0, 1)), 0, enrolled))
        approved2 = int(np.clip(round(6 * (1 - risk) + rng.normal(0, 1)), 0, enrolled))
        target = "Dropout" if risk + rng.normal(0, 0.15) > 0.7 else ("Enrolled" if risk > 0.5 else "Graduate")
        cohort = i % 3
        row = [
            1, int(rng.choice([1, 17, 39])), int(rng.integers(0, 6)), int(rng.choice([171, 9254, 9500])), 1,
            int(rng.choice([1, 3])), round(float(rng.uniform(95, 190)), 1), 1, 1, 1, 1, 1,
            round(float(rng.uniform(95, 190)), 1), int(rng.integers(0, 2)), 0, int(rng.uniform() < risk / 3),
            int(rng.uniform() > risk / 3), int(i % 2), int(rng.uniform() < 0.25),
            int(rng.integers(18, 40)), 0,
            0, enrolled, enrolled + 1, approved1, round(10 + 4 * (1 - risk), 2) if approved1 else 0, 0,
            0, enrolled, enrolled + 1, approved2, round(10 + 4 * (1 - risk), 2) if approved2 else 0, 0,
            [10.8, 13.9, 7.6][cohort], [1.4, -0.3, 2.6][cohort], [1.74, 0.79, 0.32][cohort], target,
        ]  # fmt: skip
        rows.append(row)
    header = list(uci.A_COLUMNS)
    header[4] = "Daytime/evening attendance\t"  # the real file has a stray tab in this header
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(header)
        writer.writerows(rows)
    return path


def _write_b(path: Path, n: int = 200, seed: int = 2) -> Path:
    rng = np.random.default_rng(seed)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter=";", quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(uci.B_COLUMNS)
        for i in range(n):
            ability = float(rng.uniform(4, 18))
            g1 = int(np.clip(round(ability + rng.normal(0, 1.5)), 0, 20))
            g2 = int(np.clip(round(ability + rng.normal(0, 1.5)), 0, 20))
            g3 = int(np.clip(round(ability + rng.normal(0, 1.5)), 0, 20))
            writer.writerow(
                [
                    "GP" if i % 3 else "MS", "F" if i % 2 else "M", int(rng.integers(15, 20)),
                    "U" if i % 4 else "R",
                    "GT3", "T", 2, 2, "other", "other", "course", "mother", 1, int(rng.integers(1, 5)),
                    int(ability < 7), "no", "yes", "no", "yes", "yes", "yes", "yes", "no", 4, 3, 3, 1, 1, 3,
                    int(rng.integers(0, 10)), str(g1), str(g2), g3,
                ]
            )  # fmt: skip
    return path


def test_dropout_loader_verifies_checksum_and_schema(tmp_path: Path) -> None:
    path = _write_a(tmp_path / "data.csv")
    raw = uci.load_dropout(path, expected_sha256=uci.sha256(path))
    assert tuple(raw.columns) == uci.A_COLUMNS  # stray tab and BOM handled
    with pytest.raises(DataContractError, match="SHA-256"):
        uci.load_dropout(path, expected_sha256="0" * 64)
    bad = tmp_path / "bad.csv"
    bad.write_text("a;b\n1;2\n", encoding="utf-8")
    with pytest.raises(DataContractError, match="columns"):
        uci.load_dropout(bad, expected_sha256=None)


def test_dropout_features_by_hand_and_policy(tmp_path: Path) -> None:
    frame = uci.dropout_frame(uci.load_dropout(_write_a(tmp_path / "data.csv"), expected_sha256=None))
    row = frame.iloc[1]
    assert row["sem1_approval_rate"] == pytest.approx(row["sem1_approved"] / row["sem1_enrolled"])
    assert row["sem1_failed"] == row["sem1_enrolled"] - row["sem1_approved"]
    assert row["approval_rate_change"] == pytest.approx(row["sem2_approval_rate"] - row["sem1_approval_rate"])
    assert np.isnan(frame.iloc[0]["sem1_approval_rate"])  # 0 units enrolled: rate undefined
    assert frame["cohort"].nunique() == 3
    points = uci.dropout_decision_points(frame)
    assert set(points["D0"]) < set(points["D1"]) < set(points["D2"])
    assert not any(f.startswith("sem") for f in points["D0"])
    for features in points.values():
        assert not any(word in f for f in features for word in POLICY_EXCLUDED_A)
        assert not any(f.startswith(("audit_", "y_")) for f in features)
        assert len(features) == len(set(features))
    assert not uci.dropout_population(frame, "D1").iloc[0]  # 0 units enrolled in semester 1
    assert uci.dropout_population(frame, "D0").all()


def test_performance_features_and_policy(tmp_path: Path) -> None:
    frame = uci.performance_frame(uci.load_performance(_write_b(tmp_path / "por.csv"), expected_sha256=None))
    assert set(frame["y_fail"].unique()) <= {0, 1}
    for features in uci.PERFORMANCE_POINTS.values():
        assert "absences" not in features  # recording time unknown: sensitivity only
        assert not set(features) & {"sex", "age", "address", "Dalc", "Walc", "romantic", "health"}
    assert uci.PERFORMANCE_POINTS["P1"][-1] == "g1"
    assert uci.PERFORMANCE_POINTS["P2"][-1] == "g2"


def test_end_to_end_on_synthetic_files(tmp_path: Path) -> None:
    a = _write_a(tmp_path / "a.csv")
    por, mat = _write_b(tmp_path / "por.csv"), _write_b(tmp_path / "mat.csv", seed=3)
    config = ExternalConfig.model_validate(
        {
            "run_name": "synthetic-external",
            "dropout": {"path": str(a), "sha256": uci.sha256(a)},
            "performance_portuguese": {"path": str(por), "sha256": uci.sha256(por)},
            "performance_math": {"path": str(mat), "sha256": uci.sha256(mat)},
            "validation_share": 0.15,
            "test_share": 0.15,
            "xgb_search_settings": 2,
            "bootstrap_resamples": 50,
            "cv_folds": 3,
            "cv_repeats": 2,
            "random_seed": 1,
            "report_dir": str(tmp_path / "reports"),
        }
    )
    out = run(config, tmp_path)
    results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    comparisons = results["dataset_a"]["comparisons"]
    assert set(comparisons) == {"E1", "E2", "E3"}
    assert all("p_holm" in c for c in comparisons.values())
    assert set(results["dataset_a"]["points"]) == {"D0", "D1", "D2"}
    assert set(results["performance_portuguese"]["points"]) == {"P0", "P1", "P2", "P2_with_absences"}
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "Provenance: BENCHMARK" in report
    # No student ids (a0, b17, ...) in the outputs; the config section (paths, checksums) is excluded.
    text = report + json.dumps({k: v for k, v in results.items() if k != "config"})
    assert not re.search(r"\b[ab]\d+\b", text)
