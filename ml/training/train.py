"""Train, evaluate, explain and register SEWS models (V3: multiple targets).

Usage (from the repository root):
    ml/.venv/Scripts/python -m ml.training.train --config ml/configs/oulad_v2.json

For every cutoff: run the temporal-leakage guard (training stops if any feature uses information
from after the cutoff). Then for every target, cutoff and model: compare imbalance strategies on
validation, measure seed stability, decide on calibration with an out-of-time check, pick thresholds
on validation, evaluate ONCE on the out-of-time test split, audit subgroups (performance, calibration,
FPR/FNR differences), measure drift between training and test, and save a versioned artifact. One
model per (target, cutoff) is selected with the documented rule; the primary target/cutoff choice
becomes the active model.
"""

from __future__ import annotations

import argparse
import itertools
import json
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap
import sklearn
import xgboost
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline

from ml.data.contract import AUDIT_PREFIX, TARGET_COLUMN, validate_feature_table
from ml.data.oulad import DATASET_NAME, OuladTables, dataset_version, load_oulad
from ml.evaluation.metrics import (
    best_f1_threshold,
    bootstrap_ci,
    disparity_summary,
    evaluate,
    expected_calibration_error,
    subgroup_metrics,
)
from ml.evaluation.report import write_reports
from ml.explainability.shap_explainer import ModelExplainer
from ml.features.definitions import feature_names
from ml.features.leakage import assert_no_future_leakage
from ml.features.oulad_features import build_oulad_features
from ml.features.targets import TARGETS
from ml.models.artifact import ModelArtifact, ModelMetadata, RiskThresholds
from ml.models.factory import EXPLANATION_UNITS, ModelName, build_pipeline, model_hyperparameters
from ml.models.registry import ModelRegistry
from ml.monitoring.drift import (
    clean_for_json,
    feature_drift,
    monitoring_snapshot,
    outcome_drift,
    performance_drop,
    prediction_drift,
)
from ml.training.config import TrainingConfig, load_config
from ml.training.selection import Candidate, StrategyResult, choose_imbalance_strategy, select_model
from ml.training.splits import split_frame

MODEL_ABBREVIATIONS: dict[ModelName, str] = {
    "logistic_regression": "lr",
    "random_forest": "rf",
    "xgboost": "xgb",
}
TARGET_ABBREVIATIONS = {"academic": "acad", "dropout": "drop", "course_failure": "fail", "engagement": "eng"}
EXPLAIN_SAMPLE = 400


def _git_commit(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def _library_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit-learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "shap": shap.__version__,
    }


def _xy(frame: pd.DataFrame, names: tuple[str, ...]) -> tuple[pd.DataFrame, np.ndarray]:
    return frame.loc[:, list(names)].astype(float), frame[TARGET_COLUMN].to_numpy(dtype=np.int64)


def _proba(model: Any, X: pd.DataFrame) -> np.ndarray:
    return np.asarray(model.predict_proba(X)[:, 1], dtype=np.float64)


def _background_means(pipeline: Pipeline, X_train: pd.DataFrame) -> np.ndarray | None:
    """Mean of the transformed training matrix — the SHAP baseline for linear models.
    Stored as an aggregate; no training rows are kept in the artifact."""
    steps = pipeline.named_steps
    if "scale" not in steps:
        return None
    z = steps["scale"].transform(steps["impute"].transform(X_train))
    return np.asarray(z, dtype=np.float64).mean(axis=0)


def _top_features(importance: dict[str, float], k: int = 5) -> list[str]:
    return [name for name, _ in sorted(importance.items(), key=lambda kv: (-kv[1], kv[0]))[:k]]


