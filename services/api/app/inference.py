"""Inférence en direct sur les images de la galerie uniquement (aucune image reçue d'un client)."""

from __future__ import annotations

import base64
import io
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image

from medai_ml.explain import gradcam
from medai_ml.models import build_model
from medai_ml.report import EvaluationReport
from medai_ml.train import preprocess_uint8


class InferenceUnavailable(Exception):
    """Aucun poids disponible pour ce rapport (par exemple démo statique)."""


@dataclass(frozen=True)
class GalleryImage:
    id: str
    label: int
    path: Path


class Gallery:
    def __init__(self, gallery_dir: Path) -> None:
        self.dir = Path(gallery_dir)
        self.manifest: dict[str, Any] = {}
        self.items: dict[str, GalleryImage] = {}
        mf = self.dir / "manifest.json"
        if mf.exists():
            self.manifest = json.loads(mf.read_text(encoding="utf-8"))
            for it in self.manifest.get("items", []):
                self.items[it["id"]] = GalleryImage(
                    it["id"], int(it["label"]), self.dir / f"{it['id']}.png"
                )

    def load_uint8(self, image_id: str) -> np.ndarray[Any, np.dtype[np.uint8]]:
        item = self.items[image_id]  # KeyError si l'identifiant est inconnu : pas de chemin libre
        with Image.open(item.path) as im:
            return np.asarray(im.convert("L"), dtype=np.uint8)


class Predictor:
    def __init__(self, artifacts_dir: Path) -> None:
        self.artifacts_dir = Path(artifacts_dir)

    def _weights_path(self, run_id: str, seed: int) -> Path:
        return self.artifacts_dir / run_id / f"seed{seed}.pt"

    def available(self, run_id: str, seed: int) -> bool:
        return self._weights_path(run_id, seed).exists()

    @lru_cache(maxsize=4)  # noqa: B019
    def _model(self, run_id: str, model_id: str, seed: int) -> torch.nn.Module:
        path = self._weights_path(run_id, seed)
        if not path.exists():
            raise InferenceUnavailable(f"Poids absents pour {run_id} (seed {seed}).")
        model = build_model(model_id, pretrained=False)
        state = torch.load(path, map_location="cpu", weights_only=True)
        model.load_state_dict(state)
        return model.eval()

    def _prepare(
        self, img: np.ndarray[Any, np.dtype[np.uint8]], size: int
    ) -> tuple[torch.Tensor, int | None]:
        resized_from: int | None = None
        if img.shape[0] != size:
            resized_from = int(img.shape[0])
            img = np.asarray(Image.fromarray(img).resize((size, size), Image.Resampling.BILINEAR))
        return preprocess_uint8(img).unsqueeze(0), resized_from

    def predict(
        self, rep: EvaluationReport, img: np.ndarray[Any, np.dtype[np.uint8]], seed: int
    ) -> tuple[float, int | None]:
        model = self._model(rep.run_id, rep.model_id, seed)
        x, resized_from = self._prepare(img, int(rep.config["size"]))
        with torch.no_grad():
            prob = float(torch.sigmoid(model(x)).item())
        return prob, resized_from

    def explain(
        self, rep: EvaluationReport, img: np.ndarray[Any, np.dtype[np.uint8]], seed: int
    ) -> tuple[float, str, str]:
        model = self._model(rep.run_id, rep.model_id, seed)
        x, _ = self._prepare(img, int(rep.config["size"]))
        with torch.no_grad():
            prob = float(torch.sigmoid(model(x)).item())
        cam = gradcam(model, rep.model_id, x)[0]  # (h, w) dans [0, 1]
        return prob, _overlay_png(img, cam), _heatmap_png(img.shape[0], cam)


def _png_b64(arr: np.ndarray[Any, np.dtype[np.uint8]]) -> str:
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _resize_cam(
    cam: np.ndarray[Any, np.dtype[np.float32]], size: int
) -> np.ndarray[Any, np.dtype[np.float32]]:
    im = Image.fromarray((cam * 255).astype(np.uint8)).resize(
        (size, size), Image.Resampling.BILINEAR
    )
    return np.asarray(im, dtype=np.float32) / 255.0


def _colorize(cam: np.ndarray[Any, np.dtype[np.float32]]) -> np.ndarray[Any, np.dtype[np.uint8]]:
    """Palette simple bleu -> jaune -> rouge, sans dépendance à matplotlib."""
    r = np.clip(2 * cam, 0, 1)
    g = np.clip(2 * cam, 0, 1) * np.clip(2 - 2 * cam, 0, 1)
    b = np.clip(1 - 2 * cam, 0, 1)
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def _overlay_png(
    img: np.ndarray[Any, np.dtype[np.uint8]], cam: np.ndarray[Any, np.dtype[np.float32]]
) -> str:
    size = img.shape[0]
    heat = _colorize(_resize_cam(cam, size)).astype(np.float32)
    base = np.repeat(img[..., None], 3, axis=-1).astype(np.float32)
    out = np.clip(0.55 * base + 0.45 * heat, 0, 255).astype(np.uint8)
    return _png_b64(out)


def _heatmap_png(size: int, cam: np.ndarray[Any, np.dtype[np.float32]]) -> str:
    return _png_b64((_resize_cam(cam, size) * 255).astype(np.uint8))
