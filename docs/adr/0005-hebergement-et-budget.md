# ADR 0005 - Hébergement et budget

Statut : proposé - Date : 12/10/2026

## Contexte
Budget cible 0 EUR/mois. Les offres gratuites évoluent (par exemple, selon un fil communautaire de juillet 2026 et la documentation Hugging Face, les nouveaux Spaces Docker en CPU gratuit nécessitent désormais un abonnement).

## Décision
Étape 1 : version statique du tableau de bord sur Vercel Hobby (usage personnel non commercial). Étape 2, optionnelle : backend d'inférence sur Google Cloud Run avec mise à l'échelle à zéro, dans le quota gratuit, avec alerte budgétaire configurée avant mise en ligne. Entraînement sur Colab ou CPU local.

## Alternatives écartées
- Space Hugging Face Docker : environ 9 USD/mois (abonnement PRO).
- Serveur dédié ou machine virtuelle permanente : coût récurrent.

## Conséquences
Le projet reste déployable ailleurs grâce à Docker. Toute dépense nécessite l'accord explicite du propriétaire du projet. Les limites de Vercel Hobby (usage non commercial) sont acceptées pour un portfolio.
