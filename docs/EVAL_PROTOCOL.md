# Protocole d'évaluation (pré-enregistré)

Version 1.2 - 12/10/2026

Historique
- 1.0 (12/10/2026) : version initiale, avant tout entraînement.
- 1.1 (12/10/2026) : précision de la méthode de détection de doublons (section 2) et ajout des constats de la fiche de données réelle. Aucun entraînement n'avait été exécuté ; aucune règle d'analyse (métriques, seuils, tests) n'est modifiée.

- 1.2 (12/10/2026) : précisions des analyses de phase 4 (sections 7 à 11), écrites avant tout résultat entraîné. Les règles du protocole principal (données, métriques, seuils, bootstrap de la section 8, premier alinéa) ne changent pas. Détail des changements ci-dessous.

Changements de la version 1.2
- Section 8 : le critère "l'intervalle corrigé exclut zéro" est remplacé par "p-valeur bootstrap ajustée par Holm < 0,05", plus simple à appliquer à trois comparaisons. L'intervalle à 95 % non corrigé et un intervalle conservateur de niveau 1 - 0,05/3 sont tous deux rapportés avec l'estimation de l'effet.
- Section 7 : les prédictions de validation sont archivées avec les rapports (predictions.npz) pour ajuster la température sans toucher au test.
- Section 9 : bootstrap de robustesse à 500 réplicats (au lieu de 2000) pour limiter le coût ; valeur consignée dans chaque fichier d'analyse.
- Section 10 : critère du test de sanité fixé avant toute exécution (voir cette section).
- Section 11 : non implémentée à ce jour (voir cette section).

Ce protocole est figé avant tout entraînement. Toute modification ultérieure est faite par une nouvelle version datée, avec la raison du changement, et les résultats obtenus sous l'ancienne version restent publiés. Les analyses non prévues ici sont étiquetées "exploratoires" dans les rapports.

## 1. Tâche et données

- Tâche : classification binaire d'une radiographie thoracique, classe positive = pneumonie, classe négative = normal.
- Jeu de données : PneumoniaMNIST (MedMNIST v2/+), taille 224x224, niveaux de gris, splits train / validation / test fournis par MedMNIST. Les effectifs sont lus programmatiquement et écrits dans la fiche de données ; ils ne sont pas recopiés de mémoire.
- Le jeu de test n'est utilisé qu'une fois par modèle et par seed, pour le rapport final. Il n'est jamais utilisé pour choisir un hyperparamètre, une epoch, un seuil ou un modèle.

## 2. Contrôles de validité des données (avant entraînement)

- Vérification du checksum MD5 publié par MedMNIST ; empreinte SHA-256 du fichier enregistrée.
- Effectifs et prévalence par split, lus dans les données.
- Détection de doublons entre splits en deux temps : candidats par hash perceptuel (pHash 8x8, distance de Hamming <= 4), puis confirmation par corrélation de Pearson des pixels (>= 0,99). Le pHash seul est trop grossier pour des radiographies thoraciques, qui se ressemblent toutes à basse fréquence.
- Si des doublons confirmés existent entre entraînement et test, ils sont listés et une analyse de sensibilité sans ces images est ajoutée.

Constats de la fiche de données (reports/datasheets/pneumoniamnist_224.json, générée par le pipeline, taille 224) :
- Effectifs : entraînement 4708 (3494 pneumonie), validation 524 (389 pneumonie), test 624 (390 pneumonie).
- Prévalence de pneumonie : environ 74,2 % en entraînement, 74,2 % en validation, 62,5 % en test. Les seuils choisis sur la validation sont donc appliqués à un test de prévalence plus faible : sensibilité et spécificité sont comparables, mais la précision et le F1 ne le sont pas directement entre validation et test.
- Entraînement contre test : 45 paires candidates, 0 doublon confirmé (corrélation maximale 0,86).
- Validation contre test : 5 paires candidates, 0 doublon confirmé.
- Entraînement contre validation : 39 paires candidates, 10 doublons confirmés (corrélation >= 0,99), dont 8 identiques au pixel près. La validation n'est donc pas indépendante de l'entraînement. Conséquence : l'AUC de validation (utilisée pour choisir l'epoch) et les seuils peuvent être légèrement optimistes. Le test, lui, ne contient aucun doublon confirmé de l'entraînement.
- Limite connue, à rappeler dans chaque rapport : jeu pédiatrique, centre unique ; MedMNIST tire la validation au hasard (9:1) dans le jeu d'entraînement source, sans garantie de séparation par patient ; la séparation par patient entre entraînement et test n'est pas vérifiable avec les métadonnées disponibles.

