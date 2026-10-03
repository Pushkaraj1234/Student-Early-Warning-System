"""Institutional training from the SEWS database. ALL DATA IS SYNTHETIC (sews_services.training.synthetic).

One module-level run generates a synthetic multi-term history in a rebuilt local database and trains on it
through the command line, exactly as an operator would; the tests then check what that run produced.
"""

from __future__ import annotations

import contextlib
import io
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import psycopg
import pytest
from sews_services.db import Connection, connect
from sews_services.features.institutional import DEFAULT_TZ
from sews_services.jobs.cli import EXIT_OK, main
from sews_services.jobs.scoring import score_institution
from sews_services.training.config import InstitutionalTrainingConfig
from sews_services.training.history import (
    Term,
    build_training_tables,
    completed_terms,
    load_term_history,
    term_sort_key,
    term_students,
)
from sews_services.training.synthetic import SyntheticRefusedError, generate
from sews_services.training.synthetic import main as synthetic_main
from sews_services.training.train import TrainingRefusedError, plan_split, train_institution

from ml.models.registry import ModelRegistry
from tests.conftest import dev_settings

NOW = datetime.now(UTC)
TODAY = NOW.astimezone(DEFAULT_TZ).date()
SMALL_CONFIG: dict[str, Any] = {
    "run_name": "inst-test",
    "cutoff_days": [30, 60],
    "min_label_coverage": 0.8,
    "min_class_count_per_split": 10,
    "models": ["logistic_regression", "xgboost"],
    "imbalance_strategies": ["none"],
    "calibration_method": "sigmoid",
    "risk_level_quantiles": {"watch": 0.5, "elevated": 0.75, "high": 0.9},
    "top_fractions": [0.1, 0.2],
    "selection_tolerance_pr_auc": 0.01,
    "stability_seeds": [0, 1],
    "bootstrap_iterations": 50,
    "random_seed": 11,
}


@pytest.fixture(scope="module")
def history(db_url: str) -> dict[str, Any]:
    with connect(db_url) as c:
        return generate(c, students=160, seed=3, today=TODAY)


@pytest.fixture(scope="module")
def trained(db_url: str, history: dict[str, Any], tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("train")
    config = root / "config.json"
    config.write_text(json.dumps(SMALL_CONFIG), encoding="utf-8")
    env = {"SEWS_ENV": "development", "SEWS_DATABASE_URL": db_url, "SEWS_MODEL_REGISTRY_ROOT": str(root / "registry")}
    argv = [
        "train",
        "--institution",
        str(history["institution_id"]),
        "--data-provenance",
        "synthetic",
        "--config",
        str(config),
        "--report-dir",
        str(root / "reports"),
    ]
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv, env=env)
    return {"code": code, "stdout": out.getvalue(), "stderr": err.getvalue(), "root": root}


def _summary(trained: dict[str, Any]) -> dict[str, Any]:
    lines = trained["stdout"].strip().splitlines()
    assert len(lines) == 1, "stdout must be exactly one JSON line"
    parsed: dict[str, Any] = json.loads(lines[0])
    return parsed


def _first_term(conn: Connection, institution_id: str) -> Term:
    return completed_terms(conn, institution_id, TODAY)[0]


# ------------------------------------------------------------------ pure helpers
def test_terms_sort_chronologically() -> None:
    keys = ["2025-26-even", "2024-25-odd", "2025-26-odd", "2024-25-even"]
    assert sorted(keys, key=term_sort_key) == ["2024-25-odd", "2024-25-even", "2025-26-odd", "2025-26-even"]


def test_split_is_out_of_time_and_needs_three_terms() -> None:
    def term(year: int, name: str) -> Term:
        start = date(year, 7, 20) if name == "odd" else date(year + 1, 1, 5)
        return Term(f"{year}-{(year + 1) % 100:02d}", name, start, start + timedelta(days=130))  # type: ignore[arg-type]

    three = [term(2023, "even"), term(2023, "odd"), term(2024, "odd")]
    split, check = plan_split(three)
    assert (split.train, split.validation, split.test) == (("2023-24-odd",), ("2023-24-even",), ("2024-25-odd",))
    assert check is None
    split, check = plan_split([*three, term(2024, "even")])
    assert split.test == ("2024-25-even",) and check is not None
    assert (check.train, check.validation, check.test) == (("2023-24-odd",), ("2023-24-even",), ("2024-25-odd",))
    with pytest.raises(TrainingRefusedError, match="at least 3"):
        plan_split(three[:2])


