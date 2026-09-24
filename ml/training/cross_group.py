"""Cross-group generalisation check (V4) — run here as a PROXY, not as cross-institution validation.

Framework: for each group G, compare a model that never saw G during training ("held-out") with a
model trained on all groups including G ("reference"); evaluate both on G's rows in the test period
and report the degradation (reference - held-out; positive = worse on the unseen group).

SEWS currently has data from ONE institution (OULAD: the Open University, UK), so the only groups
available are course modules. These results describe how performance changes across modules of one
UK institution. They are NOT evidence that a model generalises to other institutions or to Indian
students. When data from two or more institutions exists, the same code runs with the group
function returning the institution.

Protocol details
  * Training rows: presentations in config.split.train + config.split.validation (out of time).
  * Evaluation rows: presentations in config.split.test.
  * Imbalance strategy "none" and RAW probabilities for both models, so calibration choices do not
    confound the comparison.
  * A group is skipped (with the reason) if its evaluation rows or the held-out training rows have
    fewer than ``min_class_count`` positives or negatives.

Usage (from the repository root):
    ml/.venv/Scripts/python -m ml.training.cross_group --config ml/configs/oulad_v2.json \
        --target academic --cutoff 60 --model logistic_regression
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ml.data.contract import TARGET_COLUMN
from ml.data.oulad import DATASET_NAME, dataset_version, load_oulad
from ml.evaluation.metrics import evaluate
from ml.features.definitions import feature_names
from ml.features.oulad_features import build_oulad_features
from ml.features.targets import TARGETS
from ml.models.factory import ModelName, build_pipeline
from ml.monitoring.drift import clean_for_json
from ml.training.config import TrainingConfig, load_config

GroupFn = Callable[[pd.DataFrame], pd.Series]
REPORTED_METRICS = ("pr_auc", "roc_auc", "brier", "ece")
SCOPE_STATEMENT = (
    "Cross-MODULE proxy within ONE institution (Open University, UK). This is NOT cross-institution "
    "validation and does not show that any model generalises to other institutions or to Indian students."
)


def module_of(df: pd.DataFrame) -> pd.Series:
    """OULAD group: the course module (context_id is '<module>-<presentation>')."""
    return df["context_id"].str.split("-", n=1).str[0]


def _metrics(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    m = evaluate(y, p, threshold=0.5, top_fractions=(0.2,))
    return {
        **{k: m[k] for k in REPORTED_METRICS},
        "recall_at_top_20pct": m["top_fraction"][0]["recall"],
        "prevalence": m["prevalence"],
        "mean_predicted": m["mean_predicted"],
    }


def _class_counts(y: np.ndarray) -> tuple[int, int]:
    positives = int(y.sum())
    return positives, int(y.size - positives)


def leave_one_group_out(
    df: pd.DataFrame,
    names: tuple[str, ...],
    *,
    train_groups: tuple[str, ...],
    test_groups: tuple[str, ...],
    model_name: ModelName,
    seed: int,
    min_class_count: int,
    group_of: GroupFn = module_of,
) -> dict[str, Any]:
    """Evaluate every group as unseen. ``train_groups``/``test_groups`` are time groups (split_group)."""
    if set(train_groups) & set(test_groups):
        raise ValueError("train and test time groups must not overlap")
    groups = group_of(df)
    in_train = df["split_group"].isin(train_groups).to_numpy()
    in_test = df["split_group"].isin(test_groups).to_numpy()
    X = df.loc[:, list(names)].astype(float)
    y = df[TARGET_COLUMN].to_numpy(dtype=np.int64)

    y_all = y[in_train]
    reference = build_pipeline(model_name, "none", y_train=y_all, seed=seed).fit(X[in_train], y_all)

    rows: list[dict[str, Any]] = []
    for group in sorted(groups.unique()):
        is_group = (groups == group).to_numpy()
        eval_mask = in_test & is_group
        held_mask = in_train & ~is_group
        y_eval, y_held = y[eval_mask], y[held_mask]
        row: dict[str, Any] = {"group": str(group), "n_eval": int(eval_mask.sum())}
        short = [
            label
            for label, labels in (("evaluation rows", y_eval), ("held-out training rows", y_held))
            if min(_class_counts(labels)) < min_class_count
        ]
        if short:
            row.update(skipped=True, reason=f"fewer than {min_class_count} of a class in {', '.join(short)}")
            rows.append(row)
            continue
        held_out = build_pipeline(model_name, "none", y_train=y_held, seed=seed).fit(X[held_mask], y_held)
        ref_metrics = _metrics(y_eval, reference.predict_proba(X[eval_mask])[:, 1])
        held_metrics = _metrics(y_eval, held_out.predict_proba(X[eval_mask])[:, 1])
        row.update(
            skipped=False,
            reference=ref_metrics,
            held_out=held_metrics,
            degradation={
                k: (
                    None
                    if ref_metrics[k] is None or held_metrics[k] is None
                    else (
                        float(ref_metrics[k] - held_metrics[k])
                        if k in ("pr_auc", "roc_auc", "recall_at_top_20pct")
                        else float(held_metrics[k] - ref_metrics[k])  # brier/ece: higher is worse
                    )
                )
                for k in (*REPORTED_METRICS, "recall_at_top_20pct")
            },
        )
        rows.append(row)

    evaluated = [r for r in rows if not r["skipped"]]
    summary: dict[str, Any] = {}
    for k in (*REPORTED_METRICS, "recall_at_top_20pct"):
        values = [r["degradation"][k] for r in evaluated if r["degradation"][k] is not None]
        summary[k] = (
            {"mean": float(np.mean(values)), "max": float(np.max(values)), "min": float(np.min(values))}
            if values
            else None
        )
    return {
        "groups_evaluated": len(evaluated),
        "groups_skipped": len(rows) - len(evaluated),
        "degradation_summary": summary,
        "groups": rows,
    }


def render_markdown(result: dict[str, Any]) -> str:
    def f(v: Any) -> str:
        return "n/a" if v is None else f"{float(v):.3f}"

    lines = [
        f"# Cross-group check — {result['run_id']}",
        "",
        f"> **{SCOPE_STATEMENT}**",
        f"> Data provenance: {result['dataset']['provenance'].upper()} ({result['dataset']['version']}).",
        "",
        f"- Target: {result['target']} ({result['target_definition']})",
        f"- Decision point: day {result['cutoff_day']}; model: {result['model_name']} (raw probabilities)",
        f"- Training presentations: {', '.join(result['train_groups'])}; "
        f"evaluation presentations: {', '.join(result['test_groups'])}",
        f"- Groups evaluated: {result['groups_evaluated']}; skipped: {result['groups_skipped']}",
        "",
        "Degradation = reference (group seen in training) minus held-out (group unseen) for PR-AUC, "
        "ROC-AUC and recall at top 20%; held-out minus reference for Brier and ECE. Positive = worse "
        "on the unseen group.",
        "",
        "| Group | n | PR-AUC ref -> held-out | ROC-AUC ref -> held-out | Brier ref -> held-out | "
        "ECE ref -> held-out | Recall@20% ref -> held-out |",
        "|---|---:|---|---|---|---|---|",
    ]
    for r in result["groups"]:
        if r["skipped"]:
            lines.append(f"| {r['group']} | {r['n_eval']} | skipped: {r['reason']} | | | | |")
            continue
        ref, held = r["reference"], r["held_out"]
        cells = [
            f"{f(ref[k])} -> {f(held[k])}"
            for k in ("pr_auc", "roc_auc", "brier", "ece", "recall_at_top_20pct")
        ]
        lines.append(f"| {r['group']} | {r['n_eval']} | " + " | ".join(cells) + " |")
    lines += ["", "Mean / worst degradation across evaluated groups:", ""]
    for k, v in result["degradation_summary"].items():
        text = "n/a" if v is None else f"mean {f(v['mean'])}, worst {f(v['max'])}, best {f(v['min'])}"
        lines.append(f"- {k}: {text}")
    lines += [
        "",
        "Limitations: one institution only; modules differ in size, subject and assessment design; "
        "a single time split; no confidence intervals per group. Do not cite these numbers as "
        "cross-institution performance.",
        "",
    ]
    return "\n".join(lines)


def run(
    config: TrainingConfig, repo_root: Path, *, target: str, cutoff: int, model_name: ModelName
) -> dict[str, Any]:
    if target not in config.targets:
        raise ValueError(f"target {target!r} is not in the config targets")
    if cutoff not in config.cutoff_days:
        raise ValueError(f"cutoff {cutoff} is not in the config cutoff_days")
    timestamp = datetime.now(UTC).replace(microsecond=0)
    run_id = f"cross-module-{target}-d{cutoff}-{timestamp:%Y%m%dT%H%M%SZ}"
    path = config.dataset.path if config.dataset.path.is_absolute() else repo_root / config.dataset.path
    tables = load_oulad(path)
    names = feature_names(config.feature_version)
    df = build_oulad_features(
        tables,
        cutoff,
        score_release_lag_days=config.score_release_lag_days,
        target=target,
        feature_version=config.feature_version,
    )
    train_groups = (*config.split.train, *config.split.validation)
    evaluation = leave_one_group_out(
        df,
        names,
        train_groups=train_groups,
        test_groups=config.split.test,
        model_name=model_name,
        seed=config.random_seed,
        min_class_count=config.min_class_count_per_split,
    )
    output: dict[str, Any] = clean_for_json(
        {
            "run_id": run_id,
            "created_at": timestamp.isoformat(),
            "scope": SCOPE_STATEMENT,
            "dataset": {
                "name": DATASET_NAME,
                "version": dataset_version(path),
                "provenance": config.dataset.provenance,
            },
            "feature_version": config.feature_version,
            "target": target,
            "target_definition": TARGETS[target].definition,
            "cutoff_day": cutoff,
            "model_name": model_name,
            "train_groups": list(train_groups),
            "test_groups": list(config.split.test),
            **evaluation,
        }
    )
    report_root = config.report_dir if config.report_dir.is_absolute() else repo_root / config.report_dir
    out = report_root / run_id
    out.mkdir(parents=True, exist_ok=False)
    (out / "cross_group.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    (out / "report.md").write_text(render_markdown(output), encoding="utf-8")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--target", default="academic")
    parser.add_argument("--cutoff", type=int, default=60)
    parser.add_argument(
        "--model", default="logistic_regression", choices=["logistic_regression", "random_forest", "xgboost"]
    )
    args = parser.parse_args(argv)
    result = run(
        load_config(args.config), Path.cwd(), target=args.target, cutoff=args.cutoff, model_name=args.model
    )
    print(f"{result['run_id']}: {result['groups_evaluated']} groups evaluated", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
