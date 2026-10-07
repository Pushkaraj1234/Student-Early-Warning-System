"""End-to-end run of the v3 experiment on SYNTHETIC data with tiny settings: every stage executes, the report
and artifacts are written, and the report contains no student identifiers. Not a result."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

from ml.longitudinal import score
from ml.longitudinal.config import LongitudinalConfig
from ml.longitudinal.counterfactual import ACTIONABLE
from ml.longitudinal.evaluation import RankedScores
from ml.longitudinal.experiment import run
from ml.longitudinal.panel import TS_FEATURE_NAMES


def test_ranked_scores_match_sklearn_weighted_average_precision() -> None:
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 500).astype(np.int64)
    p = np.round(rng.uniform(size=500), 2)  # ties
    ranked = RankedScores(y, p)
    for _ in range(5):
        w = rng.integers(0, 3, 500).astype(np.float64)  # includes zero weights, like a bootstrap resample
        assert ranked.ap(w) == pytest.approx(average_precision_score(y, p, sample_weight=w), abs=1e-12)


def test_actionable_features_exist() -> None:
    assert set(ACTIONABLE) <= set(TS_FEATURE_NAMES)


def test_full_experiment_on_synthetic_data(synthetic_dir: Path, tmp_path: Path) -> None:
    config = LongitudinalConfig.model_validate(
        {
            "run_name": "synthetic-ts",
            "dataset": {
                "name": "OULAD",
                "path": str(synthetic_dir),
                "provenance": "synthetic",
                "description": "Synthetic OULAD-format test data (not real students).",
            },
            "first_week": 1,
            "last_week": 12,
            "score_release_lag_days": 14,
            "split": {"train": ["2013B", "2013J"], "validation": ["2014B"], "test": ["2014J"]},
            "rolling_origin": [
                {"train": ["2013B"], "test": ["2013J"]},
                {"train": ["2013B", "2013J"], "test": ["2014B"]},
            ],
            "lomo_train": ["2013B", "2013J", "2014B"],
            "lomo_test": ["2014J"],
            "leakage_check_weeks": [2, 6],
            "xgb_search_settings": 2,
            "sequence_grid": {
                "kinds": ["gru"],
                "hidden": [8],
                "dropout": [0.1],
                "max_epochs": 2,
                "patience": 1,
            },
            "mc_dropout_samples": 3,
            "cost_ratios": [2, 5],
            "primary_cost_ratio": 5,
            "risk_level_quantiles": [0.5, 0.75, 0.9],
            "counterfactual_week": 6,
            "counterfactual_sample": 5,
            "explain_sample": 100,
            "bootstrap_resamples": 50,
            "random_seed": 1,
            "cache_dir": str(tmp_path / "cache"),
            "output_dir": str(tmp_path / "artifacts"),
            "report_dir": str(tmp_path / "reports"),
        }
    )
    report_dir = run(config, tmp_path)
    results = json.loads((report_dir / "results.json").read_text(encoding="utf-8"))
    assert results["leakage_guard"]["passed"]
    assert results["lomo"]["skipped"]  # one synthetic module: P5 cannot run
    assert set(results["holm_family"]) == {"P1", "P2", "P4"}
    assert set(results["academic"]["models"]) >= {"xgb_v2", "xgb_ts", "l1_ts", "rf_ts", "gru", "ensemble"}
    report = (report_dir / "report.md").read_text(encoding="utf-8")
    assert "Provenance: SYNTHETIC" in report
    for chart in ("pr_auc_by_week.png", "kaplan_meier.png", "shap_importance.png"):
        assert (report_dir / chart).is_file()
    # Aggregates only: no synthetic student id (100000+) appears as a value in the report or the results
    # (digits inside longer numbers such as 0.8100053 are not identifiers).
    ids = {str(100000 + p * 1000 + i) for p in range(4) for i in range(80)}
    text = report + json.dumps(results)
    assert not any(re.search(rf"(?<![\d.]){i}(?!\d)", text) for i in ids)
    artifact = Path(config.output_dir) / results["artifacts"]["xgb_ts"]
    metadata = json.loads((artifact / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["approved_for_real_students"] is False
    assert metadata["feature_names"] == list(TS_FEATURE_NAMES)
    # A resumed run reuses every cached stage and reproduces the same numbers.
    again = run(config, tmp_path, resume=results["run_id"])
    repeat = json.loads((again / "results.json").read_text(encoding="utf-8"))
    assert repeat["academic"]["models"]["xgb_ts"]["test"] == results["academic"]["models"]["xgb_ts"]["test"]

    # Weekly batch scoring with the saved artifact (deployment prototype).
    out_csv = tmp_path / "scores.csv"
    common = ["--artifact", str(artifact), "--dataset", str(synthetic_dir), "--presentations", "2014J"]
    assert score.main([*common, "--data-provenance", "synthetic", "--week", "6", "--out", str(out_csv)]) == 0
    scores = pd.read_csv(out_csv)
    assert len(scores) > 0 and set(scores["week"]) == {6}
    assert set(scores["tier"]) <= set(score.TIERS) and scores["risk"].between(0, 1).all()
    # A benchmark/synthetic-trained model refuses real (institutional) students.
    assert score.main([*common, "--data-provenance", "institutional", "--week", "6"]) == 3
    # A model file that does not match its recorded SHA-256 is never unpickled.
    model_file = artifact / "model.joblib"
    model_file.write_bytes(model_file.read_bytes() + b"tampered")
    assert score.main([*common, "--data-provenance", "synthetic", "--week", "6", "--out", str(out_csv)]) == 3
