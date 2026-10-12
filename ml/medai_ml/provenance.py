"""Informations de provenance enregistrées dans chaque rapport."""

from __future__ import annotations

import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _git(args: list[str], cwd: Path) -> str | None:
    try:
        out = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip()


def git_state(repo: Path | None = None) -> dict[str, Any]:
    cwd = repo or Path(__file__).resolve().parent
    commit = _git(["rev-parse", "HEAD"], cwd)
    status = _git(["status", "--porcelain"], cwd)
    return {"commit": commit, "dirty": bool(status) if status is not None else None}


def environment() -> dict[str, Any]:
    import numpy
    import sklearn
    import torch

    cuda = torch.cuda.is_available()
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "torch": torch.__version__,
        "numpy": numpy.__version__,
        "scikit_learn": sklearn.__version__,
        "device": "cuda" if cuda else "cpu",
        "gpu_name": torch.cuda.get_device_name(0) if cuda else None,
        "cpu_count": __import__("os").cpu_count(),
    }


def now_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
