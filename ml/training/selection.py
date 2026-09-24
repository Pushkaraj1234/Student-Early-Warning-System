"""Documented, rule-based choices. Only VALIDATION data is used; test data never influences a
choice.

Imbalance strategy (per model): the strategy with the best validation PR-AUC, except that
'none' is preferred when it is within ``STRATEGY_TOLERANCE`` of the best — re-weighting
distorts probability estimates, so it must earn its place.

Model selection (per cutoff): never "highest accuracy". Among models whose validation PR-AUC
is within ``tolerance`` of the best, choose the most interpretable; ties are broken by the
better validation Brier score (calibration), then the lower seed-to-seed PR-AUC spread
(stability).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ml.models.factory import INTERPRETABILITY_RANK, ImbalanceStrategy, ModelName

STRATEGY_TOLERANCE = 0.005


@dataclass(frozen=True)
class StrategyResult:
    strategy: ImbalanceStrategy
    val_pr_auc: float
    val_roc_auc: float
    val_brier: float


@dataclass(frozen=True)
class Candidate:
    model_name: ModelName
    val_pr_auc: float
    val_brier: float
    stability_pr_auc_std: float


def choose_imbalance_strategy(results: Sequence[StrategyResult]) -> tuple[ImbalanceStrategy, str]:
    if not results:
        raise ValueError("no strategy results")
    best = max(results, key=lambda r: r.val_pr_auc)
    near = [r for r in results if best.val_pr_auc - r.val_pr_auc <= STRATEGY_TOLERANCE]
    for r in near:
        if r.strategy == "none":
            if best.strategy == "none":
                return "none", "no re-weighting had the best validation PR-AUC"
            return "none", (
                f"'{best.strategy}' improved validation PR-AUC by only "
                f"{best.val_pr_auc - r.val_pr_auc:.4f} (<= {STRATEGY_TOLERANCE}); unweighted training "
                "is kept because re-weighting distorts probability estimates"
            )
    return best.strategy, (
        f"'{best.strategy}' improved validation PR-AUC by more than {STRATEGY_TOLERANCE} over no re-weighting"
    )


def select_model(candidates: Sequence[Candidate], tolerance: float) -> tuple[ModelName, str]:
    if not candidates:
        raise ValueError("no candidates")
    best = max(candidates, key=lambda c: c.val_pr_auc)
    eligible = [c for c in candidates if best.val_pr_auc - c.val_pr_auc <= tolerance]
    chosen = min(
        eligible,
        key=lambda c: (INTERPRETABILITY_RANK[c.model_name], c.val_brier, c.stability_pr_auc_std),
    )
    names = ", ".join(sorted(c.model_name for c in eligible))
    rationale = (
        f"Validation PR-AUC best = {best.val_pr_auc:.4f} ({best.model_name}). Models within "
        f"{tolerance:.3f} of it: {names}. Selected the most interpretable of these "
        f"({chosen.model_name}; validation PR-AUC {chosen.val_pr_auc:.4f}, Brier {chosen.val_brier:.4f}, "
        f"seed PR-AUC std {chosen.stability_pr_auc_std:.4f})."
    )
    return chosen.model_name, rationale
