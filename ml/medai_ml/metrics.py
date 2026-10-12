"""Métriques de classification binaire et intervalles de confiance par bootstrap.

La classe positive est 1 (pneumonie). Une prédiction est positive si score >= seuil.
Toute métrique indéfinie (division par zéro, une seule classe) vaut None, jamais NaN.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.stats import rankdata

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def _div(num: float, den: float) -> float | None:
    return None if den == 0 else float(num / den)


def auc_roc(y_true: NDArray[np.generic], y_score: NDArray[np.generic]) -> float | None:
    """AUC ROC par la statistique de Mann-Whitney (rangs moyens pour les ex aequo)."""
    y = np.asarray(y_true).astype(np.int64)
    s = np.asarray(y_score, dtype=np.float64)
    n_pos = int(y.sum())
    n_neg = int(y.size - n_pos)
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = rankdata(s, method="average")
    return float((ranks[y == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def average_precision(y_true: NDArray[np.generic], y_score: NDArray[np.generic]) -> float | None:
    """AUC précision-rappel (précision moyenne, scikit-learn)."""
    from sklearn.metrics import average_precision_score

    y = np.asarray(y_true).astype(np.int64)
    if y.sum() == 0:
        return None
    return float(average_precision_score(y, np.asarray(y_score, dtype=np.float64)))


def brier(y_true: NDArray[np.generic], prob: NDArray[np.generic]) -> float:
    y = np.asarray(y_true, dtype=np.float64)
    p = np.asarray(prob, dtype=np.float64)
    return float(np.mean((p - y) ** 2))


def ece(
    y_true: NDArray[np.generic], prob: NDArray[np.generic], n_bins: int = 10, adaptive: bool = False
) -> float:
    """Erreur de calibration attendue sur la probabilité de la classe positive.

    Largeur égale (défaut) ou effectif égal (adaptive=True). Somme pondérée de |fréquence
    observée - probabilité moyenne| par intervalle.
    """
    y = np.asarray(y_true, dtype=np.float64)
    p = np.asarray(prob, dtype=np.float64)
    n = p.size
    if adaptive:
        order = np.argsort(p, kind="stable")
        groups = np.array_split(order, n_bins)
    else:
        edges = np.linspace(0.0, 1.0, n_bins + 1)
        which = np.clip(np.digitize(p, edges[1:-1], right=False), 0, n_bins - 1)
        groups = [np.flatnonzero(which == b) for b in range(n_bins)]
    total = 0.0
    for g in groups:
        if g.size:
            total += g.size / n * abs(y[g].mean() - p[g].mean())
    return float(total)


def confusion(
    y_true: NDArray[np.generic], y_score: NDArray[np.generic], threshold: float
) -> dict[str, int]:
    y = np.asarray(y_true).astype(np.int64)
    pred = (np.asarray(y_score, dtype=np.float64) >= threshold).astype(np.int64)
    return {
        "tp": int(((pred == 1) & (y == 1)).sum()),
        "fp": int(((pred == 1) & (y == 0)).sum()),
        "tn": int(((pred == 0) & (y == 0)).sum()),
        "fn": int(((pred == 0) & (y == 1)).sum()),
    }


def metrics_from_confusion(c: dict[str, int]) -> dict[str, float | None]:
    tp, fp, tn, fn = c["tp"], c["fp"], c["tn"], c["fn"]
    sens = _div(tp, tp + fn)
    spec = _div(tn, tn + fp)
    prec = _div(tp, tp + fp)
    f1 = _div(2 * tp, 2 * tp + fp + fn)
    bal = None if sens is None or spec is None else (sens + spec) / 2
    return {
        "sensitivity": sens,
        "specificity": spec,
        "precision": prec,
        "f1": f1,
        "balanced_accuracy": bal,
        "accuracy": _div(tp + tn, tp + fp + tn + fn),
    }


def binary_metrics(
    y_true: NDArray[np.generic], y_score: NDArray[np.generic], threshold: float
) -> dict[str, float | int | None]:
    """Métriques à un seuil donné, plus les effectifs de la matrice de confusion."""
    c = confusion(y_true, y_score, threshold)
    out: dict[str, float | int | None] = dict(metrics_from_confusion(c))
    out.update(c)
    return out


# ---------------------------------------------------------------- bootstrap

MetricFn = Callable[[NDArray[np.int64], NDArray[np.float64]], float | None]


@dataclass(frozen=True)
class Interval:
    estimate: float | None
    low: float | None
    high: float | None
    n_valid: int  # nombre de réplicats bootstrap où la métrique est définie


def stratified_indices(y: NDArray[np.generic], rng: np.random.Generator) -> NDArray[np.int64]:
    """Rééchantillonnage avec remise, stratifié par classe (les effectifs par classe sont conservés)."""
    yy = np.asarray(y).astype(np.int64)
    pos = np.flatnonzero(yy == 1)
    neg = np.flatnonzero(yy == 0)
    parts = []
    if pos.size:
        parts.append(rng.choice(pos, size=pos.size, replace=True))
    if neg.size:
        parts.append(rng.choice(neg, size=neg.size, replace=True))
    return np.concatenate(parts).astype(np.int64)


def bootstrap_per_seed(
    y_true: NDArray[np.generic],
    scores_by_seed: Sequence[NDArray[np.generic]],
    metric_fns: dict[str, Callable[[int, NDArray[np.int64], NDArray[np.float64]], float | None]],
    n_boot: int = 2000,
    seed: int = 12345,
    alpha: float = 0.05,
) -> dict[str, Interval]:
    """Intervalle percentile pour la moyenne sur les seeds de chaque métrique.

    Chaque réplicat rééchantillonne les images de test une fois, calcule la métrique de chaque
    seed sur ces mêmes images, puis en fait la moyenne (protocole, section 8). Chaque fonction
    reçoit l'indice de la seed pour pouvoir utiliser le seuil propre à cette seed.
    """
    y = np.asarray(y_true).astype(np.int64)
    scores = [np.asarray(s, dtype=np.float64) for s in scores_by_seed]
    rng = np.random.default_rng(seed)
    point = {
        k: _mean_valid([fn(i, y, s) for i, s in enumerate(scores)]) for k, fn in metric_fns.items()
    }
    samples: dict[str, list[float]] = {k: [] for k in metric_fns}
    for _ in range(n_boot):
        idx = stratified_indices(y, rng)
        yb = y[idx]
        for k, fn in metric_fns.items():
            m = _mean_valid([fn(i, yb, s[idx]) for i, s in enumerate(scores)])
            if m is not None:
                samples[k].append(m)
    return {k: _interval(point[k], samples[k], alpha) for k in metric_fns}


def _mean_valid(values: Sequence[float | None]) -> float | None:
    """Moyenne ; None si au moins une valeur est indéfinie (on ne moyenne pas des seeds partielles)."""
    if any(v is None for v in values):
        return None
    return float(np.mean([v for v in values if v is not None]))


def _interval(point: float | None, samples: list[float], alpha: float) -> Interval:
    if not samples:
        return Interval(point, None, None, 0)
    lo, hi = np.percentile(samples, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return Interval(point, float(lo), float(hi), len(samples))


def mean_std(values: Sequence[float | None]) -> tuple[float | None, float | None]:
    """Moyenne et écart-type (ddof=1) entre seeds ; None si une valeur est indéfinie."""
    if not values or any(v is None for v in values):
        return None, None
    arr = np.array([v for v in values if v is not None], dtype=np.float64)
    std = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
    return float(arr.mean()), std
