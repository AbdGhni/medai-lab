"""Schémas de réponse. Toute réponse JSON porte l'avertissement de recherche."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from medai_ml import DISCLAIMER


class Base(BaseModel):
    disclaimer: str = DISCLAIMER


class Health(Base):
    status: str
    version: str
    n_reports: int
    n_invalid_reports: int
    n_gallery_images: int


class MetricInterval(BaseModel):
    mean: float | None
    ci_low: float | None
    ci_high: float | None


class EvaluationSummary(BaseModel):
    run_id: str
    model_id: str
    created_at: str
    n_seeds: int
    size: int
    auc: MetricInterval | None
    # Signaux de fiabilité : un rapport non propre ne doit pas servir de résultat de référence.
    is_reference: bool = Field(description="Vrai si 224x224, sans sous-échantillon, dépôt propre.")
    dirty: bool
    train_subset: int | None
    commit: str


class EvaluationList(Base):
    items: list[EvaluationSummary]


class ModelEntry(BaseModel):
    model_id: str
    n_runs: int
    latest_run_id: str


class ModelList(Base):
    items: list[ModelEntry]


class EvaluationDetail(Base):
    report: dict[str, Any]
    summary: EvaluationSummary


class AnalysisEntry(Base):
    name: str
    created_at: str


class AnalysisList(Base):
    items: list[AnalysisEntry]


class GalleryItem(BaseModel):
    id: str
    label: int
    label_name: str


class Gallery(Base):
    license: str
    attribution: str
    selection: str
    items: list[GalleryItem]


class PredictRequest(BaseModel):
    run_id: str = Field(pattern=r"^[A-Za-z0-9._-]{1,128}$")
    image_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,32}$")

    model_config = {"extra": "forbid"}


class Prediction(Base):
    run_id: str
    image_id: str
    seed: int
    probability_pneumonia: float
    operating_points: dict[str, dict[str, float | bool]]
    ground_truth_label: int
    note: str
    resized_from: int | None = None


class Explanation(Base):
    run_id: str
    image_id: str
    seed: int
    method: str
    probability_pneumonia: float
    overlay_png_base64: str
    heatmap_png_base64: str
    sanity_checked: bool
    sanity_passed: bool | None = None
    note: str
