# ADR 0001 - Jeu de données principal

Statut : proposé - Date : 12/10/2026

## Contexte
Il faut un jeu d'imagerie médicale publiquement redistribuable pour une démo en ligne, entraînable sans infrastructure payante, sans donnée personnelle.

## Décision
PneumoniaMNIST en 224x224 (MedMNIST+), classification binaire pneumonie / normal.

## Alternatives écartées
- NIH ChestX-ray14 complet : volumineux, étiquettes issues de comptes rendus, entraînement coûteux.
- CheXpert, MIMIC-CXR : accord d'utilisation, redistribution des images impossible pour une démo publique.
- DermaMNIST : licence non commerciale.

## Conséquences
Positives : licence compatible, petite taille, reproductibilité facile.
Négatives : population pédiatrique, centre unique, séparation par patient non garantie, images réduites. Ces limites sont affichées dans l'interface et dans chaque rapport. Aucun résultat ne doit être présenté comme représentatif de la pratique clinique.
