"""Ligne de commande : python -m medai_ml {datasheet,gallery,run,compare,calibrate,robustness,sanity}."""

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
    g = sub.add_parser("gallery", help="Construit la galerie de démonstration (images du test).")
    g.add_argument("--size", type=int, default=224, choices=[28, 64, 128, 224])
    g.add_argument("--root", default=str(DEFAULT_ROOT))
    g.add_argument("--out", default="gallery")
    g.add_argument("--n-per-class", type=int, default=12)
    r = sub.add_parser("run", help="Exécute le protocole pour une configuration.")
    r.add_argument("--config", required=True)
    r.add_argument("--root", default=str(DEFAULT_ROOT))
    r.add_argument("--reports", default="reports")
    r.add_argument("--artifacts", default="artifacts")
    c = sub.add_parser("compare", help="Compare des rapports à une référence (AUC apparié, Holm).")
    c.add_argument("--baseline", required=True, help="run_id de la référence (resnet18).")
    c.add_argument("--others", nargs="+", required=True, help="run_id des autres modèles.")
    c.add_argument("--reports", default="reports")
    c.add_argument("--n-boot", type=int, default=2000)
    k = sub.add_parser("calibrate", help="Temperature scaling sur un rapport existant.")
    k.add_argument("--run", required=True)
    k.add_argument("--reports", default="reports")
    for name, text in (
        ("robustness", "Robustesse aux perturbations (test uniquement)."),
        ("sanity", "Test de sanité de Grad-CAM par randomisation des poids."),
    ):
        a = sub.add_parser(name, help=text)
        a.add_argument("--run", required=True)
        a.add_argument("--reports", default="reports")
        a.add_argument("--artifacts", default="artifacts")
        a.add_argument("--root", default=str(DEFAULT_ROOT))
    args = p.parse_args(argv)

    if args.cmd in {"compare", "calibrate", "robustness", "sanity"}:
        from . import analyze

        reports = Path(args.reports)
        if args.cmd == "compare":
            out = analyze.compare_runs(reports, args.baseline, args.others, args.n_boot)
        elif args.cmd == "calibrate":
            out = analyze.calibrate_run(reports, args.run)
        elif args.cmd == "robustness":
            out = analyze.robustness_run(reports, Path(args.artifacts), args.run, Path(args.root))
        else:
            out = analyze.sanity_run(reports, Path(args.artifacts), args.run, Path(args.root))
        print(f"Analyse écrite : {out}")
        return 0

    if args.cmd == "datasheet":
        bundle = load_pneumoniamnist(args.size, args.root)
        sheet = datasheet(bundle, with_duplicates=not args.no_duplicates)
        text = json.dumps(sheet, indent=2, allow_nan=False)
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    if args.cmd == "gallery":
        from .gallery import build_gallery

        bundle = load_pneumoniamnist(args.size, args.root)
        manifest = build_gallery(bundle, Path(args.out), args.n_per_class)
        print(f"{len(manifest['items'])} images écrites dans {args.out}")
        return 0

    cfg = load_config(args.config)
    bundle = load_pneumoniamnist(cfg.size, args.root)
    report, path = run_experiment(cfg, bundle, Path(args.reports), Path(args.artifacts))
    print(f"Rapport écrit : {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
