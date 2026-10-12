# MedAI Lab - Phase 1 : audit des dépôts et proposition d'architecture

Date : 12/10/2026
Statut : proposition, en attente de validation. Aucune installation, aucune action externe, aucune dépense n'a été faite.

Avertissement de périmètre : MedAI Lab est un prototype de recherche et de démonstration technique. Ce n'est pas un dispositif médical (pas de marquage CE au sens du règlement UE 2017/745), il ne doit pas être utilisé pour un diagnostic ou une décision clinique.

---

## 1. Audit des 5 dépôts

Méthode : clone en lecture seule (--depth 1) dans un espace temporaire isolé, lecture des README, LICENSE, manifestes, hooks, configs MCP et scripts. Rien n'a été exécuté.

### 1.1 Synthèse

| Dépôt | Nature | Licence | Taille | Dernier commit | Verdict |
|---|---|---|---|---|---|
| addyosmani/agent-skills | 25 skills d'ingénierie pour agents IA (spec, TDD, CI/CD, ADR, sécurité) | MIT (fichier LICENSE présent) | 2,6 Mo, 211 fichiers | 10/10/2026 | Adopter partiellement (6 skills, copie figée) |
| affaan-m/ECC | "Agent harness OS" : 312 skills, 72 agents, 98 commandes, hooks, configs MCP, installeurs | MIT (fichier LICENSE présent) | 110 Mo, 4 615 fichiers | 11/10/2026 | Ne pas installer. Copier 4 à 5 skills ciblés |
| FreedomIntelligence/Awesome-AI4Med | Liste de liens (LLM/MLLM médicaux, datasets, benchmarks) | Aucun fichier LICENSE | 0,9 Mo, 5 fichiers | 04/08/2026 | Lecture seule, bibliographie. Ne pas copier le contenu |
| FreedomIntelligence/OpenClaw-Medical-Skills | Agrégat de 869 skills biomédicaux pour OpenClaw | Badge "MIT" mais aucun fichier LICENSE ; licences internes hétérogènes | 313 Mo, 5 294 fichiers | 21/07/2026 | Ne pas installer. Risque juridique élevé |
| paperclipai/paperclip | Orchestrateur d'"entreprise d'agents" (Node 24 + Postgres embarqué + UI React) | MIT (fichier LICENSE présent) | 216 Mo, 9 729 fichiers | 12/10/2026 | Ne pas utiliser (hors sujet, surface d'attaque) |

### 1.2 addyosmani/agent-skills

Utile : c'est un cadre de méthode, pas du code produit. Les skills couvrent exactement la démarche demandée (spec, plan, build incrémental, tests, revue, livraison).

Skills retenus :
- spec-driven-development, planning-and-task-breakdown (phase 2)
- test-driven-development, incremental-implementation (phases 3-4)
- documentation-and-adrs, ci-cd-and-automation, security-and-hardening (transverse)

Risques :
- Le dossier hooks/ contient des scripts shell exécutés automatiquement par l'agent (session-start.sh, sdd-cache-*.sh). À ne pas activer sans relecture.
- L'installation recommandée passe par `npx skills add ...` (code npm exécuté, non figé). Préférer une copie manuelle des SKILL.md dans `.claude/skills/` du projet, figée sur un commit précis, avec attribution MIT.

### 1.3 affaan-m/ECC

Utile : quelques skills de qualité directement alignés avec la stack : mle-workflow, pytorch-patterns, fastapi-patterns, python-testing, docker-patterns. healthcare-phi-compliance et healthcare-eval-harness sont des références de lecture seulement : ils visent des DME/CDSS (prescriptions, RLS SQL, Jest) et le cadre HIPAA/DISHA, pas l'évaluation de modèles d'imagerie.

Risques :
- Installeurs (install.sh / install.ps1) qui modifient la config globale de l'agent (~/.claude), hooks exécutés à chaque appel d'outil, injection de contexte au démarrage, mémoire persistante.
- Configs MCP utilisant `npx -y` sans version figée et `@latest` (ex. serveur Supabase) : risque de chaîne d'approvisionnement ; certaines attendent des tokens (GitHub PAT, Jira, Firecrawl).
- Volume (312 skills) : bruit de contexte, conflits avec d'autres skills.
Décision proposée : aucune installation globale ; copie de 4-5 SKILL.md dans le projet, figés sur le commit audité, avec attribution.

### 1.4 FreedomIntelligence/Awesome-AI4Med

