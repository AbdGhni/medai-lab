from __future__ import annotations

import inspect

import numpy as np
import pytest

from medai_ml import thresholds as T
from medai_ml.metrics import binary_metrics


def _val() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    y[0], y[1] = 0, 1
    s = np.clip(y * 0.35 + rng.random(400) * 0.65, 0, 1)
    return y, s


def test_youden_maximises_j() -> None:
    y, s = _val()
    t = T.youden_threshold(y, s)
    m = binary_metrics(y, s, t)
    j = m["sensitivity"] + m["specificity"] - 1  # type: ignore[operator]
    for other in np.linspace(0, 1, 201):
        mo = binary_metrics(y, s, other)
        assert j >= mo["sensitivity"] + mo["specificity"] - 1 - 1e-9  # type: ignore[operator]


def test_sensitivity_threshold_meets_target_and_is_largest() -> None:
    y, s = _val()
    t = T.sensitivity_threshold(y, s, 0.95)
    assert binary_metrics(y, s, t)["sensitivity"] >= 0.95  # type: ignore[operator]
    higher = s[s > t]
    if higher.size:
        t2 = float(higher.min())
        assert binary_metrics(y, s, t2)["sensitivity"] < 0.95  # type: ignore[operator]


def test_single_class_validation_is_rejected() -> None:
    with pytest.raises(ValueError):
        T.youden_threshold(np.zeros(5), np.linspace(0, 1, 5))


def test_bad_target_is_rejected() -> None:
    y, s = _val()
    with pytest.raises(ValueError):
        T.sensitivity_threshold(y, s, 0.0)


def test_functions_cannot_receive_test_data() -> None:
    """Garde-fou structurel : seules des données de validation entrent dans le choix des seuils."""
    for fn in (T.youden_threshold, T.sensitivity_threshold, T.select_thresholds):
        names = set(inspect.signature(fn).parameters)
        assert not any("test" in n for n in names)
        assert {"y_val", "score_val"} <= names


def test_select_thresholds_keys() -> None:
    y, s = _val()
    assert set(T.select_thresholds(y, s)) == {"S1_youden", "S2_sens95"}
