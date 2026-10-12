# ADR 0003 - Protocole d'évaluation pré-enregistré

Statut : proposé - Date : 12/10/2026

## Contexte
Les comparaisons de modèles sont souvent faussées par le choix du seuil ou de l'epoch sur le jeu de test, par l'absence d'intervalles de confiance et par une seule graine aléatoire.

## Décision
Adopter EVAL_PROTOCOL.md : test utilisé une seule fois, seuils et epoch choisis sur la validation, 5 seeds, bootstrap à 2000 rééchantillonnages, comparaison appariée avec correction de Holm, rapport de tous les résultats, y compris négatifs.

## Alternatives écartées
- Validation croisée complète : coût de calcul multiplié, jeu déjà découpé par MedMNIST.
- Une seule exécution par modèle : variance d'entraînement non mesurée.

## Conséquences
Coût de calcul modéré mais plus élevé qu'une exécution unique. Le protocole peut être modifié seulement par version datée.
