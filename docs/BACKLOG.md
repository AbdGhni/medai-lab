# Backlog

Priorités MoSCoW. Estimation en jours de travail à temps partiel. Chaque élément est terminé quand ses critères d'acceptation sont vérifiés par un test automatisé ou par une preuve archivée dans le dépôt.

## Phase 3 - MVP

| ID | Priorité | Élément | Critères d'acceptation | Est. |
|---|---|---|---|---|
| M01 | Must | Structure du monorepo, gestion des dépendances (uv, pnpm), pre-commit | Installation reproductible depuis un clone propre ; ruff, mypy, eslint passent | 0,5 |
| M02 | Must | CI GitHub Actions (lint, types, tests, build Docker) | Pipeline vert sur la branche principale ; badge dans le README | 0,5 |
| M03 | Must | Module données : téléchargement, checksum, fiche de données, doublons (pHash) | Test : checksum faux => erreur ; fiche générée avec effectifs lus des données | 1 |
| M04 | Must | Configuration d'expérience YAML validée (Pydantic) | Config invalide rejetée avec message clair ; hash de config stable | 0,5 |
| M05 | Must | Entraînement resnet18, checkpoint, journal de provenance | Même seed => mêmes métriques (CPU, 1e-6) ; test smoke < 3 min en CI | 1,5 |
| M06 | Must | Module métriques (AUC, sensibilité, spécificité, précision, F1, FP/FN) et bootstrap | Résultats identiques à scikit-learn sur cas de référence ; tests de cas limites (classe unique, constantes) | 1 |
| M07 | Must | Sélection de seuil S1/S2 sur validation | Test : aucune dépendance au jeu de test (le code ne reçoit pas le test) | 0,5 |
| M08 | Must | Rapport d'évaluation JSON immuable + schéma | Validation de schéma ; rapport rejeté si provenance incomplète | 1 |
| M09 | Must | API : /health, /models, /evaluations, /evaluations/{id} | Contrat OpenAPI figé et testé ; champ disclaimer dans chaque réponse | 1 |
| M10 | Must | API : /predict et /explain sur images de la galerie | Aucune image stockée ni journalisée (test) ; upload refusé par défaut | 1,5 |
| M11 | Must | Interface : vue d'ensemble, évaluation d'un modèle, limites et datasets | Aucune valeur affichée sans rapport (test e2e) ; bandeau de mise en garde permanent | 3 |
| M12 | Must | Docker Compose (api + web) | docker compose up fonctionne depuis un clone propre | 1 |
| M13 | Must | Entraînement du modèle de référence sur Colab et publication du premier rapport | Rapport réel, avec provenance et intervalles de confiance | 1 |

| M14 | Must | Documentation : DATASETS.md, premier model card | Sources, licences et limites présentes | 0,5 |

## Phase 4 - Fonctionnalités avancées

Statut au 14/10/2026 : A01 à A05 terminés avec de vrais rapports (4 modèles x 5 seeds ; comparaison et calibration pour les 4 modèles ; robustesse et sanité Grad-CAM pour les 4 modèles, voir RESULTS.md). A07 : page d'analyses livrée avec 4 tests e2e. A06 terminé (ChestMNIST 224, exploratoire, 4 modèles). A08 à A11 non commencés.

| ID | Priorité | Élément | Critères d'acceptation | Est. |
|---|---|---|---|---|
| A01 | Must | Modèles simple_cnn, densenet121, efficientnet_b0 | 5 seeds chacun, rapports complets | 2 |
| A02 | Must | Comparaison statistique (bootstrap apparié, Holm, DeLong, McNemar) | Tests contre implémentations de référence ; rapport de comparaison | 2 |
| A03 | Must | Calibration (ECE, Brier, fiabilité, temperature scaling) | Test sur données synthétiques à calibration connue | 1,5 |
| A04 | Must | Robustesse (6 perturbations x 5 niveaux) | Courbes par sévérité avec intervalles ; test de déterminisme des perturbations | 2 |
| A05 | Must | Grad-CAM, Grad-CAM++ et test de sanité par randomisation | Corrélation de rang et SSIM rapportées ; test que la carte change après randomisation | 2 |
| A06 | Should | Décalage de domaine ChestMNIST (exploratoire) | Rapport étiqueté exploratoire avec limites | 1,5 |
| A07 | Should | Pages d'interface : comparaison, calibration, robustesse, explicabilité | Tests e2e Playwright sur 3 parcours | 3 |
| A08 | Should | Suivi MLflow local | Comparaison d'exécutions consultable en local | 0,5 |
| A09 | Should | Scans de sécurité en CI (pip-audit, npm audit, gitleaks, Trivy) | Pas de vulnérabilité critique non justifiée | 0,5 |
| A10 | Could | Analyse par sous-groupes si des métadonnées légitimes existent | Seulement si les données le permettent ; sinon mention de l'impossibilité | 0,5 |
| A11 | Could | Export ONNX de /predict | Écart de sortie < 1e-4 avec PyTorch | 1 |

## Phase 5 - Démonstration et valorisation

| ID | Priorité | Élément | Critères d'acceptation | Est. |
|---|---|---|---|---|
| D01 | Must | Version statique du tableau de bord (rapports précalculés) | Hébergée gratuitement ; mention de recherche visible. Statut : export statique et workflow Pages manuel livrés ; publication non activée | 1 |
| D02 | Should | Backend d'inférence hébergé (Cloud Run) avec plafond de coût | Alerte budgétaire à 5 EUR active avant mise en ligne ; démarrage à froid documenté | 1 |
| D03 | Must | README professionnel avec captures et résultats issus des rapports | Chaque chiffre renvoie à un rapport | 1 |
| D04 | Must | Étude de cas pour recruteurs (CASE_STUDY.md) | Problème, démarche, résultats, limites, apprentissages | 1 |
| D05 | Should | Vidéo de démonstration courte | Moins de 3 minutes | 0,5 |
| D06 | Must | Model cards finales et datasheet | Conformes au gabarit de Mitchell et al. | 1 |

## Hors backlog (exclu volontairement)

Upload libre d'images sur la démo publique, comptes utilisateurs, stockage d'images, LLM médical, toute fonction de conseil clinique.
