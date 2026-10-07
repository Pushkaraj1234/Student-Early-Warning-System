"""EWS v3 longitudinal experiment on the student-week panel (plan: docs/research/ews-v3-longitudinal-plan.md).

Stages: temporal-leakage guard -> panel -> description and Kaplan-Meier -> academic models (L1 logistic,
random forest, XGBoost on v2 and on oulad-ts-1.0.0 features, GRU / LSTM / TCN, ensemble) -> pre-specified
comparisons P1, P2 -> thresholds, alert policies, lead time, tier stability, P4 -> calibration -> fairness ->
explanations (SHAP, LASSO, counterfactuals) -> MC dropout -> withdrawal horizons, SMOTE, hazard model,
C-index -> rolling-origin CV -> leave-one-module-out, P5 -> drift -> Holm -> artifacts -> report.

Every expensive step is cached in a git-ignored work folder, so ``--resume RUN_ID`` continues an interrupted
run. Reports contain aggregates only (no student identifiers).

Usage (from the repository root):
    ml/.venv/Scripts/python -m ml.longitudinal.experiment --config ml/configs/longitudinal_v3.json \
        [--resume RUN_ID]
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import itertools
import json
import platform
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any, TypeVar

import joblib
import numpy as np
import pandas as pd
import sklearn
import torch
import xgboost
from scipy.stats import spearmanr, wilcoxon
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score, brier_score_loss

from ml.analysis.hypotheses import cluster_weights, holm
from ml.data.contract import AUDIT_PREFIX, validate_feature_table
from ml.data.oulad import DATASET_NAME, dataset_version, load_oulad
from ml.evaluation.metrics import (
    disparity_summary,
    expected_calibration_error,
    subgroup_metrics,
    threshold_metrics,
)
from ml.explainability.shap_explainer import ModelExplainer
from ml.features.oulad_features import AUDIT_ATTRIBUTES
from ml.longitudinal import alerts, counterfactual, survival
from ml.longitudinal.config import LongitudinalConfig, load_longitudinal_config
from ml.longitudinal.evaluation import (
    bootstrap_ap,
    by_week,
    equal_opportunity_thresholds,
    group_recall_gap,
    headline,
    interval,
    paired_comparison,
    student_rate_bootstrap,
)
from ml.longitudinal.panel import (
    FEATURE_VERSION_TS,
    LONGITUDINAL_FEATURES,
    TS_FEATURE_NAMES,
    V2_FEATURE_NAMES,
    assert_panel_no_leakage,
    label_column,
    load_or_build_panel,
)
from ml.longitudinal.report import write_report
from ml.longitudinal.sequence import (
    SequenceData,
    Standardizer,
    predict_sequences,
    scatter_to_rows,
    to_sequences,
    train_sequence_model,
)
from ml.longitudinal.tabular import (
    Imbalance,
    TabularName,
    TuningResult,
    build_tabular,
    proba,
    tune_l1,
    tune_xgboost,
)
from ml.monitoring.drift import clean_for_json, feature_drift

T = TypeVar("T")
ACADEMIC = "academic"
HORIZONS = ("withdraw_4w", "withdraw_8w")
HAZARD = "withdraw_1w"
IMBALANCES: tuple[Imbalance, ...] = ("none", "weights", "smote")
GENDERS = ("M", "F")
EARLY_WEEKS = 8
TOP_K = 15
# Deployment default: the 2-consecutive-week policy unless it costs more than this much student-level recall.
MAX_RECALL_LOSS_FOR_SMOOTHING = 0.02
REFERENCE_BINS = 10
FitResult = tuple[Any, dict[str, np.ndarray]]


# ------------------------------------------------------------------ run context
@dataclass
class Run:
    config: LongitudinalConfig
    repo_root: Path
    run_id: str
    report_dir: Path
    work_dir: Path
    results: dict[str, Any] = field(default_factory=dict)
    started: float = field(default_factory=time.time)

    def log(self, message: str) -> None:
        print(f"[{(time.time() - self.started) / 60:6.1f} min] {message}", flush=True)

    def memo(self, name: str, compute: Callable[[], T]) -> T:
        """Compute once per run; cached in the git-ignored work folder for --resume."""
        path = self.work_dir / f"{name}.joblib"
        if path.is_file():
            cached: T = joblib.load(path)
            return cached
        value = compute()
        joblib.dump(value, path)
        return value

    def load(self, name: str) -> Any:
        """A result an earlier stage cached with ``memo``."""
        path = self.work_dir / f"{name}.joblib"
        if not path.is_file():
            raise RuntimeError(f"stage output {name!r} is missing; run the earlier stage first")
        return joblib.load(path)

    def save(self) -> None:
        payload = clean_for_json(self.results)
        (self.report_dir / "results.json").write_text(
            json.dumps(payload, indent=2, default=float), encoding="utf-8"
        )


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


# ------------------------------------------------------------------ data helpers
@dataclass(frozen=True)
class Frames:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame


def _rows(panel: pd.DataFrame, groups: tuple[str, ...], label: str) -> pd.DataFrame:
    mask = panel["split_group"].isin(groups) & panel[label].notna()
    return panel.loc[mask].reset_index(drop=True)


def _frames(panel: pd.DataFrame, config: LongitudinalConfig, label: str) -> Frames:
    s = config.split
    return Frames(
        _rows(panel, s.train, label), _rows(panel, s.validation, label), _rows(panel, s.test, label)
    )


def _features(frame: pd.DataFrame, features: tuple[str, ...]) -> pd.DataFrame:
    return frame.loc[:, list(features)].astype(np.float32)


def _y(frame: pd.DataFrame, label: str) -> np.ndarray:
    return frame[label].to_numpy(dtype=np.int64)


def _ap(y: np.ndarray, p: np.ndarray) -> float:
    return float(average_precision_score(y, p))


def _clusters(frame: pd.DataFrame) -> np.ndarray:
    """Bootstrap cluster = the student (OULAD id_student), across weeks and registrations."""
    return frame["student_id"].astype(str).to_numpy()


def _sequences(run: Run, frames: Frames, label: str) -> tuple[SequenceData, SequenceData, SequenceData]:
    std = Standardizer.fit(frames.train, TS_FEATURE_NAMES)
    weeks = run.config.last_week
    return (
        to_sequences(frames.train, label, std, max_week=weeks),
        to_sequences(frames.validation, label, std, max_week=weeks),
        to_sequences(frames.test, label, std, max_week=weeks),
    )


def _tabular_predictions(
    name: TabularName,
    imbalance: Imbalance,
    params: dict[str, Any],
    frames: Frames,
    features: tuple[str, ...],
    label: str,
    seed: int,
) -> FitResult:
    y_tr = _y(frames.train, label)
    pipe = build_tabular(name, imbalance, params=params, y_train=y_tr, seed=seed).fit(
        _features(frames.train, features), y_tr
    )
    return pipe, {
        "val": proba(pipe, _features(frames.validation, features)),
        "test": proba(pipe, _features(frames.test, features)),
    }


# ------------------------------------------------------------------ panel, description, survival
def stage_panel(run: Run) -> pd.DataFrame:
    config = run.config
    dataset_path = _resolve(run.repo_root, config.dataset.path)
    version = dataset_version(dataset_path)
    run.results["dataset"] = {
        "name": DATASET_NAME,
        "version": version,
        "provenance": config.dataset.provenance,
        "description": config.dataset.description,
    }
    tables = load_oulad(dataset_path)
    guard: dict[str, int] = {}
    for week in config.leakage_check_weeks:
        guard[str(week)] = assert_panel_no_leakage(
            tables, week, score_release_lag_days=config.score_release_lag_days
        )
        run.log(f"leakage guard week {week}: passed ({guard[str(week)]} rows)")
    run.results["leakage_guard"] = {"passed": True, "rows_compared_by_week": guard}
    panel = load_or_build_panel(
        tables,
        weeks=config.weeks,
        score_release_lag_days=config.score_release_lag_days,
        cache_dir=_resolve(run.repo_root, config.cache_dir),
        dataset_version=version,
    )
    del tables
    gc.collect()
    validate_feature_table(panel, TS_FEATURE_NAMES, require_target=False)
    registrations = panel[["context_id", "student_id"]].drop_duplicates().shape[0]
    run.log(f"panel: {len(panel)} student-weeks, {registrations} registrations")
    return panel


def stage_describe(run: Run, panel: pd.DataFrame) -> None:
    splits: dict[str, Any] = {}
    for split in ("train", "validation", "test"):
        groups = getattr(run.config.split, split)
        part = panel[panel["split_group"].isin(groups)]
        splits[split] = {
            "presentations": list(groups),
            "student_weeks": len(part),
            "registrations": int(part[["context_id", "student_id"]].drop_duplicates().shape[0]),
            "prevalence": {t: float(part[label_column(t)].mean()) for t in (ACADEMIC, HAZARD, *HORIZONS)},
        }
    weekly = (
        panel.groupby("week")
        .agg(
            student_weeks=("week", "size"),
            academic=("y_academic", "mean"),
            withdraw_4w=("y_withdraw_4w", "mean"),
            withdraw_8w=("y_withdraw_8w", "mean"),
        )
        .reset_index()
    )
    unknown = panel.loc[panel["y_withdraw_4w"].isna(), ["context_id", "student_id"]].drop_duplicates()
    run.results["panel"] = {
        "feature_version": FEATURE_VERSION_TS,
        "features": len(TS_FEATURE_NAMES),
        "v2_features": len(V2_FEATURE_NAMES),
        "longitudinal_features": [s.name for s in LONGITUDINAL_FEATURES],
        "weeks": [run.config.first_week, run.config.last_week],
        "splits": splits,
        "by_week": weekly.to_dict(orient="records"),
        "longitudinal_missing_share": {
            s.name: float(panel[s.name].isna().mean()) for s in LONGITUDINAL_FEATURES
        },
        "withdrawn_unknown_week_registrations": len(unknown),
    }


def _registrations(panel: pd.DataFrame, groups: tuple[str, ...]) -> pd.DataFrame:
    """One row per registration present at week 1: event = left (known week), else censored at course end."""
    first = panel[(panel["week"] == 1) & panel["split_group"].isin(groups) & panel["y_withdraw_4w"].notna()]
    event = first["withdraw_week"].notna().to_numpy()
    duration = np.where(event, first["withdraw_week"], first["course_end_week"]).astype(np.float64)
    return pd.DataFrame(
        {
            "module": first["module"].astype(str).to_numpy(),
            "event": event,
            "duration": duration,
            "week1_clicks": first["clicks_this_week"].to_numpy(dtype=np.float64),
        }
    )


def stage_kaplan_meier(run: Run, panel: pd.DataFrame) -> None:
    regs = _registrations(panel, run.config.split.train)

    def curve(frame: pd.DataFrame) -> pd.DataFrame:
        return survival.kaplan_meier(frame["duration"].to_numpy(), frame["event"].to_numpy())

    def summary(c: pd.DataFrame) -> dict[str, float]:
        return {f"retained_week_{w}": survival.survival_at(c, w) for w in (4, 8, 13, 20, 30)}

    tertile = pd.qcut(regs["week1_clicks"].rank(method="first"), 3, labels=["low", "middle", "high"])
    by_activity = {str(t): curve(g) for t, g in regs.groupby(tertile, observed=True)}
    overall = curve(regs)
    run.results["kaplan_meier"] = {
        "population": "training presentations; registrations present at week 1 with a known withdrawal week",
        "registrations": len(regs),
        "events": int(regs["event"].sum()),
        "overall": summary(overall),
        "by_module": {m: summary(curve(g)) for m, g in regs.groupby("module", sort=True)},
        "by_week1_activity_tertile": {t: summary(c) for t, c in by_activity.items()},
        "curves": {
            "overall": overall.to_dict(orient="list"),
            "by_week1_activity_tertile": {t: c.to_dict(orient="list") for t, c in by_activity.items()},
        },
    }


# ------------------------------------------------------------------ academic models
@dataclass
class AcademicModels:
    predictions: dict[str, dict[str, np.ndarray]]
    tuning: dict[str, Any]
    best_sequence: str
    sequence_settings: dict[str, Any]


def _sequence_search(
    run: Run, frames: Frames, label: str
) -> tuple[dict[str, Any], dict[str, dict[str, np.ndarray]], dict[str, Any]]:
    grid = run.config.sequence_grid
    seq_tr, seq_val, seq_te = _sequences(run, frames, label)
    y_val = _y(frames.validation, label)
    trials: list[dict[str, Any]] = []
    best: dict[str, dict[str, Any]] = {}
    for kind, hidden, dropout in itertools.product(grid.kinds, grid.hidden, grid.dropout):
        model, log = train_sequence_model(
            kind,
            seq_tr,
            hidden=hidden,
            dropout=dropout,
            seed=run.config.random_seed,
            epochs=grid.max_epochs,
            validation=seq_val,
            patience=grid.patience,
        )
        p_val = scatter_to_rows(predict_sequences(model, seq_val), seq_val, len(frames.validation))
        score = _ap(y_val, p_val)
        trial = {
            "kind": kind,
            "hidden": hidden,
            "dropout": dropout,
            "best_epoch": log.best_epoch,
            "epochs_run": len(log.train_loss),
            "val_loss": min(log.val_loss),
            "val_pr_auc": score,
        }
        trials.append(trial)
        run.log(f"  {kind} h={hidden} d={dropout}: val PR-AUC {score:.4f} (best epoch {log.best_epoch})")
        if kind not in best or score > best[kind]["val_pr_auc"]:
            best[kind] = {**trial, "model": model, "p_val": p_val}
    predictions: dict[str, dict[str, np.ndarray]] = {}
    settings: dict[str, Any] = {}
    for best_kind, b in best.items():
        predictions[best_kind] = {
            "val": b["p_val"],
            "test": scatter_to_rows(predict_sequences(b["model"], seq_te), seq_te, len(frames.test)),
        }
        settings[best_kind] = {k: v for k, v in b.items() if k not in ("model", "p_val")}
        joblib.dump(b["model"], run.work_dir / f"sequence_{label}_{best_kind}.joblib")
    return {"trials": trials}, predictions, settings


def stage_academic_models(run: Run, panel: pd.DataFrame) -> AcademicModels:
    label = label_column(ACADEMIC)
    frames = _frames(panel, run.config, label)
    seed = run.config.random_seed
    y_tr, y_val = _y(frames.train, label), _y(frames.validation, label)
    preds: dict[str, dict[str, np.ndarray]] = {}
    tuning: dict[str, Any] = {}

    for name, features in (("xgb_v2", V2_FEATURE_NAMES), ("xgb_ts", TS_FEATURE_NAMES)):
        result: TuningResult = run.memo(
            f"tune_{name}",
            partial(
                tune_xgboost,
                _features(frames.train, features),
                y_tr,
                _features(frames.validation, features),
                y_val,
                imbalance="none",
                n_settings=run.config.xgb_search_settings,
                seed=seed,
            ),
        )
        tuning[name] = {"params": result.params, "val_pr_auc": result.val_pr_auc, "trials": result.trials}
        _, preds[name] = run.memo(
            f"fit_{name}",
            partial(_tabular_predictions, "xgboost", "none", result.params, frames, features, label, seed),
        )
        run.log(f"{name}: val PR-AUC {_ap(y_val, preds[name]['val']):.4f}")

    l1_result, l1_pipe = run.memo(
        "tune_l1_ts",
        lambda: tune_l1(
            _features(frames.train, TS_FEATURE_NAMES),
            y_tr,
            _features(frames.validation, TS_FEATURE_NAMES),
            y_val,
            seed=seed,
        ),
    )
    tuning["l1_ts"] = {
        "params": l1_result.params,
        "val_pr_auc": l1_result.val_pr_auc,
        "trials": l1_result.trials,
    }
    preds["l1_ts"] = {
        "val": proba(l1_pipe, _features(frames.validation, TS_FEATURE_NAMES)),
        "test": proba(l1_pipe, _features(frames.test, TS_FEATURE_NAMES)),
    }
    run.log(f"l1_ts: C={l1_result.params['C']} val PR-AUC {l1_result.val_pr_auc:.4f}")

    _, preds["rf_ts"] = run.memo(
        "fit_rf_ts",
        lambda: _tabular_predictions("random_forest", "none", {}, frames, TS_FEATURE_NAMES, label, seed),
    )
    run.log(f"rf_ts: val PR-AUC {_ap(y_val, preds['rf_ts']['val']):.4f}")

    search, seq_preds, settings = run.memo(
        "sequence_search_academic", lambda: _sequence_search(run, frames, label)
    )
    tuning["sequence"] = search
    preds.update(seq_preds)
    best_sequence = max(seq_preds, key=lambda k: float(settings[k]["val_pr_auc"]))
    preds["ensemble"] = {
        part: (preds["xgb_ts"][part] + preds[best_sequence][part]) / 2 for part in ("val", "test")
    }
    prevalence = float(y_tr.mean())
    preds["prevalence_baseline"] = {
        "val": np.full(len(frames.validation), prevalence),
        "test": np.full(len(frames.test), prevalence),
    }
    return AcademicModels(
        predictions=preds, tuning=tuning, best_sequence=best_sequence, sequence_settings=settings
    )


def stage_academic_evaluation(run: Run, panel: pd.DataFrame, models: AcademicModels) -> str:
    label = label_column(ACADEMIC)
    frames = _frames(panel, run.config, label)
    y_val, y_te = _y(frames.validation, label), _y(frames.test, label)
    weeks_te = frames.test["week"].to_numpy(dtype=np.int64)
    candidates = [m for m in models.predictions if m != "prevalence_baseline"]
    selected = max(candidates, key=lambda m: _ap(y_val, models.predictions[m]["val"]))
    test_preds = {m: p["test"] for m, p in models.predictions.items()}
    samples = run.memo(
        "bootstrap_academic",
        lambda: bootstrap_ap(
            y_te,
            test_preds,
            _clusters(frames.test),
            resamples=run.config.bootstrap_resamples,
            seed=run.config.random_seed,
        ),
    )
    table = {}
    for m, p in models.predictions.items():
        table[m] = {
            "validation": headline(y_val, p["val"]),
            "test": headline(y_te, p["test"]),
            "test_pr_auc_ci": list(interval(samples[m])),
            "test_by_week": by_week(weeks_te, y_te, p["test"]),
        }
    seq = models.best_sequence
    p1 = paired_comparison(
        _ap(y_te, test_preds["xgb_ts"]) - _ap(y_te, test_preds["xgb_v2"]),
        samples["xgb_ts"],
        samples["xgb_v2"],
        two_sided=False,
    )
    p2 = paired_comparison(
        _ap(y_te, test_preds[seq]) - _ap(y_te, test_preds["xgb_ts"]),
        samples[seq],
        samples["xgb_ts"],
        two_sided=True,
    )
    run.results["academic"] = {
        "target": "Fail or Withdrawn at course end, predicted every week",
        "models": table,
        "tuning": models.tuning,
        "sequence_settings": models.sequence_settings,
        "best_sequence_model": seq,
        "selected_model": selected,
        "selection_rule": "highest validation PR-AUC (prevalence baseline excluded)",
        "comparisons": {
            "P1": {
                "description": "XGBoost oulad-ts-1.0.0 minus XGBoost v2 features, test PR-AUC (one-sided)",
                **p1,
            },
            "P2": {
                "description": (
                    f"best sequence model ({seq}) minus XGBoost oulad-ts-1.0.0, test PR-AUC (two-sided)"
                ),
                **p2,
            },
        },
    }
    run.log(f"academic: selected {selected}; P1 {p1['effect']:+.4f}; P2 {p2['effect']:+.4f}")
    return selected


# ------------------------------------------------------------------ thresholds and alerts
def stage_alerts(run: Run, panel: pd.DataFrame, models: AcademicModels, selected: str) -> dict[str, float]:
    label = label_column(ACADEMIC)
    frames = _frames(panel, run.config, label)
    y_val, y_te = _y(frames.validation, label), _y(frames.test, label)
    p_val, p_te = models.predictions[selected]["val"], models.predictions[selected]["test"]
    thresholds = {
        "f1": alerts.fbeta_threshold(y_val, p_val, 1.0),
        "f2": alerts.fbeta_threshold(y_val, p_val, 2.0),
    }
    for ratio in run.config.cost_ratios:
        thresholds[f"cost_{ratio:g}"] = alerts.cost_threshold(y_val, p_val, cost_fn=ratio, cost_fp=1.0)
    by_threshold = {}
    for name, thr in thresholds.items():
        flags = alerts.alert_flags(frames.test, p_te, thr, "raw")
        by_threshold[name] = {
            "threshold": thr,
            "student_week": threshold_metrics(y_te, p_te, thr),
            "student": alerts.student_metrics(alerts.student_alert_table(frames.test, flags)),
        }
    tables = {
        policy: alerts.student_alert_table(
            frames.test, alerts.alert_flags(frames.test, p_te, thresholds["f1"], policy)
        )
        for policy in alerts.ALERT_POLICIES
    }
    raw, smooth = tables["raw"], tables["consecutive_2"]
    if not raw[alerts.GROUP].equals(smooth[alerts.GROUP]):
        raise RuntimeError("alert tables must list registrations in the same order")
    by_policy = {policy: alerts.student_metrics(t) for policy, t in tables.items()}
    lead = raw.loc[raw["alerted"] & (raw["adverse"] == 1), "lead_time_weeks"]
    p4 = student_rate_bootstrap(
        raw["alerted"].to_numpy(),
        smooth["alerted"].to_numpy(),
        (raw["adverse"] == 0).to_numpy(),
        raw["student_id"].astype(str).to_numpy(),
        resamples=run.config.bootstrap_resamples,
        seed=run.config.random_seed,
    )
    cut_points = np.quantile(p_val, run.config.risk_level_quantiles)
    levels = np.searchsorted(cut_points, p_te, side="right").astype(np.int64)
    levels_smoothed = np.searchsorted(cut_points, alerts.ewma_risk(frames.test, p_te), side="right").astype(
        np.int64
    )
    recall_loss = float(by_policy["raw"]["recall"] or 0.0) - float(
        by_policy["consecutive_2"]["recall"] or 0.0
    )
    run.results["alerts"] = {
        "model": selected,
        "thresholds_from": "validation (2014B)",
        "by_threshold": by_threshold,
        "policies_at_f1": by_policy,
        "lead_time_weeks_histogram_raw_f1": {
            str(int(k)): int(v)
            for k, v in zip(*np.unique(lead.to_numpy(dtype=np.float64), return_counts=True), strict=True)
        },
        "risk_tiers": {
            "quantiles": list(run.config.risk_level_quantiles),
            "cut_points": cut_points.tolist(),
            "mean_tier_changes_per_registration_raw": alerts.mean_changes(frames.test, levels),
            "mean_tier_changes_per_registration_ewma": alerts.mean_changes(frames.test, levels_smoothed),
        },
        "P4": {
            "description": (
                "student-level false-alarm rate, raw minus 2-consecutive-week policy "
                "(F1 threshold, one-sided)"
            ),
            **p4,
        },
        "deployment_default_policy": "consecutive_2"
        if recall_loss <= MAX_RECALL_LOSS_FOR_SMOOTHING
        else "raw",
        "deployment_policy_rule": (
            f"consecutive_2 if it loses at most {MAX_RECALL_LOSS_FOR_SMOOTHING} student-level recall vs raw, "
            "else raw"
        ),
    }
    return thresholds


def stage_calibration(run: Run, panel: pd.DataFrame) -> None:
    label = label_column(ACADEMIC)
    frames = _frames(panel, run.config, label)
    pipe, _ = run.load("fit_xgb_ts")
    X_val, y_val = _features(frames.validation, TS_FEATURE_NAMES), _y(frames.validation, label)
    X_te, y_te = _features(frames.test, TS_FEATURE_NAMES), _y(frames.test, label)
    raw = proba(pipe, X_te)
    out: dict[str, Any] = {
        "raw": {"brier": float(brier_score_loss(y_te, raw)), "ece": expected_calibration_error(y_te, raw)}
    }
    for method in ("sigmoid", "isotonic"):
        cal = CalibratedClassifierCV(FrozenEstimator(pipe), method=method, ensemble=False).fit(X_val, y_val)
        p = proba(cal, X_te)
        out[method] = {"brier": float(brier_score_loss(y_te, p)), "ece": expected_calibration_error(y_te, p)}
    run.results["calibration"] = {
        "model": "xgb_ts",
        "calibrator_fitted_on": "validation (2014B)",
        "test": out,
    }


# ------------------------------------------------------------------ fairness
def stage_fairness(
    run: Run, panel: pd.DataFrame, models: AcademicModels, selected: str, threshold: float
) -> None:
    label = label_column(ACADEMIC)
    frames = _frames(panel, run.config, label)
    y_val, y_te = _y(frames.validation, label), _y(frames.test, label)
    p_val, p_te = models.predictions[selected]["val"], models.predictions[selected]["test"]
    subgroups = {}
    for attr in AUDIT_ATTRIBUTES:
        groups = frames.test[f"{AUDIT_PREFIX}{attr}"].astype(str).to_numpy()
        rows = subgroup_metrics(y_te, p_te, groups, threshold=threshold)
        subgroups[attr] = {"groups": rows, "disparity": disparity_summary(rows)}

    gender_val = frames.validation[f"{AUDIT_PREFIX}gender"].astype(str).to_numpy()
    gender_te = frames.test[f"{AUDIT_PREFIX}gender"].astype(str).to_numpy()
    target_recall = float(((p_val >= threshold) & (y_val == 1)).sum() / max(int(y_val.sum()), 1))
    per_group = equal_opportunity_thresholds(y_val, p_val, gender_val, target_recall)
    single = p_te >= threshold
    adjusted = p_te >= np.array([per_group.get(g, threshold) for g in gender_te])
    positive = {g: ((y_te == 1) & (gender_te == g)).astype(np.float64) for g in GENDERS}
    hits = {
        key: {g: (flagged & (y_te == 1) & (gender_te == g)).astype(np.float64) for g in GENDERS}
        for key, flagged in (("single", single), ("per_group", adjusted))
    }
    gaps: dict[str, list[float]] = {"single": [], "per_group": []}
    for w in cluster_weights(_clusters(frames.test), run.config.bootstrap_resamples, run.config.random_seed):
        for key in gaps:
            denominators = {g: float(w @ positive[g]) for g in GENDERS}
            if min(denominators.values()) <= 0:  # a resample without positives of one group: no gap defined
                gaps[key].append(float("nan"))
                continue
            recall = {g: float(w @ hits[key][g]) / denominators[g] for g in GENDERS}
            gaps[key].append(recall["F"] - recall["M"])
    run.results["fairness"] = {
        "model": selected,
        "threshold": threshold,
        "subgroups_test_student_weeks": subgroups,
        "equal_opportunity_gender": {
            "target_recall_from_validation": target_recall,
            "per_group_thresholds": per_group,
            "single_threshold": {
                **group_recall_gap(y_te, single, gender_te, *GENDERS),
                "recall_gap_ci": list(interval(np.asarray(gaps["single"]))),
            },
            "per_group_thresholds_result": {
                **group_recall_gap(y_te, adjusted, gender_te, *GENDERS),
                "recall_gap_ci": list(interval(np.asarray(gaps["per_group"]))),
            },
            "note": (
                "analysis only: using gender at decision time is an institutional, ethical and legal choice"
            ),
        },
        "demographics_as_inputs": run.memo(
            "demographics_sensitivity", lambda: _demographics_sensitivity(run, frames, label)
        ),
    }


def _safe(name: str) -> str:
    """XGBoost rejects feature names containing [, ] or <; OULAD's age band '55<=' has one."""
    return re.sub(r"[^A-Za-z0-9_]+", "_", name)


