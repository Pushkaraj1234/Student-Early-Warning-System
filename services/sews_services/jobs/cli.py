"""Command-line runner for the batch jobs: ``python -m sews_services.jobs <command>`` (from the repository root).

One process runs one job and exits, so any scheduler (cron, a CI schedule, a cloud scheduler) can call it.
Where and how often it runs is an owner decision (docs/architecture/deployment.md); the order for a
nightly run is: score -> recommend -> outcomes -> deliver, and monitor per active production model.
``train`` runs on demand, e.g. after a semester's results are published (docs/ml/institutional-training.md).

Settings come from environment variables (sews_services.config) and are checked before any connection is
opened: a development process can only reach a loopback database, production only institutional models.
Output is one JSON line of aggregate counts (no identifiers). Exit codes: 0 done, 1 database error (logged
without data values), 2 invalid configuration or arguments, 3 the job refused to run.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import sys
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, get_args

import psycopg
from pydantic import ValidationError

from ml.models.registry import ModelRegistry
from ml.training.config import Target
from sews_services.config import ConfigError, Settings, load_settings
from sews_services.db import Connection, connect
from sews_services.features.institutional import DEFAULT_TZ, TemporalLeakageError
from sews_services.jobs.monitoring import monitor_window, summary
from sews_services.jobs.notifications import NoPushProvider, deliver_pending
from sews_services.jobs.outcomes import compute_outcomes
from sews_services.jobs.recommend import recommend_for_institution
from sews_services.jobs.scoring import ScoringRefusedError, score_institution
from sews_services.training.config import DEFAULT_CONFIG, load_training_config
from sews_services.training.train import TrainingRefusedError, render_markdown, train_institution

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_CONFIG = 2
EXIT_REFUSED = 3

# docs/ml/monitoring.md: a 7-day window of prediction dates, compared with the previous 7 days.
MONITOR_WINDOW_DAYS = 7
MAX_MONITOR_WINDOW_DAYS = 90
DEFAULT_DELIVERY_BATCH = 100
MAX_DELIVERY_BATCH = 1_000

log = logging.getLogger("sews.jobs")


def _uuid(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a UUID") from exc


def _bounded(low: int, high: int) -> Callable[[str], int]:
    def parse(value: str) -> int:
        try:
            number = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("must be an integer") from exc
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(f"must be between {low} and {high}")
        return number

    return parse


def monitor_windows(now: datetime, days: int) -> tuple[tuple[date, date], tuple[date, date]]:
    """The last ``days`` complete local days (ending yesterday) and the ``days`` before them, as inclusive
    ranges of prediction dates in the institution's time zone (the zone the scoring job dates them in)."""
    end = now.astimezone(DEFAULT_TZ).date() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    reference_end = start - timedelta(days=1)
    return (start, end), (reference_end - timedelta(days=days - 1), reference_end)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m sews_services.jobs", description="Run one SEWS batch job.")
    commands = parser.add_subparsers(dest="command", required=True)

    score = commands.add_parser("score", help="score one institution's students with its production model")
    score.add_argument("--institution", type=_uuid, required=True)
    score.add_argument("--target", choices=get_args(Target), default="academic")
    score.add_argument("--model-version", help="a specific registered version (default: the production model)")

    recommend = commands.add_parser("recommend", help="store rule suggestions for one institution (need review)")
    recommend.add_argument("--institution", type=_uuid, required=True)

    commands.add_parser("outcomes", help="compute descriptive outcome measures for finished interventions")

    monitor = commands.add_parser("monitor", help="monitoring snapshot and drift alerts for one registered model")
    monitor.add_argument("--model-registry-id", type=_uuid, required=True)
    monitor.add_argument("--window-days", type=_bounded(1, MAX_MONITOR_WINDOW_DAYS), default=MONITOR_WINDOW_DAYS)
    monitor.add_argument("--no-reference", action="store_true", help="snapshot only, no drift comparison")

    deliver = commands.add_parser("deliver", help="deliver pending push notifications")
    deliver.add_argument("--batch-size", type=_bounded(1, MAX_DELIVERY_BATCH), default=DEFAULT_DELIVERY_BATCH)

    train = commands.add_parser("train", help="train and register models from one institution's past terms")
    train.add_argument("--institution", type=_uuid, required=True)
    train.add_argument("--data-provenance", choices=("institutional", "synthetic"), required=True)
    train.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    train.add_argument("--report-dir", type=Path, help="also write metrics.json and report.md for the run here")
    return parser


def _run(args: argparse.Namespace, conn: Connection, settings: Settings, now: datetime) -> dict[str, Any]:
    if args.command == "score":
        stats = score_institution(
            conn,
            settings,
            ModelRegistry(settings.model_registry_root),
            institution_id=args.institution,
            as_of=now,
            target=args.target,
            model_version=args.model_version,
        )
        return stats.as_dict()
    if args.command == "recommend":
        return recommend_for_institution(conn, institution_id=args.institution, now=now).as_dict()
    if args.command == "outcomes":
        return compute_outcomes(conn, now=now).as_dict()
    if args.command == "train":
        # The shared training core prints per-model progress; it goes to stderr so stdout stays one JSON line.
        with contextlib.redirect_stdout(sys.stderr):
            run_summary = train_institution(
                conn,
                settings,
                args.training_config,
                institution_id=args.institution,
                data_provenance=args.data_provenance,
                now=now,
                repo_root=Path.cwd(),
            )
        if args.report_dir is not None:
            directory = args.report_dir / run_summary["run_id"]
            directory.mkdir(parents=True, exist_ok=False)
            (directory / "metrics.json").write_text(json.dumps(run_summary, indent=2, default=str), encoding="utf-8")
            (directory / "report.md").write_text(render_markdown(run_summary), encoding="utf-8")
        return {k: v for k, v in run_summary.items() if k != "cutoffs"}
    if args.command == "monitor":
        window, reference = monitor_windows(now, args.window_days)
        result = monitor_window(
            conn,
            model_registry_id=args.model_registry_id,
            window=window,
            reference=None if args.no_reference else reference,
        )
        return {"window": [d.isoformat() for d in window], **summary(result)}
    # "deliver": no push provider is configured yet, so pending notifications are marked skipped
    # (docs/architecture/deployment.md); the in-app notification list is unaffected.
    return deliver_pending(conn, NoPushProvider(), batch_size=args.batch_size).as_dict()


def main(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = load_settings(env, require_api_auth=False)
        if args.command == "train":
            args.training_config = load_training_config(args.config)
    except (ConfigError, ValidationError, OSError) as exc:
        # ConfigError and pydantic messages name settings or fields, never secret values.
        print(f"configuration error: {exc}", file=sys.stderr)
        return EXIT_CONFIG
    try:
        with connect(settings.database_url) as conn:
            result = _run(args, conn, settings, now())
    except (ScoringRefusedError, TemporalLeakageError, TrainingRefusedError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return EXIT_REFUSED
    except LookupError:
        print("refused: the model is not registered", file=sys.stderr)
        return EXIT_REFUSED
    except psycopg.Error as exc:
        # The class and SQLSTATE only: psycopg messages can quote data values.
        log.error("database error in %s job: %s (%s)", args.command, type(exc).__name__, exc.sqlstate)
        return EXIT_ERROR
    print(json.dumps({"job": args.command, "environment": settings.environment, **result}, sort_keys=True))
    return EXIT_OK
