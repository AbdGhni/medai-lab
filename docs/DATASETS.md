# Datasets, modèles pré-entraînés et licences

Mis à jour le 12/10/2026. Les informations de licence sont à reverifier à la source avant toute publication ; en cas de doute, la source fait foi.

## Jeux de données

| Jeu | Origine | Licence (selon la page PyPI de medmnist) | Utilisation dans le projet |
|---|---|---|---|
| PneumoniaMNIST | Kermany et al., 2018, redistribué par MedMNIST v2 | CC BY 4.0 | Entraînement, évaluation, démo publique (images du jeu de test) |
| ChestMNIST | NIH ChestX-ray14, redistribué par MedMNIST v2 | CC BY 4.0 (niveau MedMNIST ; vérifier les conditions du jeu NIH d'origine) | Analyse exploratoire de décalage de domaine |
| DermaMNIST | HAM10000 | CC BY-NC 4.0 (non commercial) | Exclu |
| MIMIC-CXR, CheXpert | PhysioNet, Stanford | Accord d'utilisation requis | Exclus |

Code de la bibliothèque medmnist : Apache-2.0. Citation obligatoire : Yang et al., MedMNIST v2, Scientific Data, 2023, et l'article source de chaque sous-jeu utilisé.

Données personnelles : aucune. Les jeux utilisés sont publics et distribués sous forme d'images réduites, sans métadonnées patient. Aucune donnée de santé personnelle n'est collectée par l'application.

## Fiche de données (datasheet)

Elle est générée par le pipeline (étape M03) et remplace toute valeur écrite à la main. Elle contient : checksum, effectifs par split et par classe, prévalence, résultat de la détection de doublons, date et version de la bibliothèque.

## Limites connues des données

- Population pédiatrique, centre unique : la généralisation à d'autres populations n'est pas démontrée.
- Images réduites (224x224) : perte de détails fins par rapport aux images cliniques.
- Séparation par patient entre splits non garantie.
- Étiquettes établies pour le jeu d'origine par un processus décrit dans l'article source ; la concordance inter-lecteurs n'est pas contrôlée ici.

## Composants logiciels

| Composant | Licence |
|---|---|
| PyTorch, torchvision | BSD-3 |
| timm | Apache-2.0 |
| scikit-learn, scipy, numpy | BSD-3 |
| pytorch-grad-cam | MIT |
| FastAPI, Pydantic | MIT |
| Uvicorn | BSD-3 |
| Next.js, React | MIT |
| MLflow | Apache-2.0 |

Les poids ImageNet de torchvision et timm sont utilisés selon les conditions de leurs distributeurs ; elles sont à relire et à citer dans chaque model card.

## Ressources de méthode (copiées dans .claude/skills avec attribution)

| Source | Licence | Éléments retenus |
|---|---|---|
| addyosmani/agent-skills | MIT (c) 2025 Addy Osmani | spec-driven-development, planning-and-task-breakdown, test-driven-development, incremental-implementation, documentation-and-adrs, ci-cd-and-automation, security-and-hardening |
| affaan-m/ECC | MIT (c) 2026 Affaan Mustafa | mle-workflow, pytorch-patterns, fastapi-patterns, python-testing, docker-patterns |

Copies figées sur un commit identifié, sans hooks ni scripts d'installation. Les dépôts FreedomIntelligence/Awesome-AI4Med (pas de licence), FreedomIntelligence/OpenClaw-Medical-Skills (licences hétérogènes, nombreuses mentions propriétaires) et paperclipai/paperclip ne sont pas utilisés.
