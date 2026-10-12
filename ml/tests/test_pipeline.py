from __future__ import annotations

import numpy as np
import pytest
import torch

from medai_ml.config import ExperimentConfig
from medai_ml.evaluate import run_experiment
from medai_ml.models import build_model
from medai_ml.report import load_report
from medai_ml.train import predict_probs, resolve_device, train_model


def _cfg(**kw: object) -> ExperimentConfig:
    base: dict[str, object] = {
        "model_id": "simple_cnn",
        "pretrained": False,
        "size": 28,
        "seeds": [0, 1],
        "epochs": 2,
        "batch_size": 32,
        "n_bootstrap": 100,
        "device": "cpu",
    }
    base.update(kw)
    return ExperimentConfig(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize("name", ["simple_cnn", "resnet18", "densenet121", "efficientnet_b0"])
def test_models_output_shape(name: str) -> None:
    m = build_model(name, pretrained=False).eval()
    with torch.no_grad():
        out = m(torch.zeros(2, 3, 64, 64))
    assert out.shape == (2,)


def test_same_seed_gives_identical_predictions(synthetic_bundle) -> None:  # type: ignore[no-untyped-def]
    cfg = _cfg()
    dev = resolve_device("cpu")
    a = train_model(cfg, 3, synthetic_bundle.train, synthetic_bundle.val, dev)
    b = train_model(cfg, 3, synthetic_bundle.train, synthetic_bundle.val, dev)
    np.testing.assert_allclose(a.val_probs, b.val_probs, atol=1e-6, rtol=0)
    assert a.best_epoch == b.best_epoch
    c = train_model(cfg, 4, synthetic_bundle.train, synthetic_bundle.val, dev)
    assert not np.allclose(a.val_probs, c.val_probs, atol=1e-6)


def test_model_learns_on_separable_synthetic_data(synthetic_bundle) -> None:  # type: ignore[no-untyped-def]
    from medai_ml.metrics import auc_roc

    cfg = _cfg(epochs=6, lr=0.003)
    dev = resolve_device("cpu")
    res = train_model(cfg, 0, synthetic_bundle.train, synthetic_bundle.val, dev)
    auc = auc_roc(synthetic_bundle.val.labels, res.val_probs)
    assert auc is not None and auc > 0.9


def test_train_model_has_no_access_to_test_split() -> None:
    import inspect

    params = set(inspect.signature(train_model).parameters)
    assert not any("test" in p for p in params)


def test_predict_probs_range_and_order(synthetic_bundle) -> None:  # type: ignore[no-untyped-def]
    m = build_model("simple_cnn", pretrained=False)
    p = predict_probs(m, synthetic_bundle.test, 16, torch.device("cpu"))
    assert p.shape == (len(synthetic_bundle.test),)
    assert ((p >= 0) & (p <= 1)).all()
    p2 = predict_probs(m, synthetic_bundle.test, 7, torch.device("cpu"))
    np.testing.assert_allclose(p, p2, atol=1e-6)  # indépendant de la taille de lot


def test_run_experiment_writes_valid_report(synthetic_bundle, tmp_path) -> None:  # type: ignore[no-untyped-def]
    cfg = _cfg()
    report, run_dir = run_experiment(
        cfg,
        synthetic_bundle,
        tmp_path / "reports",
        tmp_path / "artifacts",
        include_duplicates=False,
        log=lambda _: None,
    )
    loaded = load_report(run_dir / "report.json")
    assert loaded.run_id == report.run_id
    assert len(loaded.seeds) == 2
    for key in ("auc", "S1_youden/sensitivity", "S2_sens95/sensitivity", "S1_youden/fp", "brier"):
        s = loaded.aggregate[key]
        assert s.n_boot_valid > 0
    auc = loaded.aggregate["auc"]
    assert auc.ci_low is not None and auc.mean is not None and auc.ci_high is not None
    assert auc.ci_low <= auc.mean <= auc.ci_high or abs(auc.mean - auc.ci_low) < 0.1
    # les poids sont archivés avec leur empreinte
    assert all(s.weights_sha256 and len(s.weights_sha256) == 64 for s in loaded.seeds)
    # prédictions rejouables
    with np.load(run_dir / "predictions.npz") as z:
        assert z["probs"].shape == (2, len(synthetic_bundle.test))
    assert loaded.provenance.config_hash == cfg.hash()


def test_thresholds_in_report_come_from_validation(synthetic_bundle, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Les seuils du rapport doivent être reproductibles à partir des seules probabilités de validation."""
    from medai_ml.thresholds import select_thresholds

    cfg = _cfg(seeds=[0])
    report, _ = run_experiment(
        cfg, synthetic_bundle, tmp_path / "r", None, include_duplicates=False, log=lambda _: None
    )
    dev = resolve_device("cpu")
    res = train_model(cfg, 0, synthetic_bundle.train, synthetic_bundle.val, dev)
    expected = select_thresholds(synthetic_bundle.val.labels, res.val_probs, cfg.sensitivity_target)
    got = {k: v.threshold for k, v in report.seeds[0].operating_points.items()}
    assert got == pytest.approx(expected)


def test_smoke_notes_flag_subset(synthetic_bundle, tmp_path) -> None:  # type: ignore[no-untyped-def]
    report, _ = run_experiment(
        _cfg(seeds=[0], train_subset=64),
        synthetic_bundle,
        tmp_path / "r",
        None,
        include_duplicates=False,
        log=lambda _: None,
    )
    assert any("sous-échantillon" in n for n in report.notes)
    assert any("28x28" in n for n in report.notes)
