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

## Robustesse aux perturbations

Test uniquement ; les seuils S1 et S2 restent ceux fixés sur la validation d'images non perturbées. Moyenne des 5 seeds. Sources : `reports/resnet18-04e08eb9-20261012T184310Z/analyses/robustness.json`, `reports/simple_cnn-a7e858f0-20261013T093409Z/analyses/robustness.json`, `reports/densenet121-49378193-20261013T100113Z/analyses/robustness.json`, `reports/efficientnet_b0-2f9becc1-20261013T212542Z/analyses/robustness.json`.

### Synthèse : niveau le plus sévère de chaque perturbation

| Perturbation (niveau) | resnet18 AUC / sens. S1 / spéc. S1 | simple_cnn AUC / sens. S1 / spéc. S1 | densenet121 AUC / sens. S1 / spéc. S1 | efficientnet_b0 AUC / sens. S1 / spéc. S1 |
|---|---|---|---|---|
| aucune | 0.985 / 0.997 / 0.815 | 0.948 / 0.951 / 0.778 | 0.992 / 0.995 / 0.868 | 0.985 / 0.995 / 0.823 |
| gaussian_noise (0.3) | 0.601 / 1.000 / 0.000 | 0.489 / 1.000 / 0.000 | 0.483 / 1.000 / 0.000 | 0.504 / 0.676 / 0.332 |
| gaussian_blur (3.0) | 0.947 / 1.000 / 0.038 | 0.916 / 1.000 / 0.002 | 0.957 / 1.000 / 0.016 | 0.667 / 0.990 / 0.022 |
| brightness (1.6) | 0.941 / 0.994 / 0.403 | 0.847 / 0.858 / 0.609 | 0.964 / 0.997 / 0.454 | 0.913 / 0.952 / 0.509 |
| contrast (1.5) | 0.984 / 0.995 / 0.823 | 0.944 / 0.831 / 0.926 | 0.989 / 0.994 / 0.862 | 0.984 / 0.986 / 0.833 |
| jpeg (10) | 0.971 / 1.000 / 0.303 | 0.936 / 0.855 / 0.878 | 0.980 / 0.998 / 0.452 | 0.928 / 0.983 / 0.518 |
| rotation (30) | 0.962 / 0.999 / 0.134 | 0.907 / 0.379 / 0.979 | 0.978 / 0.997 / 0.462 | 0.967 / 0.944 / 0.799 |

Lecture : l'AUC (le classement des images) se dégrade peu pour des perturbations modérées, mais les seuils fixes ne tiennent pas. Pour resnet18, densenet121 et efficientnet_b0 (bruit, flou), la spécificité s'effondre : presque tout est déclaré positif. Pour simple_cnn sous rotation de 30 degrés, c'est l'inverse : la spécificité reste haute mais la sensibilité chute (des pneumonies ne sont plus détectées), ce qui est plus grave pour un dépistage. Sous bruit fort (0,3), l'AUC tombe entre 0,48 et 0,60 selon le modèle (proche du hasard). Un seuil choisi sur des données propres ne reste pas valable sous décalage de distribution. C'est une limite majeure pour tout usage réel. Les sévérités ont été fixées à l'avance, sans les ajuster aux modèles ; la sévérité d'une perturbation n'est pas comparable d'un type à l'autre.

### Détail : resnet18

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

### Détail : simple_cnn

Référence sans perturbation : AUC 0.948, spécificité S1 0.778, sensibilité S1 0.951.

