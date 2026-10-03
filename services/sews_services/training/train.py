"""Institutional training job: train, evaluate and register models from the institution's own past terms.

``python -m sews_services.jobs train --institution <uuid> --data-provenance institutional|synthetic``

1. Completed odd/even terms whose results are published (label coverage >= ``min_label_coverage``).
2. Out-of-time split by term: the latest term is the test set, the one before it validation, the rest
   training (at least 3 terms). With 4+ terms, calibration is decided on an earlier out-of-time check.
3. Feature tables from sews_services.training.history (scoring job's feature code; leakage guard per term
   and decision point).
4. The benchmark pipeline's source-independent core (ml.training.train.train_feature_table): imbalance
   comparison, seed stability, calibration decision, thresholds on validation, ONE test evaluation with
   cluster-bootstrap intervals, drift, versioned artifact.
5. The selected model per decision point is registered in public.model_registry with status 'development'.
   It scores real students only after a person approves it: the database allows status 'production' only
   for institutional data, with calibration metrics and a recorded approval.

Outputs are aggregates only: no student identifier leaves this process (rows are keyed by student id in
memory for the cluster bootstrap and are never written). Artifacts of a run that fails before registration
stay on disk unregistered; scoring only ever loads registered versions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from ml.models.artifact import ModelArtifact
from ml.models.registry_export import registry_row
from ml.training.config import Provenance
from ml.training.splits import TemporalSplit
from ml.training.train import FeatureTableSpec, train_feature_table
from sews_services.config import Settings
from sews_services.db import Connection
from sews_services.features.institutional import DEFAULT_TZ, FEATURE_VERSION, FEATURES
from sews_services.features.labels import academic_labels
from sews_services.training.config import InstitutionalTrainingConfig
from sews_services.training.history import (
    Term,
    build_training_tables,
    completed_terms,
    dataset_version,
    term_sort_key,
    term_students,
)

TARGET = "academic"
TARGET_DEFINITION = "withdrew from, or received F/Ab in, any course of the term (published results)"
TARGET_HORIZON = "end of the term (publication of results)"
DATASET_NAME = "SEWS-INSTITUTIONAL-RECORDS"
# Out-of-time training needs one term each for training, validation and test.
MIN_TERMS = 3
# The calibration check needs one more, earlier term: fit on the earlier terms, calibrate on the last
# training term, evaluate on the validation term.
MIN_TERMS_FOR_CALIBRATION_CHECK = 4

REGISTER_SQL = """
insert into public.model_registry
  (model_name, version, target, institution_id, dataset_version, feature_version, data_provenance,
   training_timestamp, validation_metrics, calibration_metrics, status, artifact_sha256)
values (%(model_name)s, %(version)s, %(target)s, %(institution_id)s, %(dataset_version)s, %(feature_version)s,
        %(data_provenance)s, %(training_timestamp)s, %(validation_metrics)s::jsonb, %(calibration_metrics)s::jsonb,
        %(status)s, %(artifact_sha256)s)
returning id::text as id
"""


class TrainingRefusedError(RuntimeError):
    """Training was refused before any model was registered (reason in the message, no identifiers)."""


@dataclass(frozen=True)
class TermCoverage:
    term: Term
    students: int
    labelled: int

    @property
    def share(self) -> float:
        return self.labelled / self.students if self.students else 0.0


def term_coverage(conn: Connection, institution_id: str, terms: list[Term]) -> list[TermCoverage]:
    out = []
    for term in terms:
        students = term_students(conn, institution_id, term)
        labelled = len(academic_labels(conn, students, term.starts_on)) if students else 0
        out.append(TermCoverage(term, len(students), labelled))
    return out


def plan_split(terms: list[Term]) -> tuple[TemporalSplit, TemporalSplit | None]:
    keys = [t.key for t in sorted(terms, key=lambda t: term_sort_key(t.key))]
    if len(keys) < MIN_TERMS:
        raise TrainingRefusedError(
            f"out-of-time training needs at least {MIN_TERMS} completed terms with published results; found {len(keys)}"
        )
    split = TemporalSplit(train=tuple(keys[:-2]), validation=(keys[-2],), test=(keys[-1],))
    split.validate(term_sort_key)
    check = None
    if len(keys) >= MIN_TERMS_FOR_CALIBRATION_CHECK:
        check = TemporalSplit(train=tuple(keys[:-3]), validation=(keys[-3],), test=(keys[-2],))
        check.validate(term_sort_key)
    return split, check


def _register(conn: Connection, artifact: ModelArtifact, institution_id: str) -> str:
    meta = artifact.metadata
    scope = UUID(institution_id) if meta.data_provenance == "institutional" else None
    row = registry_row(meta, institution_id=scope)
    params = {
        **row,
        "validation_metrics": json.dumps(row["validation_metrics"], default=float),
        "calibration_metrics": json.dumps(row["calibration_metrics"], default=float),
    }
    inserted = conn.execute(REGISTER_SQL, params).fetchone()
    if inserted is None:
        raise RuntimeError("model registration returned no row")
    return str(inserted["id"])


def headline(result: dict[str, Any]) -> dict[str, Any]:
    """The selected model's test results for one decision point (aggregates only)."""
    if result["skipped"]:
        return {"cutoff_day": result["cutoff_day"], "skipped": True, "reason": result["skip_reason"]}
    selected = result["models"][result["selected_model"]]
    ci = selected["test_bootstrap_ci"]["pr_auc"]
    return {
        "cutoff_day": result["cutoff_day"],
        "skipped": False,
        "selected_model": result["selected_model"],
        "model_version": result["selected_model_version"],
        "test": {k: selected["test"][k] for k in ("n", "prevalence", "pr_auc", "roc_auc", "brier", "ece")},
        "test_pr_auc_ci": [ci["low"], ci["high"]],
        "calibration_applied": selected["calibration_decision"]["apply"],
    }


