"""Schéma des rapports d'évaluation et écriture immuable.

Un rapport sans provenance complète est rejeté à la construction. L'écriture refuse d'écraser
un rapport existant : une nouvelle exécution crée un nouveau rapport.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import DISCLAIMER, PROTOCOL_VERSION

SCHEMA_VERSION = "1"
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commit: str
    dirty: bool
    config_hash: str
    dataset_sha256: str
    python: str
    torch: str
    numpy: str
    scikit_learn: str
    platform: str
    device: str
    gpu_name: str | None = None
    cpu_count: int | None = None

    @field_validator("commit")
    @classmethod
    def _commit(cls, v: str) -> str:
        if not _COMMIT_RE.match(v):
            raise ValueError("commit git invalide ou absent : provenance incomplète.")
        return v

    @field_validator("config_hash", "dataset_sha256")
    @classmethod
    def _sha(cls, v: str) -> str:
        if not _SHA256_RE.match(v):
            raise ValueError("empreinte SHA-256 invalide.")
        return v


class MetricSummary(BaseModel):
    """Moyenne sur les seeds, écart-type entre seeds, intervalle bootstrap 95 % sur le test."""

    model_config = ConfigDict(extra="forbid")

    mean: float | None
    std_across_seeds: float | None
    ci_low: float | None
    ci_high: float | None
    n_boot_valid: int


class OperatingPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threshold: float
    metrics: dict[str, float | int | None]


class SeedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int
    best_epoch: int
    val_auc: float | None
    test_auc: float | None
    test_auc_pr: float | None
    test_brier: float
    test_ece_10: float
    operating_points: dict[str, OperatingPoint]
    history: list[dict[str, float | None]]
    weights_sha256: str | None = None


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    run_id: str
    protocol_version: str = PROTOCOL_VERSION
    disclaimer: str = DISCLAIMER
    model_id: str
    created_at: str
    config: dict[str, Any]
    provenance: Provenance
    dataset: dict[str, Any]
    seeds: list[SeedResult] = Field(min_length=1)
    aggregate: dict[str, MetricSummary]
    notes: list[str] = Field(default_factory=list)


def write_report(
    report: EvaluationReport,
    reports_dir: Path,
    y_test: NDArray[np.int64],
    test_probs_by_seed: list[NDArray[np.float64]],
    config_yaml: str | None = None,
) -> Path:
    """Écrit reports/<run_id>/{report.json, predictions.npz, config.yaml}. N'écrase jamais."""
    run_dir = Path(reports_dir) / report.run_id
    run_dir.mkdir(parents=True, exist_ok=False)  # FileExistsError si le rapport existe déjà
    payload = json.dumps(report.model_dump(mode="json"), indent=2, allow_nan=False)
    with open(run_dir / "report.json", "x", encoding="utf-8") as f:
        f.write(payload + "\n")
    np.savez_compressed(
        run_dir / "predictions.npz",
        y_true=y_test.astype(np.int8),
        seeds=np.array([s.seed for s in report.seeds], dtype=np.int64),
        probs=np.stack(test_probs_by_seed).astype(np.float32),
    )
    if config_yaml is not None:
        with open(run_dir / "config.yaml", "x", encoding="utf-8") as f:
            f.write(config_yaml)
    return run_dir


def load_report(path: Path) -> EvaluationReport:
    """Charge et valide un rapport ; lève ValidationError si le schéma n'est pas respecté."""
    with open(path, encoding="utf-8") as f:
        return EvaluationReport.model_validate(json.load(f))
