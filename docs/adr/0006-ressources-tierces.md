# ADR 0006 - Utilisation de ressources tierces (skills, outils d'agents)

Statut : proposé - Date : 12/10/2026

## Contexte
Cinq dépôts ont été audités le 12/10/2026 (voir PHASE1_AUDIT_ARCHITECTURE.md). Certains contiennent des hooks exécutés automatiquement, des installeurs modifiant la configuration globale, des commandes de type npx -y non figées, ou des licences incohérentes.

## Décision
- Copier un nombre limité de SKILL.md (addyosmani/agent-skills, affaan-m/ECC) dans .claude/skills du projet, figés sur un commit, avec attribution MIT, sans hooks ni scripts d'installation.
- Ne rien importer depuis FreedomIntelligence/OpenClaw-Medical-Skills (licences non établies, nombreuses mentions propriétaires, scripts à risque).
- N'utiliser Awesome-AI4Med que comme bibliographie, sans recopier son contenu (pas de licence).
- Ne pas utiliser paperclipai/paperclip.

## Conséquences
Moins de commodité qu'une installation complète, mais surface d'attaque et risque juridique réduits. Toute nouvelle ressource tierce passe par une revue de licence et de sécurité consignée dans DATASETS.md.