def test_config_rejects_unsafe_values() -> None:
    with pytest.raises(ValueError, match="cutoff_days"):
        InstitutionalTrainingConfig.model_validate({**SMALL_CONFIG, "cutoff_days": [30, 30]})
    with pytest.raises(ValueError, match="min_label_coverage"):
        InstitutionalTrainingConfig.model_validate({**SMALL_CONFIG, "min_label_coverage": 0})


# ------------------------------------------------------------------ history
def test_population_keeps_students_who_later_withdrew(conn: Connection, history: dict[str, Any]) -> None:
    inst = str(history["institution_id"])
    population = set(term_students(conn, inst, _first_term(conn, inst)))
    withdrawn = {
        r["id"]
        for r in conn.execute(
            "select id::text as id from public.students where institution_id = %s and status = 'withdrawn'", (inst,)
        ).fetchall()
    }
    assert history["withdrawn"] > 0 and withdrawn <= population  # nobody is filtered out by today's status


def test_history_is_replayed_by_event_time(conn: Connection, history: dict[str, Any]) -> None:
    inst = str(history["institution_id"])
    data = load_term_history(conn, inst, _first_term(conn, inst))
    row = data.attendance.iloc[0]
    midnight = pd.Timestamp(datetime.combine(row["attendance_date"], datetime.min.time()), tz=DEFAULT_TZ)
    assert row["recorded_at"] == midnight.tz_convert("UTC")  # not the (bulk) insertion time
    recorded = pd.to_datetime(data.engagement["recorded_at"], utc=True)
    assert (recorded == pd.to_datetime(data.engagement["occurred_at"], utc=True)).all()


def test_training_tables_only_see_the_past(conn: Connection, history: dict[str, Any]) -> None:
    inst = str(history["institution_id"])
    built = build_training_tables(conn, inst, [_first_term(conn, inst)], [30, 60])
    assert all(v["passed"] for v in built.leakage.values())
    # two courses with assignments due on days 21, 42, 63, 84: two are due by day 30, four by day 60
    assert built.tables[30]["assessments_due_to_date"].max() == 2
    assert built.tables[60]["assessments_due_to_date"].max() == 4
    assert set(built.tables[30]["target"].unique()) == {0, 1}


# ------------------------------------------------------------------ the training run
def test_training_runs_from_the_command_line(trained: dict[str, Any]) -> None:
    assert trained["code"] == EXIT_OK, trained["stderr"]
    summary = _summary(trained)
    assert summary["job"] == "train" and summary["data_provenance"] == "synthetic"
    assert [t["used"] for t in summary["terms"]] == [True, True, True, True]
    assert summary["split"]["test"] == [summary["terms"][-1]["term"]]
    assert summary["calibration_check"] is not None
    assert {r["cutoff_day"] for r in summary["results"]} == {30, 60}
    assert all(not r["skipped"] and 0.0 <= r["test"]["pr_auc"] <= 1.0 for r in summary["results"])
    assert "val PR-AUC" in trained["stderr"]  # progress goes to stderr, never into the JSON line
    reports = list((trained["root"] / "reports").iterdir())
    assert len(reports) == 1 and {p.name for p in reports[0].iterdir()} == {"metrics.json", "report.md"}
    assert "SYNTHETIC" in (reports[0] / "report.md").read_text(encoding="utf-8")


def test_outputs_contain_no_student_identifiers(
    conn: Connection, trained: dict[str, Any], history: dict[str, Any]
) -> None:
    ids = [
        r["id"]
        for r in conn.execute(
            "select id::text as id from public.students where institution_id = %s", (str(history["institution_id"]),)
        ).fetchall()
    ]
    report = next((trained["root"] / "reports").iterdir())
    texts = [trained["stdout"], (report / "metrics.json").read_text(encoding="utf-8")]
    texts += [p.read_text(encoding="utf-8") for p in (trained["root"] / "registry").glob("*/metadata.json")]
    assert ids and not any(sid in text for sid in ids for text in texts)


