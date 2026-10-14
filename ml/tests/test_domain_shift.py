from __future__ import annotations

import numpy as np
import pytest
import torch

from medai_ml.analysis import write_analysis
from medai_ml.domain_shift import domain_shift_analysis, make_targets, pneumonia_index
from medai_ml.models import build_model
from medai_ml.train import resolve_device

NAMES = [
    "atelectasis",
    "cardiomegaly",
    "effusion",
    "infiltration",
    "mass",
    "nodule",
    "Pneumonia",
    "pneumothorax",
]


def _labels() -> np.ndarray:
    lab = np.zeros((10, len(NAMES)), dtype=np.int64)
    lab[0, 6] = 1  # pneumonie seule
    lab[1, 6] = 1
    lab[1, 3] = 1  # pneumonie + infiltrat
    lab[2, 3] = 1  # autre pathologie
    lab[3, 0] = 1  # autre pathologie
    return lab  # images 4 à 9 : aucune anomalie


def test_pneumonia_index_found_by_name_case_insensitive() -> None:
    assert pneumonia_index(NAMES) == 6


@pytest.mark.parametrize("names", [["a", "b"], ["pneumonia", "Pneumonia"]])
def test_pneumonia_index_missing_or_ambiguous(names: list[str]) -> None:
    with pytest.raises(ValueError):
        pneumonia_index(names)


def test_make_targets_definitions() -> None:
    t = make_targets(_labels(), NAMES)
    idx_all, y_all = t["pneumonia_vs_all"]
    assert len(idx_all) == 10 and y_all.sum() == 2
    idx_nf, y_nf = t["pneumonia_vs_no_finding"]
    # positifs (0, 1) + négatifs sans aucune anomalie (4..9) ; les images 2 et 3 sont exclues
    assert sorted(idx_nf.tolist()) == [0, 1, 4, 5, 6, 7, 8, 9]
    assert int(y_nf.sum()) == 2 and len(y_nf) == 8


def test_make_targets_shape_mismatch() -> None:
    with pytest.raises(ValueError):
        make_targets(np.zeros((3, 2), dtype=np.int64), NAMES)


def test_domain_shift_analysis_structure_and_determinism() -> None:
    torch.manual_seed(0)
    rng = np.random.default_rng(0)
    n = 80
    lab = np.zeros((n, len(NAMES)), dtype=np.int64)
    lab[: n // 4, 6] = 1
    lab[n // 4 : n // 2, 3] = 1
    images = rng.integers(0, 255, size=(n, 28, 28), dtype=np.uint8)
    models = [build_model("simple_cnn", pretrained=False) for _ in range(2)]
    thr = [{"S1_youden": 0.5, "S2_sens95": 0.3}] * 2
    dev = resolve_device("cpu")
    a = domain_shift_analysis(models, thr, images, lab, NAMES, dev, n_boot=20, log=lambda _: None)
    b = domain_shift_analysis(models, thr, images, lab, NAMES, dev, n_boot=20, log=lambda _: None)
    assert a == b
    assert a["positive_label_index"] == 6 and a["n_seeds"] == 2
    t = a["targets"]["pneumonia_vs_all"]
    assert t["n_positive"] == n // 4 and abs(t["prevalence"] - 0.25) < 1e-9
    m = t["metrics"]
    for key in ("auc", "S1_youden/sensitivity", "S2_sens95/specificity", "S1_youden/flagged_rate"):
        assert key in m
    assert 0.0 <= m["auc"]["mean"] <= 1.0
    assert a["targets"]["pneumonia_vs_no_finding"]["n_images"] == n // 4 + n // 2


def test_write_analysis_accepts_domain_shift(tmp_path) -> None:  # type: ignore[no-untyped-def]
    run = tmp_path / "r1"
    run.mkdir()
    (run / "report.json").write_text("{}")
    p = write_analysis(tmp_path, "r1", "domain_shift", {"x": 1})
    assert p.name == "domain_shift.json"
