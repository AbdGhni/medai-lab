from __future__ import annotations

import pytest
from pydantic import ValidationError

from medai_ml.config import ExperimentConfig, load_config


def test_defaults_are_valid() -> None:
    c = ExperimentConfig(model_id="resnet18")
    assert c.seeds == [0, 1, 2, 3, 4] and c.size == 224


@pytest.mark.parametrize(
    "bad",
    [
        {"model_id": "vgg"},
        {"model_id": "resnet18", "size": 100},
        {"model_id": "resnet18", "seeds": []},
        {"model_id": "resnet18", "seeds": [1, 1]},
        {"model_id": "resnet18", "lr": 0},
        {"model_id": "resnet18", "epochs": 0},
        {"model_id": "resnet18", "inconnu": 1},
    ],
)
def test_invalid_config_is_rejected(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ExperimentConfig(**bad)  # type: ignore[arg-type]


def test_hash_is_stable_and_sensitive() -> None:
    a = ExperimentConfig(model_id="resnet18")
    b = ExperimentConfig(model_id="resnet18")
    c = ExperimentConfig(model_id="resnet18", lr=2e-3)
    assert a.hash() == b.hash() != c.hash()
    assert len(a.hash()) == 64


def test_repo_configs_are_valid() -> None:
    from pathlib import Path

    for p in sorted((Path(__file__).parents[1] / "configs").glob("*.yaml")):
        load_config(p)
