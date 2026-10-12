from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings
from medai_ml.config import ExperimentConfig
from medai_ml.data import DataBundle, DatasetInfo, Split
from medai_ml.evaluate import run_experiment
from medai_ml.gallery import build_gallery


def _split(n: int, seed: int) -> Split:
    rng = np.random.default_rng(seed)
    labels = (rng.random(n) < 0.5).astype(np.int64)
    labels[0], labels[1] = 0, 1
    base = rng.normal(100, 25, size=(n, 28, 28)) + labels[:, None, None] * 40
    return Split(np.clip(base, 0, 255).astype(np.uint8), labels)


@pytest.fixture(scope="session")
def bundle() -> DataBundle:
    tr, va, te = _split(160, 1), _split(64, 2), _split(64, 3)
    info = DatasetInfo(
        "synthetic", 28, "synthetic", "n/a", "n/a", hashlib.sha256(tr.images.tobytes()).hexdigest()
    )
    return DataBundle(tr, va, te, info)


@pytest.fixture(scope="session")
def workspace(tmp_path_factory: pytest.TempPathFactory, bundle: DataBundle) -> dict[str, Path]:
    root = tmp_path_factory.mktemp("ws")
    cfg = ExperimentConfig(
        model_id="simple_cnn",
        pretrained=False,
        size=28,
        seeds=[0, 1],
        epochs=2,
        batch_size=32,
        n_bootstrap=100,
        device="cpu",
    )
    _, run_dir = run_experiment(
        cfg,
        bundle,
        root / "reports",
        root / "artifacts",
        include_duplicates=False,
        log=lambda _: None,
    )
    build_gallery(bundle, root / "gallery", n_per_class=3)
    return {
        "root": root,
        "reports": root / "reports",
        "artifacts": root / "artifacts",
        "gallery": root / "gallery",
        "run": run_dir,
    }


@pytest.fixture()
def client(workspace: dict[str, Path]) -> TestClient:
    s = Settings(
        reports_dir=workspace["reports"],
        artifacts_dir=workspace["artifacts"],
        gallery_dir=workspace["gallery"],
    )
    return TestClient(create_app(s))


@pytest.fixture()
def empty_client(tmp_path: Path) -> TestClient:
    s = Settings(
        reports_dir=tmp_path / "r", artifacts_dir=tmp_path / "a", gallery_dir=tmp_path / "g"
    )
    return TestClient(create_app(s))


def decode_png(b64: str) -> bytes:
    return base64.b64decode(b64)
