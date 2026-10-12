"""Analyses de phase 4 exécutées sur des rapports existants (aucun nouvel entraînement).

Chaque fonction lit un rapport validé, vérifie la cohérence des données et des poids
(empreintes SHA-256) et écrit un fichier dans reports/<run_id>/analyses/.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import torch

from .analysis import write_analysis
from .calibration import calibration_analysis
from .compare import (
    Predictions,
    delong_test,
    holm,
    load_predictions,
    mcnemar_exact,
    paired_bootstrap_auc,
)
from .data import DEFAULT_ROOT, DataBundle, load_pneumoniamnist
from .explain import gradcam_sanity
from .models import build_model
from .report import EvaluationReport, load_report
from .robustness import robustness_analysis
from .train import preprocess_uint8, resolve_device

ALPHA = 0.05


def _run(reports_dir: Path, run_id: str) -> tuple[EvaluationReport, Path]:
    run_dir = Path(reports_dir) / run_id
    return load_report(run_dir / "report.json"), run_dir


def _s1_threshold(report: EvaluationReport) -> float:
    return float(np.mean([s.operating_points["S1_youden"].threshold for s in report.seeds]))


def compare_runs(
    reports_dir: Path, baseline_id: str, other_ids: list[str], n_boot: int = 2000
) -> Path:
    """Chaque modèle contre le modèle de référence : AUC (bootstrap apparié, Holm), DeLong, McNemar."""
    base_rep, base_dir = _run(reports_dir, baseline_id)
    base = load_predictions(base_dir)
    m = len(other_ids)
    rows: list[dict[str, Any]] = []
    for oid in other_ids:
        rep, d = _run(reports_dir, oid)
        pred = load_predictions(d)
        if rep.provenance.dataset_sha256 != base_rep.provenance.dataset_sha256:
            raise ValueError(f"{oid} : jeu de données différent de la référence.")
        if not np.array_equal(pred.y_true, base.y_true):
            raise ValueError(f"{oid} : étiquettes de test différentes de la référence.")
        r = paired_bootstrap_auc(
            base.y_true, pred.probs, base.probs, n_boot=n_boot, alpha=ALPHA, n_comparisons=m
        )
        mean_a, mean_b = pred.probs.mean(axis=0), base.probs.mean(axis=0)
        _, _, d_diff, p_delong = delong_test(base.y_true, mean_a, mean_b)
        pa = (mean_a >= _s1_threshold(rep)).astype(np.int64)
        pb = (mean_b >= _s1_threshold(base_rep)).astype(np.int64)
        rows.append(
            {
                "model": rep.model_id,
                "run_id": oid,
                "auc_model": r.auc_a,
                "auc_baseline": r.auc_b,
                "auc_diff_model_minus_baseline": r.diff,
                "ci95": [r.ci_low, r.ci_high],
                "ci_adjusted": [r.ci_low_adjusted, r.ci_high_adjusted],
                "p_bootstrap": r.p_bootstrap,
                "delong_on_seed_mean": {"auc_diff": d_diff, "p": p_delong},
                "mcnemar_s1_on_seed_mean": mcnemar_exact(pa, pb, base.y_true),
            }
        )
    adj = holm([float(r["p_bootstrap"]) for r in rows])
    for row, p_adj in zip(rows, adj, strict=True):
        row["p_holm"] = p_adj
        row["established"] = bool(p_adj < ALPHA)
        row["wording"] = (
            "différence établie (après correction de Holm)"
            if row["established"]
            else "pas de différence démontrée"
        )
    payload = {
        "baseline": {"model": base_rep.model_id, "run_id": baseline_id},
        "n_boot": n_boot,
        "alpha": ALPHA,
        "n_comparisons": m,
        "n_seeds_baseline": len(base_rep.seeds),
        "comparisons": rows,
        "notes": [
            "Différence d'AUC moyenne sur les seeds ; mêmes images de test rééchantillonnées pour les deux modèles.",
            "DeLong et McNemar portent sur les probabilités moyennées sur les seeds (ensemble) ; McNemar au seuil S1 moyen.",
            "Une p-valeur seule ne suffit pas : lire la différence et son intervalle.",
        ],
    }
    return write_analysis(reports_dir, baseline_id, "comparison", payload)


def calibrate_run(reports_dir: Path, run_id: str) -> Path:
    _, d = _run(reports_dir, run_id)
    pred: Predictions = load_predictions(d)
    payload = calibration_analysis(pred)
    payload["method"] = "temperature scaling ajusté sur la validation de chaque seed"
    return write_analysis(reports_dir, run_id, "calibration", payload)


def _load_models(
    report: EvaluationReport, artifacts_dir: Path, device: torch.device
) -> list[torch.nn.Module]:
    models: list[torch.nn.Module] = []
    for s in report.seeds:
        w = Path(artifacts_dir) / report.run_id / f"seed{s.seed}.pt"
        if not w.exists():
            raise FileNotFoundError(f"Poids introuvables : {w}")
        if s.weights_sha256 and hashlib.sha256(w.read_bytes()).hexdigest() != s.weights_sha256:
            raise ValueError(f"Empreinte des poids différente de celle du rapport : {w}")
        mdl = build_model(report.model_id, pretrained=False).to(device)
        mdl.load_state_dict(torch.load(w, map_location=device))
        mdl.eval()
        models.append(mdl)
    return models


def _bundle_for(report: EvaluationReport, root: Path) -> DataBundle:
    bundle = load_pneumoniamnist(int(report.config["size"]), root)
    if bundle.info.sha256 != report.provenance.dataset_sha256:
        raise ValueError("Le jeu de données local ne correspond pas à celui du rapport.")
    return bundle


def robustness_run(
    reports_dir: Path,
    artifacts_dir: Path,
    run_id: str,
    root: Path = DEFAULT_ROOT,
    device_choice: str = "auto",
    n_boot: int = 500,
    bundle: DataBundle | None = None,
) -> Path:
    rep, _ = _run(reports_dir, run_id)
    device = resolve_device(device_choice)
    models = _load_models(rep, artifacts_dir, device)
    thr = [{k: v.threshold for k, v in s.operating_points.items()} for s in rep.seeds]
    out = robustness_analysis(
        models,
        thr,
        (bundle or _bundle_for(rep, Path(root))).test,
        device,
        batch_size=int(rep.config.get("batch_size", 64)),
        n_boot=n_boot,
    )
    out["thresholds_note"] = (
        "Seuils S1/S2 fixés sur la validation, non recalculés sous perturbation."
    )
    out["n_seeds"] = len(models)
    return write_analysis(reports_dir, run_id, "robustness", out)


def sanity_run(
    reports_dir: Path,
    artifacts_dir: Path,
    run_id: str,
    root: Path = DEFAULT_ROOT,
    n_per_class: int = 8,
    bundle: DataBundle | None = None,
) -> Path:
    rep, _ = _run(reports_dir, run_id)
    device = resolve_device("cpu")  # Grad-CAM sur 32 images : le CPU suffit
    models = _load_models(rep, artifacts_dir, device)
    test = (bundle or _bundle_for(rep, Path(root))).test
    idx = np.concatenate(
        [np.flatnonzero(test.labels == c)[:n_per_class] for c in (0, 1)]
    )  # premières images de chaque classe : sélection déterministe, sans tri sur les cartes
    x = torch.stack([preprocess_uint8(test.images[i]) for i in idx]).to(device)
    per_seed = []
    for s, mdl in zip(rep.seeds, models, strict=True):
        r = gradcam_sanity(mdl, rep.model_id, x, seed=s.seed)
        r["seed"] = s.seed
        per_seed.append(r)
    payload = {
        "model_id": rep.model_id,
        "image_indices": [int(i) for i in idx],
        "per_seed": per_seed,
        "passes_all_seeds": all(bool(r["passes"]) for r in per_seed),
    }
    return write_analysis(reports_dir, run_id, "gradcam_sanity", payload)
