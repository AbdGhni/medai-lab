"""Calibration : temperature scaling ajusté sur la validation, évalué sur le test.

La température n'est jamais ajustée sur le test. Les probabilités sont stockées en float32 :
elles sont bornées à [1e-7, 1 - 1e-7] avant passage en logit.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize_scalar

from .compare import Predictions
from .metrics import brier, ece

F64 = NDArray[np.float64]
_EPS = 1e-7


def to_logit(p: F64) -> F64:
    q = np.clip(np.asarray(p, dtype=np.float64), _EPS, 1 - _EPS)
    out: F64 = np.log(q / (1 - q))
    return out


def apply_temperature(p: F64, temperature: float) -> F64:
    if temperature <= 0:
        raise ValueError("La température doit être strictement positive.")
    out: F64 = 1.0 / (1.0 + np.exp(-to_logit(p) / temperature))
    return out


def nll(y: NDArray[np.generic], p: F64) -> float:
    yy = np.asarray(y, dtype=np.float64)
    q = np.clip(p, _EPS, 1 - _EPS)
    return float(-np.mean(yy * np.log(q) + (1 - yy) * np.log(1 - q)))


def fit_temperature(y_val: NDArray[np.generic], p_val: F64) -> float:
    """Température T > 0 minimisant la log-vraisemblance négative de la validation."""
    z = to_logit(p_val)
    y = np.asarray(y_val, dtype=np.float64)

    def loss(log_t: float) -> float:
        q = 1.0 / (1.0 + np.exp(-z / np.exp(log_t)))
        return nll(y, q)

    res = minimize_scalar(loss, bounds=(np.log(0.05), np.log(20.0)), method="bounded")
    return float(np.exp(res.x))


def reliability_curve(
    y: NDArray[np.generic], p: F64, n_bins: int = 10
) -> list[dict[str, float | int]]:
    """Points du diagramme de fiabilité (intervalles de largeur égale, vides ignorés)."""
    yy = np.asarray(y, dtype=np.float64)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    which = np.clip(np.digitize(p, edges[1:-1]), 0, n_bins - 1)
    out: list[dict[str, float | int]] = []
    for b in range(n_bins):
        g = np.flatnonzero(which == b)
        if g.size:
            out.append(
                {
                    "bin": b,
                    "n": int(g.size),
                    "mean_prob": float(p[g].mean()),
                    "observed_freq": float(yy[g].mean()),
                }
            )
    return out


def calibration_analysis(pred: Predictions) -> dict[str, Any]:
    """Avant/après temperature scaling pour chaque seed, puis moyenne sur les seeds."""
    if pred.y_val is None or pred.val_probs is None:
        raise ValueError(
            "Ce rapport ne contient pas les prédictions de validation : calibration impossible."
        )
    per_seed: list[dict[str, float | int]] = []
    for i, seed in enumerate(pred.seeds):
        t = fit_temperature(pred.y_val, pred.val_probs[i])
        p_raw = pred.probs[i]
        p_cal = apply_temperature(p_raw, t)
        per_seed.append(
            {
                "seed": int(seed),
                "temperature": t,
                "temperature_at_bound": bool(t < 0.0501 or t > 19.99),
                "ece10_before": ece(pred.y_true, p_raw, 10),
                "ece10_after": ece(pred.y_true, p_cal, 10),
                "ece_adaptive_before": ece(pred.y_true, p_raw, 10, adaptive=True),
                "ece_adaptive_after": ece(pred.y_true, p_cal, 10, adaptive=True),
                "brier_before": brier(pred.y_true, p_raw),
                "brier_after": brier(pred.y_true, p_cal),
                "nll_before": nll(pred.y_true, p_raw),
                "nll_after": nll(pred.y_true, p_cal),
            }
        )
    keys = [k for k in per_seed[0] if k not in ("seed", "temperature_at_bound")]
    mean = {k: float(np.mean([r[k] for r in per_seed])) for k in keys}
    return {
        "per_seed": per_seed,
        "mean_over_seeds": mean,
        "reliability_before_seed0": reliability_curve(pred.y_true, pred.probs[0]),
        "reliability_after_seed0": reliability_curve(
            pred.y_true, apply_temperature(pred.probs[0], float(per_seed[0]["temperature"]))
        ),
    }
