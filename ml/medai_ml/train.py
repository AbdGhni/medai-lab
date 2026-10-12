"""Entraînement déterministe d'un modèle pour une seed donnée.

Ce module ne reçoit JAMAIS le jeu de test : sélection d'epoch et arrêt anticipé reposent
uniquement sur la validation (protocole, sections 1 et 4).
"""

from __future__ import annotations

import copy
import os
import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import torch
from numpy.typing import NDArray
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision.transforms import v2

from .config import ExperimentConfig
from .data import Split
from .metrics import auc_roc
from .models import build_model

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)  # noqa: NPY002
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def resolve_device(choice: str) -> torch.device:
    if choice == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(choice)


class _ImageDataset(Dataset[tuple[torch.Tensor, torch.Tensor]]):
    def __init__(self, split: Split, train: bool) -> None:
        self.x = torch.from_numpy(split.images)
        self.y = torch.from_numpy(split.labels.astype(np.float32))
        self.augment = (
            v2.Compose(
                [
                    v2.RandomAffine(degrees=5, translate=(0.03, 0.03)),
                    v2.ColorJitter(brightness=0.1, contrast=0.1),
                ]
            )
            if train
            else None
        )
        self.norm = v2.Normalize(IMAGENET_MEAN, IMAGENET_STD)

    def __len__(self) -> int:
        return int(self.y.shape[0])

    def __getitem__(self, i: int) -> tuple[torch.Tensor, torch.Tensor]:
        img = self.x[i].float().div(255.0).unsqueeze(0)  # (1, H, W) dans [0, 1]
        if self.augment is not None:
            img = self.augment(img)
        img = self.norm(img.expand(3, -1, -1).contiguous())
        return img, self.y[i]


def make_loader(
    split: Split, batch_size: int, train: bool, num_workers: int, seed: int
) -> DataLoader[tuple[torch.Tensor, torch.Tensor]]:
    g = torch.Generator()
    g.manual_seed(seed)
    return DataLoader(
        _ImageDataset(split, train=train),
        batch_size=batch_size,
        shuffle=train,
        num_workers=num_workers,
        generator=g if train else None,
        drop_last=False,
    )


@torch.no_grad()
def predict_probs(
    model: nn.Module, split: Split, batch_size: int, device: torch.device, num_workers: int = 0
) -> NDArray[np.float64]:
    """Probabilités de la classe positive (sigmoïde du logit), dans l'ordre du split."""
    model.eval()
    loader = make_loader(split, batch_size, train=False, num_workers=num_workers, seed=0)
    out: list[NDArray[np.float64]] = []
    for xb, _ in loader:
        logits = model(xb.to(device))
        out.append(torch.sigmoid(logits).double().cpu().numpy())
    return np.concatenate(out)


def _bce_loss(probs: NDArray[np.float64], y: NDArray[np.int64]) -> float:
    p = np.clip(probs, 1e-7, 1 - 1e-7)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


@dataclass
class TrainResult:
    state_dict: dict[str, Any]
    best_epoch: int
    val_probs: NDArray[np.float64]
    history: list[dict[str, float | None]] = field(default_factory=list)


def subset_split(split: Split, n: int) -> Split:
    """Sous-échantillon déterministe (indépendant de la seed), pour les tests de fumée."""
    if n >= len(split):
        return split
    rng = np.random.default_rng(0)
    idx = np.sort(rng.choice(len(split), size=n, replace=False))
    return Split(images=split.images[idx], labels=split.labels[idx])


def train_model(
    cfg: ExperimentConfig, seed: int, train: Split, val: Split, device: torch.device
) -> TrainResult:
    seed_everything(seed)
    if cfg.train_subset is not None:
        train = subset_split(train, cfg.train_subset)
    model = build_model(cfg.model_id, pretrained=cfg.pretrained).to(device)
    n_pos = int(train.labels.sum())
    n_neg = len(train) - n_pos
    pos_weight = torch.tensor([n_neg / max(n_pos, 1)], dtype=torch.float32, device=device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optim = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=cfg.epochs)
    loader = make_loader(train, cfg.batch_size, True, cfg.num_workers, seed)

    best_score: tuple[float, float] | None = None  # (AUC de validation, -perte de validation)
    best_state = copy.deepcopy(model.state_dict())
    best_epoch = 0
    best_val = np.zeros(len(val))
    history: list[dict[str, float | None]] = []
    stale = 0
    for epoch in range(1, cfg.epochs + 1):
        model.train()
        total, count = 0.0, 0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            optim.zero_grad(set_to_none=True)
            loss = criterion(model(xb), yb)
            loss.backward()
            optim.step()
            total += float(loss.item()) * xb.shape[0]
            count += xb.shape[0]
        sched.step()
        val_probs = predict_probs(model, val, cfg.batch_size, device, cfg.num_workers)
        v_auc = auc_roc(val.labels, val_probs)
        v_loss = _bce_loss(val_probs, val.labels)
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": total / count,
                "val_loss": v_loss,
                "val_auc": v_auc,
            }
        )
        score = (v_auc if v_auc is not None else float("-inf"), -v_loss)
        if best_score is None or score > best_score:
            best_score = score
            best_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            best_val = val_probs
            stale = 0
        else:
            stale += 1
            if stale >= cfg.patience:
                break
    return TrainResult(
        state_dict={k: v.detach().cpu() for k, v in best_state.items()},
        best_epoch=best_epoch,
        val_probs=best_val,
        history=history,
    )
