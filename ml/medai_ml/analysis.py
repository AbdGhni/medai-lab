"""Analyses complémentaires archivées à côté d'un rapport (reports/<run_id>/analyses/<nom>.json).

Le rapport d'origine n'est jamais modifié. Chaque analyse porte l'identifiant du rapport, la
version du protocole, le commit et la date ; l'écriture n'écrase jamais un fichier existant.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import DISCLAIMER, PROTOCOL_VERSION
from .provenance import git_state, now_utc

ANALYSIS_NAMES = {"robustness", "calibration", "gradcam_sanity", "comparison", "domain_shift"}


def write_analysis(
    reports_dir: Path, run_id: str, name: str, payload: dict[str, Any], dir_name: str | None = None
) -> Path:
    """Écrit reports/<run_id>/analyses/<name>.json (comparaison : reports/<dir_name>/...)."""
    if name not in ANALYSIS_NAMES:
        raise ValueError(f"Analyse inconnue : {name}")
    run_dir = Path(reports_dir) / (dir_name or run_id)
    if not (run_dir / "report.json").exists() and dir_name is None:
        raise FileNotFoundError(f"Rapport introuvable : {run_dir}")
    out_dir = run_dir / "analyses"
    out_dir.mkdir(parents=True, exist_ok=True)
    git = git_state()
    doc = {
        "analysis": name,
        "run_id": run_id,
        "protocol_version": PROTOCOL_VERSION,
        "disclaimer": DISCLAIMER,
        "created_at": now_utc(),
        "commit": git["commit"],
        "dirty": git["dirty"],
        **payload,
    }
    path = out_dir / f"{name}.json"
    with open(path, "x", encoding="utf-8") as f:  # FileExistsError : jamais d'écrasement
        f.write(json.dumps(doc, indent=2, allow_nan=False) + "\n")
    return path
