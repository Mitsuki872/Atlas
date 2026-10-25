# 1.3.1 — accueil d’enfants à Morges

## Cause reproduite
Le champ texte V1.3 acceptait le libellé « Structure d'accueil pour enfants » mais n’en connaissait pas les catégories. Il cherchait ce texte littéralement dans les noms/valeurs OSM, d’où zéro malgré des fiches présentes. Le total d’environ 202 000 objets correspond à toute la Suisse, pas à une campagne à Morges.

## Correctif
Correspondances explicites des apostrophes typographiques/droites, accents et formulations d’accueil d’enfants : amenity=childcare, amenity=kindergarten et accueil de jour social explicitement destiné aux enfants. Les écoles génériques, résidences et accueils de seniors ne sont pas inclus. « Crèche » reste plus précis et n’inclut pas automatiquement le préscolaire. Pas de recherche élargie hors commune.

Le formulaire affiche si le métier est reconnu ou recherché littéralement. Les diagnostics de collecte conservent le mode de reconnaissance, catégories et nombre de fiches du périmètre examinées. Une campagne terminée sans résultats explique cette distinction. Recherche Overpass mise en cohérence, sans prétendre à un accès externe réussi.

## Vérification réelle
Sur la copie suisse du 20 octobre 2026, réseau désactivé : Morges comprend 628 objets indexés ; la requête exacte renvoie 6 fiches (2 childcare, 4 kindergarten), « crèche » en renvoie 2. Le rapport docs/CHILDCARE_MORGES_REAL_VALIDATION.json ne contient ni noms ni contacts. Ces fiches ne prouvent ni leur activité actuelle, ni des places disponibles ; la copie de l’utilisateur peut donner d’autres chiffres.

## Mise à jour
Sauvegarder, Stop.bat, remplacer les fichiers du projet sans supprimer data/.venv, Install.bat puis Start.bat et recharger la page. Aucun changement de base ni de format d’index : pas de reconstruction ou téléchargement suisse requis. **Dupliquer la campagne déjà terminée à zéro, puis démarrer la copie**, car les anciennes campagnes conservent leurs résultats/curseurs. Les données CRM restent conservées.

Tests : voir TEST_REPORT.md. Windows non exécuté dans ce cloud.
