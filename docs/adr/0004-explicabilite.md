# ADR 0004 - Explicabilité par Grad-CAM avec contrôles de validité

Statut : proposé - Date : 12/10/2026

## Contexte
Les cartes de saillance sont séduisantes mais peuvent être indépendantes du modèle (Adebayo et al., 2018).

## Décision
Utiliser Grad-CAM et Grad-CAM++ (pytorch-grad-cam, MIT) et exécuter un test de sanité par randomisation progressive des poids. Présenter les cartes comme indices de localisation uniquement.

## Alternatives écartées
- Cartes présentées sans contrôle : trompeur.
- Évaluation par radiologues : hors ressources du projet ; son absence est signalée.

## Conséquences
Un modèle ou une méthode échouant au test de sanité est signalé comme non fiable dans l'interface.
