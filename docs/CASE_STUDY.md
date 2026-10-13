# Étude de cas : MedAI Lab

## Problème

Les démonstrations d'IA médicale montrent souvent une métrique unique, sans protocole, sans incertitude et sans limites. L'objectif de ce projet est inverse : construire une plateforme où **chaque chiffre affiché renvoie à un rapport reproductible**, et où l'on voit aussi ce que le modèle ne sait pas faire. C'est un prototype de recherche, pas un outil clinique.

## Démarche

1. **Protocole fixé avant les résultats** ([EVAL_PROTOCOL.md](EVAL_PROTOCOL.md)) : test utilisé une fois par seed, seuils choisis sur la validation, 5 seeds, bootstrap stratifié, comparaison principale décidée à l'avance (bootstrap apparié, correction de Holm).
2. **Pipeline hors ligne, rapports immuables** avec provenance (commit, état du dépôt, empreintes de la configuration et des données, versions, matériel). L'API et l'interface ne font que lire ; elles n'affichent aucune valeur sans rapport source.
3. **Quatre modèles réels** (resnet18, simple_cnn, densenet121, efficientnet_b0) entraînés sur GPU T4 (Google Colab), sur PneumoniaMNIST 224x224.
4. **Analyses sur les quatre modèles** : comparaison statistique (bootstrap, DeLong, McNemar), calibration, robustesse à 6 perturbations x 5 niveaux, test de sanité de Grad-CAM.
5. **Qualité** : tests (pytest, Vitest, Playwright), typage strict, CI GitHub Actions, Docker.

## Résultats

Voir [RESULTS.md](RESULTS.md) (généré depuis les rapports). Lecture en trois points :

- Trois modèles pré-entraînés atteignent des AUC proches ; le CNN simple est nettement en dessous.
- La meilleure AUC moyenne (densenet121) repose sur une différence faible, établie par le critère principal mais pas par DeLong sur l'ensemble : je ne la présente pas comme robuste.
- L'AUC masque un problème : sous bruit, flou ou rotation, les seuils fixes ne tiennent plus alors que l'AUC reste correcte. La spécificité s'effondre pour trois modèles ; pour le CNN simple sous rotation forte, c'est la sensibilité qui chute. Un seuil choisi sur données propres ne tient pas sous décalage.

## Ce que j'ai appris et corrigé en route

- **La provenance a un piège** : mes analyses étaient marquées « dépôt modifié » parce que les sorties d'une analyse comptaient comme des modifications pour la suivante. J'ai corrigé la détection (en excluant les dossiers de sorties), ajouté un test, puis régénéré les analyses sur un arbre propre.
- **Un test statistique ne suffit pas** : McNemar à un seuil donné confond qualité du classement et choix du seuil ; je l'ai gardé comme complément et documenté ce biais.
- **Un critère de sanité peut échouer** : Grad-CAM échoue pour une seed sur cinq avec resnet18 (corrélation de rang 0,308 pour un seuil de 0,3) et avec densenet121 (0,438) ; il est satisfait partout avec simple_cnn et efficientnet_b0. Je le rapporte tel quel.

## Limites

Un seul jeu de données et un seul centre ; prévalence différente entre validation et test ; décalage de domaine non implémenté ; aucune validation clinique. Rien ici ne justifie un usage sur des patients.

## Prolongements possibles

Décalage de domaine avec un second jeu public ; recalibration sous décalage de prévalence ; étude de l'effet de la résolution.
