"""Train and evaluate SEWS models on the two external benchmark datasets (plan:
docs/research/external-datasets-plan.md).

Dataset A (UCI 697): decision points D0/D1/D2, stratified hold-out, tuned models, pre-specified comparisons
E1-E3 (Holm), calibration, SHAP, fairness, a financial-variable sensitivity run and leave-one-cohort-out.
Dataset B (UCI 320, Portuguese course + Math replication): decision points P0/P1/P2, repeated stratified
cross-validation, exploratory only. Reports hold aggregates only.

Usage (from the repository root):
    ml/.venv/Scripts/python -m ml.external.experiment --config ml/configs/external_v1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import GridSearchCV, RepeatedStratifiedKFold, StratifiedKFold, train_test_split

from ml.analysis.hypotheses import holm
from ml.data.contract import AUDIT_PREFIX
from ml.evaluation.metrics import (
    disparity_summary,
    expected_calibration_error,
    subgroup_metrics,
    threshold_metrics,
)
from ml.explainability.shap_explainer import ModelExplainer
from ml.external import uci
from ml.longitudinal.alerts import fbeta_threshold
from ml.longitudinal.evaluation import bootstrap_ap, headline, interval, paired_comparison
from ml.longitudinal.tabular import (
    L1_C_GRID,
    Imbalance,
    TabularName,
    build_tabular,
    proba,
    tune_l1,
    tune_xgboost,
)
from ml.monitoring.drift import clean_for_json

POINTS_A = ("D0", "D1", "D2")
B_XGB_PARAMS: dict[str, Any] = {
    "max_depth": 3,
    "learning_rate": 0.05,
    "n_estimators": 200,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
}
B_RF_PARAMS: dict[str, Any] = {
    "n_estimators": 300,
    "min_samples_leaf": 5,
    "max_features": "sqrt",
    "max_samples": None,
}
TOP_K = 10
COMPARED_MODELS: tuple[TabularName, ...] = ("xgboost", "l1_logistic")


class DatasetFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ExternalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,40}$")
    dropout: DatasetFile
    performance_portuguese: DatasetFile
    performance_math: DatasetFile
    validation_share: float = Field(gt=0, lt=0.5)
    test_share: float = Field(gt=0, lt=0.5)
    xgb_search_settings: int = Field(ge=1, le=100)
    bootstrap_resamples: int = Field(ge=50, le=10000)
    cv_folds: int = Field(ge=2, le=10)
    cv_repeats: int = Field(ge=1, le=20)
    random_seed: int
    report_dir: Path


def load_external_config(path: Path) -> ExternalConfig:
    with path.open(encoding="utf-8") as handle:
        return ExternalConfig.model_validate(json.load(handle))


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _ap(y: np.ndarray, p: np.ndarray) -> float:
    return float(average_precision_score(y, p))


def _matrix(frame: pd.DataFrame, features: tuple[str, ...]) -> pd.DataFrame:
    return frame.loc[:, list(features)].astype(np.float32)


# ------------------------------------------------------------------ dataset A
def _split(frame: pd.DataFrame, config: ExternalConfig) -> dict[str, np.ndarray]:
    """Stratified student split (the same students in each part at every decision point)."""
    ids = frame["student_id"].to_numpy()
    y = frame["y_dropout"].to_numpy()
    rest, test = train_test_split(
        ids, test_size=config.test_share, stratify=y, random_state=config.random_seed
    )
    rest_y = frame.set_index("student_id").loc[rest, "y_dropout"].to_numpy()
    train, val = train_test_split(
        rest,
        test_size=config.validation_share / (1 - config.test_share),
        stratify=rest_y,
        random_state=config.random_seed,
    )
    return {"train": np.asarray(train), "validation": np.asarray(val), "test": np.asarray(test)}


def _part(frame: pd.DataFrame, ids: np.ndarray, mask: pd.Series) -> pd.DataFrame:
    return frame[frame["student_id"].isin(ids) & mask].reset_index(drop=True)


def _choose(
    name: TabularName,
    params: dict[str, Any],
    parts: dict[str, pd.DataFrame],
    features: tuple[str, ...],
    label: str,
    seed: int,
) -> tuple[Any, Imbalance, dict[str, float]]:
    """Fit without and with class weights; keep the better one on validation PR-AUC."""
    y_tr = parts["train"][label].to_numpy()
    y_val = parts["validation"][label].to_numpy()
    scores: dict[str, float] = {}
    fitted: dict[str, Any] = {}
    imbalances: tuple[Imbalance, ...] = ("none", "weights")
    for imbalance in imbalances:
        pipe = build_tabular(name, imbalance, params=params, y_train=y_tr, seed=seed)
        pipe.fit(_matrix(parts["train"], features), y_tr)
        fitted[imbalance] = pipe
        scores[imbalance] = _ap(y_val, proba(pipe, _matrix(parts["validation"], features)))
    chosen: Imbalance = "weights" if scores["weights"] > scores["none"] else "none"
    return fitted[chosen], chosen, scores


def _point_models(
    frame: pd.DataFrame,
    split: dict[str, np.ndarray],
    point: str,
    features: tuple[str, ...],
    label: str,
    config: ExternalConfig,
) -> dict[str, Any]:
    seed = config.random_seed
    mask = uci.dropout_population(frame, point)
    parts = {k: _part(frame, ids, mask) for k, ids in split.items()}
    X_tr, y_tr = _matrix(parts["train"], features), parts["train"][label].to_numpy()
    X_val, y_val = _matrix(parts["validation"], features), parts["validation"][label].to_numpy()
    X_te, y_te = _matrix(parts["test"], features), parts["test"][label].to_numpy()
    xgb_tuning = tune_xgboost(
        X_tr, y_tr, X_val, y_val, imbalance="none", n_settings=config.xgb_search_settings, seed=seed
    )
    l1_tuning, _ = tune_l1(X_tr, y_tr, X_val, y_val, seed=seed)
    plans: list[tuple[TabularName, dict[str, Any]]] = [
        ("xgboost", xgb_tuning.params),
        ("l1_logistic", l1_tuning.params),
        ("random_forest", {}),
    ]
    models: dict[str, Any] = {}
    imbalance: dict[str, Any] = {}
    for name, params in plans:
        pipe, chosen, scores = _choose(name, params, parts, features, label, seed)
        models[name] = pipe
        imbalance[name] = {"chosen": chosen, "validation_pr_auc": scores}
    preds = {key: {"val": proba(pipe, X_val), "test": proba(pipe, X_te)} for key, pipe in models.items()}
    prevalence = float(y_tr.mean())
    preds["prevalence_baseline"] = {
        "val": np.full(len(y_val), prevalence),
        "test": np.full(len(y_te), prevalence),
    }
    return {
        "parts": parts,
        "models": models,
        "preds": preds,
        "tuning": {"xgboost": xgb_tuning.params, "l1_logistic": l1_tuning.params, "imbalance": imbalance},
    }


def _calibration(
    pipe: Any, X_val: pd.DataFrame, y_val: np.ndarray, X_te: pd.DataFrame, y_te: np.ndarray
) -> dict[str, Any]:
    raw = proba(pipe, X_te)
    out = {"raw": {"brier": float(brier_score_loss(y_te, raw)), "ece": expected_calibration_error(y_te, raw)}}
    for method in ("sigmoid", "isotonic"):
        cal = CalibratedClassifierCV(FrozenEstimator(pipe), method=method, ensemble=False).fit(X_val, y_val)
        p = proba(cal, X_te)
        out[method] = {"brier": float(brier_score_loss(y_te, p)), "ece": expected_calibration_error(y_te, p)}
    return out


def _shap_top(pipe: Any, frame: pd.DataFrame, features: tuple[str, ...]) -> list[dict[str, Any]]:
    explainer = ModelExplainer(pipe, model_name="xgboost", feature_names=features, background_means=None)
    values = explainer.mean_abs_contribution(_matrix(frame, features))
    return [
        {"feature": f, "mean_abs_shap": v} for f, v in sorted(values.items(), key=lambda kv: -kv[1])[:TOP_K]
    ]


def run_dataset_a(config: ExternalConfig, repo_root: Path) -> dict[str, Any]:
    raw = uci.load_dropout(_resolve(repo_root, config.dropout.path), expected_sha256=config.dropout.sha256)
    frame = uci.dropout_frame(raw)
    points = uci.dropout_decision_points(frame)
    split = _split(frame, config)
    label = "y_dropout"
    seed = config.random_seed
    results: dict[str, Any] = {
        "dataset": uci.DATASET_A,
        "provenance": uci.PROVENANCE,
        "students": len(frame),
        "dropout_rate": float(frame[label].mean()),
        "split_sizes": {k: len(v) for k, v in split.items()},
        "split_note": (
            "stratified random split; no enrolment year exists, so no out-of-time split is possible"
        ),
        "points": {},
    }
    by_point: dict[str, dict[str, Any]] = {}
    for point in POINTS_A:
        features = points[point]
        fitted = _point_models(frame, split, point, features, label, config)
        by_point[point] = fitted
        parts, preds = fitted["parts"], fitted["preds"]
        y_val, y_te = parts["validation"][label].to_numpy(), parts["test"][label].to_numpy()
        samples = bootstrap_ap(
            y_te,
            {k: v["test"] for k, v in preds.items()},
            parts["test"]["student_id"].to_numpy(),
            resamples=config.bootstrap_resamples,
            seed=seed,
        )
        best = max(
            (k for k in preds if k != "prevalence_baseline"), key=lambda k: _ap(y_val, preds[k]["val"])
        )
        thresholds = {
            "f1": fbeta_threshold(y_val, preds[best]["val"], 1.0),
            "f2": fbeta_threshold(y_val, preds[best]["val"], 2.0),
        }
        xgb = fitted["models"]["xgboost"]
        results["points"][point] = {
            "inputs": len(features),
            "population": {k: len(v) for k, v in parts.items()},
            "models": {
                k: {
                    "validation": headline(y_val, v["val"]),
                    "test": headline(y_te, v["test"]),
                    "test_pr_auc_ci": list(interval(samples[k])),
                }
                for k, v in preds.items()
            },
            "tuning": fitted["tuning"],
            "selected_model": best,
            "selected_at_thresholds": {
                name: threshold_metrics(y_te, preds[best]["test"], thr) for name, thr in thresholds.items()
            },
            "calibration_xgboost": _calibration(
                xgb, _matrix(parts["validation"], features), y_val, _matrix(parts["test"], features), y_te
            ),
            "shap_xgboost_test": _shap_top(xgb, parts["test"], features),
        }
        print(
            f"A {point}: " + ", ".join(f"{k} {_ap(y_te, v['test']):.3f}" for k, v in preds.items()),
            flush=True,
        )
    results["comparisons"] = _comparisons_a(by_point, label, config)
    results["fairness_d1"] = _fairness(by_point["D1"], label, results["points"]["D1"])
    results["financial_sensitivity"] = _financial_sensitivity(points, by_point, label, config)
    results["leave_one_cohort_out_d1"] = _leave_one_cohort_out(
        frame, points["D1"], by_point["D1"], label, config
    )
    results["not_graduated"] = _secondary_target(frame, split, points, config)
    return results


def _aligned_test(by_point: dict[str, dict[str, Any]], point: str, model: str, ids: np.ndarray) -> np.ndarray:
    test = by_point[point]["parts"]["test"]
    lookup = pd.Series(by_point[point]["preds"][model]["test"], index=test["student_id"].to_numpy())
    return lookup.loc[ids].to_numpy(dtype=np.float64)


def _comparisons_a(by_point: dict[str, dict[str, Any]], label: str, config: ExternalConfig) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, later, earlier, model_a, model_b, two_sided in (
        ("E1", "D1", "D0", "xgboost", "xgboost", False),
        ("E2", "D2", "D1", "xgboost", "xgboost", False),
        ("E3", "D1", "D1", "l1_logistic", "xgboost", True),
    ):
        test = by_point[later]["parts"]["test"]
        ids = test["student_id"].to_numpy()
        y = test[label].to_numpy()
        p_a = _aligned_test(by_point, later, model_a, ids)
        p_b = _aligned_test(by_point, earlier, model_b, ids)
        samples = bootstrap_ap(
            y, {"a": p_a, "b": p_b}, ids, resamples=config.bootstrap_resamples, seed=config.random_seed
        )
        out[name] = {
            "description": (
                f"{model_a} at {later} minus {model_b} at {earlier}, test PR-AUC on {len(ids)} students "
                f"({'two' if two_sided else 'one'}-sided)"
            ),
            **paired_comparison(_ap(y, p_a) - _ap(y, p_b), samples["a"], samples["b"], two_sided=two_sided),
        }
    adjusted = holm([out[k]["p_value"] for k in ("E1", "E2", "E3")])
    for key, p in zip(("E1", "E2", "E3"), adjusted, strict=True):
        out[key]["p_holm"] = p
        out[key]["supported"] = bool(p < 0.05)
    return out


def _fairness(fitted: dict[str, Any], label: str, point_result: dict[str, Any]) -> dict[str, Any]:
    best = point_result["selected_model"]
    test = fitted["parts"]["test"]
    y = test[label].to_numpy()
    p = fitted["preds"][best]["test"]
    threshold = point_result["selected_at_thresholds"]["f1"]["threshold"]
    out: dict[str, Any] = {"model": best, "threshold": threshold}
    for col in (c for c in test.columns if c.startswith(AUDIT_PREFIX)):
        rows = subgroup_metrics(y, p, test[col].astype(str).to_numpy(), threshold=threshold)
        out[col.removeprefix(AUDIT_PREFIX)] = {"groups": rows, "disparity": disparity_summary(rows)}
    return out


def _financial_sensitivity(
    points: dict[str, tuple[str, ...]],
    by_point: dict[str, dict[str, Any]],
    label: str,
    config: ExternalConfig,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "variables": list(uci.FINANCIAL_FEATURES),
        "warning": (
            "recording time undocumented; a gain may be leakage (e.g. fees recorded after students left)"
        ),
    }
    for point in ("D0", "D1"):
        fitted = by_point[point]
        parts = fitted["parts"]
        features = (*points[point], *uci.FINANCIAL_FEATURES)
        y_tr, y_te = parts["train"][label].to_numpy(), parts["test"][label].to_numpy()
        pipe = build_tabular(
            "xgboost", "none", params=fitted["tuning"]["xgboost"], y_train=y_tr, seed=config.random_seed
        ).fit(_matrix(parts["train"], features), y_tr)
        with_fin = proba(pipe, _matrix(parts["test"], features))
        without = fitted["preds"]["xgboost"]["test"]
        ids = parts["test"]["student_id"].to_numpy()
        samples = bootstrap_ap(
            y_te,
            {"with": with_fin, "without": without},
            ids,
            resamples=config.bootstrap_resamples,
            seed=config.random_seed,
        )
        out[point] = {
            "test_pr_auc_without": _ap(y_te, without),
            "test_pr_auc_with": _ap(y_te, with_fin),
            "difference_ci": list(interval(samples["with"] - samples["without"])),
        }
    return out


def _leave_one_cohort_out(
    frame: pd.DataFrame, features: tuple[str, ...], fitted: dict[str, Any], label: str, config: ExternalConfig
) -> dict[str, Any]:
    data = frame[uci.dropout_population(frame, "D1")].reset_index(drop=True)
    rows = []
    for cohort in sorted(data["cohort"].unique()):
        held = (data["cohort"] == cohort).to_numpy()
        y_train, y_held = data.loc[~held, label].to_numpy(), data.loc[held, label].to_numpy()
        row: dict[str, Any] = {
            "cohort": cohort,
            "students": int(held.sum()),
            "dropout_rate": float(y_held.mean()),
        }
        for name in COMPARED_MODELS:
            pipe = build_tabular(
                name, "none", params=fitted["tuning"][name], y_train=y_train, seed=config.random_seed
            )
            pipe.fit(_matrix(data.loc[~held], features), y_train)
            row[f"{name}_pr_auc"] = _ap(y_held, proba(pipe, _matrix(data.loc[held], features)))
        rows.append(row)
    table = pd.DataFrame(rows)
    return {
        "note": (
            "cohorts identified by their macro-economic indicators; the year order is unknown; exploratory"
        ),
        "rows": rows,
        "summary": {
            name: {
                "mean": float(table[f"{name}_pr_auc"].mean()),
                "min": float(table[f"{name}_pr_auc"].min()),
                "max": float(table[f"{name}_pr_auc"].max()),
            }
            for name in COMPARED_MODELS
        },
    }


def _secondary_target(
    frame: pd.DataFrame,
    split: dict[str, np.ndarray],
    points: dict[str, tuple[str, ...]],
    config: ExternalConfig,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "definition": "Dropout or still Enrolled at the end of the normal duration (descriptive)"
    }
    for point in POINTS_A:
        fitted = _point_models(frame, split, point, points[point], "y_not_graduated", config)
        y_te = fitted["parts"]["test"]["y_not_graduated"].to_numpy()
        out[point] = {k: headline(y_te, v["test"]) for k, v in fitted["preds"].items()}
    return out


# ------------------------------------------------------------------ dataset B
def _b_models(seed: int) -> dict[str, Any]:
    both = np.array([0, 1])  # build_tabular uses y_train only to size class weights; none are used here
    return {
        "l1_logistic": GridSearchCV(
            build_tabular("l1_logistic", "none", params={"C": 1.0}, y_train=both, seed=seed),
            {"model__C": list(L1_C_GRID)},
            scoring="average_precision",
            cv=StratifiedKFold(5, shuffle=True, random_state=seed),
        ),
        "random_forest": build_tabular("random_forest", "none", params=B_RF_PARAMS, y_train=both, seed=seed),
        "xgboost": build_tabular("xgboost", "none", params=B_XGB_PARAMS, y_train=both, seed=seed),
    }


def run_dataset_b(file: DatasetFile, name: str, config: ExternalConfig, repo_root: Path) -> dict[str, Any]:
    raw = uci.load_performance(_resolve(repo_root, file.path), expected_sha256=file.sha256)
    frame = uci.performance_frame(raw)
    y = frame["y_fail"].to_numpy()
    points = {**uci.PERFORMANCE_POINTS, "P2_with_absences": (*uci.PERFORMANCE_POINTS["P2"], "absences")}
    cv = RepeatedStratifiedKFold(
        n_splits=config.cv_folds, n_repeats=config.cv_repeats, random_state=config.random_seed
    )
    folds = list(cv.split(np.zeros(len(y)), y))
    results: dict[str, Any] = {
        "dataset": f"{uci.DATASET_B}-{name}",
        "provenance": uci.PROVENANCE,
        "students": len(frame),
        "fail_rate": float(y.mean()),
        "evaluation": (
            f"{config.cv_repeats} x {config.cv_folds} repeated stratified cross-validation (exploratory)"
        ),
        "points": {},
    }
    model_names = (*_b_models(config.random_seed), "prevalence_baseline")
    for point, features in points.items():
        X = _matrix(frame, features)
        oof = {m: np.zeros((config.cv_repeats, len(y))) for m in model_names}
        for i, (train, test) in enumerate(folds):
            repeat = i // config.cv_folds
            for model_name, model in _b_models(config.random_seed).items():
                model.fit(X.iloc[train], y[train])
                oof[model_name][repeat, test] = proba(model, X.iloc[test])
            oof["prevalence_baseline"][repeat, test] = y[train].mean()
        summary = {}
        for model_name, values in oof.items():
            aps = [_ap(y, values[r]) for r in range(config.cv_repeats)]
            summary[model_name] = {
                "pr_auc_mean": float(np.mean(aps)),
                "pr_auc_min": float(np.min(aps)),
                "pr_auc_max": float(np.max(aps)),
                "roc_auc_mean": float(
                    np.mean([roc_auc_score(y, values[r]) for r in range(config.cv_repeats)])
                ),
                "brier_mean": float(
                    np.mean([brier_score_loss(y, values[r]) for r in range(config.cv_repeats)])
                ),
            }
        entry: dict[str, Any] = {"inputs": list(features), "models": summary}
        if point == "P1":
            p = oof["xgboost"][0]
            threshold = fbeta_threshold(y, p, 1.0)
            entry["fairness_xgboost_repeat1"] = {
                "note": "threshold chosen on the same out-of-fold predictions (exploratory)",
                "threshold": threshold,
                **{
                    col.removeprefix(AUDIT_PREFIX): disparity_summary(
                        subgroup_metrics(y, p, frame[col].astype(str).to_numpy(), threshold=threshold)
                    )
                    for col in frame.columns
                    if col.startswith(AUDIT_PREFIX)
                },
            }
        results["points"][point] = entry
        print(
            f"B {name} {point}: " + ", ".join(f"{m} {s['pr_auc_mean']:.3f}" for m, s in summary.items()),
            flush=True,
        )
    return results


# ------------------------------------------------------------------ report
def _f(v: Any, digits: int = 3) -> str:
    return "n/a" if v is None else f"{float(v):.{digits}f}"


def _p(v: Any) -> str:
    return "n/a" if v is None else ("< 0.001" if float(v) < 0.001 else f"{float(v):.3f}")


def render(results: dict[str, Any]) -> str:
    a = results["dataset_a"]
    lines = [
        f"# External benchmark datasets — {results['run_id']}",
        "",
        "> **Provenance: BENCHMARK (Portugal, CC BY 4.0).** Not Indian data; models are never approved",
        "> for real students. Plan and pre-specified comparisons: `docs/research/external-datasets-plan.md`.",
        "",
        f"## A. University dropout (UCI 697): {a['students']:,} students, "
        f"dropout rate {_f(a['dropout_rate'])}",
        "",
        f"Split {a['split_sizes']}: {a['split_note']}.",
        "",
        "| Point | Model | Validation PR-AUC | Test PR-AUC [95% CI] | Test ROC-AUC | Test Brier |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for point, r in a["points"].items():
        for model, m in r["models"].items():
            ci = m["test_pr_auc_ci"]
            lines.append(
                f"| {point} | {model} | {_f(m['validation']['pr_auc'])} | {_f(m['test']['pr_auc'])} "
                f"[{_f(ci[0])}, {_f(ci[1])}] | {_f(m['test']['roc_auc'])} | {_f(m['test']['brier'])} |"
            )
    lines += [
        "",
        "| ID | Comparison | Effect [95% CI] | p | Holm p | Result |",
        "|---|---|---|---:|---:|---|",
    ]
    for key, e in a["comparisons"].items():
        lines.append(
            f"| {key} | {e['description']} | {_f(e['effect'], 4)} "
            f"[{_f(e['ci_low'], 4)}, {_f(e['ci_high'], 4)}] | "
            f"{_p(e['p_value'])} | {_p(e['p_holm'])} | {'supported' if e['supported'] else 'not supported'} |"
        )
    lines.append("")
    for point, r in a["points"].items():
        sel = r["selected_at_thresholds"]["f1"]
        top = ", ".join(s["feature"] for s in r["shap_xgboost_test"][:5])
        lines.append(
            f"- {point}: selected {r['selected_model']}; at the F1 threshold recall {_f(sel['recall'])}, "
            f"precision {_f(sel['precision'])}; top SHAP (XGBoost): {top}."
        )
    fin = a["financial_sensitivity"]
    loco = a["leave_one_cohort_out_d1"]["summary"]
    lines += [
        "",
        f"**Financial variables (sensitivity; {fin['warning']}):** "
        + "; ".join(
            f"{p}: {_f(fin[p]['test_pr_auc_without'])} -> {_f(fin[p]['test_pr_auc_with'])} "
            f"(difference CI [{_f(fin[p]['difference_ci'][0])}, {_f(fin[p]['difference_ci'][1])}])"
            for p in ("D0", "D1")
        ),
        "",
        "**Leave-one-cohort-out at D1 (exploratory):** "
        + "; ".join(
            f"{k} mean {_f(v['mean'])} (range {_f(v['min'])} to {_f(v['max'])})" for k, v in loco.items()
        ),
        "",
    ]
    for key in ("performance_portuguese", "performance_math"):
        b = results[key]
        lines += [
            f"## B. {b['dataset']}: {b['students']} students, fail rate {_f(b['fail_rate'])} "
            f"({b['evaluation']})",
            "",
            "| Point | Model | PR-AUC mean (range) | ROC-AUC mean | Brier mean |",
            "|---|---|---:|---:|---:|",
        ]
        for point, r in b["points"].items():
            for model, s in r["models"].items():
                lines.append(
                    f"| {point} | {model} | {_f(s['pr_auc_mean'])} ({_f(s['pr_auc_min'])} to "
                    f"{_f(s['pr_auc_max'])}) | {_f(s['roc_auc_mean'])} | {_f(s['brier_mean'])} |"
                )
        lines.append("")
    return "\n".join(lines)


def run(config: ExternalConfig, repo_root: Path) -> Path:
    timestamp = datetime.now(UTC).replace(microsecond=0)
    run_id = f"{config.run_name}-{timestamp:%Y%m%dT%H%M%SZ}"
    out = _resolve(repo_root, config.report_dir) / run_id
    out.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "run_id": run_id,
        "created_at": timestamp.isoformat(),
        "config": json.loads(config.model_dump_json()),
        "plan": "docs/research/external-datasets-plan.md",
        "dataset_a": run_dataset_a(config, repo_root),
        "performance_portuguese": run_dataset_b(
            config.performance_portuguese, "portuguese", config, repo_root
        ),
        "performance_math": run_dataset_b(config.performance_math, "math", config, repo_root),
    }
    payload = clean_for_json(results)
    (out / "results.json").write_text(json.dumps(payload, indent=2, default=float), encoding="utf-8")
    (out / "report.md").write_text(render(payload), encoding="utf-8")
    print(f"report: {out}", flush=True)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    run(load_external_config(args.config), Path.cwd())
    return 0


if __name__ == "__main__":
    sys.exit(main())
