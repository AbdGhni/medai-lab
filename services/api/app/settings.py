"""Configuration de l'API (variables d'environnement MEDAI_*)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    reports_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("MEDAI_REPORTS_DIR", "reports"))
    )
    artifacts_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("MEDAI_ARTIFACTS_DIR", "artifacts"))
    )
    gallery_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("MEDAI_GALLERY_DIR", "gallery"))
    )
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o for o in os.environ.get("MEDAI_CORS_ORIGINS", "http://localhost:3000").split(",") if o
        ]
    )
    reference_seed: int = (
        0  # seed utilisée pour l'inférence en direct (choix fixe, pas fondé sur le test)
    )