def train_institution(
    conn: Connection,
    settings: Settings,
    config: InstitutionalTrainingConfig,
    *,
    institution_id: str,
    data_provenance: Provenance,
    now: datetime,
    repo_root: Path,
    tz: ZoneInfo = DEFAULT_TZ,
) -> dict[str, Any]:
    """Train and register; returns the run summary (``cutoffs`` holds the full per-model metrics)."""
    if data_provenance == "benchmark":
        raise TrainingRefusedError("institutional training reads the SEWS database: institutional or synthetic only")
    if data_provenance not in settings.allowed_provenance:
        raise TrainingRefusedError("this data provenance is not allowed in this environment")
    if conn.execute("select 1 from public.institutions where id = %s", (institution_id,)).fetchone() is None:
        raise TrainingRefusedError("the institution does not exist")

    terms = completed_terms(conn, institution_id, now.astimezone(tz).date())
    coverage = term_coverage(conn, institution_id, terms)
    usable = [c.term for c in coverage if c.students and c.share >= config.min_label_coverage]
    split, check = plan_split(usable)
    shortest = min((t.ends_on - t.starts_on).days for t in usable)
    if max(config.cutoff_days) >= shortest:
        raise TrainingRefusedError(f"decision point day {max(config.cutoff_days)} is not inside every term")

    built = build_training_tables(conn, institution_id, usable, config.cutoff_days, tz)
    ds_version = dataset_version(built.tables)
    timestamp = now.astimezone(UTC).replace(microsecond=0)
    run_id = f"{config.run_name}-{timestamp:%Y%m%dT%H%M%SZ}"
    results = []
    for cutoff in config.cutoff_days:
        spec = FeatureTableSpec(
            feature_names=FEATURES,
            feature_version=FEATURE_VERSION,
            target=TARGET,
            target_definition=TARGET_DEFINITION,
            target_horizon=TARGET_HORIZON,
            cutoff_day=cutoff,
            split=split,
            calibration_check=check,
            sort_key=term_sort_key,
            dataset_name=DATASET_NAME,
            dataset_version=ds_version,
            data_provenance=data_provenance,
        )
        results.append(
            train_feature_table(
                config,
                built.tables[cutoff],
                spec,
                run_id=run_id,
                registry_root=settings.model_registry_root,
                repo_root=repo_root,
                timestamp=timestamp,
                leakage_check=built.leakage[cutoff],
            )
        )

    registered = []
    for result in results:
        if result["skipped"]:
            continue
        version = result["selected_model_version"]
        artifact = ModelArtifact.load(settings.model_registry_root / version)  # verifies the artifact hash
        registered.append({"model_version": version, "registry_id": _register(conn, artifact, institution_id)})
    conn.commit()
    if not registered:
        raise TrainingRefusedError("no decision point had enough data in every split; nothing was registered")

    calibration_check = None
    if check is not None:
        calibration_check = {
            "train": list(check.train),
            "calibrate": list(check.validation),
            "evaluate": list(check.test),
        }
    return {
        "run_id": run_id,
        "created_at": timestamp.isoformat(),
        "data_provenance": data_provenance,
        "dataset": {"name": DATASET_NAME, "version": ds_version},
        "feature_version": FEATURE_VERSION,
        "target": {"name": TARGET, "definition": TARGET_DEFINITION, "horizon": TARGET_HORIZON},
        "terms": [
            {"term": c.term.key, "students": c.students, "labelled": c.labelled, "used": c.term in usable}
            for c in coverage
        ],
        "split": {"train": list(split.train), "validation": list(split.validation), "test": list(split.test)},
        "calibration_check": calibration_check,
        "leakage_checks": {str(k): v for k, v in built.leakage.items()},
        "results": [headline(r) for r in results],
        "registered": registered,
        "cutoffs": results,
    }