Utile : bibliographie pour une extension future vers l'évaluation de modèles multimodaux (VQA médicale : VQA-RAD, SLAKE, OmniMedVQA ; outils : MedEvalKit). Très orienté LLM/MLLM, peu de ressources en classification d'images.
Risque : pas de fichier LICENSE, donc tous droits réservés par défaut sur le texte de la liste. On cite les liens, on ne recopie pas les tableaux. Chaque ressource listée a sa propre licence à vérifier à la source.

### 1.5 FreedomIntelligence/OpenClaw-Medical-Skills

Constats vérifiés dans le dépôt :
- Pas de fichier LICENSE à la racine malgré le badge MIT du README.
- 281 skills sur 869 contiennent une mention "All Rights Reserved / proprietary and confidential" (ex. multimodal-medical-imaging).
- 722 SKILL.md sur 869 ne déclarent aucune licence ; d'autres déclarent "Proprietary", "Non-Commercial", "Unknown", CC-BY-4.0, Apache-2.0...
- 1 150 scripts Python, 203 scripts shell ; 9 fichiers Python avec `shell=True`, plusieurs documents/scripts avec des installations de type `curl ... | sh`.
- Nombreux skills orientés clinique (notes SOAP, interactions médicamenteuses, détection de crise) : hors périmètre et à risque de dérive vers un usage pseudo-diagnostique.

Décision proposée : ne rien installer ni copier depuis cet agrégat. Si une idée est utile (ex. pydicom, imaging-data-commons, shap, bio-machine-learning-model-validation, regulatory-drafting), on remonte au dépôt d'origine (ex. ImagingDataCommons/idc-claude-skill) et on vérifie sa licence là-bas.

### 1.6 paperclipai/paperclip

Plateforme d'orchestration d'agents autonomes avec budgets, organigramme et gouvernance. Prérequis : Node.js 24.11+, pnpm 9.15+, Postgres embarqué. Le mode rapide démarre en "trusted local loopback".
Pour MedAI Lab : aucune valeur produit, et un projet solo n'a pas besoin d'une "entreprise d'agents". Ajoute une surface d'attaque (agents autonomes, clés API, dépenses automatiques). Décision proposée : ne pas l'utiliser.

### 1.7 Ce que l'audit change dans le projet

Les dépôts apportent surtout de la méthode de développement, pas de briques produit. Les briques produit viendront de bibliothèques établies et licenciées clairement :

| Brique | Bibliothèque | Licence |
|---|---|---|
| Données | medmnist (code Apache-2.0 ; données CC BY 4.0 sauf DermaMNIST CC BY-NC 4.0) | voir section 3 |
| Modèles | PyTorch, torchvision, timm | BSD-3 / BSD-3 / Apache-2.0 |
| Explicabilité | pytorch-grad-cam (jacobgil) | MIT |
| Métriques | scikit-learn, scipy, numpy | BSD-3 |
| API | FastAPI, Pydantic v2, Uvicorn | MIT / MIT / BSD-3 |
| Front | Next.js, React, Tailwind, shadcn/ui, Recharts | MIT |
| Suivi d'expériences | MLflow (stockage fichier local) | Apache-2.0 |
| Baseline externe (optionnelle, locale) | torchxrayvision (code Apache-2.0) | poids : licence non précisée, entraînés en partie sur des données sous accord d'usage (MIMIC-CXR, CheXpert) |

---

## 2. Architecture proposée

### 2.1 Principe directeur

Séparer strictement deux mondes :
1. Le pipeline d'évaluation hors ligne (Python) : entraîne, évalue, et produit des rapports immuables et versionnés (JSON + figures), chacun avec sa provenance : commit git, hash de config, hash des données, seed, versions des librairies, date.
2. L'application de démonstration (FastAPI + Next.js) : elle affiche ces rapports et fait de l'inférence sur des images d'exemple autorisées. Elle ne calcule jamais une performance à la volée et n'affiche jamais de chiffre sans rapport source.

Conséquence : chaque nombre visible dans l'interface renvoie à un fichier de rapport traçable. S'il n'y a pas de rapport, l'interface affiche "aucune évaluation disponible", jamais une valeur par défaut.

### 2.2 Schéma

