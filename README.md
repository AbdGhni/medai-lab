# MedAI Lab

Prototype de recherche : plateforme d'évaluation reproductible de modèles d'IA pour l'imagerie médicale.

**Ne pas utiliser pour un diagnostic ou une décision clinique.** Ce projet n'est pas un dispositif médical.

## État du projet

Phase 3 (MVP) en cours. Le pipeline, l'API et l'interface fonctionnent et sont testés. **Aucun résultat de référence n'est encore publié** : le premier entraînement complet (ResNet-18, 5 seeds, 224x224) doit être lancé sur GPU (voir `notebooks/colab_train.ipynb`). Tant qu'aucun rapport n'existe, l'interface affiche « Aucune évaluation disponible » et ne montre aucun chiffre.

## Principe

Un pipeline Python hors ligne entraîne et évalue les modèles selon un protocole fixé à l'avance ([docs/EVAL_PROTOCOL.md](docs/EVAL_PROTOCOL.md)) et écrit des rapports JSON immuables avec leur provenance (commit, empreintes de la configuration et des données, seed, versions, matériel). L'API et l'interface ne font que lire ces rapports.

- Données : PneumoniaMNIST (MedMNIST v2, CC BY 4.0), voir [docs/DATASETS.md](docs/DATASETS.md) et la fiche de données générée `reports/datasheets/pneumoniamnist_224.json`.
- Le jeu de test n'est utilisé qu'une fois par seed ; l'epoch et les seuils sont choisis sur la validation.
- Intervalles de confiance par bootstrap, 5 seeds par modèle.
- Spécification : [docs/SPEC.md](docs/SPEC.md). Décisions : [docs/adr/](docs/adr/). Backlog : [docs/BACKLOG.md](docs/BACKLOG.md).

## Démarrage

Prérequis : [uv](https://docs.astral.sh/uv/), Node.js 22 et pnpm ; Docker pour la pile complète.

```bash
# Python : installation, qualité, tests
uv sync
uv run ruff check . && uv run mypy && uv run pytest -m "not slow"

# Fiche de données réelle (télécharge PneumoniaMNIST 224x224, environ 214 Mo)
uv run python -m medai_ml datasheet --size 224 --out reports/datasheets/pneumoniamnist_224.json

# Entraînement et évaluation (GPU recommandé ; voir notebooks/colab_train.ipynb)
uv run python -m medai_ml run --config ml/configs/resnet18.yaml

# Pile complète (API sur :8000, interface sur :3000)
docker compose up --build
```

Test de fumée sans GPU (petite résolution, résultats sans valeur scientifique) :
`uv run python -m medai_ml run --config ml/configs/smoke_simple_cnn_28.yaml`

## Structure

```
ml/medai_ml/     pipeline : données, entraînement, métriques, seuils, rapports, Grad-CAM
ml/configs/      configurations d'expériences (YAML validé)
services/api/    API FastAPI (rapports, galerie, prédiction, explication)
apps/web/        interface Next.js
gallery/         24 images du jeu de test (CC BY 4.0) utilisées par la démo
reports/         rapports d'évaluation et fiche de données
docs/            spécification, protocole, ADR, backlog, audit
```

## Licences

Code : MIT. Données : voir [docs/DATASETS.md](docs/DATASETS.md) (PneumoniaMNIST : CC BY 4.0, attribution à Kermany et al. 2018 et Yang et al. 2023).
