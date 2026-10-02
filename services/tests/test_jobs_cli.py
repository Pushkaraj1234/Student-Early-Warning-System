"""The batch-job command line (python -m sews_services.jobs). ALL DATA IS SYNTHETIC (supabase/seed.sql)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sews_services.config import ConfigError, load_settings
from sews_services.jobs.cli import EXIT_CONFIG, EXIT_OK, EXIT_REFUSED, main, monitor_windows

from tests.conftest import INSTITUTION, ROOT

IDENTITY_KEYS = {"full_name", "name", "email", "roll_number", "student_id", "user_id", "recipient_id"}
HOSTED = "postgresql://postgres:not-a-real-password@db.stagingref.supabase.co:5432/postgres"


def _env(db_url: str, tmp_path: Path) -> dict[str, str]:
    return {"SEWS_ENV": "development", "SEWS_DATABASE_URL": db_url, "SEWS_MODEL_REGISTRY_ROOT": str(tmp_path)}


def _output(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1
    parsed: dict[str, object] = json.loads(out[0])
    return parsed


def test_unsafe_configuration_exits_before_connecting(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["outcomes"], env={"SEWS_ENV": "development", "SEWS_DATABASE_URL": HOSTED})
    err = capsys.readouterr().err
    assert code == EXIT_CONFIG
    assert "local database" in err and "not-a-real-password" not in err


def test_jobs_do_not_need_the_api_token_settings() -> None:
    env = {"SEWS_ENV": "staging", "SEWS_DATABASE_URL": HOSTED}
    with pytest.raises(ConfigError, match="JWT"):
        load_settings(env)
    assert load_settings(env, require_api_auth=False).environment == "staging"


@pytest.mark.parametrize(
    "argv",
    [
        ["score", "--institution", "not-a-uuid"],
        ["monitor", "--model-registry-id", str(uuid.uuid4()), "--window-days", "0"],
        ["deliver", "--batch-size", "x"],
        [],
    ],
)
def test_invalid_arguments_are_rejected(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(argv, env={})
    assert exc.value.code == EXIT_CONFIG


def test_recommend_prints_aggregate_counts_only(
    db_url: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["recommend", "--institution", INSTITUTION], env=_env(db_url, tmp_path)) == EXIT_OK
    out = _output(capsys)
    assert out["job"] == "recommend" and out["environment"] == "development" and out["students"] == 3
    assert not IDENTITY_KEYS & set(out)


def test_scoring_without_a_production_model_is_refused(
    db_url: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["score", "--institution", INSTITUTION], env=_env(db_url, tmp_path)) == EXIT_REFUSED
    captured = capsys.readouterr()
    assert captured.out == "" and "no production model" in captured.err


def test_monitoring_an_unregistered_model_is_refused(
    db_url: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["monitor", "--model-registry-id", str(uuid.uuid4())]
    assert main(argv, env=_env(db_url, tmp_path)) == EXIT_REFUSED
    assert "not registered" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["outcomes", "deliver"])
def test_global_jobs_run(command: str, db_url: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([command], env=_env(db_url, tmp_path)) == EXIT_OK
    assert _output(capsys)["job"] == command


def test_monitor_windows_use_the_institution_time_zone() -> None:
    # 20:00 UTC on 2 Oct is 01:30 on 3 Oct in Asia/Kolkata: the last complete local day is 2 Oct.
    window, reference = monitor_windows(datetime(2026, 10, 2, 20, 0, tzinfo=UTC), 7)
    assert window == (date(2026, 9, 26), date(2026, 10, 2))
    assert reference == (date(2026, 9, 19), date(2026, 9, 25))


def test_module_entry_point() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "sews_services.jobs", "--help"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": os.pathsep.join([str(ROOT / "services"), str(ROOT)])},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == EXIT_OK
    assert all(c in result.stdout for c in ("score", "recommend", "outcomes", "monitor", "deliver"))
