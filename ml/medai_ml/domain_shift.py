"""Décalage de domaine exploratoire : modèles entraînés sur PneumoniaMNIST, évalués sur ChestMNIST.

Choix de conception (voir docs/EVAL_PROTOCOL.md, section 11) :

- Aucune ré-optimisation : mêmes poids, mêmes seuils S1/S2 fixés sur la validation de
  PneumoniaMNIST. On mesure ce qui se passe quand on déplace le modèle tel quel.
- Même résolution (224) et même chaîne de prétraitement MedMNIST des deux côtés : le décalage
  porte sur la population et la définition de l'étiquette, pas sur un rééchantillonnage différent.
- Jeu d'évaluation : split de test de ChestMNIST uniquement (NIH ChestX-ray14, adultes, vues
  frontales). L'étiquette cible est « Pneumonia » (une des 14 étiquettes, lue par son nom).
- Deux définitions de la cible, fixées avant de voir les résultats :
  1. pneumonie contre tout le reste (cible principale) ;
  2. pneumonie contre « aucune anomalie » (toutes les étiquettes à 0) : sous-ensemble dont les
     négatifs sont sans autre pathologie, donc moins de confusion avec des signes voisins
     (infiltrat, condensation).
- Mesures principales : AUC (indépendante de la prévalence) et AUC précision-rappel (qui en dépend). Sensibilité, spécificité et précision
  aux seuils fixes sont rapportées avec la prévalence réelle de ce jeu.

Limites à garder en tête : les étiquettes NIH sont extraites automatiquement de comptes rendus
radiologiques (bruitées) ; la population (adultes) et la définition de « pneumonie » diffèrent de
celles de PneumoniaMNIST (enfants, diagnostic clinique) ; un écart d'AUC mélange donc décalage
d'images et décalage d'étiquettes. Résultat exploratoire, sans valeur clinique.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from numpy.typing import NDArray
from torch import nn

from .data import DEFAULT_ROOT, DatasetInfo, Split, sha256_file
from .metrics import auc_roc, average_precision, binary_metrics, bootstrap_per_seed
from .train import predict_probs

CHEST_NAME = "chestmnist"
CHEST_LICENSE = "CC BY 4.0"
POSITIVE_LABEL = "pneumonia"
TARGETS = ("pneumonia_vs_all", "pneumonia_vs_no_finding")


@dataclass(frozen=True)
class ChestTest:
    images: NDArray[np.uint8]  # (N, H, W)
    labels: NDArray[np.int64]  # (N, 14), multi-étiquettes
    label_names: list[str]
    info: DatasetInfo


def pneumonia_index(label_names: list[str], name: str = POSITIVE_LABEL) -> int:
    """Indice de l'étiquette cible, trouvé par son nom (jamais codé en dur)."""
    found = [i for i, n in enumerate(label_names) if n.strip().lower() == name]
    if len(found) != 1:
        raise ValueError(f"Étiquette « {name} » introuvable ou ambiguë dans {label_names}.")
    return found[0]


def make_targets(
    labels: NDArray[np.int64], label_names: list[str]
) -> dict[str, tuple[NDArray[np.int64], NDArray[np.int64]]]:
    """Pour chaque cible : (indices des images retenues, étiquette binaire sur ces images)."""
    if labels.ndim != 2 or labels.shape[1] != len(label_names):
        raise ValueError("labels doit avoir la forme (N, nombre d'étiquettes).")
    p = pneumonia_index(label_names)
    pneu = labels[:, p].astype(np.int64)
    everything = np.arange(labels.shape[0], dtype=np.int64)
    no_finding = labels.sum(axis=1) == 0
    keep = np.flatnonzero((pneu == 1) | no_finding).astype(np.int64)
    return {
        "pneumonia_vs_all": (everything, pneu),
        "pneumonia_vs_no_finding": (keep, pneu[keep]),
    }


