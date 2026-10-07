"""Weekly batch scoring with a saved v3 model (deployment prototype).

For an OULAD-format dataset folder and week ``k``: build the student-week panel for weeks 1..k, score every
registration still active in week ``k`` with the saved XGBoost v3 artifact, apply the artifact's alert policy
(the 2-consecutive-week policy also needs week k-1), assign risk tiers, and compare week ``k``'s features with
the training reference stored in the artifact (PSI and missing-share change). Writes one CSV row per
registration and prints a JSON monitoring summary (aggregates only).

Safety rules:
  * the model file's SHA-256 must match its metadata before it is unpickled;
  * a benchmark- or synthetic-trained model refuses institutional data (SEWS never approves such models for
    real students); institutional deployment goes through in-app training and the approval workflow.

Usage (from the repository root):
    ml/.venv/Scripts/python -m ml.longitudinal.score --artifact ml/artifacts/<version> \
        --dataset ml/data/raw/oulad --data-provenance benchmark --week 8 --presentations 2014J
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ml.data.oulad import load_oulad
from ml.longitudinal import alerts
from ml.longitudinal.panel import build_panel
from ml.monitoring.drift import MISSING_CRITICAL, MISSING_WARNING, PSI_CRITICAL, PSI_WARNING

PSI_EPS = 1e-4
TIERS = ("stable", "watch", "elevated", "high")


class ScoringRefusedError(RuntimeError):
    """The artifact or the request is not safe to score."""


def load_artifact(folder: Path) -> tuple[Any, dict[str, Any]]:
    metadata: dict[str, Any] = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    model_path = folder / "model.joblib"
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if digest != metadata.get("model_sha256"):
        raise ScoringRefusedError(
            "model file does not match the SHA-256 in its metadata; refusing to load it"
        )
    return joblib.load(model_path), metadata


def psi_against_reference(reference: dict[str, Any], values: np.ndarray) -> dict[str, float | None]:
    """PSI of ``values`` over the reference bins, and the change in the missing share."""
    finite = values[np.isfinite(values)]
    missing_change = abs(float(np.mean(~np.isfinite(values))) - float(reference["missing_share"]))
    edges = np.asarray(reference["edges"], dtype=np.float64)
    ref = np.asarray(reference["shares"], dtype=np.float64)
    if finite.size == 0 or edges.size < 2:
        return {"psi": None, "missing_share_change": missing_change}
    counts = np.histogram(np.clip(finite, edges[0], edges[-1]), bins=edges)[0]
    cur = counts / counts.sum()
    ref_e, cur_e = np.maximum(ref, PSI_EPS), np.maximum(cur, PSI_EPS)
    psi = float(np.sum((cur_e - ref_e) * np.log(cur_e / ref_e)))
    return {"psi": psi, "missing_share_change": missing_change}


def _severity(value: float | None, warning: float, critical: float) -> str | None:
    if value is None:
        return None
    return "critical" if value >= critical else ("warning" if value >= warning else None)


def score_week(
    artifact: Path, dataset: Path, *, data_provenance: str, week: int, presentations: tuple[str, ...]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    pipeline, meta = load_artifact(artifact)
    if data_provenance == "institutional" and meta["data_provenance"] != "institutional":
        raise ScoringRefusedError(
            f"a {meta['data_provenance']}-trained model must not score institutional (real) students"
        )
    if week < 2 and meta["alert_policy"] == "consecutive_2":
        raise ScoringRefusedError("the 2-consecutive-week policy needs at least two weeks of history")
    features: list[str] = list(meta["feature_names"])
    tables = load_oulad(dataset)
    panel = build_panel(
        tables, weeks=list(range(1, week + 1)), score_release_lag_days=int(meta["score_release_lag_days"])
    )
    panel = panel[panel["split_group"].isin(presentations)].reset_index(drop=True)
    if panel.empty:
        raise ScoringRefusedError(f"no registrations from {presentations} in the panel")
    matrix = panel.loc[:, features].astype(np.float32)
    risk = np.asarray(pipeline.predict_proba(matrix)[:, 1], dtype=np.float64)
    threshold = float(meta["thresholds_from_validation"][meta["default_threshold"]])
    flags = alerts.alert_flags(panel, risk, threshold, meta["alert_policy"])
    current = (panel["week"] == week).to_numpy()
    tiers = np.searchsorted(np.asarray(meta["risk_tier_cut_points"]), risk[current], side="right")
    scores = pd.DataFrame(
        {
            "context_id": panel.loc[current, "context_id"].astype(str).to_numpy(),
            "student_id": panel.loc[current, "student_id"].astype(str).to_numpy(),
            "week": week,
            "risk": risk[current],
            "tier": [TIERS[t] for t in tiers],
            "alert": flags[current],
        }
    )
    drift = {}
    for name in features:
        reference = meta["monitoring_reference"].get(name)
        if reference is None:
            continue
        result = psi_against_reference(reference, panel.loc[current, name].to_numpy(dtype=np.float64))
        drift[name] = {
            **result,
            "psi_severity": _severity(result["psi"], PSI_WARNING, PSI_CRITICAL),
            "missing_severity": _severity(result["missing_share_change"], MISSING_WARNING, MISSING_CRITICAL),
        }
    flagged = [n for n, d in drift.items() if d["psi_severity"] or d["missing_severity"]]
    summary = {
        "model_version": meta["model_version"],
        "approved_for_real_students": meta["approved_for_real_students"],
        "data_provenance": data_provenance,
        "week": week,
        "presentations": list(presentations),
        "registrations_scored": int(current.sum()),
        "alert_policy": meta["alert_policy"],
        "threshold": threshold,
        "alerts": int(scores["alert"].sum()),
        "tiers": {t: int((scores["tier"] == t).sum()) for t in TIERS},
        "mean_risk": float(scores["risk"].mean()),
        "drift_alerts": len(flagged),
        "drift_features": {n: drift[n] for n in flagged},
    }
    return scores, summary


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument(
        "--data-provenance", choices=("benchmark", "synthetic", "institutional"), required=True
    )
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--presentations", nargs="+", required=True)
    parser.add_argument("--out", type=Path, help="CSV path (default: git-ignored ml/data/processed/)")
    args = parser.parse_args(argv)
    try:
        scores, summary = score_week(
            args.artifact,
            args.dataset,
            data_provenance=args.data_provenance,
            week=args.week,
            presentations=tuple(args.presentations),
        )
    except ScoringRefusedError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 3
    out = args.out or Path("ml/data/processed") / f"scores-{summary['model_version']}-week{args.week}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    scores.to_csv(out, index=False)
    print(json.dumps(_json_safe({**summary, "scores_csv": str(out)}), default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