def _stability(
    name: ModelName,
    strategy: Any,
    names: tuple[str, ...],
    X_tr: pd.DataFrame,
    y_tr: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    seeds: tuple[int, ...],
) -> dict[str, Any]:
    pr_aucs: list[float] = []
    tops: list[list[str]] = []
    sample = X_val.sample(n=min(EXPLAIN_SAMPLE, len(X_val)), random_state=0)
    for seed in seeds:
        pipe = build_pipeline(name, strategy, y_train=y_tr, seed=seed).fit(X_tr, y_tr)
        pr_aucs.append(float(average_precision_score(y_val, _proba(pipe, X_val))))
        explainer = ModelExplainer(
            pipe, model_name=name, feature_names=names, background_means=_background_means(pipe, X_tr)
        )
        tops.append(_top_features(explainer.mean_abs_contribution(sample)))
    jaccards = [len(set(a) & set(b)) / len(set(a) | set(b)) for a, b in itertools.combinations(tops, 2)]
    return {
        "seeds": list(seeds),
        "val_pr_auc": pr_aucs,
        "val_pr_auc_mean": float(np.mean(pr_aucs)),
        "val_pr_auc_std": float(np.std(pr_aucs)),
        "top5_features_by_seed": tops,
        "top5_jaccard_mean": float(np.mean(jaccards)),
    }


def _risk_thresholds(p_val: np.ndarray, config: TrainingConfig) -> RiskThresholds:
    q = config.risk_level_quantiles
    values = np.quantile(p_val, [q.watch, q.elevated, q.high])
    return RiskThresholds(watch=float(values[0]), elevated=float(values[1]), high=float(values[2]))


def _level_table(y: np.ndarray, p: np.ndarray, thresholds: RiskThresholds) -> list[dict[str, Any]]:
    levels = np.array([thresholds.level(float(v)) for v in p])
    rows = []
    for level in ("stable", "watch", "elevated", "high"):
        mask = levels == level
        rows.append(
            {
                "risk_level": level,
                "n": int(mask.sum()),
                "share": float(mask.mean()),
                "observed_rate": float(y[mask].mean()) if mask.any() else None,
                "mean_predicted": float(p[mask].mean()) if mask.any() else None,
            }
        )
    return rows


def _calibration_decision(
    config: TrainingConfig, name: ModelName, strategy: Any, df: pd.DataFrame, names: tuple[str, ...]
) -> dict[str, Any]:
    """Apply calibration only if an out-of-time check shows it improves BOTH Brier and ECE."""
    check = config.calibration_check
    if check is None:
        return {"apply": False, "reason": "no calibration check configured; calibration not applied"}
    frames = split_frame(df, check.to_split())
    X_a, y_a = _xy(frames.train, names)
    X_b, y_b = _xy(frames.validation, names)
    X_c, y_c = _xy(frames.test, names)
    if len(np.unique(y_a)) < 2 or len(np.unique(y_b)) < 2 or len(np.unique(y_c)) < 2:
        return {"apply": False, "reason": "a check split has a single class; calibration not applied"}
    pipe = build_pipeline(name, strategy, y_train=y_a, seed=config.random_seed).fit(X_a, y_a)
    calibrator = CalibratedClassifierCV(
        FrozenEstimator(pipe), method=config.calibration_method, ensemble=False
    ).fit(X_b, y_b)
    raw, cal = _proba(pipe, X_c), _proba(calibrator, X_c)
    brier_raw, brier_cal = float(brier_score_loss(y_c, raw)), float(brier_score_loss(y_c, cal))
    ece_raw, ece_cal = expected_calibration_error(y_c, raw), expected_calibration_error(y_c, cal)
    apply = bool(brier_cal < brier_raw and ece_cal < ece_raw)
    return {
        "check_split": {
            "train": list(check.train),
            "calibrate": list(check.calibrate),
            "evaluate": list(check.evaluate),
        },
        "method": config.calibration_method,
        "brier_raw": brier_raw,
        "brier_calibrated": brier_cal,
        "ece_raw": ece_raw,
        "ece_calibrated": ece_cal,
        "apply": apply,
        "reason": (
            "calibration improved Brier and ECE out of time"
            if apply
            else "calibration did not improve both Brier and ECE out of time; not applied"
        ),
    }


