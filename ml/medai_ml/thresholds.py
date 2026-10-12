"""Choix des seuils de décision S1 (Youden) et S2 (sensibilité >= cible) sur la VALIDATION.

Ces fonctions ne reçoivent que des données de validation : elles ne peuvent pas dépendre du test.
Une prédiction est positive si score >= seuil.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import roc_curve


def _curve(
    y_val: NDArray[np.generic], score_val: NDArray[np.generic]
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    y = np.asarray(y_val).astype(np.int64)
    if np.min(y) == np.max(y):
        raise ValueError("La validation doit contenir les deux classes pour choisir un seuil.")
    fpr, tpr, thr = roc_curve(y, np.asarray(score_val, dtype=np.float64), drop_intermediate=False)
    finite = np.isfinite(thr)
    return fpr[finite], tpr[finite], thr[finite]


def youden_threshold(y_val: NDArray[np.generic], score_val: NDArray[np.generic]) -> float:
    """Seuil maximisant sensibilité + spécificité - 1 ; en cas d'égalité, le plus grand seuil."""
    fpr, tpr, thr = _curve(y_val, score_val)
    j = tpr - fpr
    best = np.flatnonzero(j >= np.max(j) - 1e-12)
    return float(np.max(thr[best]))


def sensitivity_threshold(
    y_val: NDArray[np.generic], score_val: NDArray[np.generic], target: float = 0.95
) -> float:
    """Plus grand seuil dont la sensibilité de validation est >= target."""
    if not 0.0 < target <= 1.0:
        raise ValueError("target doit appartenir à ]0, 1].")
    _, tpr, thr = _curve(y_val, score_val)
    ok = np.flatnonzero(tpr >= target - 1e-12)
    return float(np.max(thr[ok]))


def select_thresholds(
    y_val: NDArray[np.generic], score_val: NDArray[np.generic], sensitivity_target: float = 0.95
) -> dict[str, float]:
    return {
        "S1_youden": youden_threshold(y_val, score_val),
        "S2_sens95": sensitivity_threshold(y_val, score_val, sensitivity_target),
    }
