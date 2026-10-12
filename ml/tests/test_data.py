from __future__ import annotations

import numpy as np
import pytest

from medai_ml.data import Split, class_counts, datasheet, duplicate_report

from .conftest import make_split


def test_split_validates_shapes_and_labels() -> None:
    with pytest.raises(ValueError):
        Split(images=np.zeros((3, 4), dtype=np.uint8), labels=np.zeros(3, dtype=np.int64))
    with pytest.raises(ValueError):
        Split(images=np.zeros((3, 4, 4), dtype=np.uint8), labels=np.zeros(2, dtype=np.int64))
    with pytest.raises(ValueError):
        Split(images=np.zeros((3, 4, 4), dtype=np.uint8), labels=np.array([0, 1, 2]))


def test_class_counts() -> None:
    s = Split(np.zeros((4, 2, 2), dtype=np.uint8), np.array([1, 0, 0, 1]))
    assert class_counts(s) == {"n": 4, "n_pneumonia": 2, "n_normal": 2, "prevalence": 0.5}


def test_duplicate_detection_finds_copies_and_ignores_unrelated() -> None:
    rng = np.random.default_rng(0)
    # images texturées pour que le pHash soit discriminant
    a = Split(rng.integers(0, 255, (6, 64, 64)).astype(np.uint8), np.array([0, 1] * 3))
    b_imgs = rng.integers(0, 255, (6, 64, 64)).astype(np.uint8)
    b_imgs[2] = a.images[4]  # une copie exacte
    b = Split(b_imgs, np.array([0, 1] * 3))
    rep = duplicate_report(a, b)
    assert rep["confirmed_duplicate_pairs"] >= 1
    assert rep["images_a_confirmed"] >= 1
    assert rep["images_b_confirmed"] >= 1
    unrelated = duplicate_report(
        a, Split(rng.integers(0, 255, (6, 64, 64)).astype(np.uint8), np.array([0, 1] * 3))
    )
    assert unrelated["confirmed_duplicate_pairs"] == 0


def test_similar_but_different_images_are_not_confirmed() -> None:
    """Candidats pHash mais pixels différents : non comptés comme doublons."""
    rng = np.random.default_rng(1)
    base = rng.integers(60, 200, (64, 64)).astype(np.float64)
    noisy = np.clip(base + rng.normal(0, 60, base.shape), 0, 255)
    a = Split(base.astype(np.uint8)[None], np.array([0]))
    b = Split(noisy.astype(np.uint8)[None], np.array([0]))
    rep = duplicate_report(a, b, max_distance=32, min_corr=0.99)
    assert rep["candidate_pairs"] == 1 and rep["confirmed_duplicate_pairs"] == 0


def test_datasheet_is_computed_from_data(synthetic_bundle) -> None:  # type: ignore[no-untyped-def]
    sheet = datasheet(synthetic_bundle, with_duplicates=False)
    assert sheet["splits"]["train"]["n"] == len(synthetic_bundle.train)
    assert sheet["splits"]["test"]["n"] == len(synthetic_bundle.test)
    assert "duplicates" not in sheet


def test_make_split_has_both_classes() -> None:
    s = make_split(10, 0)
    assert set(np.unique(s.labels)) == {0, 1}
