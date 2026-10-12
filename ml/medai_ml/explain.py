"""Explicabilité par Grad-CAM. Les cartes sont des indices de localisation, pas des preuves.

Le test de sanité par randomisation des poids (protocole, section 10) est prévu en phase 4 :
tant qu'il n'a pas été exécuté pour un modèle, les réponses l'indiquent (`sanity_checked=False`).
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