| Perturbation | Niveau | AUC | Sensibilité S1 | Spécificité S1 | Spécificité S2 |
|---|---|---|---|---|---|
| gaussian_noise | 0.02 | 0.933 | 0.999 | 0.032 | 0.013 |
| gaussian_noise | 0.05 | 0.714 | 1.000 | 0.000 | 0.000 |
| gaussian_noise | 0.1 | 0.565 | 1.000 | 0.000 | 0.000 |
| gaussian_noise | 0.2 | 0.519 | 1.000 | 0.000 | 0.000 |
| gaussian_noise | 0.3 | 0.489 | 1.000 | 0.000 | 0.000 |
| gaussian_blur | 0.5 | 0.946 | 0.948 | 0.776 | 0.685 |
| gaussian_blur | 1.0 | 0.940 | 0.973 | 0.622 | 0.509 |
| gaussian_blur | 1.5 | 0.934 | 0.987 | 0.363 | 0.232 |
| gaussian_blur | 2.0 | 0.929 | 0.998 | 0.137 | 0.062 |
| gaussian_blur | 3.0 | 0.916 | 1.000 | 0.002 | 0.000 |
| brightness | 0.6 | 0.895 | 1.000 | 0.000 | 0.000 |
| brightness | 0.8 | 0.936 | 0.993 | 0.263 | 0.144 |
| brightness | 1.2 | 0.935 | 0.885 | 0.851 | 0.769 |
| brightness | 1.4 | 0.889 | 0.848 | 0.754 | 0.645 |
| brightness | 1.6 | 0.847 | 0.858 | 0.609 | 0.498 |
| contrast | 0.4 | 0.905 | 1.000 | 0.007 | 0.001 |
| contrast | 0.6 | 0.937 | 0.993 | 0.235 | 0.131 |
| contrast | 0.8 | 0.946 | 0.981 | 0.579 | 0.456 |
| contrast | 1.2 | 0.948 | 0.908 | 0.879 | 0.803 |
| contrast | 1.5 | 0.944 | 0.831 | 0.926 | 0.872 |
| jpeg | 90 | 0.947 | 0.949 | 0.782 | 0.674 |
| jpeg | 70 | 0.946 | 0.951 | 0.773 | 0.664 |
| jpeg | 50 | 0.947 | 0.953 | 0.766 | 0.660 |
| jpeg | 30 | 0.946 | 0.954 | 0.768 | 0.647 |
| jpeg | 10 | 0.936 | 0.855 | 0.878 | 0.780 |
| rotation | 5 | 0.948 | 0.919 | 0.851 | 0.742 |
| rotation | 10 | 0.949 | 0.884 | 0.897 | 0.823 |
| rotation | 15 | 0.946 | 0.766 | 0.941 | 0.891 |
| rotation | 20 | 0.937 | 0.594 | 0.967 | 0.926 |
| rotation | 30 | 0.907 | 0.379 | 0.979 | 0.934 |

### Détail : densenet121

Référence sans perturbation : AUC 0.992, spécificité S1 0.868, sensibilité S1 0.995.

| Perturbation | Niveau | AUC | Sensibilité S1 | Spécificité S1 | Spécificité S2 |
|---|---|---|---|---|---|
| gaussian_noise | 0.02 | 0.986 | 0.998 | 0.703 | 0.855 |
| gaussian_noise | 0.05 | 0.965 | 1.000 | 0.258 | 0.513 |
| gaussian_noise | 0.1 | 0.814 | 1.000 | 0.002 | 0.025 |
| gaussian_noise | 0.2 | 0.474 | 1.000 | 0.000 | 0.000 |
| gaussian_noise | 0.3 | 0.483 | 1.000 | 0.000 | 0.000 |
| gaussian_blur | 0.5 | 0.991 | 0.997 | 0.815 | 0.912 |
| gaussian_blur | 1.0 | 0.988 | 0.999 | 0.591 | 0.787 |
| gaussian_blur | 1.5 | 0.984 | 1.000 | 0.313 | 0.572 |
| gaussian_blur | 2.0 | 0.978 | 1.000 | 0.142 | 0.378 |
| gaussian_blur | 3.0 | 0.957 | 1.000 | 0.016 | 0.130 |
| brightness | 0.6 | 0.989 | 0.999 | 0.319 | 0.541 |
| brightness | 0.8 | 0.993 | 0.997 | 0.757 | 0.886 |
| brightness | 1.2 | 0.990 | 0.992 | 0.862 | 0.934 |
| brightness | 1.4 | 0.980 | 0.993 | 0.704 | 0.841 |
| brightness | 1.6 | 0.964 | 0.997 | 0.454 | 0.652 |
| contrast | 0.4 | 0.988 | 0.998 | 0.558 | 0.732 |
| contrast | 0.6 | 0.991 | 0.996 | 0.760 | 0.886 |
| contrast | 0.8 | 0.992 | 0.996 | 0.829 | 0.925 |
| contrast | 1.2 | 0.991 | 0.995 | 0.874 | 0.938 |
| contrast | 1.5 | 0.989 | 0.994 | 0.862 | 0.940 |
| jpeg | 90 | 0.992 | 0.996 | 0.838 | 0.920 |
| jpeg | 70 | 0.990 | 0.997 | 0.803 | 0.903 |
| jpeg | 50 | 0.990 | 0.997 | 0.775 | 0.890 |
| jpeg | 30 | 0.988 | 0.997 | 0.723 | 0.863 |
| jpeg | 10 | 0.980 | 0.998 | 0.452 | 0.678 |
| rotation | 5 | 0.991 | 0.997 | 0.814 | 0.915 |
| rotation | 10 | 0.991 | 0.996 | 0.800 | 0.923 |
| rotation | 15 | 0.990 | 0.997 | 0.768 | 0.914 |
| rotation | 20 | 0.987 | 0.997 | 0.687 | 0.881 |
| rotation | 30 | 0.978 | 0.997 | 0.462 | 0.765 |