## 3. Modèles comparés

| Identifiant | Description |
|---|---|
| simple_cnn | CNN de 4 blocs convolutifs entraîné depuis zéro (référence basse) |
| resnet18 | ResNet-18, poids ImageNet, couche finale remplacée (modèle de référence de la comparaison) |
| densenet121 | DenseNet-121, poids ImageNet |
| efficientnet_b0 | EfficientNet-B0 (timm), poids ImageNet |

Les poids ImageNet proviennent de torchvision et timm, dont les licences sont consignées dans DATASETS.md. Les entrées en niveaux de gris sont répliquées sur 3 canaux et normalisées avec les statistiques ImageNet.

## 4. Entraînement

- Seeds : 0, 1, 2, 3, 4 (5 entraînements indépendants par modèle).
- Perte : entropie croisée binaire avec pondération de classe calculée sur le train.
- Optimiseur : AdamW, planificateur cosinus, taux d'apprentissage et décroissance de poids fixés dans la configuration de chaque modèle. Une recherche d'hyperparamètres éventuelle se fait uniquement sur la validation, avec un budget identique pour tous les modèles (même nombre d'essais), et est documentée.
- Augmentation : translations et rotations faibles, variation de luminosité/contraste faible. Pas de retournement horizontal (la latéralité du cœur est une information anatomique).
- Sélection de l'epoch : meilleure AUC de validation ; arrêt anticipé avec patience fixée dans la configuration.
- Déterminisme : seeds Python, NumPy, PyTorch ; algorithmes déterministes activés quand disponibles ; matériel et versions enregistrés. Les résultats de référence sont tous produits sur le même matériel.

## 5. Métriques

Calculées sur le jeu de test, classe positive = pneumonie :
- AUC ROC (métrique primaire) ; AUC précision-rappel (secondaire) ;
- sensibilité (rappel), spécificité, précision (valeur prédictive positive), F1, exactitude équilibrée ;
- nombre de vrais positifs, faux positifs, vrais négatifs, faux négatifs ;
- Brier, ECE (voir section 7).

## 6. Seuils de décision

Deux points de fonctionnement, tous deux fixés sur la validation de chaque seed puis appliqués au test sans modification :
- S1 : seuil maximisant l'indice de Youden (sensibilité + spécificité - 1) ;
- S2 : plus grand seuil donnant une sensibilité de validation >= 0,95 (scénario de dépistage où les faux négatifs sont coûteux).

Le seuil 0,5 est rapporté à titre indicatif seulement.

## 7. Calibration

- ECE avec 10 intervalles de largeur égale, et variante à intervalles d'effectif égal ; diagramme de fiabilité ; score de Brier.
- Temperature scaling : un seul paramètre, ajusté sur la validation par minimisation de la log-vraisemblance négative, appliqué au test.
- Les seuils S1 et S2 sont recalculés sur les probabilités calibrées de la validation ; les deux versions (avant/après) sont rapportées.

## 8. Incertitude et comparaisons statistiques

- Variabilité d'entraînement : moyenne et écart-type des métriques sur les 5 seeds.
- Variabilité d'échantillonnage du test : bootstrap non paramétrique stratifié sur les images de test, 2000 rééchantillonnages, intervalle percentile à 95 %. Pour un modèle, chaque réplicat calcule la métrique de chaque seed sur les mêmes images rééchantillonnées puis en fait la moyenne.
- Comparaison primaire : chaque modèle contre resnet18 sur l'AUC, par bootstrap apparié (mêmes réplicats pour les deux modèles) ; différence d'AUC avec intervalle à 95 %. Trois comparaisons, correction de Holm-Bonferroni. Une différence est dite "établie" si la p-valeur bootstrap bilatérale ajustée par Holm est inférieure à 0,05 (p = 2 min(P(d <= 0), P(d >= 0)) sur 2000 réplicats, correction +1) ; sinon la formulation est "pas de différence démontrée".
- Complément : test de DeLong sur les probabilités moyennées sur les seeds (ensemble de seeds), et test de McNemar exact au seuil S1 (moyenne des seuils S1 des seeds pour chaque modèle) sur ces mêmes probabilités moyennées.
- Aucune p-valeur n'est présentée sans l'estimation de l'effet et son intervalle.

## 9. Robustesse

Perturbations appliquées uniquement au test (jamais à l'entraînement), 5 niveaux de sévérité chacune :

| Perturbation | Niveaux |
|---|---|
| Bruit gaussien (écart-type, image dans [0,1]) | 0,02 ; 0,05 ; 0,10 ; 0,20 ; 0,30 |
| Flou gaussien (sigma, en pixels) | 0,5 ; 1 ; 1,5 ; 2 ; 3 |
| Luminosité (facteur multiplicatif) | 0,6 ; 0,8 ; 1,2 ; 1,4 ; 1,6 |
| Contraste (facteur) | 0,4 ; 0,6 ; 0,8 ; 1,2 ; 1,5 |
| Compression JPEG (qualité) | 90 ; 70 ; 50 ; 30 ; 10 |
| Rotation (degrés) | 5 ; 10 ; 15 ; 20 ; 30 |

Rapport : AUC, sensibilité et spécificité aux seuils S1 et S2 (non recalculés) en fonction de la sévérité, avec intervalles bootstrap. Bootstrap : 500 réplicats, moyenne sur les seeds à chaque réplicat. Graine de bruit fixe, rotation sans redimensionnement (bords à 0). Les valeurs de niveau pourront être ajustées avant les expériences finales si elles sont jugées irréalistes ; tout ajustement est consigné dans une nouvelle version du protocole.

## 10. Explicabilité

- Méthode : Grad-CAM (et Grad-CAM++) sur la dernière couche convolutive de chaque architecture compatible.
- Test de sanité (Adebayo et al., 2018) : comparaison de la carte du modèle entraîné avec celle du même modèle dont les poids sont randomisés progressivement (de la dernière couche à la première) ; corrélation de rang et SSIM rapportées. Une méthode dont la carte ne change pas quand les poids sont randomisés est déclarée non fiable pour ce modèle.
- Réalisation (v1.2) : fractions randomisées 25 %, 50 %, 75 %, 100 % des couches Conv2d et Linear, en partant de la sortie ; les couches de normalisation ne sont pas réinitialisées. 16 images de test : les 8 premières de chaque classe, sélection fixée sans regarder les cartes. Corrélation de rang de Spearman et SSIM (fenêtre uniforme 7x7) entre la carte entraînée et la carte randomisée. Critère fixé avant exécution : corrélation de rang moyenne à 100 % de randomisation < 0,3 (ou carte constante) pour déclarer le test réussi pour une seed ; sinon la méthode est déclarée non fiable pour ce modèle. Ce critère est heuristique ; le test est qualitatif.
- Les cartes sont présentées comme des indices de localisation, pas comme des preuves de raisonnement. Aucune évaluation par un radiologue n'est faite : cette absence est mentionnée.

## 11. Décalage de domaine (analyse exploratoire, phase 4)

Statut v1.2 : non implémentée. Elle exige de télécharger ChestMNIST (volume important) et une définition d'étiquette à valider ; elle ne sera lancée qu'avec l'accord explicite de l'utilisateur. Aucun résultat n'est annoncé.

Évaluation des modèles entraînés sur PneumoniaMNIST contre l'étiquette "pneumonia" de ChestMNIST (radiographies d'adultes, étiquetées automatiquement à partir de comptes rendus). Prévalence faible : AUC et AUC précision-rappel sont les métriques principales ; les seuils S1/S2 de PneumoniaMNIST sont appliqués sans changement. Les différences de population, de définition d'étiquette et de bruit d'étiquette sont rappelées dans le rapport. Aucune conclusion causale n'est tirée.

## 12. Reproductibilité et traçabilité

Chaque rapport contient : identifiant d'exécution, commit git, hash de la configuration, hash du jeu de données, seed, versions de Python/PyTorch/bibliothèques, matériel, date. Les rapports sont immuables : une nouvelle exécution crée un nouveau rapport. L'interface lit exclusivement ces rapports.

## 13. Critères de réussite (non de "bonne performance")

Le projet n'impose aucun objectif de performance. Il est réussi si le protocole est suivi, si les résultats sont reproductibles et si les limites sont clairement présentées, quelle que soit la valeur des métriques obtenues.