def load_chestmnist_test(size: int = 224, root: str | Path = DEFAULT_ROOT) -> ChestTest:
    """Télécharge (si besoin), vérifie le MD5 puis charge le split de test de ChestMNIST."""
    import medmnist

    info: dict[str, Any] = medmnist.INFO[CHEST_NAME]
    md5_key = "MD5" if size == 28 else f"MD5_{size}"
    url_key = "url" if size == 28 else f"url_{size}"
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    medmnist.ChestMNIST(split="test", download=True, root=str(root_path), size=size)
    path = root_path / (f"{CHEST_NAME}.npz" if size == 28 else f"{CHEST_NAME}_{size}.npz")
    with np.load(path) as npz:  # chargement paresseux : seules les clés demandées sont lues
        images = np.asarray(npz["test_images"], dtype=np.uint8)
        labels = np.asarray(npz["test_labels"]).astype(np.int64)
    names = [str(info["label"][str(i)]) for i in range(len(info["label"]))]
    ds = DatasetInfo(
        name=CHEST_NAME,
        size=size,
        license=CHEST_LICENSE,
        source_url=str(info[url_key]),
        md5_expected=str(info[md5_key]),
        sha256=sha256_file(path),
    )
    return ChestTest(images=images, labels=labels, label_names=names, info=ds)


def _make_fn(
    thresholds: list[dict[str, float]], op: str, metric: str
) -> Callable[[int, NDArray[np.int64], NDArray[np.float64]], float | None]:
    def fn(i: int, yy: NDArray[np.int64], s: NDArray[np.float64]) -> float | None:
        m = binary_metrics(yy, s, thresholds[i][op])
        if metric == "flagged_rate":
            return float((m["tp"] or 0) + (m["fp"] or 0)) / float(len(yy))
        v = m[metric]
        return None if v is None else float(v)

    return fn


def domain_shift_analysis(
    models: list[nn.Module],
    thresholds: list[dict[str, float]],
    images: NDArray[np.uint8],
    labels: NDArray[np.int64],
    label_names: list[str],
    device: torch.device,
    batch_size: int = 64,
    n_boot: int = 1000,
    log: Callable[[str], None] = print,
) -> dict[str, Any]:
    """AUC, sensibilité, spécificité, précision et taux de positifs aux seuils S1/S2 fixes.

    `models[i]` et `thresholds[i]` correspondent à la même seed. Les probabilités sont calculées
    une seule fois sur toutes les images, puis évaluées sur chaque définition de cible.
    """
    targets = make_targets(labels, label_names)
    p = pneumonia_index(label_names)
    split = Split(images=images, labels=(labels[:, p] > 0).astype(np.int64))
    log(f"[décalage] inférence sur {len(split)} images, {len(models)} seeds")
    probs = [predict_probs(m, split, batch_size, device) for m in models]
    ops = list(thresholds[0])
    out: dict[str, Any] = {
        "n_boot": n_boot,
        "n_seeds": len(models),
        "positive_label": POSITIVE_LABEL,
        "positive_label_index": p,
        "targets": {},
    }
    for name, (idx, y) in targets.items():
        log(f"[décalage] cible {name} : {len(idx)} images, {int(y.sum())} positives")
        fns: dict[str, Callable[[int, NDArray[np.int64], NDArray[np.float64]], float | None]] = {
            "auc": lambda i, yy, s: auc_roc(yy, s),
            "auc_pr": lambda i, yy, s: average_precision(yy, s),
        }
        for op in ops:
            for met in ("sensitivity", "specificity", "precision", "flagged_rate"):
                fns[f"{op}/{met}"] = _make_fn(thresholds, op, met)
        iv = bootstrap_per_seed(y, [pr[idx] for pr in probs], fns, n_boot=n_boot, seed=2024)
        out["targets"][name] = {
            "n_images": int(len(idx)),
            "n_positive": int(y.sum()),
            "prevalence": float(y.mean()),
            "metrics": {
                k: {"mean": v.estimate, "ci_low": v.low, "ci_high": v.high} for k, v in iv.items()
            },
        }
    return out