### Détail : efficientnet_b0

Référence sans perturbation : AUC 0.985, spécificité S1 0.823, sensibilité S1 0.995.

| Perturbation | Niveau | AUC | Sensibilité S1 | Spécificité S1 | Spécificité S2 |
|---|---|---|---|---|---|
| gaussian_noise | 0.02 | 0.958 | 1.000 | 0.308 | 0.593 |
| gaussian_noise | 0.05 | 0.465 | 0.680 | 0.254 | 0.501 |
| gaussian_noise | 0.1 | 0.502 | 0.737 | 0.256 | 0.355 |
| gaussian_noise | 0.2 | 0.509 | 0.725 | 0.297 | 0.299 |
| gaussian_noise | 0.3 | 0.504 | 0.676 | 0.332 | 0.333 |
| gaussian_blur | 0.5 | 0.985 | 0.997 | 0.804 | 0.926 |
| gaussian_blur | 1.0 | 0.969 | 0.991 | 0.708 | 0.867 |
| gaussian_blur | 1.5 | 0.920 | 0.986 | 0.403 | 0.701 |
| gaussian_blur | 2.0 | 0.835 | 0.998 | 0.156 | 0.466 |
| gaussian_blur | 3.0 | 0.667 | 0.990 | 0.022 | 0.247 |
| brightness | 0.6 | 0.956 | 0.998 | 0.506 | 0.722 |
| brightness | 0.8 | 0.985 | 0.995 | 0.795 | 0.915 |
| brightness | 1.2 | 0.986 | 0.986 | 0.850 | 0.943 |
| brightness | 1.4 | 0.968 | 0.958 | 0.724 | 0.932 |
| brightness | 1.6 | 0.913 | 0.952 | 0.509 | 0.871 |
| contrast | 0.4 | 0.925 | 0.993 | 0.517 | 0.725 |
| contrast | 0.6 | 0.982 | 0.996 | 0.795 | 0.898 |
| contrast | 0.8 | 0.987 | 0.996 | 0.824 | 0.925 |
| contrast | 1.2 | 0.983 | 0.994 | 0.832 | 0.932 |
| contrast | 1.5 | 0.984 | 0.986 | 0.833 | 0.937 |
| jpeg | 90 | 0.985 | 0.997 | 0.784 | 0.915 |
| jpeg | 70 | 0.983 | 0.996 | 0.721 | 0.901 |
| jpeg | 50 | 0.982 | 0.997 | 0.697 | 0.889 |
| jpeg | 30 | 0.976 | 0.997 | 0.662 | 0.870 |
| jpeg | 10 | 0.928 | 0.983 | 0.518 | 0.815 |
| rotation | 5 | 0.989 | 0.996 | 0.815 | 0.930 |
| rotation | 10 | 0.989 | 0.986 | 0.869 | 0.955 |
| rotation | 15 | 0.986 | 0.981 | 0.854 | 0.959 |
| rotation | 20 | 0.982 | 0.977 | 0.844 | 0.957 |
| rotation | 30 | 0.967 | 0.944 | 0.799 | 0.955 |