def test_selected_models_are_registered_for_review_only(conn: Connection, trained: dict[str, Any]) -> None:
    registered = _summary(trained)["registered"]
    assert len(registered) == 2
    for item in registered:
        row = conn.execute(
            "select status, data_provenance, institution_id, artifact_sha256 from public.model_registry where id = %s",
            (item["registry_id"],),
        ).fetchone()
        assert row is not None
        assert row["status"] == "development" and row["data_provenance"] == "synthetic"
        assert row["institution_id"] is None  # synthetic models are never tied to an institution
        artifact = ModelRegistry(trained["root"] / "registry").load(item["model_version"])  # verifies the hash
        assert artifact.metadata.model_sha256 == row["artifact_sha256"]


def test_a_synthetic_model_can_never_reach_production(conn: Connection, trained: dict[str, Any]) -> None:
    registry_id = _summary(trained)["registered"][0]["registry_id"]
    for status in ("validated", "staging"):
        conn.execute("update public.model_registry set status = %s where id = %s", (status, registry_id))
    with pytest.raises(psycopg.errors.CheckViolation, match="production_requires_institutional_data"):
        conn.execute(
            "update public.model_registry set status = 'production', approved_at = now() where id = %s", (registry_id,)
        )


def test_the_trained_model_scores_the_current_term(
    db_url: str, trained: dict[str, Any], history: dict[str, Any]
) -> None:
    version = next(r["model_version"] for r in _summary(trained)["results"] if r["cutoff_day"] == 60)
    root = trained["root"] / "registry"
    inst = str(history["institution_id"])
    with connect(db_url) as c:
        stats = score_institution(
            c, dev_settings(db_url, root), ModelRegistry(root), institution_id=inst, as_of=NOW, model_version=version
        )
        active = c.execute(
            "select count(*) as n from public.students where institution_id = %s and status = 'active'", (inst,)
        ).fetchone()
    assert active is not None and active["n"] > 0
    assert stats.students == active["n"] and stats.scored == active["n"] and stats.failed == 0


def test_production_refuses_to_train_on_synthetic_or_benchmark_data(
    conn: Connection, history: dict[str, Any], tmp_path: Path
) -> None:
    production = dev_settings(
        "postgresql://unused", tmp_path, environment="production", allowed_provenance=frozenset({"institutional"})
    )
    config = InstitutionalTrainingConfig.model_validate(SMALL_CONFIG)
    for provenance in ("synthetic", "benchmark"):
        with pytest.raises(TrainingRefusedError):
            train_institution(
                conn,
                production,
                config,
                institution_id=str(history["institution_id"]),
                data_provenance=provenance,
                now=NOW,
                repo_root=tmp_path,
            )
    assert not any(tmp_path.iterdir())  # nothing was trained or saved


def test_an_unknown_institution_is_refused(conn: Connection, tmp_path: Path) -> None:
    config = InstitutionalTrainingConfig.model_validate(SMALL_CONFIG)
    with pytest.raises(TrainingRefusedError, match="does not exist"):
        train_institution(
            conn,
            dev_settings("postgresql://unused", tmp_path),
            config,
            institution_id="00000000-0000-4000-8000-000000000000",
            data_provenance="synthetic",
            now=NOW,
            repo_root=tmp_path,
        )


# ------------------------------------------------------------------ the synthetic generator
def test_synthetic_history_is_development_only(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SEWS_ENV", "staging")
    monkeypatch.setenv(
        "SEWS_DATABASE_URL", "postgresql://postgres:not-a-real-password@db.stagingref.supabase.co/postgres"
    )
    assert synthetic_main([]) == 3
    err = capsys.readouterr().err
    assert "only be generated in development" in err and "not-a-real-password" not in err


def test_synthetic_history_is_generated_once(conn: Connection, history: dict[str, Any]) -> None:
    with pytest.raises(SyntheticRefusedError, match="already exists"):
        generate(conn, students=60, seed=1, today=TODAY)
