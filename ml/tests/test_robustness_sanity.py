from __future__ import annotations

import json

import numpy as np
import pytest
import torch

from medai_ml.analysis import write_analysis
from medai_ml.data import Split
from medai_ml.explain import (
    SANITY_RANK_CORR_MAX,
    gradcam_sanity,
    randomize_top_layers,
    rank_correlation,
    ssim,
)
from medai_ml.models import build_model
from medai_ml.robustness import LEVELS, perturb_images, robustness_analysis
from medai_ml.train import preprocess_uint8, resolve_device


def _imgs(n: int = 6, size: int = 32) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(30, 220, size=(n, size, size), dtype=np.uint8)


def test_levels_match_protocol_table() -> None:
    assert set(LEVELS) == {
        "gaussian_noise",
        "gaussian_blur",
        "brightness",
        "contrast",
        "jpeg",
        "rotation",
    }
    assert all(len(v) == 5 for v in LEVELS.values())


@pytest.mark.parametrize("kind", list(LEVELS))
def test_perturbations_keep_shape_dtype_and_are_deterministic(kind: str) -> None:
    x = _imgs()
    a = perturb_images(x, kind, LEVELS[kind][-1], seed=3)
    b = perturb_images(x, kind, LEVELS[kind][-1], seed=3)
    assert a.shape == x.shape and a.dtype == np.uint8
    assert np.array_equal(a, b)
    assert not np.array_equal(a, x)


def test_perturbations_do_not_mutate_input_and_severity_is_monotone() -> None:
    x = _imgs()
    before = x.copy()
    errs = [
        np.abs(perturb_images(x, "gaussian_noise", lv).astype(float) - x).mean()
        for lv in LEVELS["gaussian_noise"]
    ]
    assert np.array_equal(x, before)
    assert errs == sorted(errs)
    blur = [
        np.abs(perturb_images(x, "gaussian_blur", lv).astype(float) - x).mean()
        for lv in LEVELS["gaussian_blur"]
    ]
    assert blur == sorted(blur)


def test_brightness_and_contrast_semantics() -> None:
    x = _imgs()
    assert perturb_images(x, "brightness", 1.4).mean() > x.mean()
    assert perturb_images(x, "brightness", 0.6).mean() < x.mean()
    assert perturb_images(x, "contrast", 0.4).std() < x.std()


def test_unknown_perturbation_rejected() -> None:
    with pytest.raises(ValueError):
        perturb_images(_imgs(), "inconnue", 1.0)


def test_robustness_analysis_structure() -> None:
    torch.manual_seed(0)
    model = build_model("simple_cnn", pretrained=False)
    rng = np.random.default_rng(1)
    y = (rng.random(40) < 0.5).astype(np.int64)
    y[:2] = [0, 1]
    test = Split(images=_imgs(40), labels=y)
    thr = [{"S1_youden": 0.5, "S2_sens95": 0.4}]
    out = robustness_analysis(
        [model],
        thr,
        test,
        resolve_device("cpu"),
        batch_size=20,
        n_boot=20,
        kinds=["brightness", "jpeg"],
        log=lambda _: None,
    )
    assert set(out["perturbations"]) == {"brightness", "jpeg"}
    assert len(out["perturbations"]["jpeg"]) == 5
    m = out["clean"]
    assert {"auc", "S1_youden/sensitivity", "S2_sens95/specificity"} <= set(m)
    json.dumps(out, allow_nan=False)  # sérialisable sans NaN


def test_randomize_changes_weights_and_leaves_original_untouched() -> None:
    torch.manual_seed(0)
    model = build_model("simple_cnn", pretrained=False)
    ref = {k: v.clone() for k, v in model.state_dict().items()}
    rnd = randomize_top_layers(model, 1.0, seed=1)
    assert all(torch.equal(ref[k], v) for k, v in model.state_dict().items())
    assert not torch.equal(rnd.state_dict()["head.weight"], ref["head.weight"])
    half = randomize_top_layers(model, 0.25, seed=1)
    # seule la couche la plus proche de la sortie est modifiée
    assert not torch.equal(half.state_dict()["head.weight"], ref["head.weight"])
    assert torch.equal(half.state_dict()["features.0.weight"], ref["features.0.weight"])