```
                 +-------------------------------+
                 |  ml/ (package medai_ml)       |
 medmnist  --->  |  data -> train -> evaluate    |---> reports/<run_id>/
 (CC BY 4.0)     |  calibrate -> robustness      |      metrics.json, preds.parquet,
                 |  explain (Grad-CAM)           |      figures, model_card.md
                 +---------------+---------------+---> artifacts/<model_id>/
                                 |                      weights + manifest (sha256)
                                 v
 +-----------------------------------------------------------------+
 |  services/api (FastAPI)                                         |
 |  GET /health  GET /models  GET /evaluations  GET /evaluations/id|
 |  GET /compare?runs=a,b   POST /predict   POST /explain          |
 |  - chaque réponse porte le champ disclaimer "research only"     |
 |  - pas de stockage d'images, pas de logs de contenu             |
 +-------------------------------+---------------------------------+
                                 | OpenAPI -> client TS généré
                                 v
 +-----------------------------------------------------------------+
 |  apps/web (Next.js App Router, TypeScript)                      |
 |  Vue d'ensemble | Modèles | Évaluation | Comparaison |          |
 |  Robustesse | Calibration | Explicabilité | Limites & datasets  |
 +-----------------------------------------------------------------+
```

### 2.3 Arborescence du monorepo

```
medai-lab/
  apps/web/                 Next.js 15+, TS strict, Tailwind, shadcn/ui, Recharts, TanStack Query
  services/api/             FastAPI, Pydantic v2, pydantic-settings, uvicorn
  ml/medai_ml/              data/ models/ training/ evaluation/ calibration/ robustness/ explain/
  ml/configs/               configs YAML validées par Pydantic (une par expérience)
  reports/                  rapports d'évaluation versionnés (générés, jamais écrits à la main)
  docs/                     ADR, datasets.md, protocole d'évaluation, model cards, usage prévu, modèle de menaces
  infra/                    Dockerfiles, docker-compose, workflows GitHub Actions
  .claude/skills/           skills retenus (copies figées + attribution)
```

### 2.4 Choix techniques et justification

| Décision | Choix | Alternative écartée | Raison |
|---|---|---|---|
| Dataset principal | PneumoniaMNIST en 224x224 (MedMNIST+) | NIH ChestX-ray14 complet, CheXpert, MIMIC-CXR | Licence CC BY 4.0 compatible avec une démo publique ; petit (5 856 images) donc entraînable sur CPU ou Colab gratuit ; images déjà dé-identifiées. CheXpert et MIMIC-CXR imposent un accord d'usage. |
| Second dataset (phase 4) | ChestMNIST (dérivé de NIH ChestX-ray14), label "pneumonia" | - | Test de décalage de domaine (pédiatrique vs adulte). À présenter comme une analyse exploratoire : définitions de labels différentes, labels extraits automatiquement de comptes rendus. |
| Modèles comparés | CNN simple (baseline), ResNet-18 et DenseNet-121 pré-entraînés ImageNet, EfficientNet-B0 (timm) | ViT large, modèles fondation | Comparaison honnête à budget de calcul raisonnable ; 3 à 5 seeds par modèle. |
| Seuil de décision | Choisi sur la validation (Youden et point à sensibilité fixe 0,95), jamais sur le test | Seuil 0,5 | Évite la fuite d'information et colle à un usage de dépistage. |
| Comparaison statistique | Bootstrap apparié (IC 95 %) + test de DeLong sur l'AUC, McNemar au seuil | Comparaison de moyennes brutes | Évite de conclure sur des écarts non significatifs. |
| Calibration | ECE, Brier, diagrammes de fiabilité, temperature scaling ajusté sur la validation | - | Demandé explicitement ; signal fort pour un recruteur. |
| Robustesse | Bruit gaussien, flou, contraste/luminosité, compression JPEG, rotation, sous-échantillonnage, 5 niveaux de sévérité | - | Courbes performance vs sévérité, reproductibles. |
| Explicabilité | Grad-CAM (et Grad-CAM++) + test de sanité par randomisation du modèle (Adebayo et al., 2018) | Cartes de chaleur seules | Montre qu'on sait que les cartes de saillance peuvent tromper. |
| Service d'inférence | PyTorch CPU dans FastAPI | ONNX Runtime seul | Grad-CAM nécessite les gradients ; ONNX possible plus tard pour /predict. |
| Suivi d'expériences | MLflow en stockage fichier + rapports JSON commités | W&B (compte externe) | Zéro dépendance à un service tiers. |
| Données dans Git | Non : téléchargement via medmnist avec vérification de checksum | DVC | Dataset public stable ; DVC ajouterait de la complexité sans gain ici. |
| Poids des modèles | GitHub Releases + manifeste sha256 | Hugging Face Hub | Pas de compte supplémentaire ; publication possible plus tard. |

### 2.5 Qualité, tests et CI/CD

