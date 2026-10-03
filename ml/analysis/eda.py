"""Exploratory data analysis of OULAD (course week 5): data quality, missing values, outliers, distributions.

    ml/.venv/Scripts/python -m ml.analysis.eda --config ml/configs/oulad_v2.json

Writes ``<report_dir>/eda-oulad-<UTC timestamp>/`` with ``report.md``, ``tables/*.csv`` and ``figures/*.png``.
Every number in the report is computed here; nothing is typed in by hand.

Deliberately NOT done here: any relationship between a feature and the outcome. Hypotheses H2 and H6
(docs/research/week04-research-design.md) are pre-registered and are tested in week 6; looking at those
relationships first would undermine them. Feature tables are profiled on the TRAINING presentations only.
Outputs are aggregates: no student identifier is written.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import matplotlib

matplotlib.use("Agg")  # files only, no display
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from ml.data.oulad import EXPECTED_COLUMNS, OuladTables, dataset_version, load_oulad
from ml.features.definitions import FEATURE_SETS
from ml.features.oulad_features import build_oulad_features
from ml.training.config import TrainingConfig, load_config

IQR_FENCE = 3.0  # "far out" values: beyond Q1 - 3*IQR or Q3 + 3*IQR (Tukey's outer fences)
STRONG_CORRELATION = 0.9  # feature pairs this correlated are near-duplicates
FIGURE_DPI = 150
DELAY_CLIP_DAYS = 60  # submission-delay histogram range (values beyond are pooled at the edges)
MISSING_TOKENS = ["?", ""]


@dataclass
class Report:
    lines: list[str]
    tables: dict[str, pd.DataFrame]
    figures: dict[str, Figure]

    def table(self, name: str, frame: pd.DataFrame, *, index: bool = False) -> None:
        self.tables[name] = frame
        shown = frame.reset_index() if index else frame
        self.lines += [markdown_table(shown), "", f"*Table: `tables/{name}.csv`*", ""]

    def figure(self, name: str, fig: Figure, caption: str) -> None:
        self.figures[name] = fig
        self.lines += [f"![{caption}](figures/{name}.png)", "", f"*Figure: {caption}*", ""]


def _cell(value: object) -> str:
    if isinstance(value, float | np.floating):
        number = float(value)
        if np.isnan(number):
            return "—"
        return f"{number:,.0f}" if number.is_integer() or abs(number) >= 1e5 else f"{number:,.3f}"
    if isinstance(value, int | np.integer):
        return f"{value:,}"
    return str(value)


def markdown_table(frame: pd.DataFrame) -> str:
    header = "| " + " | ".join(map(str, frame.columns)) + " |"
    rule = "|" + "|".join("---" for _ in frame.columns) + "|"
    rows = ["| " + " | ".join(_cell(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, rule, *rows])


def raw_profile(root: Path) -> pd.DataFrame:
    """Rows, columns, missing cells and exact duplicate rows of each source file, read as text."""
    rows = []
    for name in EXPECTED_COLUMNS:
        frame = pd.read_csv(root / name, dtype=str, na_values=MISSING_TOKENS, keep_default_na=False)
        missing = frame.isna().sum()
        rows.append(
            {
                "file": name,
                "rows": len(frame),
                "columns": frame.shape[1],
                "missing cells": int(missing.sum()),
                "columns with missing": ", ".join(f"{c} ({v:,})" for c, v in missing.items() if v) or "none",
                "duplicate rows": int(frame.duplicated().sum()),
            }
        )
    return pd.DataFrame(rows)


def quality_checks(t: OuladTables) -> pd.DataFrame:
    info, reg, sa, ass = t.student_info, t.registration, t.student_assessment, t.assessments
    keys = ["code_module", "code_presentation", "id_student"]
    merged = info.merge(reg, on=keys, how="left")
    unregistered = merged["date_unregistration"].notna()
    withdrawn = merged["final_result"] == "Withdrawn"
    registrations_per_student = info.groupby("id_student").size()
    imd = info["imd_band"].dropna().unique()
    checks: list[tuple[str, object]] = [
        ("Registrations (student x module presentation)", len(info)),
        ("Distinct students", int(info["id_student"].nunique())),
        ("Students with more than one registration", int((registrations_per_student > 1).sum())),
        ("Duplicate registration keys", int(info.duplicated(keys).sum())),
        ("Unregistration date present but result not 'Withdrawn'", int((unregistered & ~withdrawn).sum())),
        ("Result 'Withdrawn' but no unregistration date", int((withdrawn & ~unregistered).sum())),
        ("Registration date missing", int(merged["date_registration"].isna().sum())),
        ("Assessment submissions", len(sa)),
        ("Submissions with missing score", int(sa["score"].isna().sum())),
        ("Scores outside 0-100", int(((sa["score"] < 0) | (sa["score"] > 100)).sum())),
        ("Banked submissions (carried over from an earlier attempt)", int(sa["is_banked"].sum())),
        ("Assessments with no due date", int(ass["date"].isna().sum())),
        (
            "IMD band labels without a '%' sign (inconsistent coding)",
            ", ".join(sorted(b for b in imd if "%" not in b)),
        ),
    ]
    return pd.DataFrame(checks, columns=["check", "value"])


def outcome_table(t: OuladTables) -> pd.DataFrame:
    counts = pd.crosstab(t.student_info["code_presentation"], t.student_info["final_result"])
    counts = counts[["Pass", "Distinction", "Fail", "Withdrawn"]]
    counts["registrations"] = counts.sum(axis=1)
    counts["adverse share (Fail or Withdrawn)"] = (counts["Fail"] + counts["Withdrawn"]) / counts[
        "registrations"
    ]
    return counts.sort_index()


def describe(values: pd.Series) -> dict[str, float]:
    v = values.dropna().astype(float)
    if v.empty:
        return {"n": 0.0, "missing share": 1.0}
    q1, q3 = (float(q) for q in np.quantile(v.to_numpy(), [0.25, 0.75]))
    iqr = q3 - q1
    far = float(((v < q1 - IQR_FENCE * iqr) | (v > q3 + IQR_FENCE * iqr)).mean()) if iqr > 0 else 0.0
    return {
        "n": float(v.size),
        "missing share": float(values.isna().mean()),
        "mean": float(v.mean()),
        "std": float(v.std()),
        "min": float(v.min()),
        "p25": q1,
        "median": float(v.median()),
        "p75": q3,
        "max": float(v.max()),
        "skewness": float(cast(float, v.skew())),  # numeric Series: pandas returns a float
        "far-out share": far,
    }


def _hist(values: pd.Series, title: str, xlabel: str, *, log10: bool = False, bins: int = 50) -> Figure:
    fig, ax = plt.subplots(figsize=(7, 4))
    data = values.dropna().astype(float).to_numpy()
    if log10:
        data = np.log10(np.clip(data, 0, None) + 1)
        xlabel = f"log10(1 + {xlabel})"
    ax.hist(data, bins=bins, color="#2f6f8f", edgecolor="white", linewidth=0.4)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("count")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def _correlation_figure(corr: pd.DataFrame, cutoff: int) -> Figure:
    names = list(corr.columns)
    fig, ax = plt.subplots(figsize=(10, 9))
    image = ax.imshow(corr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(names)), names, rotation=90, fontsize=6)
    ax.set_yticks(range(len(names)), names, fontsize=6)
    ax.set_title(f"Spearman correlation between features, day {cutoff} (training presentations)")
    fig.colorbar(image, ax=ax, shrink=0.7)
    fig.tight_layout()
    return fig


def _missingness_figure(missing: pd.DataFrame) -> Figure:
    fig, ax = plt.subplots(figsize=(8, 9))
    order = missing.mean(axis=1).sort_values().index
    y = np.arange(len(order))
    width = 0.8 / len(missing.columns)
    for k, column in enumerate(missing.columns):
        ax.barh(
            y + (k - (len(missing.columns) - 1) / 2) * width,
            missing.loc[order, column],
            height=width,
            label=column,
        )
    ax.set_yticks(y, list(order), fontsize=7)
    ax.set_xlabel("share missing (training presentations)")
    ax.set_title("Missing values per feature by decision point")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def run(config: TrainingConfig, repo_root: Path) -> Path:
    root = config.dataset.path if config.dataset.path.is_absolute() else repo_root / config.dataset.path
    report_root = config.report_dir if config.report_dir.is_absolute() else repo_root / config.report_dir
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = report_root / f"eda-oulad-{stamp}"
    tables = load_oulad(root)
    train_groups = list(config.split.train)
    specs = FEATURE_SETS[config.feature_version]
    names = [s.name for s in specs]
    r = Report(
        lines=[
            f"# Exploratory data analysis — OULAD ({stamp})",
            "",
            "> **Provenance: BENCHMARK** — Open University, UK, 2013-2014 (CC BY 4.0). Not Indian data.",
            "> Feature-outcome relationships are deliberately not shown (pre-registered hypotheses H2 and H6 "
            "are tested in week 6). Feature tables are profiled on the training presentations only.",
            "",
            f"- Dataset version `{dataset_version(root)}`; feature set `{config.feature_version}` "
            f"({len(specs)} features)",
            f"- Training presentations profiled: {', '.join(train_groups)}; decision points: "
            f"{', '.join(f'day {c}' for c in config.cutoff_days)}",
            "- Outliers: share of values beyond Tukey's outer fences "
            f"(Q1 - {IQR_FENCE:g}·IQR, Q3 + {IQR_FENCE:g}·IQR)",
            "",
            "## 1. Source files",
            "",
        ],
        tables={},
        figures={},
    )
    r.table("source_files", raw_profile(root))
    r.lines += ["## 2. Data-quality checks", ""]
    r.table("quality_checks", quality_checks(tables))
    r.lines += ["## 3. Outcome by presentation", ""]
    r.table("outcome_by_presentation", outcome_table(tables), index=True)

    r.lines += ["## 4. Raw distributions", ""]
    keys = ["code_module", "code_presentation", "id_student"]
    clicks = tables.student_vle_daily.groupby(keys)["sum_click"].sum()
    active_days = tables.student_vle_daily.groupby(keys)["date"].nunique().astype(float)
    submitted = tables.student_assessment.merge(
        tables.assessments[["id_assessment", "date"]], on="id_assessment"
    )
    delay = submitted["date_submitted"] - submitted["date"]
    raw_stats = pd.DataFrame(
        {
            "total VLE clicks per registration": describe(clicks),
            "active VLE days per registration": describe(active_days),
            "assessment score": describe(tables.student_assessment["score"]),
            "submission delay (days, negative = early)": describe(delay),
            "studied credits": describe(tables.student_info["studied_credits"].astype(float)),
        }
    ).T
    r.table("raw_distributions", raw_stats, index=True)
    r.figure(
        "clicks_per_registration",
        _hist(clicks, "Total VLE clicks per registration", "clicks", log10=True),
        "total VLE clicks per registration (log scale: heavily right-skewed)",
    )
    r.figure(
        "assessment_scores",
        _hist(tables.student_assessment["score"], "Assessment scores", "score", bins=40),
        "distribution of assessment scores (0-100)",
    )
    r.figure(
        "submission_delay",
        _hist(delay.clip(-DELAY_CLIP_DAYS, DELAY_CLIP_DAYS), "Submission delay vs due date", "days"),
        f"submission delay relative to the due date (negative = early; clipped to ±{DELAY_CLIP_DAYS} days)",
    )

    r.lines += [
        "## 5. Feature tables (training presentations)",
        "",
        "Missing values are *informative*, not errors: a feature is missing when it is not defined yet at "
        "the decision point (for example, no score released by day 30). Logistic regression and random "
        "forest fill them with the training median and add a 'was missing' indicator column; XGBoost "
        "handles them natively. Far-out values are legitimate behaviour (very active students), so they "
        "are kept, not removed.",
        "",
    ]
    missing_by_day: dict[str, pd.Series] = {}
    for cutoff in config.cutoff_days:
        df = build_oulad_features(
            tables,
            cutoff,
            score_release_lag_days=config.score_release_lag_days,
            feature_version=config.feature_version,
        )
        df = df[df["split_group"].isin(train_groups)]
        stats = pd.DataFrame({n: describe(df[n]) for n in names}).T
        stats.insert(0, "family", [s.family for s in specs])
        missing_by_day[f"day {cutoff}"] = df[names].isna().mean()
        r.lines += [f"### Day {cutoff} — {len(df):,} registrations", ""]
        r.table(f"features_day{cutoff}", stats, index=True)
        if cutoff == config.primary_cutoff_day:
            corr = df[names].corr(method="spearman")
            r.figure(
                f"feature_correlation_day{cutoff}",
                _correlation_figure(corr, cutoff),
                f"feature-feature Spearman correlation at day {cutoff} (redundancy, not outcome association)",
            )
            matrix = corr.to_numpy()
            found = [
                (names[i], names[j], float(matrix[i, j]))
                for i in range(len(names))
                for j in range(i + 1, len(names))
                if abs(matrix[i, j]) >= STRONG_CORRELATION
            ]
            found.sort(key=lambda row: -abs(row[2]))
            pairs = pd.DataFrame(found, columns=["feature A", "feature B", "Spearman rho"])
            r.lines += [
                f"Feature pairs with |rho| >= {STRONG_CORRELATION:g} at day {cutoff} (near-duplicates: tree "
                "models are unaffected, linear coefficients become unstable):",
                "",
            ]
            r.table(f"strong_feature_pairs_day{cutoff}", pairs)

    r.lines += ["## 6. Missing values by decision point", ""]
    r.figure(
        "feature_missingness",
        _missingness_figure(pd.DataFrame(missing_by_day)),
        "share of missing values per feature at each decision point",
    )

    r.lines += ["## 7. Composition by audit attribute (never model inputs)", ""]
    composition = pd.concat(
        {
            col: tables.student_info[col].fillna("missing").value_counts(normalize=True).rename("share")
            for col in ("gender", "age_band", "disability", "imd_band", "highest_education")
        }
    ).reset_index()
    composition.columns = ["attribute", "group", "share"]
    r.table("audit_attribute_composition", composition)

    (out / "tables").mkdir(parents=True)
    (out / "figures").mkdir()
    for name, frame in r.tables.items():
        frame.to_csv(out / "tables" / f"{name}.csv")
    for name, fig in r.figures.items():
        fig.savefig(out / "figures" / f"{name}.png", dpi=FIGURE_DPI)
        plt.close(fig)
    (out / "report.md").write_text("\n".join(r.lines), encoding="utf-8")
    return out


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