## Test de sanité de Grad-CAM

Randomisation en cascade des couches convolutives et linéaires (Adebayo et al., 2018), 16 images fixes du test, critère fixé à l'avance : corrélation de rang moyenne < 0,3 une fois tous les poids randomisés. Sources : `reports/resnet18-04e08eb9-20261012T184310Z/analyses/gradcam_sanity.json`, `reports/simple_cnn-a7e858f0-20261013T093409Z/analyses/gradcam_sanity.json`, `reports/densenet121-49378193-20261013T100113Z/analyses/gradcam_sanity.json`, `reports/efficientnet_b0-2f9becc1-20261013T212542Z/analyses/gradcam_sanity.json`.

| Modèle | Seed | Corrélation de rang à 100 % | Images exploitables | Verdict |
|---|---|---|---|---|
| resnet18 | 0 | 0.236 | 14 | critère satisfait |
| resnet18 | 1 | -0.022 | 13 | critère satisfait |
| resnet18 | 2 | -0.114 | 15 | critère satisfait |
| resnet18 | 3 | 0.000 | 16 | critère satisfait |
| resnet18 | 4 | 0.308 | 16 | critère non satisfait |
| simple_cnn | 0 | -0.036 | 16 | critère satisfait |
| simple_cnn | 1 | 0.131 | 16 | critère satisfait |
| simple_cnn | 2 | 0.071 | 16 | critère satisfait |
| simple_cnn | 3 | 0.005 | 16 | critère satisfait |
| simple_cnn | 4 | 0.091 | 16 | critère satisfait |
| densenet121 | 0 | 0.155 | 11 | critère satisfait |
| densenet121 | 1 | 0.119 | 11 | critère satisfait |
| densenet121 | 2 | 0.438 | 11 | critère non satisfait |
| densenet121 | 3 | -0.318 | 11 | critère satisfait |
| densenet121 | 4 | 0.090 | 11 | critère satisfait |
| efficientnet_b0 | 0 | 0.000 | 16 | critère satisfait |
| efficientnet_b0 | 1 | -0.255 | 16 | critère satisfait |
| efficientnet_b0 | 2 | -0.619 | 15 | critère satisfait |
| efficientnet_b0 | 3 | 0.283 | 13 | critère satisfait |
| efficientnet_b0 | 4 | -0.168 | 16 | critère satisfait |

- resnet18 : critère satisfait pour toutes les seeds : **non**.
- simple_cnn : critère satisfait pour toutes les seeds : **oui**.
- densenet121 : critère satisfait pour toutes les seeds : **non**.
- efficientnet_b0 : critère satisfait pour toutes les seeds : **oui**.

Ce test est qualitatif et ne démontre pas la validité clinique des cartes ; tant qu'il n'est pas satisfait pour toutes les seeds, les cartes ne sont présentées qu'à titre indicatif.

## Ce que ces résultats ne montrent pas

- Aucune validation clinique, aucune étude sur des patients en conditions réelles.
- Un seul jeu de données public (PneumoniaMNIST, radiographies pédiatriques d'un seul centre) : la généralisation à d'autres hôpitaux, appareils ou populations n'est pas évaluée. Le décalage de domaine (ChestMNIST) n'est pas implémenté.
- La prévalence diffère entre validation et test, ce qui affecte seuils et calibration.
- 10 doublons confirmés entre entraînement et validation (aucun entre entraînement et test), voir DATASETS.md.
- Les comparaisons entre modèles ne valent que pour ce jeu de test et ces 5 seeds.
