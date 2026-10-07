"""Course week 6: the pre-registered hypothesis tests of docs/research/week04-research-design.md.

    ml/.venv/Scripts/python -m ml.analysis.hypotheses --config ml/configs/oulad_v2.json

Runs H1-H6 exactly as fixed in week 4 (including its change log), applies Holm's correction across the 10
tests and writes ``<report_dir>/hypotheses-<UTC timestamp>/`` (``report.md``, ``results.json``). Effect sizes
with 95% intervals are reported for every test, significant or not. Nothing here selects, changes or approves
a model.

Benchmark data only (OULAD, UK): no conclusion applies to Indian students. Outputs are aggregates only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy import stats
from sklearn.metrics import average_precision_score, roc_auc_score

from ml.data.contract import AUDIT_PREFIX, TARGET_COLUMN
from ml.data.oulad import OuladTables, load_oulad
from ml.features.definitions import FEATURE_SETS
from ml.features.oulad_features import build_oulad_features
from ml.models.factory import ModelName, build_pipeline
from ml.models.registry import ModelRegistry
from ml.training.config import TrainingConfig, load_config

ALPHA = 0.05
RESAMPLES = 2000
SEED = 20261003
# Below these absolute effects a significant result is "detectable but practically negligible" (week 4 §2).
NEGLIGIBLE = {"pr_auc": 0.01, "roc_auc": 0.01, "recall": 0.02}
TARGET = "academic"
RUN_ID = "oulad-v2-20260924T003349Z"  # the published V2 run whose models H1, H3 and H5 concern
KEY = ["student_id", "context_id"]

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
WeightedMetric = Callable[[IntArray, FloatArray, FloatArray], float]


@dataclass
class TestResult:
    id: str
    hypothesis: str
    status: str
    metric: str
    estimate: float
    ci_low: float | None
    ci_high: float | None
    p_value: float
    test: str
    details: dict[str, Any]
    p_holm: float = float("nan")
    supported: bool = False
    negligible: bool = False


# ------------------------------------------------------------------ statistics
def _midrank(x: FloatArray) -> FloatArray:
    order = np.argsort(x, kind="mergesort")
    xs = x[order]
    n = xs.size
    ranks = np.empty(n, dtype=np.float64)
    i = 0
    while i < n:
        j = i
        while j < n and xs[j] == xs[i]:
            j += 1
        ranks[i:j] = 0.5 * (i + j - 1) + 1
        i = j
    out = np.empty(n, dtype=np.float64)
    out[order] = ranks
    return out


def delong(y: IntArray, p_a: FloatArray, p_b: FloatArray) -> dict[str, float]:
    """Paired DeLong test for two correlated ROC curves on the same cases (fast midrank algorithm).
    Returns both AUCs, the difference (a - b), its standard error and the z statistic."""
    pos, neg = y == 1, y == 0
    m, n = int(pos.sum()), int(neg.sum())
    aucs, pos_parts, neg_parts = [], [], []
    for p in (p_a, p_b):
        tx, ty, tz = _midrank(p[pos]), _midrank(p[neg]), _midrank(np.concatenate([p[pos], p[neg]]))
        aucs.append((tz[:m].sum() - m * (m + 1) / 2) / (m * n))
        pos_parts.append((tz[:m] - tx) / n)
        neg_parts.append(1.0 - (tz[m:] - ty) / m)
    s_pos, s_neg = np.cov(np.vstack(pos_parts)), np.cov(np.vstack(neg_parts))
    var = (s_pos[0, 0] + s_pos[1, 1] - 2 * s_pos[0, 1]) / m + (
        s_neg[0, 0] + s_neg[1, 1] - 2 * s_neg[0, 1]
    ) / n
    se = float(np.sqrt(max(float(var), 0.0)))
    delta = float(aucs[0] - aucs[1])
    return {
        "auc_a": float(aucs[0]),
        "auc_b": float(aucs[1]),
        "delta": delta,
        "se": se,
        "z": delta / se if se > 0 else float("nan"),
    }


def cluster_weights(clusters: NDArray[Any], resamples: int, seed: int) -> Iterator[FloatArray]:
    """Cluster bootstrap as row weights: each resample draws clusters (students) with replacement; a row's
    weight is how many times its cluster was drawn. Weighted metrics on all rows equal metrics on the
    resampled rows."""
    _, inverse = np.unique(clusters, return_inverse=True)
    k = int(inverse.max()) + 1
    rng = np.random.default_rng(seed)
    for _ in range(resamples):
        counts = rng.multinomial(k, np.full(k, 1.0 / k))
        yield counts[inverse].astype(np.float64)


def _ap(y: IntArray, p: FloatArray, w: FloatArray) -> float:
    return float(average_precision_score(y, p, sample_weight=w))


def _roc(y: IntArray, p: FloatArray, w: FloatArray) -> float:
    return float(roc_auc_score(y, p, sample_weight=w))


def bootstrap_p(samples: FloatArray, *, two_sided: bool) -> float:
    """p-value for H0 'effect <= 0' (one-sided) or 'effect = 0' (two-sided) from bootstrap effects
    (definition fixed in the week 4 change log)."""
    b = samples.size
    upper = (1 + int(np.sum(samples <= 0))) / (b + 1)
    if not two_sided:
        return upper
    lower = (1 + int(np.sum(samples >= 0))) / (b + 1)
    return min(1.0, 2 * min(upper, lower))


def paired_bootstrap(
    y: IntArray, p_a: FloatArray, p_b: FloatArray, clusters: NDArray[Any], metric: WeightedMetric
) -> tuple[float, FloatArray]:
    ones = np.ones(y.size)
    observed = metric(y, p_a, ones) - metric(y, p_b, ones)
    effects = [metric(y, p_a, w) - metric(y, p_b, w) for w in cluster_weights(clusters, RESAMPLES, SEED)]
    return observed, np.asarray(effects, dtype=np.float64)


def holm(p_values: list[float]) -> list[float]:
    """Holm step-down adjusted p-values (monotone, capped at 1)."""
    m = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return [float(v) for v in adjusted]


def _ci(samples: FloatArray) -> tuple[float, float]:
    low, high = np.quantile(samples, [ALPHA / 2, 1 - ALPHA / 2])
    return float(low), float(high)


# ------------------------------------------------------------------ data
@dataclass
class Tables:
    config: TrainingConfig
    oulad: OuladTables
    registry: ModelRegistry
    frames: dict[int, pd.DataFrame]


def _frame(t: Tables, cutoff: int) -> pd.DataFrame:
    if cutoff not in t.frames:
        t.frames[cutoff] = build_oulad_features(
            t.oulad,
            cutoff,
            score_release_lag_days=t.config.score_release_lag_days,
            target=TARGET,
            feature_version=t.config.feature_version,
        )
    return t.frames[cutoff]


def _split(t: Tables, cutoff: int, part: str) -> pd.DataFrame:
    groups = {"train": t.config.split.train, "test": t.config.split.test}[part]
    df = _frame(t, cutoff)
    return df[df["split_group"].isin(groups)].reset_index(drop=True)


def _artifact_scores(t: Tables, model: str, cutoff: int, frame: pd.DataFrame) -> FloatArray:
    return t.registry.load(f"{RUN_ID}-acad-{model}-d{cutoff}").predict_proba(frame)


def _y(frame: pd.DataFrame) -> IntArray:
    return frame[TARGET_COLUMN].to_numpy(dtype=np.int64)


# ------------------------------------------------------------------ hypotheses
def h1(t: Tables) -> list[TestResult]:
    test = {c: _split(t, c, "test") for c in (30, 60, 90)}
    merged = test[90][KEY].copy()
    for c in (30, 60, 90):
        part = test[c].assign(**{f"p{c}": _artifact_scores(t, "xgb", c, test[c])})
        merged = merged.merge(
            part[[*KEY, TARGET_COLUMN, f"p{c}"]].rename(columns={TARGET_COLUMN: f"y{c}"}), on=KEY
        )
    if not (merged["y30"].equals(merged["y60"]) and merged["y60"].equals(merged["y90"])):
        raise RuntimeError("the label differs between decision points for the same registration")
    y = merged["y90"].to_numpy(dtype=np.int64)
    clusters = merged["student_id"].to_numpy()
    ones = np.ones(y.size)
    lr = {c: _artifact_scores(t, "lr", c, merged[KEY].merge(test[c], on=KEY)) for c in (30, 60, 90)}
    results = []
    for test_id, early, late in (("H1a", 30, 60), ("H1b", 60, 90)):
        p_late, p_early = merged[f"p{late}"].to_numpy(), merged[f"p{early}"].to_numpy()
        d = delong(y, p_late, p_early)
        p_delong = float(stats.norm.sf(d["z"]))
        observed, effects = paired_bootstrap(y, p_late, p_early, clusters, _roc)
        p_boot = bootstrap_p(effects, two_sided=False)
        low, high = _ci(effects)
        results.append(
            TestResult(
                test_id,
                f"ROC-AUC higher at day {late} than at day {early} (same students)",
                "confirmatory (estimate seen)",
                "roc_auc",
                observed,
                low,
                high,
                max(p_delong, p_boot),
                "one-sided paired DeLong and cluster bootstrap; larger p (XGBoost)",
                {
                    "n_registrations": int(y.size),
                    "n_students": int(pd.unique(clusters).size),
                    f"roc_auc_day{early}": d["auc_b"],
                    f"roc_auc_day{late}": d["auc_a"],
                    "delong_z": d["z"],
                    "p_delong": p_delong,
                    "p_bootstrap": p_boot,
                    "robustness_logistic_regression_delta": _roc(y, lr[late], ones)
                    - _roc(y, lr[early], ones),
                },
            )
        )
    return results


def h2(t: Tables) -> list[TestResult]:
    families = {s.name: s.family for s in FEATURE_SETS[t.config.feature_version]}
    names = list(families)
    plan = (("H2a", "engagement", 30), ("H2b", "assignment", 30), ("H2c", "academic", 90))
    results = []
    for test_id, family, cutoff in plan:
        train, test = _split(t, cutoff, "train"), _split(t, cutoff, "test")
        kept = [n for n in names if families[n] != family]
        y_tr, y_te = _y(train), _y(test)
        ones = np.ones(y_te.size)

        def fit_predict(
            model: ModelName,
            columns: list[str],
            tr: pd.DataFrame = train,
            te: pd.DataFrame = test,
            y_fit: IntArray = y_tr,
        ) -> FloatArray:
            pipe = build_pipeline(model, "none", y_train=y_fit, seed=t.config.random_seed)
            pipe.fit(tr[columns].astype(float), y_fit)
            return np.asarray(pipe.predict_proba(te[columns].astype(float))[:, 1], dtype=np.float64)

        full, ablated = fit_predict("xgboost", names), fit_predict("xgboost", kept)
        observed, effects = paired_bootstrap(y_te, full, ablated, test["student_id"].to_numpy(), _ap)
        low, high = _ci(effects)
        lr_delta = _ap(y_te, fit_predict("logistic_regression", names), ones) - _ap(
            y_te, fit_predict("logistic_regression", kept), ones
        )
        results.append(
            TestResult(
                test_id,
                f"removing the {family} family lowers PR-AUC at day {cutoff}",
                "pre-registered",
                "pr_auc",
                observed,
                low,
                high,
                bootstrap_p(effects, two_sided=False),
                "one-sided paired cluster bootstrap (XGBoost, retrained without the family)",
                {
                    "family_size": len(names) - len(kept),
                    "pr_auc_full": _ap(y_te, full, ones),
                    "pr_auc_without_family": _ap(y_te, ablated, ones),
                    "n_test": int(y_te.size),
                    "prevalence": float(y_te.mean()),
                    "robustness_logistic_regression_delta": lr_delta,
                },
            )
        )
    return results


def h3(t: Tables) -> TestResult:
    test = _split(t, 60, "test")
    y, clusters, ones = _y(test), test["student_id"].to_numpy(), np.ones(len(test))
    xgb, lr = _artifact_scores(t, "xgb", 60, test), _artifact_scores(t, "lr", 60, test)
    observed, effects = paired_bootstrap(y, xgb, lr, clusters, _ap)
    low, high = _ci(effects)
    d = delong(y, xgb, lr)
    return TestResult(
        "H3",
        "XGBoost and logistic regression differ in PR-AUC at day 60",
        "confirmatory (estimate seen)",
        "pr_auc",
        observed,
        low,
        high,
        bootstrap_p(effects, two_sided=True),
        "two-sided paired cluster bootstrap",
        {
            "pr_auc_xgboost": _ap(y, xgb, ones),
            "pr_auc_logistic_regression": _ap(y, lr, ones),
            "roc_auc_delta": d["delta"],
            "roc_auc_delong_p_two_sided": float(2 * stats.norm.sf(abs(d["z"]))),
        },
    )


def h4(repo_root: Path) -> TestResult:
    path = next(repo_root.glob("ml/reports/cross-module-academic-d60-*/cross_group.json"))
    report = json.loads(path.read_text(encoding="utf-8"))
    rows = [
        (g["group"], g["reference"]["ece"], g["held_out"]["ece"])
        for g in report["groups"]
        if not g["skipped"]
    ]
    degradation = np.array([held - ref for _, ref, held in rows])
    result = stats.wilcoxon(degradation, alternative="greater", method="exact")
    return TestResult(
        "H4",
        "ECE is higher on an unseen module than on the same module seen in training",
        "confirmatory (estimate seen)",
        "ece_degradation_median",
        float(np.median(degradation)),
        float(degradation.min()),
        float(degradation.max()),
        float(result.pvalue),
        "one-sided exact Wilcoxon signed-rank over modules (interval = min..max across modules, not a CI)",
        {
            "modules": len(rows),
            "per_module": {g: held - ref for g, ref, held in rows},
            "source": path.parent.name,
        },
    )


def h5(t: Tables) -> TestResult:
    test = _split(t, 60, "test")
    artifact = t.registry.load(f"{RUN_ID}-acad-xgb-d60")
    flagged = (artifact.predict_proba(test) >= artifact.metadata.decision_threshold).astype(np.float64)
    y = _y(test)
    gender = test[f"{AUDIT_PREFIX}gender"].to_numpy()

    def recall(w: FloatArray, group: str) -> float:
        mask = (gender == group) & (y == 1)
        return float((w[mask] * flagged[mask]).sum() / w[mask].sum())

    ones = np.ones(y.size)
    observed = recall(ones, "F") - recall(ones, "M")
    clusters = test["student_id"].to_numpy()
    effects = np.array([recall(w, "F") - recall(w, "M") for w in cluster_weights(clusters, RESAMPLES, SEED)])
    low, high = _ci(effects)
    return TestResult(
        "H5",
        "recall at day 60 differs between female and male students",
        "confirmatory (estimate seen)",
        "recall_gap_female_minus_male",
        observed,
        low,
        high,
        bootstrap_p(effects, two_sided=True),
        "two-sided cluster bootstrap (active model, XGBoost day 60, at its decision threshold)",
        {
            "threshold": artifact.metadata.decision_threshold,
            "recall_female": recall(ones, "F"),
            "recall_male": recall(ones, "M"),
            "positives_female": int(((gender == "F") & (y == 1)).sum()),
            "positives_male": int(((gender == "M") & (y == 1)).sum()),
        },
    )


def h6(t: Tables) -> list[TestResult]:
    train = _split(t, 30, "train")
    results = []
    for test_id, feature in (("H6a", "active_days_to_date"), ("H6b", "assignment_completion_rate")):
        data = train[[feature, TARGET_COLUMN, "student_id"]].dropna().reset_index(drop=True)
        x, yv = data[feature].to_numpy(dtype=np.float64), data[TARGET_COLUMN].to_numpy(dtype=np.float64)
        test = stats.spearmanr(x, yv, alternative="less")
        rows = np.arange(len(data))
        boot = []
        for w in cluster_weights(data["student_id"].to_numpy(), RESAMPLES, SEED):
            idx = np.repeat(rows, w.astype(np.int64))  # rows of each drawn student, as many times as drawn
            boot.append(float(stats.spearmanr(x[idx], yv[idx]).statistic))
        low, high = _ci(np.asarray(boot))
        results.append(
            TestResult(
                test_id,
                f"{feature} at day 30 is negatively associated with the adverse outcome",
                "pre-registered",
                "spearman_rho",
                float(test.statistic),
                low,
                high,
                float(test.pvalue),
                "one-sided Spearman correlation (training presentations)",
                {
                    "n": len(data),
                    "missing_excluded": int(len(train) - len(data)),
                    "note": "p assumes independent rows; the interval is a student-level cluster bootstrap",
                },
            )
        )
    return results


# ------------------------------------------------------------------ run
def sanity_checks(t: Tables, repo_root: Path) -> dict[str, float]:
    """The saved artifacts must reproduce the published V2 test PR-AUC exactly (same data, same models)."""
    report_root = (
        t.config.report_dir if t.config.report_dir.is_absolute() else repo_root / t.config.report_dir
    )
    published = json.loads((report_root / RUN_ID / "metrics.json").read_text(encoding="utf-8"))
    out: dict[str, float] = {}
    for c in published["cutoffs"]:
        if c["target"] != TARGET:
            continue
        test = _split(t, c["cutoff_day"], "test")
        for name, abbr in (("logistic_regression", "lr"), ("xgboost", "xgb")):
            mine = _ap(_y(test), _artifact_scores(t, abbr, c["cutoff_day"], test), np.ones(len(test)))
            gap = abs(mine - c["models"][name]["test"]["pr_auc"])
            if gap > 1e-9:
                raise RuntimeError(
                    f"{name} day {c['cutoff_day']} does not reproduce the published PR-AUC ({gap:.2e})"
                )
            out[f"{abbr}_d{c['cutoff_day']}"] = mine
    return out


def apply_holm(results: list[TestResult]) -> None:
    for r, adjusted in zip(results, holm([r.p_value for r in results]), strict=True):
        r.p_holm = adjusted
        r.supported = adjusted < ALPHA
        threshold = next((v for k, v in NEGLIGIBLE.items() if k in r.metric), None)
        r.negligible = r.supported and threshold is not None and abs(r.estimate) < threshold


def run(config: TrainingConfig, repo_root: Path) -> Path:
    root = config.dataset.path if config.dataset.path.is_absolute() else repo_root / config.dataset.path
    registry_root = config.output_dir if config.output_dir.is_absolute() else repo_root / config.output_dir
    t = Tables(config, load_oulad(root), ModelRegistry(registry_root), {})
    reproduced = sanity_checks(t, repo_root)
    results = [*h1(t), *h2(t), h3(t), h4(repo_root), h5(t), *h6(t)]
    apply_holm(results)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_root = config.report_dir if config.report_dir.is_absolute() else repo_root / config.report_dir
    out = report_root / f"hypotheses-{stamp}"
    out.mkdir(parents=True)
    payload = {
        "created_at": stamp,
        "alpha": ALPHA,
        "resamples": RESAMPLES,
        "seed": SEED,
        "run_id": RUN_ID,
        "reproduced_published_pr_auc": reproduced,
        "results": [asdict(r) for r in results],
    }
    (out / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (out / "report.md").write_text(render(payload), encoding="utf-8")
    return out


def _fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:.4f}"


def render(payload: dict[str, Any]) -> str:
    reproduced = ", ".join(f"{k} {v:.4f}" for k, v in payload["reproduced_published_pr_auc"].items())
    lines = [
        f"# Pre-registered hypothesis tests — {payload['created_at']}",
        "",
        "> **Provenance: BENCHMARK** (OULAD, UK). Hypotheses, tests and decision rules: "
        "docs/research/week04-research-design.md (fixed before this run). Holm correction across all tests, "
        f"alpha = {payload['alpha']}; {payload['resamples']} cluster-bootstrap resamples (students), "
        f"seed {payload['seed']}.",
        "",
        f"Sanity check: the saved V2 models reproduce the published test PR-AUC exactly ({reproduced}).",
        "",
        "| ID | Hypothesis | Status | Effect | 95% interval | p | Holm p | Supported | Note |",
        "|---|---|---|---:|---|---:|---:|---|---|",
    ]
    for r in payload["results"]:
        note = "practically negligible" if r["negligible"] else ""
        lines.append(
            f"| {r['id']} | {r['hypothesis']} | {r['status']} | {r['estimate']:.4f} ({r['metric']}) | "
            f"[{_fmt(r['ci_low'])}, {_fmt(r['ci_high'])}] | {r['p_value']:.2e} | {r['p_holm']:.2e} | "
            f"{'yes' if r['supported'] else 'no'} | {note} |"
        )
    lines += ["", "## Details", ""]
    for r in payload["results"]:
        lines += [
            f"### {r['id']} — {r['test']}",
            "",
            "```json",
            json.dumps(r["details"], indent=2),
            "```",
            "",
        ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    print(run(load_config(args.config), Path.cwd()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