def _demographics_sensitivity(run: Run, frames: Frames, label: str) -> dict[str, Any]:
    tuned: TuningResult = run.load("tune_xgb_ts")
    cols = [f"{AUDIT_PREFIX}{a}" for a in AUDIT_ATTRIBUTES]
    dummies = [
        pd.get_dummies(f[cols].astype(str), dtype=np.float32).rename(columns=_safe)
        for f in (frames.train, frames.validation, frames.test)
    ]
    names = sorted(dummies[0].columns)
    X = [
        pd.concat([_features(f, TS_FEATURE_NAMES), d.reindex(columns=names, fill_value=0.0)], axis=1)
        for f, d in zip((frames.train, frames.validation, frames.test), dummies, strict=True)
    ]
    y_tr, y_val, y_te = _y(frames.train, label), _y(frames.validation, label), _y(frames.test, label)
    pipe = build_tabular("xgboost", "none", params=tuned.params, y_train=y_tr, seed=run.config.random_seed)
    pipe.fit(X[0], y_tr)
    p_val, p_te = proba(pipe, X[1]), proba(pipe, X[2])
    gender_te = frames.test[f"{AUDIT_PREFIX}gender"].astype(str).to_numpy()
    _, base = run.load("fit_xgb_ts")
    thr = alerts.fbeta_threshold(y_val, p_val, 1.0)
    base_thr = alerts.fbeta_threshold(y_val, base["val"], 1.0)
    return {
        "inputs_added": names,
        "with_demographics": {
            "test": headline(y_te, p_te),
            **group_recall_gap(y_te, p_te >= thr, gender_te, *GENDERS),
        },
        "without_demographics": {
            "test": headline(y_te, base["test"]),
            **group_recall_gap(y_te, base["test"] >= base_thr, gender_te, *GENDERS),
        },
        "note": "sensitivity analysis only; SEWS does not use demographics as model inputs",
    }


