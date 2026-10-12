# MedAI Lab - Cahier des charges

Version 0.1 - 12/10/2026 - Statut : proposé, à valider

## 1. Objet

MedAI Lab est une plateforme d'évaluation de modèles d'IA pour l'imagerie médicale. Elle entraîne et compare plusieurs modèles de classification sur un jeu de données public, mesure leurs performances avec une méthodologie statistique rigoureuse, analyse leur calibration, leur robustesse et leurs limites, et présente les résultats dans une interface web.

Le projet sert aussi de vitrine technique (ingénierie ML, MLOps, développement full stack) pour une candidature à un poste d'AI Engineer / ML Engineer.

## 2. Périmètre et exclusions

Dans le périmètre :
- classification binaire d'images de radiographie thoracique (pneumonie vs normal) sur PneumoniaMNIST ;
- comparaison reproductible de plusieurs architectures ;
- explicabilité (Grad-CAM) avec contrôles de validité ;
- tableau de bord d'évaluation, API, tests, Docker, CI/CD, documentation.

Hors périmètre :
- tout usage diagnostique, thérapeutique ou de décision clinique ;
- tout traitement de données personnelles de santé ;
- l'upload d'images arbitraires sur la démo publique ;
- l'entraînement sur des jeux de données soumis à un accord d'usage (MIMIC-CXR, CheXpert) ;
- le marquage CE / la conformité au règlement UE 2017/745.

Mention obligatoire, affichée dans l'interface, présente dans chaque réponse de l'API et dans le README : "Prototype de recherche. Ne pas utiliser pour un diagnostic ou une décision clinique."

## 3. Utilisateurs cibles

- U1 Recruteur / ingénieur ML qui évalue le travail : veut comprendre en 5 minutes ce qui a été fait, vérifier la rigueur, lancer le projet en une commande.
- U2 Relecteur technique : veut lire le protocole, les ADR, le code, les tests et refaire tourner une expérience.
- U3 Visiteur de la démo : veut voir des prédictions et des cartes d'explication sur des images d'exemple.

## 4. Exigences fonctionnelles

| ID | Exigence |
|---|---|
| F1 | Le pipeline télécharge PneumoniaMNIST (taille 224) via la bibliothèque medmnist, vérifie l'intégrité (checksum) et produit une fiche de données (effectifs par split et par classe, vérification de doublons entre splits). |
| F2 | Le pipeline entraîne un modèle à partir d'un fichier de configuration YAML validé, avec seed fixée, et sauvegarde poids, configuration, versions, matériel et checksum. |
| F3 | Le pipeline évalue un modèle entraîné sur le jeu de test selon le protocole EVAL_PROTOCOL.md et écrit un rapport JSON immuable et versionné (métriques avec intervalles de confiance, matrice de confusion, prédictions par image). |
| F4 | Le pipeline compare plusieurs modèles avec les tests statistiques pré-enregistrés et produit un rapport de comparaison. |
| F5 | Le pipeline calcule la calibration (ECE, Brier, diagramme de fiabilité) avant et après temperature scaling. |
| F6 | Le pipeline calcule la robustesse : performance en fonction de la sévérité de 6 perturbations. |
| F7 | Le pipeline produit des cartes Grad-CAM et exécute le test de sanité par randomisation des poids. |
| F8 | L'API expose : santé, liste des modèles, liste et détail des évaluations, comparaison, prédiction et explication sur une image de la galerie. |
| F9 | L'interface affiche : vue d'ensemble, modèles, évaluation d'un modèle, comparaison, calibration, robustesse, explicabilité, datasets et limites. |
| F10 | L'interface et l'API n'affichent jamais une valeur de performance qui ne provient pas d'un rapport généré. Sans rapport, ils affichent "aucune évaluation disponible". |
| F11 | Chaque rapport affiche sa provenance : commit git, hash de configuration, hash des données, seed, versions des bibliothèques, matériel, date. |
| F12 | Une commande unique (docker compose up) démarre l'API et l'interface en local avec les rapports et poids de référence. |

