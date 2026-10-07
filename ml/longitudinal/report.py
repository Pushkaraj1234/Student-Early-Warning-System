"""Markdown report and charts for the v3 longitudinal experiment (aggregates only, no identifiers)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODEL_LABELS = {
    "xgb_v2": "XGBoost, v2 features",
    "xgb_ts": "XGBoost, v3 features",
    "l1_ts": "L1 logistic (LASSO), v3",
    "rf_ts": "Random forest, v3",
    "gru": "GRU",
    "lstm": "LSTM",
    "tcn": "TCN",
    "ensemble": "Ensemble (XGBoost + best sequence)",
    "prevalence_baseline": "Prevalence baseline",
}


def _f(v: Any, digits: int = 3) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return f"{v:,}"
    return f"{float(v):.{digits}f}"


def _p(v: Any) -> str:
    if v is None:
        return "n/a"
    return "< 0.001" if float(v) < 0.001 else f"{float(v):.3f}"


def _label(name: str) -> str:
    return MODEL_LABELS.get(name, name)


def _result(entry: dict[str, Any]) -> str:
    return "supported" if entry.get("supported") else "not supported"


def _charts(results: dict[str, Any], out: Path) -> list[str]:
    files = []
    academic = results.get("academic", {})
    if academic:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        keys = ["xgb_v2", "xgb_ts", "l1_ts", academic.get("best_sequence_model"), "ensemble"]
        for key in [k for k in keys if k in academic["models"]]:
            rows = academic["models"][key]["test_by_week"]
            ax.plot([r["week"] for r in rows], [r["pr_auc"] for r in rows], label=_label(key))
        base = academic["models"]["prevalence_baseline"]["test_by_week"]
        ax.plot(
            [r["week"] for r in base], [r["prevalence"] for r in base], "k--", label="Prevalence (chance)"
        )
        ax.set_xlabel("Week of the course (prediction made at the end of the week)")
        ax.set_ylabel("Test PR-AUC (2014J)")
        ax.set_title("Fail or Withdrawn: ranking quality by week")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out / "pr_auc_by_week.png", dpi=120)
        plt.close(fig)
        files.append("pr_auc_by_week.png")
    km = results.get("kaplan_meier", {}).get("curves")
    if km:
        fig, ax = plt.subplots(figsize=(7, 4.5))
        ax.step(km["overall"]["time"], km["overall"]["survival"], where="post", label="All", color="black")
        for tertile, curve in km["by_week1_activity_tertile"].items():
            ax.step(curve["time"], curve["survival"], where="post", label=f"Week-1 activity: {tertile}")
        ax.set_xlabel("Week")
        ax.set_ylabel("Share still registered (Kaplan-Meier)")
        ax.set_title("Retention in the training presentations")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out / "kaplan_meier.png", dpi=120)
        plt.close(fig)
        files.append("kaplan_meier.png")
    hist = results.get("alerts", {}).get("lead_time_weeks_histogram_raw_f1")
    if hist:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.bar([int(k) for k in hist], list(hist.values()))
        ax.set_xlabel("Weeks between the first alert and the outcome")
        ax.set_ylabel("Adverse registrations")
        ax.set_title("Lead time of the first alert (raw policy, F1 threshold, test)")
        fig.tight_layout()
        fig.savefig(out / "lead_time.png", dpi=120)
        plt.close(fig)
        files.append("lead_time.png")
    shap_rows = results.get("explanations", {}).get("shap", {}).get("all_weeks")
    if shap_rows:
        fig, ax = plt.subplots(figsize=(7, 5))
        rows = list(reversed(shap_rows))
        ax.barh(
            [r["feature"] for r in rows],
            [r["mean_abs_shap"] for r in rows],
            color=["tab:orange" if r["new_in_v3"] else "tab:blue" for r in rows],
        )
        ax.set_xlabel("Mean |SHAP| (log-odds); orange = new in v3")
        ax.set_title("XGBoost (v3 features): global importance, test sample")
        fig.tight_layout()
        fig.savefig(out / "shap_importance.png", dpi=120)
        plt.close(fig)
        files.append("shap_importance.png")
    return files


def _comparison_row(name: str, entry: dict[str, Any]) -> str:
    return (
        f"| {name} | {entry['description']} | {_f(entry['effect'], 4)} [{_f(entry.get('ci_low'), 4)}, "
        f"{_f(entry.get('ci_high'), 4)}] | {_p(entry['p_value'])} | {_p(entry.get('p_holm'))} | "
        f"{_result(entry)} |"
    )


def render(results: dict[str, Any], charts: list[str]) -> str:
    d = results["dataset"]
    lines = [
        f"# EWS v3 longitudinal study — {results['run_id']}",
        "",
        f"> **Provenance: {d['provenance'].upper()}** — {d['description']} Dataset version `{d['version']}`.",
        "> These results describe the method on this dataset, not Indian students. Benchmark-trained",
        "> models are never approved for real students.",
        "",
        f"Plan and pre-specified comparisons: `{results['plan']}`. Leakage guard: passed at weeks "
        f"{', '.join(results['leakage_guard']['rows_compared_by_week'])}.",
        "",
    ]
    panel = results["panel"]
    lines += [
        "## 1. Panel",
        "",
        f"Feature set `{panel['feature_version']}`: {panel['features']} features "
        f"({panel['v2_features']} v2 + {len(panel['longitudinal_features'])} longitudinal). "
        f"Weeks {panel['weeks'][0]}-{panel['weeks'][1]}. "
        f"Registrations recorded as Withdrawn without a date (excluded from the withdrawal horizons only): "
        f"{panel['withdrawn_unknown_week_registrations']}.",
        "",
        "| Split | Presentations | Student-weeks | Registrations | Fail/Withdrawn | "
        "Withdraw ≤ 4 wk | Withdraw ≤ 8 wk |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for split, s in panel["splits"].items():
        prev = s["prevalence"]
        lines.append(
            f"| {split} | {', '.join(s['presentations'])} | {s['student_weeks']:,} | "
            f"{s['registrations']:,} | "
            f"{_f(prev['academic'])} | {_f(prev['withdraw_4w'])} | {_f(prev['withdraw_8w'])} |"
        )
    km = results["kaplan_meier"]
    lines += [
        "",
        f"**Retention (Kaplan-Meier, training presentations, {km['registrations']:,} registrations, "
        f"{km['events']:,} withdrawals):** "
        + ", ".join(f"week {k.split('_')[-1]}: {_f(v)}" for k, v in km["overall"].items())
        + ". By week-1 activity tertile at week 13: "
        + ", ".join(f"{t} {_f(s['retained_week_13'])}" for t, s in km["by_week1_activity_tertile"].items())
        + ".",
        "",
    ]
    academic = results["academic"]
    lines += [
        "## 2. Fail or Withdrawn, predicted every week",
        "",
        "| Model | Validation PR-AUC | Test PR-AUC [95% CI] | Test ROC-AUC | Test Brier | Test ECE |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, m in academic["models"].items():
        ci = m["test_pr_auc_ci"]
        lines.append(
            f"| {_label(name)} | {_f(m['validation']['pr_auc'])} | {_f(m['test']['pr_auc'])} "
            f"[{_f(ci[0])}, {_f(ci[1])}] | {_f(m['test']['roc_auc'])} | {_f(m['test']['brier'])} | "
            f"{_f(m['test']['ece'])} |"
        )
    lines += [
        "",
        f"Selected by validation PR-AUC: **{_label(academic['selected_model'])}**. Best sequence model: "
        f"{_label(academic['best_sequence_model'])}. Test prevalence "
        f"{_f(academic['models']['xgb_ts']['test']['prevalence'])}.",
        "",
    ]
    comparisons = [
        ("P1", academic["comparisons"]["P1"]),
        ("P2", academic["comparisons"]["P2"]),
        ("P4", results["alerts"]["P4"]),
    ]
    lines += [
        "## 3. Pre-specified comparisons (Holm-corrected)",
        "",
        "| ID | Comparison | Effect [95% CI] | p | Holm p | Result |",
        "|---|---|---|---:|---:|---|",
        *(_comparison_row(name, entry) for name, entry in comparisons),
    ]
    if "P5" in results.get("lomo", {}):
        p5 = results["lomo"]["P5"]
        lines.append(
            f"| P5 | {p5['description']} | median {_f(p5['effect'], 4)} "
            f"({p5['modules_where_l1_degrades_less']}/{p5['n']} modules) | {_p(p5['p_value'])} | "
            f"{_p(p5.get('p_holm'))} | {_result(p5)} |"
        )
    al = results["alerts"]
    lines += [
        "",
        f"## 4. Thresholds and alerts ({_label(al['model'])}; thresholds chosen on validation)",
        "",
        "| Threshold | Value | Student-week recall | Student-week precision | Student recall | "
        "Student false-alarm rate | Median lead (weeks) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, t in al["by_threshold"].items():
        sw, st = t["student_week"], t["student"]
        lines.append(
            f"| {name} | {_f(t['threshold'])} | {_f(sw['recall'])} | {_f(sw['precision'])} | "
            f"{_f(st['recall'])} | "
            f"{_f(st['false_alarm_rate'])} | {_f(st['lead_time_median_weeks'], 1)} |"
        )
    lines += [
        "",
        "| Alert policy (F1 threshold) | Student recall | False-alarm rate | Precision | "
        "Median lead (weeks) | "
        "Lead ≥ 4 weeks | Alert flips per registration |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for policy, m in al["policies_at_f1"].items():
        lines.append(
            f"| {policy} | {_f(m['recall'])} | {_f(m['false_alarm_rate'])} | {_f(m['precision'])} | "
            f"{_f(m['lead_time_median_weeks'], 1)} | {_f(m['lead_time_share_4w_or_more'])} | "
            f"{_f(m['mean_flips_per_registration'], 2)} |"
        )
    tiers = al["risk_tiers"]
    lines += [
        "",
        f"Risk tiers (validation quantiles {tiers['quantiles']}): mean tier changes per registration "
        f"{_f(tiers['mean_tier_changes_per_registration_raw'], 2)} with raw weekly risk, "
        f"{_f(tiers['mean_tier_changes_per_registration_ewma'], 2)} with smoothed risk. "
        "Deployment default policy: "
        f"**{al['deployment_default_policy']}** ({al['deployment_policy_rule']}).",
        "",
    ]
    cal = results["calibration"]["test"]
    lines += [
        "## 5. Calibration (XGBoost v3; calibrator fitted on validation)",
        "",
        "| | Brier | ECE |",
        "|---|---:|---:|",
        *(f"| {k} | {_f(v['brier'])} | {_f(v['ece'])} |" for k, v in cal.items()),
        "",
    ]
    fair = results["fairness"]
    eo = fair["equal_opportunity_gender"]
    single, adjusted = eo["single_threshold"], eo["per_group_thresholds_result"]
    demo = fair["demographics_as_inputs"]
    lines += [
        f"## 6. Fairness ({_label(fair['model'])}, F1 threshold, test student-weeks)",
        "",
        "| Attribute | Recall gap (lowest group) | FPR gap | Calibration-gap spread |",
        "|---|---:|---:|---:|",
    ]
    for attr, s in fair["subgroups_test_student_weeks"].items():
        disp = s["disparity"]
        lines.append(
            f"| {attr} | {_f(disp['recall']['gap'])} ({disp['recall']['min_group']}) | "
            f"{_f(disp['false_positive_rate']['gap'])} | {_f(disp['calibration_gap']['gap'])} |"
        )
    lines += [
        "",
        f"Gender recall gap (F minus M): single threshold {_f(single['recall_gap'])} "
        f"[{_f(single['recall_gap_ci'][0])}, {_f(single['recall_gap_ci'][1])}]; per-group thresholds "
        f"{_f(adjusted['recall_gap'])} "
        f"[{_f(adjusted['recall_gap_ci'][0])}, {_f(adjusted['recall_gap_ci'][1])}] "
        f"(precision {_f(single['precision'])} → {_f(adjusted['precision'])}; "
        f"flagged {_f(single['flagged_rate'])} → "
        f"{_f(adjusted['flagged_rate'])}). Note: {eo['note']}.",
        "",
        "Demographics as inputs (sensitivity only): test PR-AUC "
        f"{_f(demo['without_demographics']['test']['pr_auc'])} "
        f"→ {_f(demo['with_demographics']['test']['pr_auc'])}; gender recall gap "
        f"{_f(demo['without_demographics']['recall_gap'])} → {_f(demo['with_demographics']['recall_gap'])}.",
        "",
    ]
    ex = results["explanations"]
    cf = ex["counterfactuals"]
    lasso = ex["lasso"]
    lines += [
        "## 7. Explanations",
        "",
        "Top SHAP features (XGBoost v3, test sample): "
        + ", ".join(
            f"{r['feature']}{' (v3)' if r['new_in_v3'] else ''}" for r in ex["shap"]["all_weeks"][:10]
        )
        + ".",
        "",
        f"LASSO (C = {lasso['C']}): {lasso['nonzero']} of {lasso['inputs']} inputs kept; features zeroed: "
        f"{', '.join(lasso['zeroed_features']) or 'none'}.",
        "",
        f"Counterfactuals (week {cf['week']}, {cf['evaluated']} flagged student-weeks): "
        "one actionable change "
        f"suffices for {cf['solved_with_1_change']}, two for {cf['solved_with_2_changes']}, none found for "
        f"{cf['not_solved']}. Most frequent single levers: "
        + (", ".join(f"{k} ({v})" for k, v in list(cf["single_change_features"].items())[:5]) or "none")
        + ". These show what the model responds to, not causes.",
        "",
    ]
    mc = results["mc_dropout"]
    lines += [
        f"## 8. Uncertainty (MC dropout, {_label(mc['model'])}, {mc['samples']} samples)",
        "",
        f"Test PR-AUC {_f(mc['test_pr_auc_mean_prediction'])}; most certain 80%: "
        f"{_f(mc['test_pr_auc_most_certain_80pct'])}; least certain 20%: "
        f"{_f(mc['test_pr_auc_least_certain_20pct'])}; "
        f"Spearman(uncertainty, |error|) = {_f(mc['spearman_uncertainty_vs_abs_error'])}.",
        "",
    ]
    wd = results["withdrawal"]
    lines += ["## 9. Withdrawal within 4 and 8 weeks", ""]
    for target in ("withdraw_4w", "withdraw_8w"):
        t = wd[target]
        lines += [
            f"**{target}** — selected {t['selected_model']}; hazard-model derived risk test PR-AUC "
            f"{_f(t['hazard_model_derived']['pr_auc'])}.",
            "",
            "| Model (imbalance) | Validation PR-AUC | Test PR-AUC [95% CI] | Test ROC-AUC |",
            "|---|---:|---:|---:|",
        ]
        for name, m in t["models"].items():
            ci = m["test_pr_auc_ci"]
            lines.append(
                f"| {name} | {_f(m['validation']['pr_auc'])} | {_f(m['test']['pr_auc'])} "
                f"[{_f(ci[0])}, {_f(ci[1])}] | "
                f"{_f(m['test']['roc_auc'])} |"
            )
        lines.append("")
    lines += [
        "Concordance (time to withdrawal, test): "
        + "; ".join(
            f"{k.replace('_', ' ')}: hazard model {_f(v['c_index_hazard_model'])}, direct 8-week model "
            f"{_f(v['c_index_direct_8w_model'])} "
            f"({v['events']} withdrawals / {v['registrations']} registrations)"
            for k, v in wd["concordance"].items()
        )
        + ".",
        "",
        "Largest weekly hazard odds ratios per SD (L1 logistic): "
        + (
            ", ".join(
                f"{r['feature']} {_f(r['odds_ratio'], 2)}"
                for r in wd.get("hazard_odds_ratios_per_sd", [])[:6]
            )
            or "none"
        )
        + ".",
        "",
    ]
    ro = results["rolling_origin"]
    lines += ["## 10. Rolling-origin cross-validation", "", f"Note: {ro['note']}.", ""]
    for target in ("academic", "withdraw_4w"):
        folds = ro[target]["folds"]
        names = list(folds[0]["models"])
        lines += [
            f"**{target}** (test PR-AUC)",
            "",
            "| Train → test | " + " | ".join(_label(n) for n in names) + " |",
            "|---|" + "---:|" * len(names),
        ]
        for fold in folds:
            lines.append(
                f"| {'+'.join(fold['train'])} → {'+'.join(fold['test'])} | "
                + " | ".join(_f(fold["models"][n]["pr_auc"]) for n in names)
                + " |"
            )
        summary = ro[target]["summary"]
        lines.append(
            "| mean (SD) | "
            + " | ".join(f"{_f(summary[n]['pr_auc_mean'])} ({_f(summary[n]['pr_auc_sd'])})" for n in names)
            + " |"
        )
        lines.append("")
    lomo = results["lomo"]
    lines += ["## 11. Unseen module (leave-one-module-out)", ""]
    if lomo.get("skipped"):
        lines += [f"Skipped: {lomo['reason']}.", ""]
    else:
        lines += [
            f"{lomo['scope']} Train {', '.join(lomo['train_presentations'])}; evaluate "
            f"{', '.join(lomo['test_presentations'])}.",
            "",
            "| Module | Model | PR-AUC with module | PR-AUC module unseen | Degradation |",
            "|---|---|---:|---:|---:|",
            *(
                f"| {r['module']} | {r['model']} | {_f(r['reference_pr_auc'])} | "
                f"{_f(r['held_out_pr_auc'])} | "
                f"{_f(r['degradation'])} |"
                for r in lomo["rows"]
            ),
            "",
        ]
    dr = results["drift"]
    lines += [
        "## 12. Drift (training vs test presentation)",
        "",
        f"{dr['alerts']} drift alerts ({dr['critical_alerts']} critical). Highest PSI: "
        + ", ".join(f"{r['feature']} {_f(r['psi'])}" for r in dr["top_psi"][:5])
        + ".",
        "",
    ]
    art = results.get("artifacts", {})
    if art:
        lines += [
            "## 13. Artifacts (git-ignored, benchmark only, never approved for real students)",
            "",
            f"`ml/artifacts/{art['xgb_ts']}` (XGBoost v3; thresholds, alert policy and monitoring "
            "reference in its "
            f"metadata) and `ml/artifacts/{art['sequence']}` (sequence model state).",
            "",
        ]
    if charts:
        lines += ["## Charts", "", *(f"![{c}]({c})" for c in charts), ""]
    return "\n".join(lines)


def write_report(results: dict[str, Any], report_dir: Path) -> Path:
    charts = _charts(results, report_dir)
    path = report_dir / "report.md"
    path.write_text(render(results, charts), encoding="utf-8")
    return path