def test_rank_correlation_and_ssim_basics() -> None:
    rng = np.random.default_rng(0)
    a = rng.random((16, 16)).astype(np.float32)
    assert rank_correlation(a, a) == pytest.approx(1.0)
    assert rank_correlation(a, np.zeros_like(a)) is None
    assert ssim(a, a) == pytest.approx(1.0)
    assert ssim(a, rng.random((16, 16)).astype(np.float32)) < 0.5


def test_gradcam_sanity_runs_and_reports_verdict() -> None:
    torch.manual_seed(0)
    model = build_model("simple_cnn", pretrained=False)
    x = torch.stack([preprocess_uint8(im) for im in _imgs(3)])
    out = gradcam_sanity(model, "simple_cnn", x)
    assert [r["fraction_randomized"] for r in out["rows"]] == [0.25, 0.5, 0.75, 1.0]  # type: ignore[attr-defined]
    assert out["threshold_rank_corr"] == SANITY_RANK_CORR_MAX
    assert out["passes"] is None or isinstance(out["passes"], bool)
    json.dumps(out, allow_nan=False)


def test_write_analysis_never_overwrites_and_requires_report(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(FileNotFoundError):
        write_analysis(tmp_path, "run-x", "robustness", {"a": 1})
    run = tmp_path / "run-x"
    run.mkdir()
    (run / "report.json").write_text("{}")
    p = write_analysis(tmp_path, "run-x", "robustness", {"a": 1})
    doc = json.loads(p.read_text())
    assert doc["run_id"] == "run-x" and doc["a"] == 1 and "disclaimer" in doc
    with pytest.raises(FileExistsError):
        write_analysis(tmp_path, "run-x", "robustness", {"a": 2})
    with pytest.raises(ValueError):
        write_analysis(tmp_path, "run-x", "autre", {})


def test_sanity_excludes_constant_base_maps_and_flags_unevaluable(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import medai_ml.explain as ex

    calls = {"n": 0}

    def fake_gradcam(model, model_id, x, plus_plus=False):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        b = x.shape[0]
        rng = np.random.default_rng(calls["n"])
        maps = rng.random((b, 8, 8)).astype(np.float32)
        if calls["n"] == 1:  # carte du modèle entraîné : toutes constantes
            maps[:] = 0.0
        return maps

    monkeypatch.setattr(ex, "gradcam", fake_gradcam)
    model = build_model("simple_cnn", pretrained=False)
    out = ex.gradcam_sanity(model, "simple_cnn", torch.zeros(6, 3, 32, 32))
    assert out["passes"] is None
    assert out["rows"][0]["n_excluded_base_constant"] == 6  # type: ignore[index]


def test_sanity_randomized_constant_counts_as_zero_correlation(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import medai_ml.explain as ex

    calls = {"n": 0}

    def fake_gradcam(model, model_id, x, plus_plus=False):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        b = x.shape[0]
        if calls["n"] == 1:
            return np.random.default_rng(0).random((b, 8, 8)).astype(np.float32)
        return np.zeros((b, 8, 8), dtype=np.float32)  # modèle randomisé : cartes nulles

    monkeypatch.setattr(ex, "gradcam", fake_gradcam)
    model = build_model("simple_cnn", pretrained=False)
    out = ex.gradcam_sanity(model, "simple_cnn", torch.zeros(6, 3, 32, 32))
    last = out["rows"][-1]  # type: ignore[index]
    assert last["rank_corr_mean"] == 0.0 and last["n_randomized_constant"] == 6
    assert out["passes"] is True
