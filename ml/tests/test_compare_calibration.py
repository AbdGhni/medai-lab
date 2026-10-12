from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from medai_ml.calibration import (
    apply_temperature,
    calibration_analysis,
    fit_temperature,
    nll,
    to_logit,
)
from medai_ml.compare import (
    Predictions,
    delong_test,
    holm,
    mcnemar_exact,
    paired_bootstrap_auc,
)


def _scores(n: int = 300, signal_a: float = 1.5, signal_b: float = 0.3, seed: int = 0):  # type: ignore[no-untyped-def]
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < 0.6).astype(np.int64)
    y[:2] = [0, 1]
    shared = rng.normal(size=n)
    a = 1 / (1 + np.exp(-(signal_a * (y - 0.5) * 2 + shared)))
    b = 1 / (1 + np.exp(-(signal_b * (y - 0.5) * 2 + shared)))
    return y, a, b


def test_holm_matches_hand_computation() -> None:
    assert holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert holm([0.5]) == [0.5]
    assert all(0 <= p <= 1 for p in holm([0.9, 0.95, 0.99]))


def test_holm_is_monotone_and_not_below_raw() -> None:
    raw = [0.001, 0.2, 0.01, 0.04]
    adj = holm(raw)
    assert all(a >= r for a, r in zip(adj, raw, strict=True))


def test_delong_auc_matches_sklearn_and_detects_difference() -> None:
    y, a, b = _scores()
    auc_a, auc_b, diff, p = delong_test(y, a, b)
    assert auc_a == pytest.approx(roc_auc_score(y, a))
    assert auc_b == pytest.approx(roc_auc_score(y, b))
    assert diff == pytest.approx(auc_a - auc_b)
    assert p < 0.01


def test_delong_identical_scores_gives_p_one() -> None:
    y, a, _ = _scores()
    assert delong_test(y, a, a.copy())[3] == 1.0


def test_delong_agrees_with_paired_bootstrap() -> None:
    y, a, b = _scores(seed=3)
    r = paired_bootstrap_auc(y, a[None, :], b[None, :], n_boot=400)
    _, _, d, p = delong_test(y, a, b)
    assert r.diff == pytest.approx(d)
    assert (p < 0.05) == (r.p_bootstrap < 0.05)


def test_paired_bootstrap_interval_contains_estimate_and_is_symmetric_in_sign() -> None:
    y, a, b = _scores(seed=1)
    ab = paired_bootstrap_auc(y, a[None, :], b[None, :], n_boot=300)
    ba = paired_bootstrap_auc(y, b[None, :], a[None, :], n_boot=300)
    assert ab.ci_low <= ab.diff <= ab.ci_high
    assert ab.diff == pytest.approx(-ba.diff)


def test_adjusted_interval_is_wider_with_more_comparisons() -> None:
    y, a, b = _scores(seed=2)
    one = paired_bootstrap_auc(y, a[None, :], b[None, :], n_boot=400, n_comparisons=1)
    three = paired_bootstrap_auc(y, a[None, :], b[None, :], n_boot=400, n_comparisons=3)
    assert three.ci_low_adjusted <= one.ci_low_adjusted
    assert three.ci_high_adjusted >= one.ci_high_adjusted


def test_paired_bootstrap_same_model_no_difference() -> None:
    y, a, _ = _scores()
    r = paired_bootstrap_auc(y, a[None, :], a[None, :].copy(), n_boot=200)
    assert r.diff == 0 and r.ci_low == 0 and r.ci_high == 0
    assert r.p_bootstrap == 1.0


def test_paired_bootstrap_rejects_mismatched_images() -> None:
    y, a, b = _scores()
    with pytest.raises(ValueError):
        paired_bootstrap_auc(y, a[None, :], b[None, :-1])


def test_mcnemar_exact_known_values() -> None:
    y = np.array([1] * 10 + [0] * 10)
    a = y.copy()
    b = y.copy()
    b[:8] = 1 - b[:8]  # B se trompe 8 fois où A a juste
    r = mcnemar_exact(a, b, y)
    assert r["a_only_correct"] == 8 and r["b_only_correct"] == 0
    assert r["p"] == pytest.approx(2 * 0.5**8)
    same = mcnemar_exact(a, a, y)
    assert same["p"] == 1.0


def test_temperature_recovers_known_overconfidence() -> None:
    rng = np.random.default_rng(0)
    n = 20000
    z = rng.normal(size=n) * 2
    y = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(np.int64)  # étiquettes cohérentes avec z
    p_over = 1 / (1 + np.exp(-3 * z))  # modèle sûr de lui : vraie T = 3
    t = fit_temperature(y, p_over)
    assert t == pytest.approx(3.0, rel=0.1)
    assert nll(y, apply_temperature(p_over, t)) < nll(y, p_over)


def test_temperature_one_is_identity_and_rejects_nonpositive() -> None:
    p = np.array([0.1, 0.5, 0.9])
    assert apply_temperature(p, 1.0) == pytest.approx(p, abs=1e-6)
    with pytest.raises(ValueError):
        apply_temperature(p, 0.0)
    assert np.all(np.isfinite(to_logit(np.array([0.0, 1.0]))))


def test_calibration_analysis_requires_validation_predictions() -> None:
    y, a, _ = _scores()
    pred = Predictions(y_true=y, probs=a[None, :], seeds=np.array([0]))
    with pytest.raises(ValueError, match="validation"):
        calibration_analysis(pred)


def test_calibration_analysis_improves_nll_on_overconfident_model() -> None:
    rng = np.random.default_rng(5)

    def draw(n: int):  # type: ignore[no-untyped-def]
        z = rng.normal(size=n) * 2
        y = (rng.random(n) < 1 / (1 + np.exp(-z))).astype(np.int64)
        return y, 1 / (1 + np.exp(-3 * z))

    yv, pv = draw(3000)
    yt, pt = draw(3000)
    pred = Predictions(
        y_true=yt, probs=pt[None, :], seeds=np.array([0]), y_val=yv, val_probs=pv[None, :]
    )
    out = calibration_analysis(pred)
    m = out["mean_over_seeds"]
    assert m["nll_after"] < m["nll_before"]
    assert m["ece10_after"] <= m["ece10_before"]
    assert out["per_seed"][0]["temperature"] > 1.5
