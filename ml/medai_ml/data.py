"""Chargement et contrôle de PneumoniaMNIST (MedMNIST v2/+, CC BY 4.0).

Le téléchargement est délégué à `medmnist`, qui vérifie la somme MD5 publiée. On calcule en plus
un SHA-256 du fichier, enregistré dans la provenance de chaque rapport.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

DATASET_NAME = "pneumoniamnist"
DATASET_LICENSE = "CC BY 4.0"
DEFAULT_ROOT = Path.home() / ".medmnist"

UInt8Array = NDArray[np.uint8]
Int64Array = NDArray[np.int64]


@dataclass(frozen=True)
class Split:
    images: UInt8Array  # (N, H, W), niveaux de gris
    labels: Int64Array  # (N,), 1 = pneumonie

    def __post_init__(self) -> None:
        if self.images.ndim != 3:
            raise ValueError("images doit avoir la forme (N, H, W).")
        if self.images.shape[0] != self.labels.shape[0]:
            raise ValueError("images et labels doivent avoir le même effectif.")
        if not set(np.unique(self.labels)).issubset({0, 1}):
            raise ValueError("Les labels doivent valoir 0 ou 1.")

    def __len__(self) -> int:
        return int(self.labels.shape[0])


@dataclass(frozen=True)
class DatasetInfo:
    name: str
    size: int
    license: str
    source_url: str
    md5_expected: str
    sha256: str


@dataclass(frozen=True)
class DataBundle:
    train: Split
    val: Split
    test: Split
    info: DatasetInfo


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def _file_name(size: int) -> str:
    return f"{DATASET_NAME}.npz" if size == 28 else f"{DATASET_NAME}_{size}.npz"


def load_pneumoniamnist(size: int = 224, root: str | Path = DEFAULT_ROOT) -> DataBundle:
    """Télécharge (si besoin), vérifie le MD5 puis charge les trois splits."""
    import medmnist  # import tardif : dépendance lourde

    info: dict[str, Any] = medmnist.INFO[DATASET_NAME]
    md5_key = "MD5" if size == 28 else f"MD5_{size}"
    url_key = "url" if size == 28 else f"url_{size}"
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    # Instancier la classe officielle déclenche le téléchargement et la vérification MD5.
    medmnist.PneumoniaMNIST(split="test", download=True, root=str(root_path), size=size)
    path = root_path / _file_name(size)
    with np.load(path) as npz:

        def split(name: str) -> Split:
            return Split(
                images=np.asarray(npz[f"{name}_images"], dtype=np.uint8),
                labels=np.asarray(npz[f"{name}_labels"]).reshape(-1).astype(np.int64),
            )

        train, val, test = split("train"), split("val"), split("test")
    ds_info = DatasetInfo(
        name=DATASET_NAME,
        size=size,
        license=DATASET_LICENSE,
        source_url=str(info[url_key]),
        md5_expected=str(info[md5_key]),
        sha256=sha256_file(path),
    )
    return DataBundle(train=train, val=val, test=test, info=ds_info)


# ---------------------------------------------------------------- fiche de données


def class_counts(split: Split) -> dict[str, Any]:
    n = len(split)
    pos = int(split.labels.sum())
    return {
        "n": n,
        "n_pneumonia": pos,
        "n_normal": n - pos,
        "prevalence": None if n == 0 else pos / n,
    }


def phash_bits(images: UInt8Array, hash_size: int = 8) -> NDArray[np.float32]:
    """Hash perceptuel (pHash) de chaque image, sous forme de matrice (N, hash_size**2) de 0/1."""
    import imagehash
    from PIL import Image

    out = np.zeros((images.shape[0], hash_size * hash_size), dtype=np.float32)
    for i in range(images.shape[0]):
        h = imagehash.phash(Image.fromarray(images[i]), hash_size=hash_size)
        out[i] = np.asarray(h.hash, dtype=np.float32).reshape(-1)
    return out


def cross_split_distances(
    a_bits: NDArray[np.float32], b_bits: NDArray[np.float32]
) -> NDArray[np.int32]:
    """Distances de Hamming entre tous les couples (a_i, b_j)."""
    n_bits = a_bits.shape[1]
    agree = a_bits @ b_bits.T + (1 - a_bits) @ (1 - b_bits).T
    return np.asarray(n_bits - agree, dtype=np.int32)


def _pearson(a: UInt8Array, b: UInt8Array) -> float:
    x = a.astype(np.float64).ravel()
    y = b.astype(np.float64).ravel()
    x -= x.mean()
    y -= y.mean()
    return float((x @ y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12))


def duplicate_report(
    a: Split, b: Split, max_distance: int = 4, hash_size: int = 8, min_corr: float = 0.99
) -> dict[str, Any]:
    """Cherche les doublons entre deux splits en deux temps.

    1. Candidats : couples (image de a, image de b) à distance pHash <= max_distance. Le pHash
       est grossier : deux radiographies thoraciques différentes peuvent être proches.
    2. Vérification : corrélation de Pearson des pixels. Un couple est un doublon probable si
       corrélation >= min_corr. Seuls ces couples sont comptés comme doublons.
    """
    da = cross_split_distances(phash_bits(a.images, hash_size), phash_bits(b.images, hash_size))
    ii, jj = np.where(da <= max_distance)
    corr = np.array([_pearson(a.images[i], b.images[j]) for i, j in zip(ii, jj, strict=True)])
    confirmed = corr >= min_corr
    return {
        "hash": f"phash{hash_size}",
        "max_distance": max_distance,
        "min_pixel_correlation": min_corr,
        "candidate_pairs": int(ii.size),
        "confirmed_duplicate_pairs": int(confirmed.sum()),
        "images_a_confirmed": int(np.unique(ii[confirmed]).size),
        "images_b_confirmed": int(np.unique(jj[confirmed]).size),
        "max_pixel_correlation_of_candidates": float(corr.max()) if corr.size else None,
    }


def datasheet(bundle: DataBundle, with_duplicates: bool = True) -> dict[str, Any]:
    """Fiche de données calculée à partir des données réelles (rien n'est saisi à la main)."""
    sheet: dict[str, Any] = {
        "dataset": bundle.info.name,
        "size": bundle.info.size,
        "license": bundle.info.license,
        "source_url": bundle.info.source_url,
        "md5_expected": bundle.info.md5_expected,
        "sha256": bundle.info.sha256,
        "splits": {
            "train": class_counts(bundle.train),
            "val": class_counts(bundle.val),
            "test": class_counts(bundle.test),
        },
        "image_shape": list(bundle.train.images.shape[1:]),
        "pixel_dtype": "uint8",
    }
    if with_duplicates:
        sheet["duplicates"] = {
            "train_vs_test": duplicate_report(bundle.train, bundle.test),
            "val_vs_test": duplicate_report(bundle.val, bundle.test),
            "train_vs_val": duplicate_report(bundle.train, bundle.val),
        }
    return sheet
