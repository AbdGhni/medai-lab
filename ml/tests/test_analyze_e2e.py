from __future__ import annotations

import json
from pathlib import Path

import pytest

from medai_ml import analyze
from medai_ml.config import ExperimentConfig
from medai_ml.evaluate import run_experiment


def _cfg(epochs: int) -> ExperimentConfig:
    return ExperimentConfig(
        model_id="simple_cnn",
        pretrained=False,
        size=28,
        seeds=[0, 1],
        epochs=epochs,
        batch_size=32,
        n_bootstrap=100,
        device="cpu",
    )


@pytest.fixture(scope="module")
def runs(synthetic_bundle, tmp_path_factory):  # type: ignore[no-untyped-def]
    base = tmp_path_factory.mktemp("e2e")
    reports, artifacts = base / "reports", base / "artifacts"
    ids = []
    for ep in (3, 1):
        rep, _ = run_experiment(
            _cfg(ep),
            synthetic_bundle,
            reports,
            artifacts,
            include_duplicates=False,
            log=lambda _: None,
        )
        ids.append(rep.run_id)
    return reports, artifacts, ids


def _load(p: Path) -> dict:  # type: ignore[type-arg]
    return json.loads(p.read_text(encoding="utf-8"))


def test_compare_writes_consistent_comparison(runs) -> None:  # type: ignore[no-untyped-def]
    reports, _, (base, other) = runs
    path = analyze.compare_runs(reports, base, [other], n_boot=100)
    doc = _load(path)
    row = doc["comparisons"][0]
    assert path.parent.name == "analyses" and path.parent.parent.name == base
    assert row["ci95"][0] <= row["auc_diff_model_minus_baseline"] <= row["ci95"][1]
    assert row["p_holm"] >= row["p_bootstrap"]
    assert row["wording"] in {
        "différence établie (après correction de Holm)",
        "pas de différence démontrée",
    }
    assert {"auc_diff", "p"} <= set(row["delong_on_seed_mean"])
    assert doc["n_comparisons"] == 1
    with pytest.raises(FileExistsError):  # une analyse n'est jamais écrasée
        analyze.compare_runs(reports, base, [other], n_boot=100)


def test_calibrate_uses_validation_predictions(runs) -> None:  # type: ignore[no-untyped-def]
    reports, _, (base, _) = runs
    doc = _load(analyze.calibrate_run(reports, base))
    assert len(doc["per_seed"]) == 2
    assert all(r["temperature"] > 0 for r in doc["per_seed"])
    assert "mean_over_seeds" in doc


def test_robustness_and_sanity_check_weights(runs, synthetic_bundle, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    reports, artifacts, (base, _) = runs
    monkeypatch.setattr(analyze, "_bundle_for", lambda rep, root: synthetic_bundle)
    monkeypatch.setattr(
        analyze,
        "robustness_analysis",
        lambda *a, **k: __import__("medai_ml.robustness", fromlist=["x"]).robustness_analysis(
            *a, **{**k, "kinds": ["brightness"], "n_boot": 10, "log": lambda _: None}
        ),
    )
    rob = _load(analyze.robustness_run(reports, artifacts, base, n_boot=10, device_choice="cpu"))
    assert set(rob["perturbations"]) == {"brightness"} and rob["n_seeds"] == 2
    san = _load(analyze.sanity_run(reports, artifacts, base, n_per_class=2))
    assert len(san["per_seed"]) == 2 and isinstance(san["passes_all_seeds"], bool)


def test_tampered_weights_are_rejected(runs, synthetic_bundle, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    reports, artifacts, (_, other) = runs
    monkeypatch.setattr(analyze, "_bundle_for", lambda rep, root: synthetic_bundle)
    w = artifacts / other / "seed0.pt"
    data = bytearray(w.read_bytes())
    data[-5] ^= 0xFF
    w.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="Empreinte"):
        analyze.sanity_run(reports, artifacts, other, n_per_class=2)