# ------------------------------------------------------------------ explanations and uncertainty
def stage_explanations(run: Run, panel: pd.DataFrame) -> None:
    label = label_column(ACADEMIC)
    frames = _frames(panel, run.config, label)
    seed = run.config.random_seed
    pipe, xgb_preds = run.load("fit_xgb_ts")
    explainer = ModelExplainer(
        pipe, model_name="xgboost", feature_names=TS_FEATURE_NAMES, background_means=None
    )
    sample = frames.test.sample(n=min(run.config.explain_sample, len(frames.test)), random_state=seed)
    longitudinal = {s.name for s in LONGITUDINAL_FEATURES}

    def top(frame: pd.DataFrame, k: int) -> list[dict[str, Any]]:
        values = explainer.mean_abs_contribution(_features(frame, TS_FEATURE_NAMES))
        ranked = sorted(values.items(), key=lambda kv: -kv[1])[:k]
        return [{"feature": f, "mean_abs_shap": v, "new_in_v3": f in longitudinal} for f, v in ranked]

    _, l1_pipe = run.load("tune_l1_ts")
    coef = l1_pipe.named_steps["model"].coef_[0]
    indicator = l1_pipe.named_steps["impute"].indicator_
    names = [*TS_FEATURE_NAMES, *(f"missing:{TS_FEATURE_NAMES[i]}" for i in indicator.features_)]
    order = np.argsort(-np.abs(coef))

    y_val = _y(frames.validation, label)
    thr = alerts.fbeta_threshold(y_val, xgb_preds["val"], 1.0)
    week_rows = frames.test[frames.test["week"] == run.config.counterfactual_week]
    flagged = week_rows[proba(pipe, _features(week_rows, TS_FEATURE_NAMES)) >= thr]
    chosen = flagged.sample(n=min(run.config.counterfactual_sample, len(flagged)), random_state=seed)
    candidates = counterfactual.candidate_values(frames.train, counterfactual.ACTIONABLE)

    def predict(frame: pd.DataFrame) -> np.ndarray:
        return proba(pipe, _features(frame, TS_FEATURE_NAMES))

    found = [
        counterfactual.find_counterfactual(
            chosen.iloc[[i]][list(TS_FEATURE_NAMES)].reset_index(drop=True), predict, thr, candidates
        )
        for i in range(len(chosen))
    ]
    solved = [c for c in found if c is not None]
    single = pd.Series([c.changes[0][0] for c in solved if len(c.changes) == 1], dtype=object).value_counts()
    pairs = pd.Series(
        [f for c in solved if len(c.changes) == 2 for f, _, _ in c.changes], dtype=object
    ).value_counts()
    run.results["explanations"] = {
        "shap": {
            "model": "xgb_ts",
            "units": "log-odds (SHAP, tree)",
            "rows": len(sample),
            "all_weeks": top(sample, TOP_K),
            "early_weeks": {
                "weeks": f"1-{EARLY_WEEKS}",
                "top": top(sample[sample["week"] <= EARLY_WEEKS], 10),
            },
            "later_weeks": {"weeks": f">{EARLY_WEEKS}", "top": top(sample[sample["week"] > EARLY_WEEKS], 10)},
        },
        "lasso": {
            "C": run.load("tune_l1_ts")[0].params["C"],
            "inputs": len(coef),
            "nonzero": int(np.count_nonzero(coef)),
            "zeroed_features": [
                n for n, c in zip(names, coef, strict=True) if c == 0 and not n.startswith("missing:")
            ],
            "top_coefficients_per_sd": [
                {"input": names[i], "coefficient": float(coef[i])} for i in order[:TOP_K] if coef[i] != 0
            ],
        },
        "counterfactuals": {
            "model": "xgb_ts",
            "week": run.config.counterfactual_week,
            "threshold": thr,
            "flagged_rows_at_week": len(flagged),
            "evaluated": len(chosen),
            "solved_with_1_change": sum(1 for c in solved if len(c.changes) == 1),
            "solved_with_2_changes": sum(1 for c in solved if len(c.changes) == 2),
            "not_solved": len(chosen) - len(solved),
            "single_change_features": {str(k): int(v) for k, v in single.items()},
            "two_change_features": {str(k): int(v) for k, v in pairs.items()},
            "median_risk_drop": float(np.median([c.risk_before - c.risk_after for c in solved]))
            if solved
            else None,
            "examples": [
                {
                    "changes": [{"feature": f, "from": a, "to": b} for f, a, b in c.changes],
                    "risk_before": c.risk_before,
                    "risk_after": c.risk_after,
                }
                for c in solved[:5]
            ],
            "actionable_features": dict(counterfactual.ACTIONABLE),
        },
    }


