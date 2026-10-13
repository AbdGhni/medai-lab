# Fiches modèles

Format inspiré de Mitchell et al. (2019). **Prototype de recherche, pas un dispositif médical : aucune utilisation clinique.** Tous les chiffres sont dans [RESULTS.md](RESULTS.md), généré depuis les rapports de `reports/`.

## Informations communes

- **Tâche** : classification binaire pneumonie / normal sur radiographie thoracique pédiatrique, 224x224, un canal.
- **Données** : PneumoniaMNIST (MedMNIST v2, CC BY 4.0 ; source Kermany et al. 2018, Yang et al. 2023). Entraînement 4708, validation 524, test 624 images. Prévalence 74,2 % / 74,2 % / 62,5 %. Un seul centre. Détails : [DATASETS.md](DATASETS.md).
- **Entraînement** : 5 seeds (0 à 4), 15 epochs au plus, arrêt anticipé sur la validation, configuration dans `ml/configs/`. Poids initiaux ImageNet pour resnet18, densenet121 et efficientnet_b0 ; simple_cnn est entraîné depuis zéro.
- **Évaluation** : [EVAL_PROTOCOL.md](EVAL_PROTOCOL.md) (test utilisé une fois par seed, seuils choisis sur la validation, bootstrap stratifié).
- **Usage prévu** : étudier une méthode d'évaluation (métriques, calibration, robustesse, explicabilité) et la communiquer. **Hors périmètre** : diagnostic, triage, aide à la décision, tout usage sur des patients.
- **Facteurs et sous-groupes** : le jeu de données ne fournit pas de métadonnées exploitables (âge, sexe, appareil) ; aucune analyse par sous-groupe n'est possible.

## Modèles

| Modèle | Rôle | Particularités |
|---|---|---|
| resnet18 | Référence de la comparaison | Sanité Grad-CAM : 4 seeds sur 5 |
| simple_cnn | Base légère | Nettement moins bon que la référence (différence d'AUC établie) ; sous rotation forte, la sensibilité chute |
| densenet121 | Candidat | Meilleure AUC moyenne ; avantage faible ; sanité Grad-CAM : 4 seeds sur 5 |
| efficientnet_b0 | Candidat | Pas de différence démontrée avec la référence ; sanité Grad-CAM : 5 seeds sur 5 ; AUC très dégradée par un flou fort |

## Résultats et nuances (valeurs : RESULTS.md)

- Les AUC de resnet18, densenet121 et efficientnet_b0 sont proches ; seul simple_cnn est clairement en dessous.
- densenet121 : le bootstrap apparié établit une petite différence d'AUC moyenne avec resnet18 (après correction de Holm), mais DeLong sur l'ensemble des 5 seeds ne la retrouve pas. Elle n'est pas présentée comme robuste.
- Calibration : l'ECE reste de l'ordre de quelques centièmes ; le temperature scaling n'améliore pas systématiquement le test.
- Robustesse (4 modèles) : l'AUC se dégrade peu pour des perturbations modérées, mais les seuils fixes ne tiennent pas. Bruit et flou : la spécificité s'effondre (presque tout est déclaré positif). simple_cnn sous rotation de 30 degrés : la sensibilité chute (0,379 dans le rapport), c'est-à-dire que des pneumonies ne sont plus détectées. Bruit fort : AUC proche du hasard pour tous. efficientnet_b0 est le plus touché par un flou fort sur l'AUC.
- Explicabilité : test de sanité d'Adebayo et al. (2018) satisfait pour toutes les seeds avec simple_cnn et efficientnet_b0, pas pour resnet18 (1 seed sur 5 échoue) ni densenet121 (1 seed sur 5 échoue ; seulement 11 images exploitables sur 16). Les cartes Grad-CAM sont indicatives et ne prouvent pas que le modèle regarde les bonnes structures.

## Limites et risques connus

- Un seul centre, population pédiatrique : aucune garantie de généralisation. Le décalage de domaine (ChestMNIST) n'est pas évalué.
- La prévalence diffère entre validation et test ; seuils et calibration en sont affectés.
- 10 doublons confirmés entre entraînement et validation (aucun entre entraînement et test).
- Résolution 224 issue de MedMNIST : ce n'est pas la résolution clinique.
- Les performances sont celles de ce jeu de test, pas une estimation de performance en conditions réelles.

## Éthique et données

Données publiques anonymisées, sous licence ouverte ; aucune donnée de santé personnelle n'est collectée, stockée ou journalisée par l'application. L'API n'accepte que les images de la galerie (24 images du test).