def train_target_cutoff(
    config: TrainingConfig,
    tables: OuladTables,
    target: str,
    cutoff: int,
    *,
    run_id: str,
    ds_version: str,
    registry_root: Path,
    repo_root: Path,
    timestamp: datetime,
    leakage_check: dict[str, Any],
) -> dict[str, Any]:
    names = feature_names(config.feature_version)
    df = build_oulad_features(
        tables,
        cutoff,
        score_release_lag_days=config.score_release_lag_days,
        target=target,
        feature_version=config.feature_version,
    )
    validate_feature_table(df, names)
    frames = split_frame(df, config.split.to_split())
    X_tr, y_tr = _xy(frames.train, names)
    X_val, y_val = _xy(frames.validation, names)
    X_te, y_te = _xy(frames.test, names)

    distribution: dict[str, dict[str, Any]] = {
        split: {
            "n": len(f),
            "positives": int(f[TARGET_COLUMN].sum()),
            "prevalence": float(f[TARGET_COLUMN].mean()),
            "groups": sorted(f["split_group"].unique()),
        }
        for split, f in (("train", frames.train), ("validation", frames.validation), ("test", frames.test))
    }
    header = {
        "target": target,
        "target_definition": TARGETS[target].definition,
        "target_horizon": TARGETS[target].horizon,
        "cutoff_day": cutoff,
        "rows": len(df),
        "unassigned_rows": frames.unassigned_rows,
        "distribution": distribution,
    }
    minimum = config.min_class_count_per_split
    short = [
        f"{split}: {d['positives']} positives / {d['n'] - d['positives']} negatives"
        for split, d in distribution.items()
        if min(d["positives"], d["n"] - d["positives"]) < minimum
    ]
    if short:
        reason = f"insufficient data (need >= {minimum} of each class per split): " + "; ".join(short)
        print(f"  {target} day {cutoff}: SKIPPED - {reason}", flush=True)
        return {**header, "skipped": True, "skip_reason": reason}

    models: dict[str, Any] = {}
    candidates: list[Candidate] = []

    for name in config.models:
        comparison: list[StrategyResult] = []
        fitted: dict[str, Pipeline] = {}
        for strategy in config.imbalance_strategies:
            pipe = build_pipeline(name, strategy, y_train=y_tr, seed=config.random_seed).fit(X_tr, y_tr)
            p = _proba(pipe, X_val)
            comparison.append(
                StrategyResult(
                    strategy=strategy,
                    val_pr_auc=float(average_precision_score(y_val, p)),
                    val_roc_auc=float(roc_auc_score(y_val, p)),
                    val_brier=float(brier_score_loss(y_val, p)),
                )
            )
            fitted[strategy] = pipe
        strategy, strategy_rationale = choose_imbalance_strategy(comparison)
        pipe = fitted[strategy]
        stability = _stability(name, strategy, names, X_tr, y_tr, X_val, y_val, config.stability_seeds)

        decision = _calibration_decision(config, name, strategy, df, names)
        fitted_calibrator = CalibratedClassifierCV(
            FrozenEstimator(pipe), method=config.calibration_method, ensemble=False
        ).fit(X_val, y_val)
        calibrator: Any = fitted_calibrator if decision["apply"] else pipe
        p_val = _proba(calibrator, X_val)
        thresholds = _risk_thresholds(p_val, config)
        decision_threshold = best_f1_threshold(y_val, p_val)

        p_te_raw = _proba(pipe, X_te)
        p_te_cal = _proba(fitted_calibrator, X_te)
        p_te = _proba(calibrator, X_te)
        val_metrics = evaluate(y_val, p_val, threshold=decision_threshold, top_fractions=config.top_fractions)
        test_metrics = evaluate(y_te, p_te, threshold=decision_threshold, top_fractions=config.top_fractions)
        calibration_on_test = {
            "raw": {
                "brier": float(brier_score_loss(y_te, p_te_raw)),
                "ece": expected_calibration_error(y_te, p_te_raw),
            },
            "calibrated": {
                "brier": float(brier_score_loss(y_te, p_te_cal)),
                "ece": expected_calibration_error(y_te, p_te_cal),
            },
            "applied": decision["apply"],
        }
        ci = bootstrap_ci(
            y_te,
            p_te,
            frames.test["student_id"].to_numpy(),
            {
                "pr_auc": lambda y, p: float(average_precision_score(y, p)),
                "roc_auc": lambda y, p: float(roc_auc_score(y, p)),
                "brier": lambda y, p: float(brier_score_loss(y, p)),
            },
            iterations=config.bootstrap_iterations,
            seed=config.random_seed,
        )
        subgroups: dict[str, Any] = {}
        for col in frames.test.columns:
            if col.startswith(AUDIT_PREFIX):
                rows = subgroup_metrics(y_te, p_te, frames.test[col].to_numpy(), threshold=decision_threshold)
                subgroups[col.removeprefix(AUDIT_PREFIX)] = {
                    "groups": rows,
                    "disparity": disparity_summary(rows),
                }

        feature_stats, feature_alerts = feature_drift(X_tr, X_te, names)
        pred_psi, pred_alerts = prediction_drift(_proba(calibrator, X_tr), p_te)
        drift = {
            "reference": "training period",
            "current": "test period",
            "features": feature_stats,
            "prediction_psi": pred_psi,
            "alerts": [
                a.as_dict()
                for a in (
                    feature_alerts
                    + pred_alerts
                    + outcome_drift(float(y_tr.mean()), float(y_te.mean()))
                    + performance_drop(float(val_metrics["pr_auc"]), float(test_metrics["pr_auc"]))
                )
            ],
        }
        snapshot = monitoring_snapshot(p_te, [thresholds.level(float(v)) for v in p_te], X_te, names)

        background = _background_means(pipe, X_tr)
        explainer = ModelExplainer(pipe, model_name=name, feature_names=names, background_means=background)
        importance = explainer.mean_abs_contribution(
            X_te.sample(n=min(1000, len(X_te)), random_state=config.random_seed)
        )

        model_version = f"{run_id}-{TARGET_ABBREVIATIONS[target]}-{MODEL_ABBREVIATIONS[name]}-d{cutoff}"
        metrics = clean_for_json(
            {
                "validation": val_metrics,
                "test": test_metrics,
                "test_calibration_comparison": calibration_on_test,
                "test_bootstrap_ci": ci,
                "test_risk_levels": _level_table(y_te, p_te, thresholds),
                "imbalance_comparison": [vars(r) for r in comparison],
                "stability": stability,
                "subgroups_test": subgroups,
                "drift_train_vs_test": drift,
                "monitoring_snapshot_test": snapshot,
                "global_importance_test": dict(sorted(importance.items(), key=lambda kv: -kv[1])),
            }
        )
        metadata = ModelMetadata(
            model_version=model_version,
            model_name=name,
            feature_version=config.feature_version,
            feature_names=names,
            dataset_name=DATASET_NAME,
            dataset_version=ds_version,
            data_provenance=config.dataset.provenance,
            cutoff_day=cutoff,
            target=target,
            target_definition=f"{TARGETS[target].definition}; horizon: {TARGETS[target].horizon}",
            training_timestamp=timestamp,
            split={
                "train": list(config.split.train),
                "validation": list(config.split.validation),
                "test": list(config.split.test),
            },
            imbalance_strategy=strategy,
            hyperparameters=model_hyperparameters(pipe),
            calibration_method=config.calibration_method if decision["apply"] else "none",
            calibration_decision=clean_for_json(decision),
            leakage_check=leakage_check,
            risk_thresholds=thresholds,
            decision_threshold=decision_threshold,
            explanation_units=EXPLANATION_UNITS[name],
            metrics=json.loads(json.dumps(metrics, default=float)),
            random_seed=config.random_seed,
            library_versions=_library_versions(),
            git_commit=_git_commit(repo_root),
        )
        saved = ModelArtifact(
            pipeline=pipe, calibrator=calibrator, metadata=metadata, background_means=background
        ).save(registry_root / model_version)
        models[name] = {
            "model_version": model_version,
            "imbalance_strategy": strategy,
            "imbalance_rationale": strategy_rationale,
            "calibration_decision": clean_for_json(decision),
            "risk_thresholds": thresholds.model_dump(),
            "decision_threshold": decision_threshold,
            "model_sha256": saved.model_sha256,
            **metrics,
        }
        candidates.append(
            Candidate(
                model_name=name,
                val_pr_auc=float(val_metrics["pr_auc"]),
                val_brier=float(val_metrics["brier"]),
                stability_pr_auc_std=float(stability["val_pr_auc_std"]),
            )
        )
        print(
            f"  {target} day {cutoff} {name}: val PR-AUC {val_metrics['pr_auc']:.4f} "
            f"test PR-AUC {test_metrics['pr_auc']:.4f} calibration applied={decision['apply']}",
            flush=True,
        )

    selected, rationale = select_model(candidates, config.selection_tolerance_pr_auc)
    return {
        **header,
        "skipped": False,
        "models": models,
        "selected_model": selected,
        "selected_model_version": models[selected]["model_version"],
        "selection_rationale": rationale,
    }