- Python : ruff, mypy, pytest, couverture minimale 80 % sur ml/ et services/.
- Métriques : tests contre scikit-learn comme référence, tests de propriétés (hypothesis), cas limites (une seule classe, prédictions constantes).
- Reproductibilité : test "smoke train" en CI sur un sous-ensemble 28x28 (moins de 3 minutes CPU), qui vérifie que deux exécutions avec la même seed donnent les mêmes métriques.
- Tests de contrat API (schéma OpenAPI figé, golden files).
- Front : ESLint, typecheck, Vitest, Playwright pour 3 parcours clés.
- Sécurité : pip-audit, npm audit, gitleaks, scan d'image Trivy, Dependabot.
- GitHub Actions : lint -> tests -> build Docker -> (sur tag) publication.

### 2.6 Cadre éthique et réglementaire (intégré au produit, pas seulement à la doc)

- Bandeau permanent et champ `disclaimer` dans chaque réponse API : prototype de recherche, pas de diagnostic.
- Démo publique : galerie d'images du jeu de test uniquement ; l'upload libre est désactivé par défaut (activable en local). Pas de stockage ni de journalisation des images.
- Documentation : usage prévu et usages exclus, datasheet du dataset, model card par modèle (Mitchell et al., 2019), protocole d'évaluation inspiré des grilles CLAIM 2024 et TRIPOD+AI (2024).
- Limites connues documentées d'emblée : PneumoniaMNIST est pédiatrique (1-5 ans, un seul centre) ; résolution réduite ; risque de raccourcis d'apprentissage ; la séparation par patient des splits MedMNIST est à vérifier avant toute affirmation de généralisation.

---

## 3. Datasets et licences

| Dataset | Source | Licence | Usage prévu |
|---|---|---|---|
| PneumoniaMNIST (MedMNIST v2/+) | Kermany et al., 2018, via MedMNIST | CC BY 4.0 (attribution + citation obligatoires) | Entraînement, évaluation, démo publique |
| ChestMNIST | NIH ChestX-ray14, via MedMNIST | CC BY 4.0 au niveau MedMNIST | Décalage de domaine (phase 4) |
| DermaMNIST | HAM10000 via MedMNIST | CC BY-NC 4.0 | Exclu de la démo publique (usage non commercial seulement) |
| MIMIC-CXR, CheXpert | PhysioNet / Stanford | Accord d'usage requis | Exclus |

Aucune donnée personnelle de santé n'est utilisée. Tout nouveau dataset passe par une fiche (source, licence, dé-identification, biais connus) avant d'être ajouté.

---

