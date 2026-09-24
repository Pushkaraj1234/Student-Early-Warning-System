"""Human-readable (Markdown) and machine-readable (JSON) evaluation reports.

Reports contain only aggregate metrics — no student-level rows.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MODEL_LABELS = {
    "logistic_regression": "Logistic Regression",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}


def _f(value: Any, digits: int = 3) -> str:
    return "n/a" if value is None else f"{float(value):.{digits}f}"


def _ci(ci: dict[str, Any], key: str) -> str:
    c = ci.get(key)
    return "" if not c else f" [{c['low']:.3f}, {c['high']:.3f}]"


def _leakage_text(checks: dict[str, Any] | None) -> str:
    if not checks:
        return "not run"
    return "; ".join(
        f"day {day} passed ({c['rows_compared']} rows, {c['features_compared']} features)"
        for day, c in checks.items()
    )


def _cutoff_section(c: dict[str, Any]) -> list[str]:
    lines = [
        f"## Target: {c.get('target', 'academic')} — decision point day {c['cutoff_day']}",
        "",
        f"Definition: {c.get('target_definition', 'final_result is Fail or Withdrawn')}. "
        f"Horizon: {c.get('target_horizon', 'end of the module presentation')}.",
        "",
    ]
    lines += [
        "### Data and class distribution",
        "",
        "| Split | Presentations | Registrations | Adverse outcomes | Prevalence |",
        "|---|---|---:|---:|---:|",
    ]
    for split in ("train", "validation", "test"):
        d = c["distribution"][split]
        lines.append(
            f"| {split} | {', '.join(d['groups'])} | {d['n']} | {d['positives']} | {_f(d['prevalence'])} |"
        )
    lines += ["", f"Rows not assigned to any split: {c['unassigned_rows']}.", ""]
    if c.get("skipped"):
        return [*lines, f"**Not trained** — {c['skip_reason']}. No model exists for this target here.", ""]

    lines += [
        "### Imbalance strategy comparison (validation, uncalibrated)",
        "",
        "| Model | Strategy | PR-AUC | ROC-AUC | Brier |",
        "|---|---|---:|---:|---:|",
    ]
    for name, m in c["models"].items():
        for r in m["imbalance_comparison"]:
            chosen = " (selected)" if r["strategy"] == m["imbalance_strategy"] else ""
            lines.append(
                f"| {MODEL_LABELS[name]} | {r['strategy']}{chosen} | {_f(r['val_pr_auc'])} | "
                f"{_f(r['val_roc_auc'])} | {_f(r['val_brier'])} |"
            )
    lines += [""]
    for name, m in c["models"].items():
        lines.append(f"- {MODEL_LABELS[name]}: {m['imbalance_rationale']}.")
    lines += [
        "",
        "SMOTE/oversampling was not used: it fabricates synthetic minority rows and distorts "
        "probability calibration; class re-weighting was compared instead.",
        "",
    ]

    lines += [
        "### Held-out test performance (out-of-time)",
        "",
        "95% intervals: cluster bootstrap over students. Threshold for precision/recall/F1 = the "
        "F1-optimal threshold chosen on validation.",
        "",
        "Brier/ECE are shown for raw and calibrated probabilities on test; the reported model uses "
        "calibration only where the out-of-time check below showed it helps.",
        "",
        "| Model | PR-AUC | ROC-AUC | Brier (raw -> cal) | ECE (raw -> cal) | Threshold | Precision | "
        "Recall | F1 |",
        "|---|---|---|---|---|---:|---:|---:|---:|",
    ]
    for name, m in c["models"].items():
        t, ci = m["test"], m["test_bootstrap_ci"]
        comp = m["test_calibration_comparison"]
        raw, cal = comp["raw"], comp["calibrated"]
        at = t["at_threshold"]
        cells = [
            f"{_f(t['pr_auc'])}{_ci(ci, 'pr_auc')}",
            f"{_f(t['roc_auc'])}{_ci(ci, 'roc_auc')}",
            f"{_f(raw['brier'])} -> {_f(cal['brier'])}",
            f"{_f(raw['ece'])} -> {_f(cal['ece'])}",
            _f(at["threshold"]),
            _f(at["precision"]),
            _f(at["recall"]),
            _f(at["f1"]),
        ]
        lines.append(f"| {MODEL_LABELS[name]} | " + " | ".join(cells) + " |")
    lines += [
        "",
        "#### Capacity view (test): flag the top k% highest-risk registrations",
        "",
        "| Model | "
        + " | ".join(
            f"top {int(x['fraction'] * 100)}% precision / recall"
            for x in next(iter(c["models"].values()))["test"]["top_fraction"]
        )
        + " |",
        "|---|" + "---|" * len(next(iter(c["models"].values()))["test"]["top_fraction"]),
    ]
    for name, m in c["models"].items():
        cells = [f"{_f(x['precision'])} / {_f(x['recall'])}" for x in m["test"]["top_fraction"]]
        lines.append(f"| {MODEL_LABELS[name]} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "#### Class-specific performance and confusion matrices (test, at threshold)",
        "",
        "| Model | Class 0 P / R / F1 (n) | Class 1 P / R / F1 (n) | TN | FP | FN | TP |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for name, m in c["models"].items():
        at = m["test"]["at_threshold"]
        pc, cm = at["per_class"], at["confusion_matrix"]
        cells = [
            f"{_f(pc[k]['precision'])} / {_f(pc[k]['recall'])} / {_f(pc[k]['f1'])} ({pc[k]['support']})"
            for k in ("0", "1")
        ]
        lines.append(
            f"| {MODEL_LABELS[name]} | {cells[0]} | {cells[1]} | {cm['tn']} | {cm['fp']} | "
            f"{cm['fn']} | {cm['tp']} |"
        )

    lines += [
        "",
        "#### Risk levels on test (thresholds = validation quantiles of calibrated probability)",
        "",
        "| Model | Thresholds (watch / elevated / high) | stable | watch | elevated | high |",
        "|---|---|---|---|---|---|",
    ]
    for name, m in c["models"].items():
        th = m["risk_thresholds"]
        cells = [
            f"{r['n']} ({_f(r['share'], 2)}), obs {_f(r['observed_rate'], 2)}" for r in m["test_risk_levels"]
        ]
        lines.append(
            f"| {MODEL_LABELS[name]} | {_f(th['watch'])} / {_f(th['elevated'])} / {_f(th['high'])} | "
            + " | ".join(cells)
            + " |"
        )

    lines += [
        "",
        "### Stability (validation PR-AUC across training seeds; top-5 SHAP features overlap)",
        "",
        "| Model | PR-AUC mean | PR-AUC std | Top-5 Jaccard (mean pairwise) |",
        "|---|---:|---:|---:|",
    ]
    for name, m in c["models"].items():
        s = m["stability"]
        lines.append(
            f"| {MODEL_LABELS[name]} | {_f(s['val_pr_auc_mean'], 4)} | {_f(s['val_pr_auc_std'], 4)} | "
            f"{_f(s['top5_jaccard_mean'], 2)} |"
        )

    lines += [
        "",
        "### Interpretability",
        "",
        "| Model | Explanation method | Top-5 features by mean abs(SHAP) on test |",
        "|---|---|---|",
    ]
    methods = {
        "logistic_regression": "Linear SHAP (log-odds); coefficients are directly inspectable",
        "random_forest": "Tree SHAP (probability); 300 trees",
        "xgboost": "Tree SHAP (log-odds); 400 boosted trees",
    }
    for name, m in c["models"].items():
        top = list(m["global_importance_test"])[:5]
        lines.append(f"| {MODEL_LABELS[name]} | {methods[name]} | {', '.join(top)} |")

    lines += [
        "",
        "### Model selection",
        "",
        f"**Selected: {MODEL_LABELS[c['selected_model']]}** (`{c['selected_model_version']}`).",
        "",
        c["selection_rationale"],
        "",
    ]

    lines += [
        "### Calibration decision (out-of-time check; applied only if Brier AND ECE improve)",
        "",
        "| Model | Check split | Brier raw -> cal | ECE raw -> cal | Applied |",
        "|---|---|---|---|---|",
    ]
    for name, m in c["models"].items():
        d = m["calibration_decision"]
        split = d.get("check_split")
        split_text = (
            f"{','.join(split['train'])} / {','.join(split['calibrate'])} / {','.join(split['evaluate'])}"
            if split
            else "n/a"
        )
        lines.append(
            f"| {MODEL_LABELS[name]} | {split_text} | "
            f"{_f(d.get('brier_raw'))} -> {_f(d.get('brier_calibrated'))} | "
            f"{_f(d.get('ece_raw'))} -> {_f(d.get('ece_calibrated'))} | "
            f"{'yes' if d.get('apply') else 'no'} |"
        )
    lines.append("")

    sel = c["models"][c["selected_model"]]
    lines += ["### Subgroup audit of the selected model (test; audit attributes are NOT model inputs)", ""]
    for attr, audit in sel["subgroups_test"].items():
        lines += [
            f"**{attr}**",
            "",
            "| Group | n | Prevalence | Mean predicted | Calibration gap | ECE | Recall | FNR | "
            "Precision | FPR |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for r in audit["groups"]:
            if r.get("insufficient_data"):
                lines.append(f"| {r['group']} | {r['n']} | too few rows for reliable metrics | | | | | | | |")
            else:
                lines.append(
                    f"| {r['group']} | {r['n']} | {_f(r['prevalence'])} | {_f(r['mean_predicted'])} | "
                    f"{_f(r['calibration_gap'])} | {_f(r['ece'])} | {_f(r['recall'])} | "
                    f"{_f(r['false_negative_rate'])} | {_f(r['precision'])} | "
                    f"{_f(r['false_positive_rate'])} |"
                )
        gap_text = "; ".join(
            f"{k} {_f(v['gap'])} ({v['max_group']} vs {v['min_group']})"
            for k, v in audit["disparity"].items()
            if v["gap"] is not None
        )
        lines += [
            "",
            f"Largest gaps between groups (max - min): "
            f"{gap_text or 'not computable (fewer than two groups with enough data)'}",
            "",
        ]

    alerts = sel["drift_train_vs_test"]["alerts"]
    lines += ["### Drift, training period vs test period (selected model)", ""]
    if alerts:
        lines += [
            "| Type | Subject | Statistic | Value | Threshold | Severity |",
            "|---|---|---|---:|---:|---|",
        ]
        lines += [
            f"| {a['alert_type']} | {a['subject']} | {a['statistic']} | {_f(a['value'])} | "
            f"{_f(a['threshold'])} | {a['severity']} |"
            for a in alerts
        ]
    else:
        lines.append("No drift alerts.")
    lines.append("")
    return lines


PROVENANCE_NOTES = {
    "benchmark": (
        "These results describe method behaviour on this benchmark dataset. They are **not** evidence "
        "about Indian students and must not be presented as such. No model here is approved to score "
        "real students: that requires validation on institutional data (see docs/ml/ml-strategy.md §5)."
    ),
    "synthetic": (
        "This run used **SYNTHETIC** data. The numbers below are **not** model performance and describe "
        "no real students; they only show that the pipeline executes end to end."
    ),
    "institutional": (
        "Institutional data: results apply only to the institution and period evaluated and must be "
        "reviewed against docs/ml/ml-strategy.md §5 before any model is approved."
    ),
}


def render_markdown(summary: dict[str, Any]) -> str:
    ds = summary["dataset"]
    lines = [
        f"# SEWS baseline evaluation — {summary['run_id']}",
        "",
        f"> **Data provenance: {ds['provenance'].upper()}.** {ds['description']}",
        f"> {PROVENANCE_NOTES[ds['provenance']]}",
        "",
        f"- Dataset version: `{ds['version']}`",
        f"- Feature version: `{summary['feature_version']}` ({len(summary['feature_names'])} features)",
        f"- Targets: {summary['target_definition']}",
        f"- Temporal leakage guard (features from full data == features from data truncated at the "
        f"cutoff): {_leakage_text(summary.get('leakage_checks'))}",
        f"- Score release lag assumption: {summary['config']['score_release_lag_days']} days "
        "(OULAD has no grade-release dates)",
        f"- Split (out-of-time): {summary['config']['split']}",
        f"- Created: {summary['created_at']}; git commit: {summary['git_commit'] or 'none (no commits yet)'}",
        f"- Libraries: {summary['library_versions']}",
        f"- Active model (primary decision point): `{summary['active_model_version']}`",
        "",
        "Attendance features are absent because OULAD contains no attendance data.",
        "",
    ]
    for c in summary["cutoffs"]:
        lines += _cutoff_section(c)
    lines += [
        "## Limitations",
        "",
        f"- Trained and evaluated on {ds['provenance']} data only; performance on Indian institutions is "
        "unknown (RQ5).",
        "- OULAD dates are relative; prediction dates are nominal (presentation start + cutoff).",
        "- Score availability depends on an assumed release lag; results may change with the true lag.",
        "- Validation (2014B) overlaps in calendar time with the end of 2013J; this can make validation "
        "slightly optimistic. The test split (2014J) starts after all training/validation presentations.",
        "- The calibrator (when applied) and thresholds are fitted on the same validation split; whether "
        "calibration is applied is decided on a separate out-of-time check, not on the test split.",
        "- Subgroup audit attributes are never model inputs; differences are reported, not corrected, and "
        "small groups are not reported.",
        "- Drift thresholds are conventional heuristics, not validated limits.",
        "- SHAP values are associations with the model output, not causal effects.",
        "",
    ]
    return "\n".join(lines)


def write_reports(summary: dict[str, Any], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "metrics.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (directory / "report.md").write_text(render_markdown(summary), encoding="utf-8")
