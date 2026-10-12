"""Robustesse aux perturbations d'image, appliquées au test uniquement (protocole, section 9).

Les seuils S1/S2 sont ceux fixés sur la validation : ils ne sont pas recalculés sous perturbation.
Chaque perturbation est déterministe (graine fixe) et reproductible.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from typing import Any

import numpy as np
import torch
from numpy.typing import NDArray
from PIL import Image
from scipy import ndimage
from torch import nn

from .data import Split
from .metrics import auc_roc, binary_metrics, bootstrap_per_seed
from .train import predict_probs

U8 = NDArray[np.uint8]

LEVELS: dict[str, list[float]] = {
    "gaussian_noise": [0.02, 0.05, 0.10, 0.20, 0.30],
    "gaussian_blur": [0.5, 1.0, 1.5, 2.0, 3.0],
    "brightness": [0.6, 0.8, 1.2, 1.4, 1.6],
    "contrast": [0.4, 0.6, 0.8, 1.2, 1.5],
    "jpeg": [90, 70, 50, 30, 10],
    "rotation": [5, 10, 15, 20, 30],
}


def _to_u8(x: NDArray[np.float64]) -> U8:
    return np.clip(np.rint(x * 255.0), 0, 255).astype(np.uint8)


def _noise(img: U8, level: float, rng: np.random.Generator) -> U8:
    x = img.astype(np.float64) / 255.0
    return _to_u8(x + rng.normal(0.0, level, size=x.shape))


def _blur(img: U8, level: float, rng: np.random.Generator) -> U8:
    return _to_u8(ndimage.gaussian_filter(img.astype(np.float64) / 255.0, sigma=level))


def _brightness(img: U8, level: float, rng: np.random.Generator) -> U8:
    return _to_u8(img.astype(np.float64) / 255.0 * level)


def _contrast(img: U8, level: float, rng: np.random.Generator) -> U8:
    x = img.astype(np.float64) / 255.0
    return _to_u8((x - x.mean()) * level + x.mean())


def _jpeg(img: U8, level: float, rng: np.random.Generator) -> U8:
    buf = io.BytesIO()
    Image.fromarray(img, mode="L").save(buf, format="JPEG", quality=int(level))
    buf.seek(0)
    return np.array(Image.open(buf).convert("L"), dtype=np.uint8)


def _rotation(img: U8, level: float, rng: np.random.Generator) -> U8:
    out = ndimage.rotate(
        img.astype(np.float64), angle=level, reshape=False, order=1, mode="constant", cval=0.0
    )
    return _to_u8(out / 255.0)


_FNS: dict[str, Callable[[U8, float, np.random.Generator], U8]] = {
    "gaussian_noise": _noise,
    "gaussian_blur": _blur,
    "brightness": _brightness,
    "contrast": _contrast,
    "jpeg": _jpeg,
    "rotation": _rotation,
}


def perturb_images(images: U8, kind: str, level: float, seed: int = 0) -> U8:
    """Applique une perturbation à (N, H, W) uint8 ; renvoie un nouveau tableau uint8."""
    if kind not in _FNS:
        raise ValueError(f"Perturbation inconnue : {kind}")
    rng = np.random.default_rng(seed)
    fn = _FNS[kind]
    return np.stack([fn(im, level, rng) for im in images]).astype(np.uint8)


def robustness_analysis(
    models: list[nn.Module],
    thresholds: list[dict[str, float]],
    test: Split,
    device: torch.device,
    batch_size: int = 64,
    n_boot: int = 500,
    kinds: list[str] | None = None,
    levels: dict[str, list[float]] | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """AUC, sensibilité et spécificité (S1, S2) par perturbation et sévérité, avec intervalles.

    `models[i]` et `thresholds[i]` correspondent à la même seed. Le niveau "clean" est le test
    non perturbé, recalculé ici pour servir de référence dans la même exécution.
    """
    lv = levels or LEVELS
    ops = list(thresholds[0])
    y = test.labels

    def evaluate(split: Split) -> dict[str, Any]:
        probs = [predict_probs(m, split, batch_size, device) for m in models]
        fns: dict[str, Callable[[int, NDArray[np.int64], NDArray[np.float64]], float | None]] = {
            "auc": lambda i, yy, s: auc_roc(yy, s)
        }
        for op in ops:
            for met in ("sensitivity", "specificity"):
                fns[f"{op}/{met}"] = _make_fn(thresholds, op, met)
        iv = bootstrap_per_seed(y, probs, fns, n_boot=n_boot, seed=777)
        return {k: {"mean": v.estimate, "ci_low": v.low, "ci_high": v.high} for k, v in iv.items()}

    out: dict[str, Any] = {"n_boot": n_boot, "clean": evaluate(test), "perturbations": {}}
    for kind in kinds or list(lv):
        rows = []
        for level in lv[kind]:
            log(f"[robustesse] {kind} {level}")
            pert = Split(images=perturb_images(test.images, kind, level), labels=y)
            rows.append({"level": level, "metrics": evaluate(pert)})
        out["perturbations"][kind] = rows
    return out


def _make_fn(
    thresholds: list[dict[str, float]], op: str, metric: str
) -> Callable[[int, NDArray[np.int64], NDArray[np.float64]], float | None]:
    def fn(i: int, yy: NDArray[np.int64], s: NDArray[np.float64]) -> float | None:
        v = binary_metrics(yy, s, thresholds[i][op])[metric]
        return None if v is None else float(v)

    return fn
