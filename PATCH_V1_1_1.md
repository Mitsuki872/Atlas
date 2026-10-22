# Correctif 1.1.1 — Overpass indisponible

## Que signifie le 502 ?

La requête de collecte a reçu « Bad Gateway » du service Overpass ou d’un intermédiaire réseau. Cela ne prouve ni une mauvaise installation, ni un problème dans vos prospects. Le serveur peut être surchargé ou temporairement inaccessible. L’application ne peut pas réparer ce service externe ni garantir l’heure de rétablissement.

Le connecteur effectuait déjà trois essais, puis laissait remonter une erreur technique accompagnée d’un message générique inadapté. Cette version clarifie le diagnostic et encadre les nouvelles tentatives.

## Comportement corrigé

- Maximum trois essais pour les 500/502/503/504 ou timeouts, avec 15 puis 30 secondes d’attente avant les nouveaux essais. Aucun cycle infini.
- Un `Retry-After` long reporte immédiatement le nouvel essai au lieu de bloquer le worker en attente. Les dates HTTP et nombres de secondes sont compris.
- HTTP 429 : pas d’essais répétés immédiats ; respect du délai de la source. HTTP 403/406 : pas de retry ni de changement automatique d’instance pour contourner le refus.
- Après épuisement des essais transitoires, la campagne reste en échec explicite, avec un délai de reprise d’au moins cinq minutes, ou davantage si demandé par le serveur. Les résultats déjà stockés, le curseur, les corrections et le non-contact sont conservés.
- Le délai est stocké en base et s’applique également aux autres campagnes Overpass. Un redémarrage ou une duplication ne permet pas de court-circuiter l’attente.
- L’interface affiche l’heure locale de reprise possible et désactive Reprendre avant celle-ci ; le backend refuse aussi une reprise prématurée. Une campagne en échec ne se relance pas automatiquement. Cliquer Reprendre après attente tente de nouveau, sans promesse de succès.
- Les demandes Pause/Arrêter envoyées pendant la découverte ne sont pas remplacées par « échec » à la réception tardive d’une erreur réseau.
- Diagnostics conserve le composant, l’erreur et un identifiant. Aucun résultat incomplet n’est présenté comme une collecte réussie.

## Mise à jour de votre installation existante

Aucune nouvelle dépendance, aucune nouvelle migration et aucune suppression de base.

1. Fermer avec Stop.bat et conserver une sauvegarde de `data`. Backup.bat convient si ses scripts ont déjà été débloqués. Sinon, depuis le dossier du programme dans un terminal : `.venv\Scripts\python.exe -m app.manage backup`.
2. Extraire le ZIP puis copier les nouveaux fichiers dans le dossier actuel, **sans supprimer ni remplacer `data` ni `.venv`**.
3. Relancer Start.bat et actualiser la page du navigateur. Il n’est pas nécessaire de relancer Installer.ps1 pour ce correctif si la version 1.1 fonctionne déjà.
4. Attendre le délai indiqué puis utiliser Reprendre. Pour une erreur 502 d’une ancienne version sans délai affiché, attendre environ cinq minutes avant de réessayer. Si le service reste indisponible, attendre davantage ; il n’est pas utile de relancer en boucle ni de redémarrer le PC.

Si une nouvelle installation Windows bloque les scripts téléchargés non signés, après vérification de leur provenance, retirer uniquement leur marque de téléchargement dans le dossier du projet via `Unblock-File`, comme expliqué dans le dépannage Windows. Ne pas désactiver globalement la politique d’exécution. Les scripts Windows eux-mêmes ne sont pas validés sur Windows dans cette session.

## Validation

71 tests backend réussis sur Linux. Les cas de panne utilisent des réponses contrôlées et vérifient explicitement les délais, le nombre de requêtes, la conservation des données et le respect de Pause/Arrêt. Le scénario navigateur vérifie l’état de panne et le bouton de reprise en plus des filtres, CRM, exports et presse-papiers V1.1. Aucun test simulé n’est présenté comme preuve de disponibilité réelle d’Overpass. Voir TEST_REPORT.md.
