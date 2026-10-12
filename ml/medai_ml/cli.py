"""Ligne de commande : python -m medai_ml {datasheet,run}."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import load_config
from .data import DEFAULT_ROOT, datasheet, load_pneumoniamnist
from .evaluate import run_experiment


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="medai_ml", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("datasheet", help="Génère la fiche de données depuis les données réelles.")
    d.add_argument("--size", type=int, default=224, choices=[28, 64, 128, 224])
    d.add_argument("--root", default=str(DEFAULT_ROOT))
    d.add_argument("--out", default=None, help="Fichier JSON de sortie (sinon stdout).")
    d.add_argument("--no-duplicates", action="store_true")
    r = sub.add_parser("run", help="Exécute le protocole pour une configuration.")
    r.add_argument("--config", required=True)
    r.add_argument("--root", default=str(DEFAULT_ROOT))
    r.add_argument("--reports", default="reports")
    r.add_argument("--artifacts", default="artifacts")
    args = p.parse_args(argv)

    if args.cmd == "datasheet":
        bundle = load_pneumoniamnist(args.size, args.root)
        sheet = datasheet(bundle, with_duplicates=not args.no_duplicates)
        text = json.dumps(sheet, indent=2, allow_nan=False)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    cfg = load_config(args.config)
    bundle = load_pneumoniamnist(cfg.size, args.root)
    report, path = run_experiment(cfg, bundle, Path(args.reports), Path(args.artifacts))
    print(f"Rapport écrit : {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