def run(config: TrainingConfig, repo_root: Path) -> dict[str, Any]:
    timestamp = datetime.now(UTC).replace(microsecond=0)
    run_id = f"{config.run_name}-{timestamp:%Y%m%dT%H%M%SZ}"
    dataset_path = (
        config.dataset.path if config.dataset.path.is_absolute() else repo_root / config.dataset.path
    )
    registry_root = config.output_dir if config.output_dir.is_absolute() else repo_root / config.output_dir
    report_root = config.report_dir if config.report_dir.is_absolute() else repo_root / config.report_dir

    ds_version = dataset_version(dataset_path)
    print(f"run {run_id}: dataset {ds_version} ({config.dataset.provenance})", flush=True)
    tables = load_oulad(dataset_path)

    # Temporal leakage guard: raises TemporalLeakageError (and stops the run) on any leak.
    leakage: dict[int, dict[str, Any]] = {}
    for cutoff in config.cutoff_days:
        check = assert_no_future_leakage(
            tables,
            cutoff,
            score_release_lag_days=config.score_release_lag_days,
            feature_version=config.feature_version,
        )
        leakage[cutoff] = {
            "passed": True,
            "rows_compared": check.rows_compared,
            "features_compared": check.features_compared,
        }
        print(f"leakage guard day {cutoff}: passed ({check.rows_compared} rows)", flush=True)

    results = [
        train_target_cutoff(
            config,
            tables,
            target,
            cutoff,
            run_id=run_id,
            ds_version=ds_version,
            registry_root=registry_root,
            repo_root=repo_root,
            timestamp=timestamp,
            leakage_check=leakage[cutoff],
        )
        for target in config.targets
        for cutoff in config.cutoff_days
    ]
    primary = next(
        r
        for r in results
        if r["target"] == config.primary_target and r["cutoff_day"] == config.primary_cutoff_day
    )
    if primary["skipped"]:
        raise RuntimeError(f"primary target/cutoff could not be trained: {primary['skip_reason']}")
    ModelRegistry(registry_root).set_active(primary["selected_model_version"])

    summary = {
        "run_id": run_id,
        "created_at": timestamp.isoformat(),
        "config": json.loads(config.model_dump_json()),
        "dataset": {
            "name": DATASET_NAME,
            "version": ds_version,
            "provenance": config.dataset.provenance,
            "description": config.dataset.description,
        },
        "feature_version": config.feature_version,
        "feature_names": list(feature_names(config.feature_version)),
        "targets": {
            t: {"definition": TARGETS[t].definition, "horizon": TARGETS[t].horizon} for t in config.targets
        },
        "target_definition": "; ".join(f"{t}: {TARGETS[t].definition}" for t in config.targets),
        "leakage_checks": {str(k): v for k, v in leakage.items()},
        "library_versions": _library_versions(),
        "git_commit": _git_commit(repo_root),
        "active_model_version": primary["selected_model_version"],
        "cutoffs": results,
    }
    write_reports(summary, report_root / run_id)
    print(f"active model: {primary['selected_model_version']}", flush=True)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    run(load_config(args.config), Path.cwd())
    return 0


if __name__ == "__main__":
    sys.exit(main())