## 5. Exigences non fonctionnelles

| ID | Exigence | Critère mesurable |
|---|---|---|
| N1 | Reproductibilité | Deux exécutions avec la même seed, config, matériel et versions donnent des métriques identiques à 1e-6 près sur CPU. Sur GPU, l'écart observé est mesuré et documenté. |
| N2 | Qualité du code | ruff et mypy sans erreur ; couverture des tests >= 80 % sur ml/ et services/api. |
| N3 | Sécurité | Aucune image stockée ni journalisée ; dépendances figées par lockfile ; pip-audit, npm audit, gitleaks et Trivy sans vulnérabilité critique non justifiée. |
| N4 | Performance de la démo | Réponse de /predict < 2 s sur CPU pour une image de la galerie (mesure documentée, après démarrage). |
| N5 | Accessibilité | Interface sans erreur bloquante Lighthouse accessibilité >= 90 ; contraste AA ; navigation clavier. |
| N6 | Coût | Hébergement à 0 EUR/mois cible, plafond 10 EUR/mois, alerte budgétaire configurée avant tout déploiement. |
| N7 | Honnêteté scientifique | Aucune performance dans les documents sans rapport source ; limites documentées dans la même page que les résultats. |
| N8 | Licences | Registre des licences à jour (docs/DATASETS.md) ; attribution des sources ; aucun code ou skill importé sans licence vérifiée. |

## 6. Architecture

Voir docs/adr/0002-separation-pipeline-et-application.md. Résumé : un pipeline Python hors ligne produit des rapports versionnés ; une API FastAPI et une interface Next.js les servent et les affichent, sans jamais recalculer une performance.

## 7. Critères d'acceptation par phase

Phase 3 (MVP) acceptée si :
- F1, F2, F3, F8 (sous-ensemble), F9 (3 pages), F10, F11, F12 sont réalisés ;
- un rapport réel existe pour au moins un modèle (ResNet-18), avec intervalles de confiance ;
- la CI (lint, types, tests, build Docker) est verte ;
- le test de reproductibilité passe ;
- un test automatisé vérifie que l'interface refuse d'afficher une valeur sans rapport (F10).

Phase 4 acceptée si :
- F4, F5, F6, F7 et les pages correspondantes sont réalisés ;
- au moins 4 modèles x 5 seeds sont évalués ;
- chaque conclusion de comparaison cite l'intervalle de confiance ou le test utilisé ;
- les limites sont documentées pour chaque analyse.

Phase 5 acceptée si :
- la démo publique est en ligne, sans donnée personnelle, avec la mention de recherche visible ;
- le README et l'étude de cas sont publiés ;
- le coût réel est conforme à N6.

## 8. Hypothèses et dépendances

- Colab (GPU T4 gratuit, non garanti) ou CPU local suffisent pour l'entraînement ; les poids et rapports de référence sont produits sur un matériel unique déclaré.
- Les splits fournis par MedMNIST sont utilisés tels quels ; leur absence éventuelle de séparation par patient est traitée comme une limite (voir EVAL_PROTOCOL.md section 2).
- Les compteurs d'images annoncés par la documentation de MedMNIST sont vérifiés par le script de fiche de données avant d'être cités.

## 9. Références méthodologiques

- Yang et al., MedMNIST v2, Scientific Data, 2023.
- Mitchell et al., Model Cards for Model Reporting, 2019.
- Gebru et al., Datasheets for Datasets, 2021.
- Collins et al., TRIPOD+AI statement, BMJ, 2024.
- Tejani et al., CLAIM 2024 update, Radiology: Artificial Intelligence, 2024.
- Adebayo et al., Sanity Checks for Saliency Maps, NeurIPS 2018.
- Guo et al., On Calibration of Modern Neural Networks, ICML 2017.
- DeLong et al., Comparing the areas under two or more correlated ROC curves, Biometrics, 1988.
