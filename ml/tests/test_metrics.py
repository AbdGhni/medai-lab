from __future__ import annotations

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sklearn.metrics import average_precision_score, roc_auc_score

from medai_ml import metrics as M


@settings(max_examples=60, deadline=None)
@given(
    n=st.integers(min_value=4, max_value=200),
    seed=st.integers(min_value=0, max_value=10_000),
    levels=st.integers(min_value=2, max_value=50),
)
def test_auc_matches_sklearn_with_ties(n: int, seed: int, levels: int) -> None:
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    y[0], y[1] = 0, 1
    s = rng.integers(0, levels, n).astype(float) / levels  # beaucoup d'ex aequo
    assert M.auc_roc(y, s) == pytest.approx(roc_auc_score(y, s), abs=1e-12)


def test_auc_single_class_is_none() -> None:
    assert M.auc_roc(np.zeros(5), np.linspace(0, 1, 5)) is None
    assert M.auc_roc(np.ones(5), np.linspace(0, 1, 5)) is None


def test_auc_constant_scores_is_half() -> None:
    assert M.auc_roc(np.array([0, 1, 0, 1]), np.full(4, 0.3)) == pytest.approx(0.5)


def test_average_precision_matches_sklearn() -> None:
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 300)
    s = rng.random(300)
    assert M.average_precision(y, s) == pytest.approx(average_precision_score(y, s))
    assert M.average_precision(np.zeros(4), np.ones(4)) is None


def test_confusion_and_metrics_known_case() -> None:
    y = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    s = np.array([0.9, 0.8, 0.7, 0.2, 0.6, 0.1, 0.1, 0.2, 0.3, 0.4])
    m = M.binary_metrics(y, s, 0.5)
    assert (m["tp"], m["fp"], m["tn"], m["fn"]) == (3, 1, 5, 1)
    assert m["sensitivity"] == pytest.approx(3 / 4)
    assert m["specificity"] == pytest.approx(5 / 6)
    assert m["precision"] == pytest.approx(3 / 4)
    assert m["f1"] == pytest.approx(2 * 3 / (2 * 3 + 1 + 1))
    assert m["balanced_accuracy"] == pytest.approx((3 / 4 + 5 / 6) / 2)
    assert m["accuracy"] == pytest.approx(8 / 10)


def test_threshold_is_inclusive() -> None:
    m = M.binary_metrics(np.array([1, 0]), np.array([0.5, 0.5]), 0.5)
    assert (m["tp"], m["fp"]) == (1, 1)


def test_undefined_metrics_are_none_not_nan() -> None:
    # aucune prédiction positive : précision indéfinie
    m = M.binary_metrics(np.array([1, 0, 1]), np.array([0.1, 0.1, 0.1]), 0.9)
    assert m["precision"] is None
    assert m["f1"] == 0.0
    # un seul type de classe : spécificité indéfinie
    m2 = M.binary_metrics(np.array([1, 1]), np.array([0.9, 0.2]), 0.5)
    assert m2["specificity"] is None and m2["balanced_accuracy"] is None


def test_brier_and_ece_perfect_and_worst() -> None:
    y = np.array([0, 1, 0, 1])
    assert M.brier(y, y.astype(float)) == 0.0
    assert M.ece(y, y.astype(float)) == 0.0
    assert M.ece(y, 1.0 - y) == pytest.approx(1.0)


def test_ece_calibrated_synthetic_is_small() -> None:
    rng = np.random.default_rng(1)
    p = rng.random(20000)
    y = (rng.random(20000) < p).astype(int)  # calibré par construction
    assert M.ece(y, p, 10) < 0.02
    assert M.ece(y, p, 10, adaptive=True) < 0.02


def test_ece_detects_overconfidence() -> None:
    rng = np.random.default_rng(2)
    p = rng.random(20000)
    y = (rng.random(20000) < p).astype(int)
    over = np.clip((p - 0.5) * 3 + 0.5, 0, 1)  # trop confiant
    assert M.ece(y, over, 10) > 0.1


def test_stratified_bootstrap_keeps_class_counts() -> None:
    y = np.array([0] * 30 + [1] * 7)
    idx = M.stratified_indices(y, np.random.default_rng(0))
    assert int(y[idx].sum()) == 7 and idx.size == 37


def _fns() -> dict[str, object]:
    return {"auc": lambda i, y, s: M.auc_roc(y, s)}


def test_bootstrap_is_deterministic_and_contains_estimate() -> None:
    rng = np.random.default_rng(3)
    y = rng.integers(0, 2, 200)
    y[0], y[1] = 0, 1
    scores = [np.clip(y * 0.3 + rng.random(200) * 0.7, 0, 1) for _ in range(3)]
    a = M.bootstrap_per_seed(y, scores, _fns(), n_boot=300, seed=7)  # type: ignore[arg-type]
    b = M.bootstrap_per_seed(y, scores, _fns(), n_boot=300, seed=7)  # type: ignore[arg-type]
    assert a == b
    iv = a["auc"]
    assert iv.low is not None and iv.high is not None and iv.estimate is not None
    assert iv.low <= iv.estimate <= iv.high
    assert iv.n_valid == 300


def test_bootstrap_interval_narrows_with_more_data() -> None:
    def width(n: int) -> float:
        rng = np.random.default_rng(5)
        y = rng.integers(0, 2, n)
        y[0], y[1] = 0, 1
        s = np.clip(y * 0.3 + rng.random(n) * 0.7, 0, 1)
        iv = M.bootstrap_per_seed(y, [s], _fns(), n_boot=300, seed=1)["auc"]  # type: ignore[arg-type]
        assert iv.low is not None and iv.high is not None
        return iv.high - iv.low

    assert width(2000) < width(100)


def test_mean_std() -> None:
    assert M.mean_std([1.0, 3.0]) == (2.0, pytest.approx(2**0.5))
    assert M.mean_std([1.0, None]) == (None, None)
    assert M.mean_std([2.0]) == (2.0, 0.0)