def _f(value: Any) -> str:
    return "—" if value is None else f"{value:.3f}"


def render_markdown(summary: dict[str, Any]) -> str:
    """Human-readable run report (aggregates only)."""
    synthetic = summary["data_provenance"] == "synthetic"
    banner = (
        "> **Data provenance: SYNTHETIC.** Generated data (sews_services.training.synthetic). These numbers prove that "
        "the pipeline runs end to end; they say nothing about real students, and this model can never be approved "
        "for production (database rule)."
        if synthetic
        else "> **Data provenance: INSTITUTIONAL.** Aggregate results only. A model scores students only after a "
        "person approves it in the model registry."
    )
    lines = [
        f"# Institutional training — {summary['run_id']}",
        "",
        banner,
        "",
        f"- Dataset `{summary['dataset']['version']}`; feature set `{summary['feature_version']}`",
        f"- Target `{summary['target']['name']}`: {summary['target']['definition']}; horizon: "
        f"{summary['target']['horizon']}",
        f"- Out-of-time split by term: train {summary['split']['train']}, validation {summary['split']['validation']}, "
        f"test {summary['split']['test']}",
        f"- Calibration check: {summary['calibration_check'] or 'none (needs 4 or more terms); not applied'}",
        "- Availability by event time (docs/ml/institutional-training.md); temporal leakage guard: "
        + "; ".join(f"day {k} passed ({v['terms']} terms)" for k, v in summary["leakage_checks"].items()),
        "",
        "## Terms",
        "",
        "| Term | Students | Labelled | Used |",
        "|---|---:|---:|---|",
        *(
            f"| {t['term']} | {t['students']} | {t['labelled']} | {'yes' if t['used'] else 'no'} |"
            for t in summary["terms"]
        ),
        "",
    ]
    for result in summary["cutoffs"]:
        lines += [f"## Decision point: day {result['cutoff_day']} of the term", ""]
        if result["skipped"]:
            lines += [f"Not trained: {result['skip_reason']}", ""]
            continue
        dist = result["distribution"]
        lines += [
            "| Split | Terms | Students | Adverse | Prevalence |",
            "|---|---|---:|---:|---:|",
            *(
                f"| {s} | {', '.join(dist[s]['groups'])} | {dist[s]['n']} | {dist[s]['positives']} | "
                f"{_f(dist[s]['prevalence'])} |"
                for s in ("train", "validation", "test")
            ),
            "",
            "| Model | Validation PR-AUC | Test PR-AUC [95% CI] | Test ROC-AUC | Test Brier | Test ECE | Calibrated |",
            "|---|---:|---|---:|---:|---:|---|",
        ]
        for name, m in result["models"].items():
            ci = m["test_bootstrap_ci"]["pr_auc"]
            mark = " (**selected**)" if name == result["selected_model"] else ""
            lines.append(
                f"| {name}{mark} | {_f(m['validation']['pr_auc'])} | {_f(m['test']['pr_auc'])} "
                f"[{_f(ci['low'])}, {_f(ci['high'])}] | {_f(m['test']['roc_auc'])} | {_f(m['test']['brier'])} | "
                f"{_f(m['test']['ece'])} | {'yes' if m['calibration_decision']['apply'] else 'no'} |"
            )
        lines += ["", f"Selection: {result['selection_rationale']}", ""]
    lines += [
        "## Registered (status `development`)",
        "",
        *(f"- `{r['model_version']}`" for r in summary["registered"]),
        "",
        "## Limitations",
        "",
        "- Training replays history by event time; if live data is recorded late, live features lag (monitoring).",
        "- The schema stores no withdrawal date: a student who withdrew before a decision point is still counted.",
        "- No subgroup audit: the institutional schema holds no audit attributes (docs/ml/fairness.md).",
        "- PR-AUC must be read against prevalence; feature contributions are associations, not causes.",
        "",
    ]
    return "\n".join(lines)
