"""Configuration d'expérience validée (Pydantic) et hash stable."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

ModelName = Literal["simple_cnn", "resnet18", "densenet121", "efficientnet_b0"]


class ExperimentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: ModelName
    pretrained: bool = True
    dataset: Literal["pneumoniamnist"] = "pneumoniamnist"
    size: Literal[28, 64, 128, 224] = 224
    seeds: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4], min_length=1)
    epochs: int = Field(default=15, ge=1)
    batch_size: int = Field(default=64, ge=1)
    lr: float = Field(default=1e-3, gt=0)
    weight_decay: float = Field(default=1e-4, ge=0)
    patience: int = Field(default=4, ge=1)
    num_workers: int = Field(default=0, ge=0)
    n_bootstrap: int = Field(default=2000, ge=100)
    sensitivity_target: float = Field(default=0.95, gt=0, le=1)
    train_subset: int | None = Field(
        default=None, ge=8
    )  # sous-échantillon, tests de fumée seulement
    device: Literal["auto", "cpu", "cuda"] = "auto"

    @field_validator("seeds")
    @classmethod
    def _unique_seeds(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("Les seeds doivent être distinctes.")
        return v

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def load_config(path: str | Path) -> ExperimentConfig:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    if not isinstance(raw, dict):
        raise ValueError(f"Configuration invalide : {path} doit contenir un dictionnaire YAML.")
    return ExperimentConfig(**raw)
