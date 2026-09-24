"""Cross-group (leave-one-group-out) framework on SYNTHETIC in-memory data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.training.cross_group import SCOPE_STATEMENT, leave_one_group_out, module_of, render_markdown

NAMES = ("f1", "f2")


def _frame() -> pd.DataFrame:
    """Modules A-E: outcome driven by f1. Module Z: outcome driven by f2 (a group unlike the
    others). Module T: too small to evaluate."""
    rng = np.random.default_rng(3)
    parts = []
    for module, n in (*((m, 300) for m in "ABCDE"), ("Z", 900), ("T", 8)):
        for pres in ("2013B", "2013J", "2014J"):
            f1, f2 = rng.normal(size=n), rng.normal(size=n)
            signal = f2 if module == "Z" else f1
            y = (signal + rng.normal(scale=0.5, size=n) > 0.8).astype(np.int64)
            parts.append(
                pd.DataFrame(
                    {
                        "context_id": f"{module}-{pres}",
                        "split_group": pres,
                        "f1": f1,
                        "f2": f2,
                        "target": y,
                    }
                )
            )
    return pd.concat(parts, ignore_index=True)


def _run(df: pd.DataFrame) -> dict:  # type: ignore[type-arg]
    return leave_one_group_out(
        df,
        NAMES,
        train_groups=("2013B", "2013J"),
        test_groups=("2014J",),
        model_name="logistic_regression",
        seed=0,
        min_class_count=20,
    )


def test_module_of_parses_context_id() -> None:
    assert module_of(pd.DataFrame({"context_id": ["AAA-2013J", "BBB-2014B"]})).tolist() == ["AAA", "BBB"]


def test_unlike_group_shows_degradation_and_small_group_is_skipped() -> None:
    result = _run(_frame())
    by_group = {r["group"]: r for r in result["groups"]}
    assert by_group["T"]["skipped"] is True and "fewer than 20" in by_group["T"]["reason"]
    assert result["groups_evaluated"] == 6 and result["groups_skipped"] == 1
    like = [by_group[m]["degradation"]["pr_auc"] for m in "ABCDE"]
    unlike = by_group["Z"]["degradation"]["pr_auc"]
    # leaving out one of five similar modules costs little; the unlike module degrades clearly
    assert max(abs(v) for v in like) < 0.1
    assert unlike > 0.15 and unlike > 2 * max(abs(v) for v in like)
    assert result["degradation_summary"]["pr_auc"]["max"] == pytest.approx(unlike)


def test_overlapping_time_groups_are_rejected() -> None:
    with pytest.raises(ValueError, match="must not overlap"):
        leave_one_group_out(
            _frame(),
            NAMES,
            train_groups=("2013B", "2014J"),
            test_groups=("2014J",),
            model_name="logistic_regression",
            seed=0,
            min_class_count=20,
        )


def test_report_states_it_is_not_cross_institution() -> None:
    result = {
        **_run(_frame()),
        "run_id": "cross-module-test",
        "dataset": {"provenance": "synthetic", "version": "syn-1"},
        "target": "academic",
        "target_definition": "synthetic",
        "cutoff_day": 60,
        "model_name": "logistic_regression",
        "train_groups": ["2013B", "2013J"],
        "test_groups": ["2014J"],
    }
    text = render_markdown(result)
    assert SCOPE_STATEMENT in text
    assert "NOT cross-institution" in text
    assert "| T | " in text and "skipped" in text
