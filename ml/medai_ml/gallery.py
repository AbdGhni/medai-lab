"""Galerie de démonstration : images du jeu de test PneumoniaMNIST (CC BY 4.0).

Seules ces images sont utilisables sur la démo publique. Aucune image fournie par un visiteur
n'est acceptée.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .data import DataBundle

ATTRIBUTION = (
    "Images issues de PneumoniaMNIST (MedMNIST v2), licence CC BY 4.0. "
    "Source d'origine : Kermany et al., Cell 2018. Redistribution MedMNIST : Yang et al., "
    "Scientific Data 2023. Images redimensionnées et recadrées par MedMNIST."
)


def build_gallery(
    bundle: DataBundle, out_dir: Path, n_per_class: int = 12, seed: int = 0
) -> dict[str, Any]:
    """Écrit des PNG (taille native du bundle) et manifest.json. Sélection aléatoire fixée."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    labels = bundle.test.labels
    chosen: list[int] = []
    for cls in (0, 1):
        idx = np.flatnonzero(labels == cls)
        chosen += sorted(
            int(i) for i in rng.choice(idx, size=min(n_per_class, idx.size), replace=False)
        )
    items: list[dict[str, Any]] = []
    for k, i in enumerate(chosen):
        image_id = f"t{k:03d}"
        Image.fromarray(bundle.test.images[i]).save(out_dir / f"{image_id}.png")
        items.append({"id": image_id, "test_index": i, "label": int(labels[i])})
    manifest: dict[str, Any] = {
        "dataset": bundle.info.name,
        "size": bundle.info.size,
        "license": bundle.info.license,
        "attribution": ATTRIBUTION,
        "label_names": {"0": "normal", "1": "pneumonie"},
        "selection": f"tirage aléatoire de {n_per_class} images par classe dans le test, seed {seed}",
        "dataset_sha256": bundle.info.sha256,
        "items": items,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest
