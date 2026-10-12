"""Explicabilité par Grad-CAM. Les cartes sont des indices de localisation, pas des preuves.

Le test de sanité par randomisation des poids (protocole, section 10) est implémenté plus bas ;
tant qu'il n'a pas été exécuté pour un modèle, les réponses indiquent `sanity_checked=False`.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from numpy.typing import NDArray
from torch import nn


def target_layer(model_id: str, model: nn.Module) -> nn.Module:
    """Dernière couche convolutive utilisée par Grad-CAM pour chaque architecture."""
    m: Any = model
    layer: nn.Module
    if model_id == "simple_cnn":
        layer = m.features[-2]
    elif model_id == "resnet18":
        layer = m.backbone.layer4[-1]
    elif model_id == "densenet121":
        layer = m.backbone.features
    elif model_id == "efficientnet_b0":
        layer = m.backbone.blocks[-1]
    else:
        raise ValueError(f"Modèle inconnu : {model_id}")
    return layer


def gradcam(
    model: nn.Module,
    model_id: str,
    x: torch.Tensor,
    plus_plus: bool = False,
) -> NDArray[np.float32]:
    """Carte Grad-CAM (B, H, W) dans [0, 1] pour la classe positive (pneumonie).

    `x` : (B, 3, H, W) déjà prétraité. Le modèle est mis en mode évaluation.
    """
    from pytorch_grad_cam import GradCAM, GradCAMPlusPlus
    from pytorch_grad_cam.utils.model_targets import BinaryClassifierOutputTarget

    model.eval()
    cls = GradCAMPlusPlus if plus_plus else GradCAM
    layer = target_layer(model_id, model)
    with cls(model=model, target_layers=[layer]) as cam:
        targets = [BinaryClassifierOutputTarget(1) for _ in range(x.shape[0])]
        maps = cam(input_tensor=x, targets=targets)
    return np.asarray(maps, dtype=np.float32)


# ----------------------------------------------------------------------------------------
# Test de sanité par randomisation en cascade des poids (Adebayo et al., 2018)

#: Critère fixé avant toute expérience (protocole v1.2) : si, poids entièrement randomisés,
#: la corrélation de rang moyenne avec la carte du modèle entraîné reste >= ce seuil, la
#: méthode est déclarée non fiable pour ce modèle.
SANITY_RANK_CORR_MAX = 0.3
SANITY_FRACTIONS = (0.25, 0.5, 0.75, 1.0)


def _randomizable(model: nn.Module) -> list[nn.Module]:
    return [m for m in model.modules() if isinstance(m, nn.Conv2d | nn.Linear)]


def randomize_top_layers(model: nn.Module, fraction: float, seed: int = 0) -> nn.Module:
    """Copie du modèle dont la fraction `fraction` des couches Conv/Linear les plus proches de
    la sortie est réinitialisée au hasard (en cascade, de la dernière couche à la première)."""
    import copy

    clone = copy.deepcopy(model)
    layers = _randomizable(clone)
    n = int(np.ceil(fraction * len(layers)))
    gen_state = torch.random.get_rng_state()
    torch.manual_seed(seed)
    try:
        for layer in reversed(layers):
            if n <= 0:
                break
            layer.reset_parameters()  # type: ignore[operator]
            n -= 1
    finally:
        torch.random.set_rng_state(gen_state)
    return clone


def rank_correlation(a: NDArray[np.float32], b: NDArray[np.float32]) -> float | None:
    """Corrélation de rang de Spearman entre deux cartes ; None si l'une est constante."""
    from scipy.stats import spearmanr

    fa, fb = a.ravel().astype(np.float64), b.ravel().astype(np.float64)
    if np.ptp(fa) == 0 or np.ptp(fb) == 0:
        return None
    return float(spearmanr(fa, fb).statistic)


def ssim(a: NDArray[np.float32], b: NDArray[np.float32], win: int = 7) -> float:
    """SSIM moyen (fenêtre uniforme) entre deux cartes dans [0, 1]."""
    from scipy.ndimage import uniform_filter

    x, y = a.astype(np.float64), b.astype(np.float64)
    c1, c2 = 0.01**2, 0.03**2
    mx, my = uniform_filter(x, win), uniform_filter(y, win)
    vx = uniform_filter(x * x, win) - mx * mx
    vy = uniform_filter(y * y, win) - my * my
    cxy = uniform_filter(x * y, win) - mx * my
    s = ((2 * mx * my + c1) * (2 * cxy + c2)) / ((mx * mx + my * my + c1) * (vx + vy + c2))
    return float(s.mean())


def gradcam_sanity(
    model: nn.Module, model_id: str, x: torch.Tensor, seed: int = 0
) -> dict[str, object]:
    """Compare les cartes Grad-CAM du modèle entraîné à celles du modèle randomisé en cascade.

    `x` : (B, 3, H, W) prétraité. Renvoie, par fraction randomisée, la corrélation de rang et
    le SSIM moyens sur les images, et un verdict fondé sur SANITY_RANK_CORR_MAX.
    """
    base = gradcam(model, model_id, x)
    rows: list[dict[str, object]] = []
    for frac in SANITY_FRACTIONS:
        rnd = randomize_top_layers(model, frac, seed)
        maps = gradcam(rnd, model_id, x)
        corrs = [rank_correlation(base[i], maps[i]) for i in range(x.shape[0])]
        defined = [c for c in corrs if c is not None]
        rows.append(
            {
                "fraction_randomized": frac,
                "rank_corr_mean": float(np.mean(defined)) if defined else None,
                "n_undefined": len(corrs) - len(defined),
                "ssim_mean": float(np.mean([ssim(base[i], maps[i]) for i in range(x.shape[0])])),
            }
        )
    full = rows[-1]["rank_corr_mean"]
    # Carte constante après randomisation = méthode clairement sensible aux poids.
    sensitive = full is None or (isinstance(full, float) and full < SANITY_RANK_CORR_MAX)
    return {
        "model_id": model_id,
        "n_images": int(x.shape[0]),
        "rows": rows,
        "threshold_rank_corr": SANITY_RANK_CORR_MAX,
        "passes": bool(sensitive),
        "note": "Test qualitatif de Adebayo et al. (2018) ; ne démontre pas la validité clinique des cartes.",
    }
