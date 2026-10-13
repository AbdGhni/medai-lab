# Résultats

Ce fichier est généré par `scripts/make_results.py` à partir des rapports versionnés dans `reports/`. Aucune valeur n'est saisie à la main. Prototype de recherche : ne pas utiliser pour un diagnostic ou une décision clinique.

## Protocole en bref

PneumoniaMNIST 224x224, jeu de test utilisé une fois par seed, 5 seeds, seuils choisis sur la validation (S1 : Youden ; S2 : sensibilité >= 0,95 sur la validation), intervalles de confiance à 95 % par bootstrap stratifié (2000 réplicats). Détails : [EVAL_PROTOCOL.md](EVAL_PROTOCOL.md).

## Rapports sources

| Modèle | run_id | Protocole | Commit | Matériel |
|---|---|---|---|---|
| resnet18 | `resnet18-04e08eb9-20261012T184310Z` | 1.0 | `61eab74a` | Tesla T4 |
| simple_cnn | `simple_cnn-a7e858f0-20261013T093409Z` | 1.2 | `aae94554` | Tesla T4 |
| densenet121 | `densenet121-49378193-20261013T100113Z` | 1.2 | `aae94554` | Tesla T4 |
| efficientnet_b0 | `efficientnet_b0-2f9becc1-20261013T212542Z` | 1.2 | `cc20e0e6` | Tesla T4 |

Le rapport de resnet18 a été produit sous le protocole 1.0 (avant l'ajout de l'enregistrement des prédictions de validation et des analyses de la phase 4) ; les règles d'évaluation de la section ci-dessus étaient déjà les mêmes.

## Performance sur le jeu de test (moyenne des 5 seeds, IC 95 %)

| Modèle | AUC | AUC-PR | Sensibilité S1 | Spécificité S1 | Sensibilité S2 | Spécificité S2 |
|---|---|---|---|---|---|---|
| resnet18 | 0.985 [0.977 ; 0.991] | 0.988 [0.981 ; 0.994] | 0.997 [0.993 ; 0.999] | 0.815 [0.771 ; 0.854] | 0.982 [0.972 ; 0.990] | 0.893 [0.857 ; 0.926] |
| simple_cnn | 0.948 [0.930 ; 0.965] | 0.966 [0.952 ; 0.978] | 0.951 [0.930 ; 0.968] | 0.778 [0.726 ; 0.822] | 0.973 [0.956 ; 0.987] | 0.680 [0.624 ; 0.731] |
| densenet121 | 0.992 [0.984 ; 0.997] | 0.994 [0.986 ; 0.998] | 0.995 [0.989 ; 0.999] | 0.868 [0.829 ; 0.903] | 0.984 [0.973 ; 0.992] | 0.935 [0.908 ; 0.960] |
| efficientnet_b0 | 0.985 [0.976 ; 0.993] | 0.986 [0.976 ; 0.994] | 0.995 [0.991 ; 0.998] | 0.823 [0.780 ; 0.861] | 0.975 [0.964 ; 0.986] | 0.926 [0.897 ; 0.954] |

Lecture : les intervalles ne couvrent que l'incertitude d'échantillonnage du jeu de test (624 images, un seul centre). Ils ne couvrent ni un changement d'hôpital, ni de population, ni d'appareil.

### Faux positifs et faux négatifs (moyenne sur les seeds, seuil S1)

| Modèle | Faux négatifs | Faux positifs | Vrais positifs | Vrais négatifs |
|---|---|---|---|---|
| resnet18 | 1.2 | 43.4 | 388.8 | 190.6 |
| simple_cnn | 19.2 | 52.0 | 370.8 | 182.0 |
| densenet121 | 1.8 | 31.0 | 388.2 | 203.0 |
| efficientnet_b0 | 1.8 | 41.4 | 388.2 | 192.6 |

## Comparaison à resnet18 (AUC apparié)

Source : `reports/resnet18-04e08eb9-20261012T184310Z/analyses/comparison.json` (commit `2664cbd7`). Bootstrap apparié sur la différence d'AUC moyenne entre seeds, 2000 réplicats, correction de Holm sur 3 comparaisons.

