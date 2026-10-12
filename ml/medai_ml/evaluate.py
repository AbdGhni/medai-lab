"""Orchestration : entraînement par seed, choix des seuils sur la validation, évaluation du test."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml
from numpy.typing import NDArray

from .config import ExperimentConfig
from .data import DataBundle, datasheet
from .metrics import (
    Interval,
    auc_roc,
    average_precision,
    binary_metrics,
    bootstrap_per_seed,
    brier,
    ece,
    mean_std,
)
from .models import build_model
from .provenance import environment, git_state, now_utc
from .report import (
    EvaluationReport,
    MetricSummary,
    OperatingPoint,
    Provenance,
    SeedResult,
    write_report,
)
from .thresholds import select_thresholds
from .train import predict_probs, resolve_device, subset_split, train_model

OP_METRICS = [
    "sensitivity",
    "specificity",
    "precision",
    "f1",
    "balanced_accuracy",
    "accuracy",
    "tp",
    "fp",
    "tn",
    "fn",
]


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def run_experiment(
    cfg: ExperimentConfig,
    bundle: DataBundle,
    reports_dir: Path,
    artifacts_dir: Path | None = None,
    include_duplicates: bool = True,
    log: Callable[[str], None] = print,
) -> tuple[EvaluationReport, Path]:
    """Exécute le protocole pour toutes les seeds de la configuration et écrit le rapport."""
    device = resolve_device(cfg.device)
    env = environment()
    git = git_state()
    created = now_utc()
    run_id = f"{cfg.model_id}-{cfg.hash()[:8]}-{created.replace('-', '').replace(':', '')}"

    y_val = bundle.val.labels
    y_test = bundle.test.labels
    seed_results: list[SeedResult] = []
    test_probs: list[NDArray[np.float64]] = []
    val_probs: list[NDArray[np.float64]] = []
    thresholds_by_seed: list[dict[str, float]] = []
    if artifacts_dir is not None:
        (artifacts_dir / run_id).mkdir(parents=True, exist_ok=True)

    for seed in cfg.seeds:
        log(f"[seed {seed}] entraînement ({cfg.model_id}, {device})")
        res = train_model(cfg, seed, bundle.train, bundle.val, device)
        # Seuils choisis sur la validation uniquement.
        thr = select_thresholds(y_val, res.val_probs, cfg.sensitivity_target)
        # Le test n'est touché qu'ici, une seule fois par seed, après sélection du modèle et des seuils.
        model = build_model(cfg.model_id, pretrained=False).to(device)
        model.load_state_dict(res.state_dict)
        p_test = predict_probs(model, bundle.test, cfg.batch_size, device, cfg.num_workers)
        test_probs.append(p_test)
        val_probs.append(res.val_probs)
        thresholds_by_seed.append(thr)
        weights_sha = None
        if artifacts_dir is not None:
            wpath = artifacts_dir / run_id / f"seed{seed}.pt"
            torch.save(res.state_dict, wpath)
            weights_sha = hashlib.sha256(wpath.read_bytes()).hexdigest()
        ops = {
            name: OperatingPoint(threshold=t, metrics=binary_metrics(y_test, p_test, t))
            for name, t in thr.items()
        }
        seed_results.append(
            SeedResult(
                seed=seed,
                best_epoch=res.best_epoch,
                val_auc=auc_roc(y_val, res.val_probs),
                test_auc=auc_roc(y_test, p_test),
                test_auc_pr=average_precision(y_test, p_test),
                test_brier=brier(y_test, p_test),
                test_ece_10=ece(y_test, p_test, 10),
                operating_points=ops,
                history=res.history,
                weights_sha256=weights_sha,
            )
        )
        log(
            f"[seed {seed}] AUC val={seed_results[-1].val_auc} AUC test={seed_results[-1].test_auc}"
        )

    aggregate = _aggregate(cfg, y_test, test_probs, thresholds_by_seed, seed_results)
    provenance = Provenance(
        commit=git["commit"] or "",
        dirty=bool(git["dirty"]),
        config_hash=cfg.hash(),
        dataset_sha256=bundle.info.sha256,
        python=env["python"],
        torch=env["torch"],
        numpy=env["numpy"],
        scikit_learn=env["scikit_learn"],
        platform=env["platform"],
        device=str(device.type),
        gpu_name=env["gpu_name"],
        cpu_count=env["cpu_count"],
    )
    notes = list(_standard_notes(cfg))
    report = EvaluationReport(
        run_id=run_id,
        model_id=cfg.model_id,
        created_at=created,
        config=cfg.model_dump(mode="json"),
        provenance=provenance,
        dataset=datasheet(bundle, with_duplicates=include_duplicates),
        seeds=seed_results,
        aggregate=aggregate,
        notes=notes,
    )
    path = write_report(
        report,
        reports_dir,
        y_test,
        test_probs,
        config_yaml=yaml.safe_dump(cfg.model_dump(mode="json"), sort_keys=True),
        y_val=y_val,
        val_probs_by_seed=val_probs,
    )
    return report, path


def _standard_notes(cfg: ExperimentConfig) -> list[str]:
    notes = [
        "Le jeu de test n'a été utilisé qu'une fois par seed, après sélection de l'epoch et des seuils sur la validation.",
        "Intervalle bootstrap : percentile 95 %, rééchantillonnage stratifié des images de test, moyenne sur les seeds à chaque réplicat.",
        "Limite : jeu pédiatrique, centre unique ; la validation est tirée au hasard du jeu d'entraînement source (9:1), sans garantie de séparation par patient.",
    ]
    if cfg.train_subset is not None:
        notes.append(
            f"ATTENTION : entraînement sur un sous-échantillon de {cfg.train_subset} images (test de fumée)."
        )
    if cfg.size != 224:
        notes.append(f"Résolution {cfg.size}x{cfg.size} : ne pas comparer aux résultats à 224x224.")
    return notes


def _aggregate(
    cfg: ExperimentConfig,
    y_test: NDArray[np.int64],
    probs: list[NDArray[np.float64]],
    thresholds: list[dict[str, float]],
    seed_results: list[SeedResult],
) -> dict[str, MetricSummary]:
    fns: dict[str, Callable[[int, NDArray[np.int64], NDArray[np.float64]], float | None]] = {
        "auc": lambda i, y, s: auc_roc(y, s),
        "auc_pr": lambda i, y, s: average_precision(y, s),
        "brier": lambda i, y, s: brier(y, s),
        "ece_10": lambda i, y, s: ece(y, s, 10),
    }
    for op in thresholds[0]:
        for m in OP_METRICS:
            fns[f"{op}/{m}"] = _op_fn(thresholds, op, m)
    intervals: dict[str, Interval] = bootstrap_per_seed(
        y_test, probs, fns, n_boot=cfg.n_bootstrap, seed=12345
    )
    per_seed: dict[str, list[float | None]] = {
        "auc": [r.test_auc for r in seed_results],
        "auc_pr": [r.test_auc_pr for r in seed_results],
        "brier": [r.test_brier for r in seed_results],
        "ece_10": [r.test_ece_10 for r in seed_results],
    }
    for op in thresholds[0]:
        for m in OP_METRICS:
            vals: list[float | None] = []
            for r in seed_results:
                v: Any = r.operating_points[op].metrics[m]
                vals.append(None if v is None else float(v))
            per_seed[f"{op}/{m}"] = vals
    out: dict[str, MetricSummary] = {}
    for k, iv in intervals.items():
        mean, std = mean_std(per_seed[k])
        out[k] = MetricSummary(
            mean=mean,
            std_across_seeds=std,
            ci_low=iv.low,
            ci_high=iv.high,
            n_boot_valid=iv.n_valid,
        )
    return out


def _op_fn(
    thresholds: list[dict[str, float]], op: str, metric: str
) -> Callable[[int, NDArray[np.int64], NDArray[np.float64]], float | None]:
    def fn(i: int, y: NDArray[np.int64], s: NDArray[np.float64]) -> float | None:
        v = binary_metrics(y, s, thresholds[i][op])[metric]
        return None if v is None else float(v)

    return fn


__all__ = ["run_experiment", "subset_split"]
