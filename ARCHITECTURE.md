# Architecture effective

## Choix

Local-first : un backend FastAPI sert une interface HTML/CSS/JavaScript sans compilation, une API JSON et une base SQLite SQLAlchemy. Un second processus Python traite les campagnes. Alembic versionne le schéma ; chaque migration sur une base existante est précédée d’une sauvegarde SQLite. Python 3.12 est la référence de validation.

Alternative à Next.js / TypeScript / Tailwind : un seul environnement Python suffit à l’usage quotidien. Cela réduit les prérequis et le nombre de services Windows. Compromis : pas de typage statique du frontend, pas de bibliothèque avancée de composants, pas de rendu React ; tests navigateur requis pour le parcours interactif. Node/Playwright ne servent qu’à la QA facultative.

## Frontières

- `db.py` : entités, moteur et sessions. UUID stables ; relations et clés étrangères SQLite activées ; journal WAL.
- `domain.py` : normalisation, validation Pydantic, horaires, scoring et schéma d’export ATLAS.
- `connectors.py` : protocole de découverte et connecteur Overpass, mapping des données et provenance ODbL.
- `network.py` : fetch public borné, DNS épinglé, contrôle des redirections et audit HTML.
- `worker.py` : file persistante `jobs`, curseur et résultats de découverte conservés, transactions par entreprise, reprise au démarrage.
- `main.py` : API et protections locales, CRM, exports, import autorisé, diagnostics et agrégats.
- `manage.py` : migrations, sauvegardes et restauration hors ligne.
- `scripts/launcher.py` : démarrage/arrêt/diagnostic des seuls processus enregistrés avec PID, commande et heure de création ; contrôle fonctionnel avant succès.

## Modèle de données

Campaign → Job, Campaign ↔ Company par Membership. Company → Activity et SourceRecord. PlanningExport conserve le payload effectivement exporté ; Setting conserve les pondérations, décisions d’ambiguïté, heartbeat et limite de requêtes ; Log conserve les erreurs worker. Une activité distingue note, appel, rappel, devis, vente, opportunité et correction. Pas de synchronisation automatique entre devis, vente et statut CRM : ce sont des faits déclarés distincts.

Les entités détaillées du cahier des charges ne sont pas toutes séparées en tables V0.1 : contacts, horaires, audit et score sont des champs JSON versionnables par les prochaines migrations. Les enregistrements sources conservent la provenance antérieure. Aucun nom similaire ne provoque de fusion. Les identifiants OSM différents restent distincts ; les branches d’une chaîne ne sont pas fusionnées sur leur domaine partagé.

## Résilience

Le worker réserve une socket locale pour garantir une seule instance. Au redémarrage, les jobs `running` redeviennent `queued` ; le curseur indique le prochain enregistrement. Une entreprise, son appartenance et son curseur sont validés dans une seule transaction. Une pause est observée entre deux entreprises ; un audit en cours peut encore finir. Un arrêt conserve les résultats et l’historique ; une campagne arrêtée doit être dupliquée pour recommencer. Une source en échec donne une campagne en échec explicite, reprenable après correction.

Les audits sont réutilisés 24 heures, y compris les états non observés : attendre cette durée ou modifier explicitement le site pour invalider l’audit. La découverte est réutilisée pour la reprise d’un même job. Les requêtes Overpass sont espacées d’au moins 60 secondes, avec trois essais maximum seulement sur erreurs transitoires HTTP et backoff. Les interruptions pendant la découverte peuvent nécessiter de refaire cette requête bornée. La mise en pause n’annule pas un appel HTTP déjà parti.

## Préparation SaaS

API, domaine, connecteur et worker sont séparés. SQLAlchemy et types génériques facilitent PostgreSQL, mais ce changement n’est pas testé et nécessite notamment des migrations adaptées. Il n’existe pas encore d’authentification, organisation, isolation multi-tenant, quotas, abonnements ou facturation. Ne pas exposer cette application sur Internet. Les jetons locaux protègent contre les requêtes d’autres pages web ; ils ne remplacent pas une authentification SaaS.

## Patch V1.1

Migration additive 0003 : email, canton, contacts JSON structurés et quality_score JSON. Le champ score devient exclusivement une mesure de besoin démontré, nullable pour les opportunités non évaluées. contacts.py normalise et évalue la complétude ; filters.py construit les requêtes SQL partagées par listes et exports ; enrichment.py gère les pages contact autorisées. Le worker libère toute transaction avant les accès réseau et relit les corrections/suppressions avant écriture. Un changement manuel de site pendant un audit empêche l’application des résultats de l’ancien site. Les anciennes données et payloads d’export restent conservés. Les nouveaux exports ATLAS ont schema_version 1.1 et incluent email et data_quality.

## Source locale V1.2

`osm_download.py` télécharge un snapshot Geofabrik HTTPS fixé/contrôlé, avec Range et empreinte fournisseur. `osm_index.py` utilise osmium + shapely pour lire le PBF en flux, assembler les limites administratives et construire un index SQLite distinct du CRM. Manifest activé atomiquement après intégrité. `osm_local.py` exécute la découverte hors réseau avec les mêmes identités OSM. `datasets.py` conserve les tâches de préparation via la migration 0004, avec progression, annulation et reprise. Le worker priorise ces tâches et récupère les préparations interrompues au redémarrage. Les sources plus anciennes ne remplacent pas les contacts plus récents ; les corrections manuelles restent prioritaires. L’index 3 ne contient que des objets nommés dans les huit catégories prises en charge. Aucun service supplémentaire quotidien.


## 1.3
Migration 0005 : companies.identification/qualification et audit_runs, criterion_results, audit_evidence, score_snapshots, audit_opportunities, outreach_suppressions. Modules scoring (grille versionnée/calcul), audits (historique/cache/jobs), scoring_api (identification/observations/réglages/archive/événements), quick_audit (preuves HTTP/DOM), audit_adapters (frontière autorisée/budget/prompt optionnel). Aucun changement de stack. Voir docs/SCORING_INTEGRATION.md et SCORING_V1_3.md.


## 1.4
Migration 0006 additive website_jobs. website_discovery : sources/candidats/vérification/jobs ; search_credentials : clé dans un fichier env local dédié, jamais SQLite/export ; workspace_api : vues de lecture CRM/planning et commandes de recherche. Worker unique récupère les recherches running, contrôle annulation/pause et mises à jour concurrentes. Couche frontend conserve les routes historiques, ajoute #company?id= et distingue Prospects, Pipeline CRM et Planification. Anciennes mesures de domaine non réattribuées à un nouveau site. Aucun framework ni dépendance graphique ajoutés.