| Modèle | Différence d'AUC | IC 95 % | IC corrigé | p (Holm) | Verdict | DeLong (moyenne des seeds) p | McNemar S1 p |
|---|---|---|---|---|---|---|---|
| simple_cnn | -0.0364 | [-0.0521 ; -0.0219] | [-0.0553 ; -0.0189] | 0,003 | différence établie (après correction de Holm) | < 0,001 | 0,007 |
| densenet121 | +0.0071 | [+0.0028 ; +0.0119] | [+0.0015 ; +0.0132] | 0,004 | différence établie (après correction de Holm) | 0,254 | < 0,001 |
| efficientnet_b0 | +0.0005 | [-0.0045 ; +0.0048] | [-0.0057 ; +0.0057] | 0,840 | pas de différence démontrée | 0,710 | 0,008 |

**Désaccord à signaler (densenet121).** Le critère principal établit une différence d'AUC moyenne entre seeds, mais DeLong sur les probabilités moyennées (un ensemble de 5 seeds) ne la retrouve pas. La différence est donc faible et sensible à la façon de l'évaluer ; elle ne doit pas être présentée comme robuste.

Précautions de lecture :

- Le critère principal est le bootstrap apparié ; DeLong et McNemar sont complémentaires et portent sur les probabilités moyennées sur les seeds (un ensemble), pas sur chaque seed.
- McNemar est évalué au seuil S1 moyen de chaque modèle : deux modèles dont les seuils donnent des spécificités différentes diffèrent presque toujours à ce test, même à AUC égale. Il ne mesure pas la qualité du classement.
- Une différence « établie » est une différence statistique sur ce jeu de test, pas une preuve de supériorité clinique ni de généralisation.

## Calibration (temperature scaling ajusté sur la validation)

| Modèle | ECE 10 avant | ECE 10 après | NLL avant | NLL après | Brier avant | Brier après | Température moyenne |
|---|---|---|---|---|---|---|---|
| resnet18 | 0.051 | 0.050 | 0.200 | 0.226 | 0.051 | 0.052 | 1.08 |
| simple_cnn | 0.038 | 0.043 | 0.287 | 0.292 | 0.083 | 0.082 | 0.82 |
| densenet121 | 0.037 | 0.038 | 0.149 | 0.145 | 0.035 | 0.035 | 1.03 |
| efficientnet_b0 | 0.070 | 0.071 | 0.403 | 0.329 | 0.060 | 0.058 | 1.44 |

Le temperature scaling est ajusté sur la validation puis évalué sur le test. Il n'améliore pas systématiquement le test : la prévalence de pneumonie diffère entre validation (74,2 %) et test (62,5 %), ce qui limite ce qu'une recalibration sur la validation peut corriger.

## Robustesse de resnet18 aux perturbations

Source : `reports/resnet18-04e08eb9-20261012T184310Z/analyses/robustness.json`. Test uniquement ; les seuils S1 et S2 restent ceux fixés sur la validation d'images non perturbées. Moyenne des 5 seeds.

Référence sans perturbation : AUC 0.985, spécificité S1 0.815, sensibilité S1 0.997.

