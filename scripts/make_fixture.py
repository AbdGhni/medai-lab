"""Fabrique un petit espace de test SYNTHÉTIQUE (rapport, poids, galerie) pour les tests de bout en bout.

Les images sont du bruit synthétique : les chiffres obtenus n'ont aucune valeur scientifique.
Usage : python scripts/make_fixture.py <dossier_de_sortie>
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

from medai_ml.config import ExperimentConfig
from medai_ml.data import DataBundle, DatasetInfo, Split
from medai_ml.evaluate import run_experiment
from medai_ml.gallery import build_gallery


def _split(n: int, seed: int) -> Split:
    rng = np.random.default_rng(seed)
    labels = (rng.random(n) < 0.5).astype(np.int64)
    labels[0], labels[1] = 0, 1
    imgs = rng.normal(100, 25, size=(n, 28, 28)) + labels[:, None, None] * 40
    return Split(np.clip(imgs, 0, 255).astype(np.uint8), labels)


def main(out: Path) -> None:
    tr, va, te = _split(160, 1), _split(64, 2), _split(64, 3)
    info = DatasetInfo(
        "synthetic", 28, "synthetic", "n/a", "n/a", hashlib.sha256(tr.images.tobytes()).hexdigest()
    )
    bundle = DataBundle(tr, va, te, info)
    cfg = ExperimentConfig(
        model_id="simple_cnn",
        pretrained=False,
        size=28,
        seeds=[0, 1],
        epochs=2,
        batch_size=32,
        n_bootstrap=200,
        device="cpu",
    )
    run_experiment(
        cfg, bundle, out / "reports", out / "artifacts", include_duplicates=False, log=print
    )
    build_gallery(bundle, out / "gallery", n_per_class=3)
    print(f"Fixture synthétique écrite dans {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