def stage_mc_dropout(run: Run, panel: pd.DataFrame, models: AcademicModels) -> None:
    label = label_column(ACADEMIC)
    frames = _frames(panel, run.config, label)
    kind = models.best_sequence
    model = joblib.load(run.work_dir / f"sequence_{label}_{kind}.joblib")
    _, _, seq_te = _sequences(run, frames, label)
    draws = predict_sequences(
        model, seq_te, mc_samples=run.config.mc_dropout_samples, seed=run.config.random_seed
    )
    mean = scatter_to_rows(draws.mean(axis=0), seq_te, len(frames.test))
    spread = scatter_to_rows(draws.std(axis=0), seq_te, len(frames.test))
    y = _y(frames.test, label)
    certain = spread <= np.quantile(spread, 0.8)
    rho = spearmanr(spread, np.abs(y - mean))
    run.results["mc_dropout"] = {
        "model": kind,
        "samples": run.config.mc_dropout_samples,
        "test_pr_auc_mean_prediction": _ap(y, mean),
        "test_pr_auc_most_certain_80pct": _ap(y[certain], mean[certain]),
        "test_pr_auc_least_certain_20pct": _ap(y[~certain], mean[~certain]),
        "spearman_uncertainty_vs_abs_error": float(rho.statistic),
        "uncertainty_quantiles_p10_p50_p90": np.quantile(spread, [0.1, 0.5, 0.9]).tolist(),
    }


# ------------------------------------------------------------------ withdrawal horizons and hazard
def _fit_sequence(run: Run, frames: Frames, label: str, settings: dict[str, Any]) -> dict[str, np.ndarray]:
    seq_tr, seq_val, seq_te = _sequences(run, frames, label)
    model, _ = train_sequence_model(
        settings["kind"],
        seq_tr,
        hidden=int(settings["hidden"]),
        dropout=float(settings["dropout"]),
        seed=run.config.random_seed,
        epochs=run.config.sequence_grid.max_epochs,
        validation=seq_val,
        patience=run.config.sequence_grid.patience,
    )
    return {
        "val": scatter_to_rows(predict_sequences(model, seq_val), seq_val, len(frames.validation)),
        "test": scatter_to_rows(predict_sequences(model, seq_te), seq_te, len(frames.test)),
    }


def stage_withdrawal(run: Run, panel: pd.DataFrame, models: AcademicModels) -> dict[str, dict[str, Any]]:
    seed = run.config.random_seed
    tuned_params: dict[str, dict[str, Any]] = {}
    out: dict[str, Any] = {}
    hazard: dict[str, np.ndarray] = {}
    for target in (*HORIZONS, HAZARD):
        label = label_column(target)
        frames = _frames(panel, run.config, label)
        X_tr, y_tr = _features(frames.train, TS_FEATURE_NAMES), _y(frames.train, label)
        X_val, y_val = _features(frames.validation, TS_FEATURE_NAMES), _y(frames.validation, label)
        y_te = _y(frames.test, label)
        xgb: TuningResult = run.memo(
            f"tune_xgb_{target}",
            partial(
                tune_xgboost,
                X_tr,
                y_tr,
                X_val,
                y_val,
                imbalance="none",
                n_settings=run.config.xgb_search_settings,
                seed=seed,
            ),
        )
        l1, _ = run.memo(f"tune_l1_{target}", partial(tune_l1, X_tr, y_tr, X_val, y_val, seed=seed))
        tuned_params[target] = {"xgboost": xgb.params, "l1_logistic": l1.params}
        variants: list[tuple[TabularName, Imbalance, dict[str, Any]]]
        if target == HAZARD:
            variants = [("xgboost", "none", xgb.params), ("l1_logistic", "none", l1.params)]
        else:
            variants = [("xgboost", i, xgb.params) for i in IMBALANCES] + [
                ("l1_logistic", i, l1.params) for i in IMBALANCES
            ]
        preds: dict[str, dict[str, np.ndarray]] = {}
        for name, imbalance, params in variants:
            key = f"{name}_{imbalance}"
            pipe, preds[key] = run.memo(
                f"fit_{target}_{key}",
                partial(_tabular_predictions, name, imbalance, params, frames, TS_FEATURE_NAMES, label, seed),
            )
            run.log(f"{target} {key}: val PR-AUC {_ap(y_val, preds[key]['val']):.4f}")
            if target == HAZARD and name == "l1_logistic":
                coef = pipe.named_steps["model"].coef_[0][: len(TS_FEATURE_NAMES)]
                top = np.argsort(-np.abs(coef))[:10]
                out["hazard_odds_ratios_per_sd"] = [
                    {"feature": TS_FEATURE_NAMES[i], "odds_ratio": float(np.exp(coef[i]))}
                    for i in top
                    if coef[i] != 0
                ]
        if target == HAZARD:
            hazard = preds["xgboost_none"]
            out["hazard_model"] = {
                "label": "withdraws in the next week (discrete-time hazard)",
                "validation": headline(y_val, hazard["val"]),
                "test": headline(y_te, hazard["test"]),
            }
            continue
        if target == "withdraw_4w":
            settings = models.sequence_settings[models.best_sequence]
            preds[models.best_sequence] = run.memo(
                f"sequence_{target}", partial(_fit_sequence, run, frames, label, settings)
            )
        samples = run.memo(
            f"bootstrap_{target}",
            partial(
                bootstrap_ap,
                y_te,
                {k: v["test"] for k, v in preds.items()},
                _clusters(frames.test),
                resamples=run.config.bootstrap_resamples,
                seed=seed,
            ),
        )
        best = max(preds, key=lambda k: _ap(y_val, preds[k]["val"]))
        f2 = alerts.fbeta_threshold(y_val, preds[best]["val"], 2.0)
        out[target] = {
            "models": {
                k: {
                    "validation": headline(y_val, v["val"]),
                    "test": headline(y_te, v["test"]),
                    "test_pr_auc_ci": list(interval(samples[k])),
                }
                for k, v in preds.items()
            },
            "selected_model": best,
            "selected_at_f2_threshold": threshold_metrics(y_te, preds[best]["test"], f2),
        }
    for target, weeks in (("withdraw_4w", 4), ("withdraw_8w", 8)):
        y_te = _y(_frames(panel, run.config, label_column(target)).test, label_column(target))
        out[target]["hazard_model_derived"] = headline(y_te, survival.risk_within(hazard["test"], weeks))
    out["concordance"] = _concordance(run, panel, hazard)
    out["tuned_params"] = tuned_params
    run.results["withdrawal"] = out
    return tuned_params