## 4. Risques

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Interprétation clinique de la démo par un visiteur | Moyenne | Élevé | Bandeau, champ disclaimer, galerie uniquement, page "Limites" |
| Résultats surestimés (fuite de données, seuil choisi sur le test) | Moyenne | Élevé | Seuil sur validation, IC bootstrap, multi-seeds, rapports générés uniquement par le pipeline |
| Licences (skills agrégés, poids pré-entraînés) | Élevée si on importe sans vérifier | Élevé | Aucune importation depuis OpenClaw ; registre des licences dans docs/ ; torchxrayvision en local uniquement |
| Chaîne d'approvisionnement (npx -y, hooks, scripts d'install) | Moyenne | Moyen | Pas d'installeurs tiers ; dépendances figées (uv.lock, pnpm-lock) ; scans CI |
| Grad-CAM trompeur | Élevée | Moyen | Test de sanité par randomisation, présentation prudente |
| Dérive de périmètre (trop de fonctionnalités) | Élevée | Moyen | Backlog priorisé, MVP strict en phase 3 |
| Hébergement gratuit qui change de conditions (ex. HF Spaces : depuis l'été 2026, les nouveaux Spaces Docker/Gradio en CPU gratuit exigent un abonnement PRO) | Moyenne | Faible | Architecture déployable n'importe où (Docker) ; mode statique de secours |
| Démarrage à froid lent (image PyTorch CPU d'environ 1 Go) | Élevée | Faible | Rapports servis statiquement ; message de chargement ; image slim |

---

## 5. Coûts estimés

Les montants sont ceux publiés par les fournisseurs à la date de l'audit ; ils peuvent changer.

| Poste | Option recommandée | Coût |
|---|---|---|
| Développement et CI | Poste local + GitHub Actions (gratuit pour dépôt public) | 0 EUR |
| Entraînement | CPU local ou Google Colab gratuit (GPU T4 quand disponible) | 0 EUR (option Colab payant à l'usage : environ 10 EUR, non nécessaire a priori) |
| Front | Vercel Hobby (gratuit, usage personnel non commercial : convient à un portfolio) | 0 EUR |
| Backend option A | Google Cloud Run, mise à l'échelle à zéro ; quota gratuit mensuel : 2 M requêtes, 180 000 vCPU-s, 360 000 GiB-s | 0 EUR attendu ; carte bancaire requise pour le compte, alerte budgétaire à 5 EUR |
| Backend option B | Hugging Face Space Docker (nécessite l'abonnement PRO) | environ 9 USD/mois |
| Option C (secours) | Tout statique : tableau de bord + galerie Grad-CAM précalculée, sans inférence live | 0 EUR |
| Nom de domaine | Optionnel | environ 10 à 15 EUR/an |

Recommandation : démarrer en option C (statique) dès la fin du MVP, puis ajouter l'option A pour l'inférence live. Budget plafond proposé : 0 EUR, avec une tolérance de 10 EUR/mois si tu choisis l'option B.

---

## 6. Ressources nécessaires

De ton côté :
- Un compte GitHub et un nom de dépôt (public recommandé pour la visibilité recruteurs et la CI gratuite).
- Sur ton PC Windows : Python 3.11 ou 3.12, Node.js 20 LTS ou plus, Git, Docker Desktop (à confirmer : je n'ai pas pu vérifier ce qui est installé côté Windows ; la VM liée a Python 3, Node et Git, mais pas Docker).
- Savoir si tu as un GPU NVIDIA (sinon : CPU + Colab, suffisant pour ce dataset).
- Plus tard, pour le déploiement : compte Vercel, compte Google Cloud (option A) ou HF PRO (option B).

Temps estimé (à temps partiel, en parallèle de l'alternance) : 6 à 8 semaines pour les phases 2 à 5.

---

## 7. Plan d'exécution

| Phase | Contenu | Livrables | Critère d'acceptation | Durée estimée |
|---|---|---|---|---|
| 2. Cahier des charges | Spécification, user stories, backlog priorisé (MoSCoW), protocole d'évaluation pré-enregistré, ADR | docs/SPEC.md, docs/BACKLOG.md, docs/EVAL_PROTOCOL.md, docs/adr/0001-0005 | Protocole figé avant tout entraînement (métriques, splits, seuil, tests statistiques) | 3-4 jours |
| 3. MVP | Monorepo, pipeline data + 1 modèle (ResNet-18), évaluation complète avec IC, API /predict /explain /evaluations, front 3 pages, Docker Compose, CI | `docker compose up` lance tout ; 1 rapport réel | Reproductibilité : même seed = mêmes métriques ; couverture 80 % ; CI verte ; aucune valeur affichée sans rapport | 2 semaines |
| 4. Avancé | 4 modèles x 3-5 seeds, comparaison statistique, calibration, robustesse, décalage de domaine, sanité Grad-CAM, pages front correspondantes | Rapports comparatifs, model cards | Chaque conclusion appuyée par un IC ou un test ; limites documentées | 2-3 semaines |
| 5. Démo et valorisation | Déploiement, README professionnel, étude de cas recruteurs, vidéo courte de démo | URL publique, README, CASE_STUDY.md | Démo fonctionnelle sans données personnelles ; disclaimer visible ; budget respecté | 1 semaine |

Points de validation : je m'arrête à la fin de chaque phase pour ton accord, et avant toute installation, création de compte, publication ou dépense.

---

## 8. Décisions attendues de ta part

1. Dataset principal : PneumoniaMNIST 224 (CC BY 4.0) - d'accord ?
2. Hébergement : option C puis A (0 EUR), ou option B (environ 9 USD/mois) ?
3. Skills de développement : copie figée de 6 skills agent-skills et 4-5 skills ECC dans le projet, sans hooks ni installeurs - d'accord ?
4. Dépôt GitHub : public ? quel nom (proposition : medai-lab) ?
5. Matériel : GPU NVIDIA disponible ? Docker Desktop installé ?

---

## Sources

- Dépôts audités : github.com/addyosmani/agent-skills, github.com/affaan-m/ECC, github.com/FreedomIntelligence/Awesome-AI4Med, github.com/FreedomIntelligence/OpenClaw-Medical-Skills, github.com/paperclipai/paperclip (commits du 21/07 au 12/10/2026)
- MedMNIST (licences et tailles) : https://pypi.org/project/medmnist
- MedMNIST v2, article : https://arxiv.org/abs/2110.14795
- torchxrayvision : https://pypi.org/project/torchxrayvision
- Tarifs matériel Hugging Face Spaces : https://huggingface.co/docs/hub/main/spaces-gpus
- Changement CPU Basic gratuit HF (fil communautaire, juillet 2026) : https://discuss.huggingface.co/t/official-community-complaint-revert-free-cpu-basic-spaces-and-remove-anti-developer-sdk-restrictions/177703
- Quota gratuit Cloud Run : https://cloud.google.com/run/pricing
- Vercel Hobby : https://vercel.com/docs/plans/hobby
