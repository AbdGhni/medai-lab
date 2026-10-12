"""Comparaisons statistiques entre modèles, à partir des prédictions archivées (aucun ré-entraînement).

Primaire : différence d'AUC par bootstrap apparié (mêmes images rééchantillonnées pour les deux
modèles, moyenne sur les seeds à chaque réplicat), p-valeur bootstrap bilatérale, correction de
Holm. Compléments : DeLong sur les probabilités moyennées sur les seeds, McNemar exact.
Toute p-valeur est rendue avec l'estimation de l'effet et son intervalle.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from .metrics import auc_roc, stratified_indices

F64 = NDArray[np.float64]
I64 = NDArray[np.int64]


@dataclass(frozen=True)
class Predictions:
    y_true: I64
    probs: F64  # (n_seeds, n_test)
    seeds: I64
    y_val: I64 | None = None
    val_probs: F64 | None = None


def load_predictions(run_dir: Path) -> Predictions:
    with np.load(Path(run_dir) / "predictions.npz") as z:
        has_val = "val_probs" in z.files and "y_val" in z.files
        return Predictions(
            y_true=z["y_true"].astype(np.int64),
            probs=z["probs"].astype(np.float64),
            seeds=z["seeds"].astype(np.int64),
            y_val=z["y_val"].astype(np.int64) if has_val else None,
            val_probs=z["val_probs"].astype(np.float64) if has_val else None,
        )


@dataclass(frozen=True)
class PairedAucResult:
    auc_a: float
    auc_b: float
    diff: float  # A - B
    ci_low: float
    ci_high: float
    ci_low_adjusted: float  # niveau 1 - alpha/m (Bonferroni, conservateur)
    ci_high_adjusted: float
    p_bootstrap: float
    n_boot: int


def _mean_auc(y: I64, probs: F64) -> float:
    vals = [auc_roc(y, s) for s in probs]
    if any(v is None for v in vals):
        raise ValueError("AUC indéfinie : une seule classe présente.")
    return float(np.mean([v for v in vals if v is not None]))


def paired_bootstrap_auc(
    y: I64,
    probs_a: F64,
    probs_b: F64,
    n_boot: int = 2000,
    seed: int = 20260,
    alpha: float = 0.05,
    n_comparisons: int = 1,
) -> PairedAucResult:
    """Différence d'AUC (A - B) ; chaque réplicat applique les mêmes indices aux deux modèles."""
    if probs_a.shape[1] != y.size or probs_b.shape[1] != y.size:
        raise ValueError("Les prédictions doivent porter sur les mêmes images de test.")
    rng = np.random.default_rng(seed)
    diffs = np.empty(n_boot, dtype=np.float64)
    for r in range(n_boot):
        idx = stratified_indices(y, rng)
        yb = y[idx]
        diffs[r] = _mean_auc(yb, probs_a[:, idx]) - _mean_auc(yb, probs_b[:, idx])
    est_a, est_b = _mean_auc(y, probs_a), _mean_auc(y, probs_b)
    lo, hi = np.percentile(diffs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    a_adj = alpha / max(n_comparisons, 1)
    lo_adj, hi_adj = np.percentile(diffs, [100 * a_adj / 2, 100 * (1 - a_adj / 2)])
    # p bootstrap bilatérale, avec correction +1 pour ne jamais annoncer p = 0
    p_le = (np.sum(diffs <= 0) + 1) / (n_boot + 1)
    p_ge = (np.sum(diffs >= 0) + 1) / (n_boot + 1)
    p = float(min(1.0, 2 * min(p_le, p_ge)))
    return PairedAucResult(
        auc_a=est_a,
        auc_b=est_b,
        diff=est_a - est_b,
        ci_low=float(lo),
        ci_high=float(hi),
        ci_low_adjusted=float(lo_adj),
        ci_high_adjusted=float(hi_adj),
        p_bootstrap=p,
        n_boot=n_boot,
    )


def holm(p_values: Sequence[float]) -> list[float]:
    """p-valeurs ajustées de Holm-Bonferroni (contrôle du risque global de première espèce)."""
    m = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.empty(m, dtype=np.float64)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, (m - rank) * p_values[i])
        adjusted[i] = min(1.0, running)
    return [float(v) for v in adjusted]


# ---------------------------------------------------------------- DeLong


def _midrank(x: F64) -> F64:
    out: F64 = stats.rankdata(x, method="average").astype(np.float64)
    return out


def _delong_components(y: I64, scores: F64) -> tuple[float, F64, F64]:
    pos, neg = scores[y == 1], scores[y == 0]
    m, n = pos.size, neg.size
    tx = _midrank(pos)
    ty = _midrank(neg)
    tz = _midrank(np.concatenate([pos, neg]))
    auc = float((tz[:m].sum() - m * (m + 1) / 2) / (m * n))
    v01 = (tz[:m] - tx) / n
    v10 = 1.0 - (tz[m:] - ty) / m
    return auc, v01, v10


def delong_test(y: I64, scores_a: F64, scores_b: F64) -> tuple[float, float, float, float]:
    """Test de DeLong (corrélé) : renvoie (AUC A, AUC B, différence, p bilatérale)."""
    auc_a, a01, a10 = _delong_components(y, scores_a)
    auc_b, b01, b10 = _delong_components(y, scores_b)
    m, n = a01.size, a10.size
    s01 = np.cov(np.vstack([a01, b01]))
    s10 = np.cov(np.vstack([a10, b10]))
    s = s01 / m + s10 / n
    var = s[0, 0] + s[1, 1] - 2 * s[0, 1]
    diff = auc_a - auc_b
    if var <= 1e-18:
        return auc_a, auc_b, diff, 1.0 if abs(diff) < 1e-12 else 0.0
    z = diff / np.sqrt(var)
    return auc_a, auc_b, diff, float(2 * stats.norm.sf(abs(z)))


def mcnemar_exact(pred_a: I64, pred_b: I64, y: I64) -> dict[str, float | int]:
    """McNemar exact sur l'exactitude des deux classifieurs (b : A juste B faux ; c : l'inverse)."""
    ok_a, ok_b = pred_a == y, pred_b == y
    b = int(np.sum(ok_a & ~ok_b))
    c = int(np.sum(~ok_a & ok_b))
    p = 1.0 if b + c == 0 else float(stats.binomtest(b, b + c, 0.5).pvalue)
    return {"a_only_correct": b, "b_only_correct": c, "p": p}
