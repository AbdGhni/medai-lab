from __future__ import annotations

import json

import numpy as np
import pytest
from pydantic import ValidationError

from medai_ml.report import (
    EvaluationReport,
    MetricSummary,
    OperatingPoint,
    Provenance,
    SeedResult,
    load_report,
    write_report,
)

SHA = "a" * 64
COMMIT = "b" * 40


def _prov(**kw: object) -> Provenance:
    base: dict[str, object] = {
        "commit": COMMIT,
        "dirty": False,
        "config_hash": SHA,
        "dataset_sha256": SHA,
        "python": "3.13",
        "torch": "2.x",
        "numpy": "2.x",
        "scikit_learn": "1.x",
        "platform": "test",
        "device": "cpu",
    }
    base.update(kw)
    return Provenance(**base)  # type: ignore[arg-type]


def _report(prov: Provenance | None = None) -> EvaluationReport:
    seed = SeedResult(
        seed=0,
        best_epoch=1,
        val_auc=0.9,
        test_auc=0.8,
        test_auc_pr=0.7,
        test_brier=0.2,
        test_ece_10=0.1,
        operating_points={
            "S1_youden": OperatingPoint(threshold=0.5, metrics={"tp": 3, "f1": None})
        },
        history=[{"epoch": 1.0, "val_auc": None}],
    )
    return EvaluationReport(
        run_id="run-1",
        model_id="resnet18",
        created_at="2026-10-12T00:00:00Z",
        config={},
        provenance=prov or _prov(),
        dataset={},
        seeds=[seed],
        aggregate={
            "auc": MetricSummary(
                mean=0.8, std_across_seeds=0.0, ci_low=0.7, ci_high=0.9, n_boot_valid=100
            )
        },
    )


@pytest.mark.parametrize("bad", ["", "unknown", "abc", "g" * 40])
def test_missing_or_invalid_commit_is_rejected(bad: str) -> None:
    with pytest.raises(ValidationError):
        _prov(commit=bad)


def test_invalid_hash_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _prov(dataset_sha256="xyz")


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _prov(inconnu=1)


def test_report_contains_disclaimer() -> None:
    assert "Ne pas utiliser pour un diagnostic" in _report().disclaimer


def test_write_is_immutable_and_roundtrips(tmp_path) -> None:  # type: ignore[no-untyped-def]
    rep = _report()
    y = np.array([0, 1, 0, 1])
    probs = [np.array([0.1, 0.9, 0.2, 0.8])]
    run_dir = write_report(rep, tmp_path, y, probs, config_yaml="a: 1\n")
    assert (run_dir / "report.json").exists() and (run_dir / "predictions.npz").exists()
    loaded = load_report(run_dir / "report.json")
    assert loaded == rep
    with pytest.raises(FileExistsError):
        write_report(rep, tmp_path, y, probs)


def test_json_has_no_nan(tmp_path) -> None:  # type: ignore[no-untyped-def]
    run_dir = write_report(_report(), tmp_path, np.array([0, 1]), [np.array([0.2, 0.8])])
    text = (run_dir / "report.json").read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text
    json.loads(text)


def test_nan_metric_is_refused_at_write(tmp_path) -> None:  # type: ignore[no-untyped-def]
    rep = _report()
    rep.seeds[0].operating_points["S1_youden"].metrics["f1"] = float("nan")
    with pytest.raises(ValueError):
        write_report(rep, tmp_path, np.array([0, 1]), [np.array([0.2, 0.8])])
