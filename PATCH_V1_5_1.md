# Patch 1.5.1 — Liste synchronisée et sélection groupée

Le tableau utilise désormais les mêmes mesures partielles Site/Présence que le dossier : positifs/mesurés (ex. 2/3), explicitement partiels, sans inventer de note complète. Les résultats filtrés et triés sont relus toutes les trois secondes lorsque la liste est visible. Les cases, filtres en cours de saisie et sélection sont conservés ; les fiches peuvent changer de place si le tri dépend des nouvelles mesures. Un navigateur en arrière-plan reprend la synchronisation à son retour.

En haut à droite, « Analyse en cours : domaine… » et trois points animés apparaissent pour une tâche réellement en cours (recherche de site ou audit), disparaissent quand elle se termine. Les éléments en attente ne sont pas présentés comme démarrés. Aucun nouvel écran de file d’attente.

Cocher une entreprise affiche une barre flottante bleue en bas : désélectionner, ouvrir ATLAS, supprimer. La case d’en-tête sélectionne la page ; « Sélectionner tous les résultats filtrés » couvre toutes les pages, maximum 1 000. La sélection est partagée avec ATLAS comme auparavant. La confirmation indique le nombre et la portée : suppression de toutes les vues/campagnes, pas uniquement du lot courant.

Avant suppression, une sauvegarde SQLite est réellement créée ; un échec de sauvegarde empêche la suppression. La migration 0008 ajoute deleted_at. La suppression est logique : listes, exports courants, tableau de bord et sélection ATLAS excluent les fiches supprimées. Coordonnées, notes, historiques et oppositions ne sont pas détruits. Les tâches de site/audit sont annulées et les collectes ultérieures ne réactivent pas une fiche supprimée. Il n’y a pas encore de corbeille dans l’interface ; récupération via sauvegarde/restauration hors ligne. Les anciens exports ATLAS restent des documents historiques, non réécrits.

Mise à jour : Backup.bat, Stop.bat, remplacer les fichiers en conservant data et .venv, Install.bat puis Start.bat. La migration crée aussi sa sauvegarde préalable. Pas de nouveau téléchargement suisse. Windows non exécuté dans ce cloud Linux.
