from __future__ import annotations

import hashlib

import numpy as np
import pytest

from medai_ml.data import DataBundle, DatasetInfo, Split


def make_split(n: int, seed: int, size: int = 28, pos_rate: float = 0.5) -> Split:
    """Images synthétiques : la classe positive est un peu plus lumineuse (apprenable)."""
    rng = np.random.default_rng(seed)
    labels = (rng.random(n) < pos_rate).astype(np.int64)
    # garantir les deux classes
    labels[0], labels[1] = 0, 1
    base = rng.normal(100, 25, size=(n, size, size))
    base += labels[:, None, None] * 40
    return Split(images=np.clip(base, 0, 255).astype(np.uint8), labels=labels)


@pytest.fixture(scope="session")
def synthetic_bundle() -> DataBundle:
    train, val, test = make_split(160, 1), make_split(64, 2), make_split(64, 3)
    sha = hashlib.sha256(train.images.tobytes()).hexdigest()
    info = DatasetInfo(
        name="synthetic",
        size=28,
        license="synthetic",
        source_url="n/a",
        md5_expected="n/a",
        sha256=sha,
    )
    return DataBundle(train=train, val=val, test=test, info=info)
