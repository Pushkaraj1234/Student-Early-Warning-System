"""Week 6 statistics, checked against known references before use on real data. Synthetic inputs only."""

from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from ml.analysis.hypotheses import bootstrap_p, cluster_weights, delong, holm


def _scores(seed: int, n: int = 400) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    good = y + rng.normal(0, 0.8, n)
    weak = y + rng.normal(0, 2.5, n)
    return y.astype(np.int64), good, weak


def test_delong_aucs_match_sklearn_including_ties() -> None:
    y, good, weak = _scores(1)
    good = np.round(good, 1)  # force ties: midranks must match sklearn's tie handling
    d = delong(y, good, weak)
    assert d["auc_a"] == pytest.approx(roc_auc_score(y, good), abs=1e-12)
    assert d["auc_b"] == pytest.approx(roc_auc_score(y, weak), abs=1e-12)
    assert d["delta"] == pytest.approx(d["auc_a"] - d["auc_b"])


def test_delong_detects_a_real_difference_and_not_an_absent_one() -> None:
    y, good, weak = _scores(2)
    assert delong(y, good, weak)["z"] > 3  # clearly better model
    same = delong(y, good, good)
    assert same["delta"] == 0 and same["se"] == 0


def test_holm_matches_hand_computed_adjustment() -> None:
    # sorted p: 0.01, 0.02, 0.03, 0.5 -> 4*0.01=0.04, 3*0.02=0.06, 2*0.03=0.06, 1*0.5=0.5
    assert holm([0.03, 0.01, 0.5, 0.02]) == pytest.approx([0.06, 0.04, 0.5, 0.06])
    assert holm([0.9, 0.8]) == pytest.approx([1.0, 1.0])  # capped at 1 and monotone


def test_bootstrap_p_values() -> None:
    clearly_positive = np.full(999, 0.05)
    assert bootstrap_p(clearly_positive, two_sided=False) == pytest.approx(1 / 1000)
    assert bootstrap_p(clearly_positive, two_sided=True) == pytest.approx(2 / 1000)
    centred = np.linspace(-1, 1, 1001)
    assert bootstrap_p(centred, two_sided=True) == pytest.approx(1.0)


def test_cluster_weights_resample_students_not_rows() -> None:
    clusters = np.array(["a", "a", "b", "c", "c", "c"])
    for w in cluster_weights(clusters, 50, seed=3):
        assert w[0] == w[1] and w[3] == w[4] == w[5]  # a student's rows always move together
        assert w[0] + w[2] + w[3] == 3  # three students drawn with replacement