def _concordance(run: Run, panel: pd.DataFrame, hazard: dict[str, np.ndarray]) -> dict[str, Any]:
    test = _frames(panel, run.config, label_column(HAZARD)).test
    test8 = _frames(panel, run.config, label_column("withdraw_8w")).test
    if not test[["context_id", "student_id", "week"]].equals(test8[["context_id", "student_id", "week"]]):
        raise RuntimeError("withdrawal targets must share their test rows")
    direct8 = run.load("fit_withdraw_8w_xgboost_none")[1]
    result = {}
    for week in (4, 8):
        mask = (test["week"] == week).to_numpy()
        rows = test[mask]
        event = rows["withdraw_week"].notna().to_numpy()
        duration = np.where(event, rows["withdraw_week"], rows["course_end_week"]).astype(np.float64)
        result[f"week_{week}"] = {
            "registrations": int(mask.sum()),
            "events": int(event.sum()),
            "c_index_hazard_model": survival.concordance_index(duration, event, hazard["test"][mask]),
            "c_index_direct_8w_model": survival.concordance_index(duration, event, direct8["test"][mask]),
        }
    return result


# ------------------------------------------------------------------ rolling origin, LOMO, drift
def stage_rolling_origin(
    run: Run, panel: pd.DataFrame, models: AcademicModels, withdrawal_params: dict[str, dict[str, Any]]
) -> None:
    seed = run.config.random_seed
    plans: dict[str, dict[str, dict[str, Any]]] = {
        ACADEMIC: {
            "l1_logistic": run.load("tune_l1_ts")[0].params,
            "xgboost": run.load("tune_xgb_ts").params,
            models.best_sequence: models.sequence_settings[models.best_sequence],
        },
        "withdraw_4w": {
            "l1_logistic": withdrawal_params["withdraw_4w"]["l1_logistic"],
            "xgboost": withdrawal_params["withdraw_4w"]["xgboost"],
        },
    }
    out: dict[str, Any] = {}
    for target, plan in plans.items():
        label = label_column(target)
        folds: list[dict[str, Any]] = []
        for i, fold in enumerate(run.config.rolling_origin):
            train, test = _rows(panel, fold.train, label), _rows(panel, fold.test, label)
            y_tr, y_te = _y(train, label), _y(test, label)

            def compute(
                train: pd.DataFrame = train,
                test: pd.DataFrame = test,
                y_tr: np.ndarray = y_tr,
                label: str = label,
                plan: dict[str, dict[str, Any]] = plan,
            ) -> dict[str, np.ndarray]:
                preds: dict[str, np.ndarray] = {}
                for name, params in plan.items():
                    if name in ("l1_logistic", "xgboost"):
                        tab: TabularName = "l1_logistic" if name == "l1_logistic" else "xgboost"
                        pipe = build_tabular(tab, "none", params=params, y_train=y_tr, seed=seed)
                        pipe.fit(_features(train, TS_FEATURE_NAMES), y_tr)
                        preds[name] = proba(pipe, _features(test, TS_FEATURE_NAMES))
                        continue
                    std = Standardizer.fit(train, TS_FEATURE_NAMES)
                    seq_tr = to_sequences(train, label, std, max_week=run.config.last_week)
                    seq_te = to_sequences(test, label, std, max_week=run.config.last_week)
                    model, _ = train_sequence_model(
                        params["kind"],
                        seq_tr,
                        hidden=int(params["hidden"]),
                        dropout=float(params["dropout"]),
                        seed=seed,
                        epochs=max(1, int(params["best_epoch"])),
                    )
                    preds[name] = scatter_to_rows(predict_sequences(model, seq_te), seq_te, len(test))
                return preds

            preds = run.memo(f"rolling_{target}_{i}", compute)
            folds.append(
                {
                    "train": list(fold.train),
                    "test": list(fold.test),
                    "train_rows": len(train),
                    "test_rows": len(test),
                    "models": {name: headline(y_te, p) for name, p in preds.items()},
                }
            )
            run.log(
                f"rolling {target} fold {i + 1}: "
                + ", ".join(f"{n} {_ap(y_te, p):.3f}" for n, p in preds.items())
            )
        summary = {
            name: {
                "pr_auc_mean": float(np.mean([f["models"][name]["pr_auc"] for f in folds])),
                "pr_auc_sd": float(np.std([f["models"][name]["pr_auc"] for f in folds], ddof=1))
                if len(folds) > 1
                else None,
            }
            for name in plan
        }
        out[target] = {"folds": folds, "summary": summary}
    out["note"] = (
        "hyperparameters fixed from the hold-out validation (2014B); the fold testing on 2014B is optimistic"
    )
    run.results["rolling_origin"] = out


