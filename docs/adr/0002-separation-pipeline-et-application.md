# ADR 0002 - Séparation du pipeline d'évaluation et de l'application

Statut : proposé - Date : 12/10/2026

## Contexte
Une plateforme d'évaluation perd sa crédibilité si l'interface peut afficher des chiffres non issus d'une expérience traçable.

## Décision
Un pipeline Python hors ligne (package ml/) produit des rapports JSON immuables avec provenance complète. L'API FastAPI et l'interface Next.js lisent ces rapports et n'en recalculent jamais le contenu. L'inférence en direct est limitée aux images de la galerie.

## Alternatives écartées
- Calcul des métriques à la volée dans l'API : risque d'incohérence et de valeurs non reproductibles.
- Base de données relationnelle pour les résultats : complexité sans bénéfice pour un nombre limité de rapports ; fichiers versionnés dans Git suffisants.

## Conséquences
Un test automatisé vérifie qu'aucune valeur n'est affichée sans rapport. Le mode statique (rapports précalculés) devient possible pour l'hébergement gratuit. Les rapports sont versionnés avec le code.
