"""Tests nécessitant le réseau (Zenodo). Marqués slow ; exécutés en CI."""

from __future__ import annotations

import pytest

from medai_ml.data import datasheet, load_pneumoniamnist

pytestmark = pytest.mark.slow


def test_real_28_matches_published_counts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import medmnist

    bundle = load_pneumoniamnist(28, tmp_path)
    expected = medmnist.INFO["pneumoniamnist"]["n_samples"]
    assert len(bundle.train) == expected["train"]
    assert len(bundle.val) == expected["val"]
    assert len(bundle.test) == expected["test"]
    assert bundle.train.images.shape[1:] == (28, 28)
    sheet = datasheet(bundle, with_duplicates=False)
    assert len(sheet["sha256"]) == 64


def test_smoke_run_on_real_28(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from medai_ml.config import load_config
    from medai_ml.evaluate import run_experiment

    cfg = load_config("ml/configs/smoke_simple_cnn_28.yaml")
    bundle = load_pneumoniamnist(28, tmp_path)
    report, run_dir = run_experiment(
        cfg, bundle, tmp_path / "reports", None, include_duplicates=False, log=lambda _: None
    )
    assert (run_dir / "report.json").exists()
    assert report.aggregate["auc"].mean is not None