def stage_lomo(run: Run, panel: pd.DataFrame) -> None:
    label = label_column(ACADEMIC)
    seed = run.config.random_seed
    train, test = _rows(panel, run.config.lomo_train, label), _rows(panel, run.config.lomo_test, label)
    modules = sorted(set(test["module"].astype(str)) & set(train["module"].astype(str)))
    if len(modules) < 2:
        run.results["lomo"] = {"skipped": True, "reason": f"needs at least 2 modules, found {len(modules)}"}
        return
    plans: dict[str, tuple[TabularName, dict[str, Any]]] = {
        "l1_logistic": ("l1_logistic", run.load("tune_l1_ts")[0].params),
        "xgboost": ("xgboost", run.load("tune_xgb_ts").params),
    }
    y_tr_all, y_te_all = _y(train, label), _y(test, label)
    module_tr, module_te = train["module"].astype(str).to_numpy(), test["module"].astype(str).to_numpy()
    X_te = _features(test, TS_FEATURE_NAMES)

    def fit_predict(model_key: str, mask: np.ndarray) -> np.ndarray:
        name, params = plans[model_key]
        pipe = build_tabular(name, "none", params=params, y_train=y_tr_all[mask], seed=seed)
        pipe.fit(_features(train.loc[mask], TS_FEATURE_NAMES), y_tr_all[mask])
        return proba(pipe, X_te)

    rows = []
    for model_key in plans:
        reference = run.memo(
            f"lomo_{model_key}_reference", partial(fit_predict, model_key, np.ones(len(train), dtype=bool))
        )
        for m in modules:
            held = run.memo(f"lomo_{model_key}_without_{m}", partial(fit_predict, model_key, module_tr != m))
            sel = module_te == m
            ref_ap, held_ap = _ap(y_te_all[sel], reference[sel]), _ap(y_te_all[sel], held[sel])
            rows.append(
                {
                    "model": model_key,
                    "module": m,
                    "test_rows": int(sel.sum()),
                    "reference_pr_auc": ref_ap,
                    "held_out_pr_auc": held_ap,
                    "degradation": ref_ap - held_ap,
                }
            )
        run.log(f"lomo {model_key}: done")
    degradation = pd.DataFrame(rows).pivot_table(
        index="module", columns="model", values="degradation", aggfunc="first"
    )
    diff = (degradation["l1_logistic"] - degradation["xgboost"]).to_numpy()
    p_value = float(wilcoxon(diff, alternative="less", method="exact").pvalue) if np.any(diff != 0) else 1.0
    run.results["lomo"] = {
        "train_presentations": list(run.config.lomo_train),
        "test_presentations": list(run.config.lomo_test),
        "modules": modules,
        "rows": rows,
        "P5": {
            "description": (
                "degradation(L1 logistic) - degradation(XGBoost) per unseen module; one-sided exact Wilcoxon"
            ),
            "effect": float(np.median(diff)),
            "modules_where_l1_degrades_less": int(np.sum(diff < 0)),
            "p_value": p_value,
            "two_sided": False,
            "n": int(diff.size),
        },
        "scope": "Cross-MODULE proxy within one UK institution; not cross-institution validation.",
    }


def stage_drift(run: Run, panel: pd.DataFrame) -> None:
    label = label_column(ACADEMIC)
    frames = _frames(panel, run.config, label)
    stats, drift_alerts = feature_drift(
        _features(frames.train, TS_FEATURE_NAMES), _features(frames.test, TS_FEATURE_NAMES), TS_FEATURE_NAMES
    )
    ranked = sorted(stats, key=lambda r: -(r["psi"] if r["psi"] is not None else 0.0))
    run.results["drift"] = {
        "reference": "training presentations",
        "current": "test presentation",
        "top_psi": ranked[:10],
        "alerts": len(drift_alerts),
        "critical_alerts": sum(1 for a in drift_alerts if a.severity == "critical"),
    }


