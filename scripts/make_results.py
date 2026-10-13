"""Génère docs/RESULTS.md à partir des rapports versionnés. Aucun chiffre n'est saisi à la main.

Usage : python scripts/make_results.py
Chaque tableau cite le run_id du rapport d'où viennent les valeurs.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
ORDER = ["resnet18", "simple_cnn", "densenet121", "efficientnet_b0"]
BASELINE = "resnet18"


def _runs() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for d in sorted(REPORTS.iterdir()):
        if (d / "report.json").exists():
            out[d.name.rsplit("-", 2)[0]] = d
    return out


def _load(p: Path) -> dict:  # type: ignore[type-arg]
    return json.loads(p.read_text(encoding="utf-8"))


def _ci(a: dict, key: str, nd: int = 3) -> str:  # type: ignore[type-arg]
    m = a[key]
    return f"{m['mean']:.{nd}f} [{m['ci_low']:.{nd}f} ; {m['ci_high']:.{nd}f}]"


def _p(x: float) -> str:
    return "< 0,001" if x < 0.001 else f"{x:.3f}".replace(".", ",")


def build() -> str:
    runs = _runs()
    reps = {m: _load(runs[m] / "report.json") for m in ORDER if m in runs}
    L: list[str] = []
    L.append("# Résultats")
    L.append("")
    L.append(
        "Ce fichier est généré par `scripts/make_results.py` à partir des rapports versionnés "
        "dans `reports/`. Aucune valeur n'est saisie à la main. Prototype de recherche : ne pas "
        "utiliser pour un diagnostic ou une décision clinique."
    )
    L.append("")
    L.append("## Protocole en bref")
    L.append("")
    L.append(
        "PneumoniaMNIST 224x224, jeu de test utilisé une fois par seed, 5 seeds, seuils choisis sur "
        "la validation (S1 : Youden ; S2 : sensibilité >= 0,95 sur la validation), intervalles de "
        "confiance à 95 % par bootstrap stratifié (2000 réplicats). Détails : "
        "[EVAL_PROTOCOL.md](EVAL_PROTOCOL.md)."
    )
    L.append("")
    L.append("## Rapports sources")
    L.append("")
    L.append("| Modèle | run_id | Protocole | Commit | Matériel |")
    L.append("|---|---|---|---|---|")
    for m, r in reps.items():
        pv = r["provenance"]
        L.append(
            f"| {m} | `{r['run_id']}` | {r['protocol_version']} | `{pv['commit'][:8]}` | "
            f"{pv.get('gpu_name') or pv['device']} |"
        )
    L.append("")
    old = [m for m, r in reps.items() if r["protocol_version"] != "1.2"]
    if old:
        L.append(
            f"Le rapport de {', '.join(old)} a été produit sous le protocole 1.0 (avant l'ajout de "
            "l'enregistrement des prédictions de validation et des analyses de la phase 4) ; les "
            "règles d'évaluation de la section ci-dessus étaient déjà les mêmes."
        )
        L.append("")
    L.append("## Performance sur le jeu de test (moyenne des 5 seeds, IC 95 %)")
    L.append("")
    L.append(
        "| Modèle | AUC | AUC-PR | Sensibilité S1 | Spécificité S1 | Sensibilité S2 | Spécificité S2 |"
    )
    L.append("|---|---|---|---|---|---|---|")
    for m, r in reps.items():
        a = r["aggregate"]
        L.append(
            f"| {m} | {_ci(a, 'auc')} | {_ci(a, 'auc_pr')} | {_ci(a, 'S1_youden/sensitivity')} | "
            f"{_ci(a, 'S1_youden/specificity')} | {_ci(a, 'S2_sens95/sensitivity')} | "
            f"{_ci(a, 'S2_sens95/specificity')} |"
        )
    L.append("")
    L.append(
        "Lecture : les intervalles ne couvrent que l'incertitude d'échantillonnage du jeu de test "
        "(624 images, un seul centre). Ils ne couvrent ni un changement d'hôpital, ni de "
        "population, ni d'appareil."
    )
    L.append("")
    L.append("### Faux positifs et faux négatifs (moyenne sur les seeds, seuil S1)")
    L.append("")
    L.append("| Modèle | Faux négatifs | Faux positifs | Vrais positifs | Vrais négatifs |")
    L.append("|---|---|---|---|---|")
    for m, r in reps.items():
        a = r["aggregate"]
        L.append(
            f"| {m} | {a['S1_youden/fn']['mean']:.1f} | {a['S1_youden/fp']['mean']:.1f} | "
            f"{a['S1_youden/tp']['mean']:.1f} | {a['S1_youden/tn']['mean']:.1f} |"
        )
    L.append("")

    comp_path = runs[BASELINE] / "analyses" / "comparison.json"
    if comp_path.exists():
        c = _load(comp_path)
        L.append("## Comparaison à resnet18 (AUC apparié)")
        L.append("")
        L.append(
            f"Source : `{comp_path.relative_to(ROOT)}` (commit `{c['commit'][:8]}`). "
            f"Bootstrap apparié sur la différence d'AUC moyenne entre seeds, {c['n_boot']} "
            "réplicats, correction de Holm sur "
            f"{c['n_comparisons']} comparaisons."
        )
        L.append("")
        L.append(
            "| Modèle | Différence d'AUC | IC 95 % | IC corrigé | p (Holm) | Verdict | "
            "DeLong (moyenne des seeds) p | McNemar S1 p |"
        )
        L.append("|---|---|---|---|---|---|---|---|")
        for x in c["comparisons"]:
            lo, hi = x["ci95"]
            alo, ahi = x["ci_adjusted"]
            L.append(
                f"| {x['model']} | {x['auc_diff_model_minus_baseline']:+.4f} | "
                f"[{lo:+.4f} ; {hi:+.4f}] | [{alo:+.4f} ; {ahi:+.4f}] | {_p(x['p_holm'])} | "
                f"{x['wording']} | {_p(x['delong_on_seed_mean']['p'])} | "
                f"{_p(x['mcnemar_s1_on_seed_mean']['p'])} |"
            )
        L.append("")
        for x in c["comparisons"]:
            if x["established"] and x["delong_on_seed_mean"]["p"] >= c["alpha"]:
                L.append(
                    f"**Désaccord à signaler ({x['model']}).** Le critère principal établit une "
                    "différence d'AUC moyenne entre seeds, mais DeLong sur les probabilités moyennées "
                    "(un ensemble de 5 seeds) ne la retrouve pas. La différence est donc faible et "
                    "sensible à la façon de l'évaluer ; elle ne doit pas être présentée comme "
                    "robuste."
                )
                L.append("")
        L.append("Précautions de lecture :")
        L.append("")
        L.append(
            "- Le critère principal est le bootstrap apparié ; DeLong et McNemar sont "
            "complémentaires et portent sur les probabilités moyennées sur les seeds (un "
            "ensemble), pas sur chaque seed."
        )
        L.append(
            "- McNemar est évalué au seuil S1 moyen de chaque modèle : deux modèles dont les "
            "seuils donnent des spécificités différentes diffèrent presque toujours à ce test, "
            "même à AUC égale. Il ne mesure pas la qualité du classement."
        )
        L.append(
            "- Une différence « établie » est une différence statistique sur ce jeu de test, pas "
            "une preuve de supériorité clinique ni de généralisation."
        )
        L.append("")

    L.append("## Calibration (temperature scaling ajusté sur la validation)")
    L.append("")
    L.append(
        "| Modèle | ECE 10 avant | ECE 10 après | NLL avant | NLL après | Brier avant | Brier après | Température moyenne |"
    )
    L.append("|---|---|---|---|---|---|---|---|")
    for m in reps:
        cp = runs[m] / "analyses" / "calibration.json"
        if not cp.exists():
            continue
        c2 = _load(cp)["mean_over_seeds"]
        L.append(
            f"| {m} | {c2['ece10_before']:.3f} | {c2['ece10_after']:.3f} | "
            f"{c2['nll_before']:.3f} | {c2['nll_after']:.3f} | {c2['brier_before']:.3f} | "
            f"{c2['brier_after']:.3f} | {c2['temperature']:.2f} |"
        )
    L.append("")
    L.append(
        "Le temperature scaling est ajusté sur la validation puis évalué sur le test. Il n'améliore "
        "pas systématiquement le test : la prévalence de pneumonie diffère entre validation "
        "(74,2 %) et test (62,5 %), ce qui limite ce qu'une recalibration sur la validation peut "
        "corriger."
    )
    L.append("")

    rob = {
        m: _load(runs[m] / "analyses" / "robustness.json")
        for m in ORDER
        if m in runs and (runs[m] / "analyses" / "robustness.json").exists()
    }
    if rob:
        L.append("## Robustesse aux perturbations")
        L.append("")
        L.append(
            "Test uniquement ; les seuils S1 et S2 restent ceux fixés sur la validation d'images "
            "non perturbées. Moyenne des 5 seeds. Sources : "
            + ", ".join(
                f"`{(runs[m] / 'analyses' / 'robustness.json').relative_to(ROOT)}`" for m in rob
            )
            + "."
        )
        L.append("")
        L.append("### Synthèse : niveau le plus sévère de chaque perturbation")
        L.append("")
        L.append(
            "| Perturbation (niveau) | "
            + " | ".join(f"{m} AUC / sens. S1 / spéc. S1" for m in rob)
            + " |"
        )
        L.append("|---|" + "---|" * len(rob))
        first = next(iter(rob.values()))
        L.append(
            "| aucune | "
            + " | ".join(
                f"{r['clean']['auc']['mean']:.3f} / {r['clean']['S1_youden/sensitivity']['mean']:.3f} / "
                f"{r['clean']['S1_youden/specificity']['mean']:.3f}"
                for r in rob.values()
            )
            + " |"
        )
        for name, rows in first["perturbations"].items():
            lvl = rows[-1]["level"]
            cells = []
            for r in rob.values():
                x = r["perturbations"][name][-1]
                cells.append(
                    f"{x['metrics']['auc']['mean']:.3f} / {x['metrics']['S1_youden/sensitivity']['mean']:.3f} / "
                    f"{x['metrics']['S1_youden/specificity']['mean']:.3f}"
                )
            L.append(f"| {name} ({lvl}) | " + " | ".join(cells) + " |")
        L.append("")
        L.append(
            "Lecture : l'AUC (le classement des images) se dégrade peu pour des perturbations "
            "modérées, mais les seuils fixes ne tiennent pas. Pour resnet18, densenet121 et "
            "efficientnet_b0 (bruit, flou), la spécificité s'effondre : presque tout est déclaré "
            "positif. Pour simple_cnn sous rotation de 30 degrés, c'est l'inverse : la spécificité "
            "reste haute mais la sensibilité chute (des pneumonies ne sont plus détectées), ce qui "
            "est plus grave pour un dépistage. Sous bruit fort (0,3), l'AUC tombe entre 0,48 et 0,60 "
            "selon le modèle (proche du hasard). Un seuil choisi sur des données propres ne reste pas valable "
            "sous décalage de distribution. C'est une limite majeure pour tout usage réel. "
            "Les sévérités ont été fixées à l'avance, sans les ajuster aux modèles ; la sévérité "
            "d'une perturbation n'est pas comparable d'un type à l'autre."
        )
        L.append("")
        for m, r in rob.items():
            L.append(f"### Détail : {m}")
            L.append("")
            cl = r["clean"]
            L.append(
                f"Référence sans perturbation : AUC {cl['auc']['mean']:.3f}, spécificité S1 "
                f"{cl['S1_youden/specificity']['mean']:.3f}, sensibilité S1 "
                f"{cl['S1_youden/sensitivity']['mean']:.3f}."
            )
            L.append("")
            L.append(
                "| Perturbation | Niveau | AUC | Sensibilité S1 | Spécificité S1 | Spécificité S2 |"
            )
            L.append("|---|---|---|---|---|---|")
            for name, rows in r["perturbations"].items():
                for x in rows:
                    m2 = x["metrics"]
                    L.append(
                        f"| {name} | {x['level']} | {m2['auc']['mean']:.3f} | "
                        f"{m2['S1_youden/sensitivity']['mean']:.3f} | "
                        f"{m2['S1_youden/specificity']['mean']:.3f} | "
                        f"{m2['S2_sens95/specificity']['mean']:.3f} |"
                    )
            L.append("")

    san = {
        m: _load(runs[m] / "analyses" / "gradcam_sanity.json")
        for m in ORDER
        if m in runs and (runs[m] / "analyses" / "gradcam_sanity.json").exists()
    }
    if san:
        L.append("## Test de sanité de Grad-CAM")
        L.append("")
        L.append(
            "Randomisation en cascade des couches convolutives et linéaires (Adebayo et al., "
            "2018), 16 images fixes du test, critère fixé à l'avance : corrélation de rang moyenne "
            "< 0,3 une fois tous les poids randomisés. Sources : "
            + ", ".join(
                f"`{(runs[m] / 'analyses' / 'gradcam_sanity.json').relative_to(ROOT)}`" for m in san
            )
            + "."
        )
        L.append("")
        L.append("| Modèle | Seed | Corrélation de rang à 100 % | Images exploitables | Verdict |")
        L.append("|---|---|---|---|---|")
        for m, sd in san.items():
            for i, ps in enumerate(sd["per_seed"]):
                last = ps["rows"][-1]
                rc = last["rank_corr_mean"]
                verdict = {
                    True: "critère satisfait",
                    False: "critère non satisfait",
                    None: "non concluant",
                }[ps["passes"]]
                L.append(
                    f"| {m} | {i} | {'n/a' if rc is None else f'{rc:.3f}'} | "
                    f"{last['n_valid_images']} | {verdict} |"
                )
        L.append("")
        for m, sd in san.items():
            L.append(
                f"- {m} : critère satisfait pour toutes les seeds : "
                f"**{'oui' if sd['passes_all_seeds'] else 'non'}**."
            )
        L.append("")
        L.append(
            "Ce test est qualitatif et ne démontre pas la validité clinique des cartes ; tant "
            "qu'il n'est pas satisfait pour toutes les seeds, les cartes ne sont présentées qu'à "
            "titre indicatif."
        )
        L.append("")

    L.append("## Ce que ces résultats ne montrent pas")
    L.append("")
    for t in (
        "Aucune validation clinique, aucune étude sur des patients en conditions réelles.",
        "Un seul jeu de données public (PneumoniaMNIST, radiographies pédiatriques d'un seul "
        "centre) : la généralisation à d'autres hôpitaux, appareils ou populations n'est pas "
        "évaluée. Le décalage de domaine (ChestMNIST) n'est pas implémenté.",
        "La prévalence diffère entre validation et test, ce qui affecte seuils et calibration.",
        "10 doublons confirmés entre entraînement et validation (aucun entre entraînement et test), voir DATASETS.md.",
        "Les comparaisons entre modèles ne valent que pour ce jeu de test et ces 5 seeds.",
    ):
        L.append(f"- {t}")
    L.append("")
    return "\n".join(L)


START = "<!-- RESULTS:START -->"
END = "<!-- RESULTS:END -->"


def summary() -> str:
    runs = _runs()
    L = [
        "| Modèle | AUC [IC 95 %] | Sensibilité S1 | Spécificité S1 | Rapport |",
        "|---|---|---|---|---|",
    ]
    for m in ORDER:
        if m not in runs:
            continue
        r = _load(runs[m] / "report.json")
        a = r["aggregate"]
        L.append(
            f"| {m} | {_ci(a, 'auc')} | {a['S1_youden/sensitivity']['mean']:.3f} | "
            f"{a['S1_youden/specificity']['mean']:.3f} | `{r['run_id']}` |"
        )
    return "\n".join(L)


def patch_readme() -> None:
    p = ROOT / "README.md"
    t = p.read_text(encoding="utf-8")
    a, b = t.index(START) + len(START), t.index(END)
    p.write_text(t[:a] + "\n" + summary() + "\n" + t[b:], encoding="utf-8")


if __name__ == "__main__":
    out = ROOT / "docs" / "RESULTS.md"
    out.write_text(build(), encoding="utf-8")
    patch_readme()
    print(f"écrit : {out}")
