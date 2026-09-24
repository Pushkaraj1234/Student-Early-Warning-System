"""Export trained artifacts as rows for ``public.model_registry`` (V4).

Every exported row has status ``development``. Promotion (validated -> staging -> production) is a
human decision recorded in the database, where the lifecycle trigger enforces the rules (production
requires institutional data, calibration evaluation and an approval). This module never promotes.

Rows contain aggregate metrics only; no student-level data.

Usage (from the repository root):
    ml/.venv/Scripts/python -m ml.models.registry_export --registry ml/artifacts --out registry.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from ml.models.artifact import ModelArtifact, ModelMetadata

# Mirrors the CHECK constraints on public.model_registry.
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HEADLINE = ("pr_auc", "roc_auc", "brier", "ece", "prevalence")


class RegistryExportError(ValueError):
    """The artifact cannot be represented as a valid model_registry row."""


def _headline(metrics: dict[str, Any]) -> dict[str, Any]:
    return {k: metrics.get(k) for k in HEADLINE}


def registry_row(metadata: ModelMetadata, *, institution_id: UUID | None = None) -> dict[str, Any]:
    if metadata.data_provenance == "institutional" and institution_id is None:
        raise RegistryExportError("institutional models must name the institution they were trained for")
    if metadata.data_provenance != "institutional" and institution_id is not None:
        raise RegistryExportError("only institutional models are scoped to an institution")
    for label, value, pattern in (
        ("model_name", metadata.model_name, NAME_RE),
        ("version", metadata.model_version, VERSION_RE),
        ("dataset_version", metadata.dataset_version, VERSION_RE),
        ("feature_version", metadata.feature_version, VERSION_RE),
    ):
        if not pattern.fullmatch(value):
            raise RegistryExportError(f"{label} does not match the registry format")
    if not metadata.model_sha256:
        raise RegistryExportError("artifact has no model hash")
    m = metadata.metrics
    if "validation" not in m or "test" not in m:
        raise RegistryExportError("artifact has no evaluation metrics")
    return {
        "model_name": metadata.model_name,
        "version": metadata.model_version,
        "target": metadata.target,
        "institution_id": str(institution_id) if institution_id else None,
        "dataset_version": metadata.dataset_version,
        "feature_version": metadata.feature_version,
        "data_provenance": metadata.data_provenance,
        "training_timestamp": metadata.training_timestamp.isoformat(),
        "validation_metrics": {
            "cutoff_day": metadata.cutoff_day,
            "split": metadata.split,
            "decision_threshold": metadata.decision_threshold,
            "validation": _headline(m["validation"]),
            "test": _headline(m["test"]),
            "test_bootstrap_ci": m.get("test_bootstrap_ci", {}),
        },
        "calibration_metrics": {
            "method": metadata.calibration_method,
            "decision": metadata.calibration_decision,
            "test_comparison": m.get("test_calibration_comparison", {}),
        },
        "status": "development",
        "artifact_sha256": metadata.model_sha256,
    }


def export_registry(root: Path, *, institution_id: UUID | None = None) -> list[dict[str, Any]]:
    """Rows for every verified artifact under ``root`` (hashes are checked on load)."""
    rows = []
    for path in sorted(p for p in root.iterdir() if p.is_dir() and (p / "metadata.json").is_file()):
        artifact = ModelArtifact.load(path)
        rows.append(registry_row(artifact.metadata, institution_id=institution_id))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--institution-id", type=UUID, default=None)
    args = parser.parse_args(argv)
    rows = export_registry(args.registry, institution_id=args.institution_id)
    args.out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"exported {len(rows)} model(s) with status 'development'", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