def stage_holm(run: Run) -> None:
    entries = [
        ("P1", run.results["academic"]["comparisons"]["P1"]),
        ("P2", run.results["academic"]["comparisons"]["P2"]),
        ("P4", run.results["alerts"]["P4"]),
    ]
    if not run.results["lomo"].get("skipped"):
        entries.append(("P5", run.results["lomo"]["P5"]))
    adjusted = holm([float(e["p_value"]) for _, e in entries])
    for (_, entry), p_adj in zip(entries, adjusted, strict=True):
        entry["p_holm"] = p_adj
        entry["supported"] = bool(p_adj < 0.05)
    run.results["holm_family"] = {
        name: {"p": e["p_value"], "p_holm": e["p_holm"], "supported": e["supported"]} for name, e in entries
    }


# ------------------------------------------------------------------ artifacts
def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_bins(X: pd.DataFrame) -> dict[str, Any]:
    """Per-feature decile edges and training shares (aggregates only) for PSI monitoring at scoring time."""
    out = {}
    for name in X.columns:
        values = X[name].to_numpy(dtype=np.float64)
        finite = values[np.isfinite(values)]
        if finite.size == 0:
            continue
        edges = np.unique(np.quantile(finite, np.linspace(0, 1, REFERENCE_BINS + 1)))
        if edges.size < 2:
            shares = np.array([1.0])
        else:
            counts = np.histogram(finite, bins=edges)[0]
            shares = counts / counts.sum()
        out[str(name)] = {
            "edges": edges.tolist(),
            "shares": shares.tolist(),
            "missing_share": float(np.mean(~np.isfinite(values))),
        }
    return out


def _library_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scikit-learn": sklearn.__version__,
        "xgboost": xgboost.__version__,
        "torch": torch.__version__,
    }


def stage_artifacts(run: Run, panel: pd.DataFrame, models: AcademicModels) -> None:
    label = label_column(ACADEMIC)
    frames = _frames(panel, run.config, label)
    out_root = _resolve(run.repo_root, run.config.output_dir)
    pipe, preds = run.load("fit_xgb_ts")
    y_val = _y(frames.validation, label)
    cost_key = f"cost_{run.config.primary_cost_ratio:g}"
    xgb_thresholds = {
        "f1": alerts.fbeta_threshold(y_val, preds["val"], 1.0),
        "f2": alerts.fbeta_threshold(y_val, preds["val"], 2.0),
        cost_key: alerts.cost_threshold(
            y_val, preds["val"], cost_fn=run.config.primary_cost_ratio, cost_fp=1.0
        ),
    }
    version = f"{run.run_id}-acad-xgb-ts"
    folder = out_root / version
    folder.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, folder / "model.joblib")
    metadata = {
        "model_version": version,
        "model_name": "xgboost",
        "feature_version": FEATURE_VERSION_TS,
        "feature_names": list(TS_FEATURE_NAMES),
        "target": "Fail or Withdrawn at course end; a prediction every week (cutoff = day 7k)",
        "dataset": run.results["dataset"],
        "data_provenance": run.config.dataset.provenance,
        "approved_for_real_students": False,
        "approval_note": "benchmark-trained; SEWS never approves benchmark models for real students",
        "split": json.loads(run.config.split.model_dump_json()),
        "hyperparameters": run.load("tune_xgb_ts").params,
        "thresholds_from_validation": xgb_thresholds,
        "default_threshold": "f1",
        "alert_policy": run.results["alerts"]["deployment_default_policy"],
        "risk_tier_cut_points": np.quantile(preds["val"], run.config.risk_level_quantiles).tolist(),
        "score_release_lag_days": run.config.score_release_lag_days,
        "validation": headline(y_val, preds["val"]),
        "test": headline(_y(frames.test, label), preds["test"]),
        "monitoring_reference": reference_bins(_features(frames.train, TS_FEATURE_NAMES)),
        "model_sha256": _sha256(folder / "model.joblib"),
        "library_versions": _library_versions(),
        "created_at": run.results["created_at"],
    }
    (folder / "metadata.json").write_text(
        json.dumps(clean_for_json(metadata), indent=2, default=float), encoding="utf-8"
    )

    seq = joblib.load(run.work_dir / f"sequence_{label}_{models.best_sequence}.joblib")
    seq_folder = out_root / f"{run.run_id}-acad-{models.best_sequence}"
    seq_folder.mkdir(parents=True, exist_ok=True)
    torch.save(seq.state_dict(), seq_folder / "state_dict.pt")
    std = Standardizer.fit(frames.train, TS_FEATURE_NAMES)
    seq_meta = {
        "model_version": seq_folder.name,
        "settings": models.sequence_settings[models.best_sequence],
        "feature_version": FEATURE_VERSION_TS,
        "feature_names": list(TS_FEATURE_NAMES),
        "standardizer": {
            "mean": std.mean.tolist(),
            "std": std.std.tolist(),
            "indicator_features": list(std.indicator_features),
        },
        "max_week": run.config.last_week,
        "data_provenance": run.config.dataset.provenance,
        "approved_for_real_students": False,
        "state_dict_sha256": _sha256(seq_folder / "state_dict.pt"),
    }
    (seq_folder / "metadata.json").write_text(
        json.dumps(clean_for_json(seq_meta), indent=2), encoding="utf-8"
    )
    run.results["artifacts"] = {
        "xgb_ts": version,
        "sequence": seq_folder.name,
        "xgb_ts_thresholds": xgb_thresholds,
    }


# ------------------------------------------------------------------ main
def run(config: LongitudinalConfig, repo_root: Path, resume: str | None = None) -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0)
    run_id = resume or f"{config.run_name}-{timestamp:%Y%m%dT%H%M%SZ}"
    report_dir = _resolve(repo_root, config.report_dir) / run_id
    work_dir = _resolve(repo_root, config.cache_dir) / run_id
    report_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    r = Run(config=config, repo_root=repo_root, run_id=run_id, report_dir=report_dir, work_dir=work_dir)
    r.results.update(
        {
            "run_id": run_id,
            "created_at": timestamp.isoformat(),
            "config": json.loads(config.model_dump_json()),
            "plan": "docs/research/ews-v3-longitudinal-plan.md",
            "library_versions": _library_versions(),
        }
    )
    r.log(f"run {run_id}")
    panel = stage_panel(r)
    stage_describe(r, panel)
    stage_kaplan_meier(r, panel)
    r.save()
    models = stage_academic_models(r, panel)
    selected = stage_academic_evaluation(r, panel, models)
    r.save()
    thresholds = stage_alerts(r, panel, models, selected)
    stage_calibration(r, panel)
    stage_fairness(r, panel, models, selected, thresholds["f1"])
    r.save()
    stage_explanations(r, panel)
    stage_mc_dropout(r, panel, models)
    r.save()
    withdrawal_params = stage_withdrawal(r, panel, models)
    r.save()
    stage_rolling_origin(r, panel, models, withdrawal_params)
    r.save()
    stage_lomo(r, panel)
    stage_drift(r, panel)
    stage_holm(r)
    stage_artifacts(r, panel, models)
    r.save()
    write_report(clean_for_json(r.results), report_dir)
    r.log(f"report: {report_dir}")
    return report_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--resume", help="run id of an interrupted run to continue")
    args = parser.parse_args(argv)
    run(load_longitudinal_config(args.config), Path.cwd(), resume=args.resume)
    return 0


if __name__ == "__main__":
    sys.exit(main())