| Perturbation | Niveau | AUC | Sensibilité S1 | Spécificité S1 | Spécificité S2 |
|---|---|---|---|---|---|
| gaussian_noise | 0.02 | 0.983 | 0.999 | 0.562 | 0.749 |
| gaussian_noise | 0.05 | 0.966 | 1.000 | 0.137 | 0.316 |
| gaussian_noise | 0.1 | 0.879 | 1.000 | 0.002 | 0.018 |
| gaussian_noise | 0.2 | 0.703 | 1.000 | 0.000 | 0.000 |
| gaussian_noise | 0.3 | 0.601 | 1.000 | 0.000 | 0.000 |
| gaussian_blur | 0.5 | 0.984 | 0.998 | 0.773 | 0.874 |
| gaussian_blur | 1.0 | 0.982 | 1.000 | 0.590 | 0.773 |
| gaussian_blur | 1.5 | 0.977 | 1.000 | 0.377 | 0.601 |
| gaussian_blur | 2.0 | 0.971 | 1.000 | 0.208 | 0.411 |
| gaussian_blur | 3.0 | 0.947 | 1.000 | 0.038 | 0.143 |
| brightness | 0.6 | 0.974 | 1.000 | 0.331 | 0.547 |
| brightness | 0.8 | 0.985 | 0.997 | 0.718 | 0.851 |
| brightness | 1.2 | 0.982 | 0.994 | 0.799 | 0.895 |
| brightness | 1.4 | 0.966 | 0.994 | 0.606 | 0.777 |
| brightness | 1.6 | 0.941 | 0.994 | 0.403 | 0.577 |
| contrast | 0.4 | 0.976 | 1.000 | 0.444 | 0.647 |
| contrast | 0.6 | 0.984 | 0.997 | 0.685 | 0.842 |
| contrast | 0.8 | 0.985 | 0.997 | 0.774 | 0.883 |
| contrast | 1.2 | 0.984 | 0.996 | 0.828 | 0.901 |
| contrast | 1.5 | 0.984 | 0.995 | 0.823 | 0.905 |
| jpeg | 90 | 0.985 | 0.998 | 0.791 | 0.883 |
| jpeg | 70 | 0.984 | 0.998 | 0.742 | 0.856 |
| jpeg | 50 | 0.983 | 0.998 | 0.707 | 0.841 |
| jpeg | 30 | 0.982 | 0.999 | 0.639 | 0.791 |
| jpeg | 10 | 0.971 | 1.000 | 0.303 | 0.524 |
| rotation | 5 | 0.984 | 0.997 | 0.746 | 0.862 |
| rotation | 10 | 0.983 | 0.996 | 0.715 | 0.855 |
| rotation | 15 | 0.982 | 0.997 | 0.615 | 0.813 |
| rotation | 20 | 0.975 | 0.997 | 0.444 | 0.676 |
| rotation | 30 | 0.962 | 0.999 | 0.134 | 0.355 |

Lecture : l'AUC (le classement des images) se dégrade peu pour des perturbations modérées, mais la spécificité aux seuils fixes chute fortement : le modèle déclare alors presque tout positif. Un seuil choisi sur des données propres ne reste pas valable sous décalage de distribution. C'est une limite majeure pour tout usage réel.

## Test de sanité de Grad-CAM (resnet18)

Source : `reports/resnet18-04e08eb9-20261012T184310Z/analyses/gradcam_sanity.json`. Randomisation en cascade des couches convolutives et linéaires (Adebayo et al., 2018), 16 images fixes du test, critère fixé à l'avance : corrélation de rang moyenne < 0,3 une fois tous les poids randomisés.

| Seed | Corrélation de rang à 100 % | Images exploitables | Verdict |
|---|---|---|---|
| 0 | 0.236 | 14 | critère satisfait |
| 1 | -0.022 | 13 | critère satisfait |
| 2 | -0.114 | 15 | critère satisfait |
| 3 | 0.000 | 16 | critère satisfait |
| 4 | 0.308 | 16 | critère non satisfait |

Critère satisfait pour toutes les seeds : **non**. Ce test est qualitatif et ne démontre pas la validité clinique des cartes ; tant qu'il n'est pas satisfait pour toutes les seeds, les cartes ne sont présentées qu'à titre indicatif.

## Ce que ces résultats ne montrent pas

- Aucune validation clinique, aucune étude sur des patients en conditions réelles.
- Un seul jeu de données public (PneumoniaMNIST, radiographies pédiatriques d'un seul centre) : la généralisation à d'autres hôpitaux, appareils ou populations n'est pas évaluée. Le décalage de domaine (ChestMNIST) n'est pas implémenté.
- La prévalence diffère entre validation et test, ce qui affecte seuils et calibration.
- 10 doublons confirmés entre entraînement et validation (aucun entre entraînement et test), voir DATASETS.md.
- Les comparaisons entre modèles ne valent que pour ce jeu de test et ces 5 seeds.
