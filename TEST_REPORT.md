# Rapport de validation — patch V1.1 — 22 octobre 2026

## Périmètre et verdict

Patch appliqué au code existant avec migration additive 0003 et sauvegarde préalable. Fonctionnalités locales de qualité des prospects validées sur Linux, sur bases temporaires avec données synthétiques clairement identifiées. Pas de perte de données observée dans les tests de migration et de reprise. La collecte réelle, Lighthouse et Windows ne sont pas déclarés validés.

Le rapport de la préversion précédente est conservé dans `docs/TEST_REPORT_0_1.md` ; les résultats ci-dessous concernent ce patch.

## Tests réellement exécutés

| Contrôle | Résultat |
|---|---|
| `.venv/bin/python -m pytest -q` | **60 tests réussis, 0 échec, 0 ignoré** ; 1 avertissement de dépréciation Starlette/AnyIO |
| `CHROMIUM_PATH=/usr/bin/chromium .venv/bin/python scripts/test_browser.py` | Parcours navigateur réel réussi, incluant les sept filtres de contact et les actions rapides |
| `node --check app/static/app.js` et `node --check tests/browser.cjs` | Réussis |
| `.venv/bin/python -m compileall -q app migrations scripts` | Réussi |
| Sauvegarde de la base de l’instance avant migration | Fichier SQLite daté créé dans data/backups |
| Migration 0002 → 0003 sur l’instance | Réussie ; aucune base remplacée |
| Migration sur une ancienne base de test contenant données CRM et corrections | Réussie, puis relancée pour vérifier l’idempotence |
| Diagnostic réel `GET https://overpass-api.de/api/status` | **HTTP 406** ; aucun accès de découverte réussi revendiqué |
| Présence des outils Lighthouse | Chromium présent, CLI/package Lighthouse absents ; aucune mesure Lighthouse exécutée |
| Installation Windows | **Non exécutée**, machine Linux |

## Matrice des filtres de contact

Quatre entreprises synthétiques distinctes sont insérées dans une base de test SQLite : téléphone seulement, e-mail seulement, les deux, aucun. Les requêtes passent par la vraie API FastAPI et exécutent les filtres SQL ; les réponses ne sont pas simulées.

| Filtre | Résultats attendus et obtenus |
|---|---:|
| Avec téléphone | 2 |
| Sans téléphone | 2 |
| Avec e-mail | 2 |
| Sans e-mail | 2 |
| Téléphone et e-mail | 1 |
| Au moins un contact | 3 |
| Aucun contact | 1 |

Tests de cumul avec site, canton, commune, secteur, campagne, score d’opportunité, qualité, statut et dates de vérification. Vérification des totaux indépendants de la taille de page, offset, absence de lignes après le dernier résultat, tri stable et concordance avec les exports. Paramètres invalides et dates inversées donnent une erreur de validation explicite.

## Non-régressions et protection des données

- Chez Nina : e-mail stocké dans raw_tags.email exposé comme principal, avec champ source, date et confiance. Adresse du test réservée `.example`, pas de donnée personnelle réelle.
- Domaine sans schéma : `restaurant-delice-angevin.com` normalisé en HTTPS avant l’appel réseau du test, puis DNS/SSRF appliqués dans le client réel. Le test utilise une réponse HTML contrôlée et ne prouve pas la disponibilité de ce domaine réel.
- Horaires `Mo-Fr 11:30-15:00,18:00-24:00` : dix plages ; 23:59 inclus, borne de minuit et pause de midi respectées, dans le domaine et dans les requêtes SQL.
- Source clairsemée et source riche avec le même constat technique : même opportunité, qualités de données différentes. Audit impossible : opportunité inconnue ; audit exploitable sans problème détecté : zéro de besoin démontré.
- Collecte équilibrée : alternance, redistribution d’une place de secteur vide, absence de secteur inventé ; mode pertinence distinct.
- Enrichissement contrôlé : deux pages du même site, e-mail générique seulement, exclusion d’une adresse nom/prénom et d’un mobile privé ; correction manuelle conservée ; autorisation exigée et non-contact imposé.
- Timeouts : un nouvel essai maximum ; aucun retry d’un refus de politique. Robots, TLS et protections SSRF restent activés.
- Migration d’une ancienne base : nom/téléphone corrigés, UUID, non-contact, campagne en pause, activité historique, job, appartenance et décision d’ambiguïté conservés. Domaine et e-mail repris depuis les sources ; valeurs d’origine et ancien score archivés ; dates d’origine non rajeunies. Sauvegarde préalable et seconde migration sans duplication.
- Modification manuelle de téléphone/site pendant l’audit du worker : requête API acceptée pendant le réseau, correction conservée, résultats de l’ancien site non appliqués. Le worker ne bloque pas SQLite en conservant une transaction d’écriture pendant les appels réseau.
- Les tests antérieurs de CRM, planification, export, CSV, pause/reprise, sauvegarde/restauration, SSRF et jeton local sont conservés, avec attentes de scoring adaptées à la nouvelle sémantique explicitement demandée.

## Parcours navigateur

Création/modification d’une campagne ; CRM, note et horaire sourcé ; import via le sélecteur de fichier ; sélection et prompt ATLAS ; copie et lecture du vrai presse-papiers Chromium ; sauvegarde ; thème/layout mobile sans débordement global et absence d’erreur JavaScript non gérée.

Extension V1.1 : sept filtres de contact dans l’interface, combinaison recherche/canton, rechargement conservant les filtres, pagination de 55 lignes avec offset conservé dans l’URL et après rechargement ; liens tel/mailto vérifiés ; copie réelle des coordonnées ; statut Contacté ; note et relance via actions rapides ; sélection ATLAS ; boutons sans contact effectivement désactivés.

Les premières exécutions ont permis d’adapter les tests de scoring à la séparation demandée, d’isoler le cache robots entre fixtures et d’attendre la fin effective d’ouverture d’une fiche avant assertion sur le formulaire de relance. L’extraction de téléphone a également été corrigée pour ne pas traiter tout le document comme le contexte d’un lien isolé. Les résultats annoncés sont ceux des exécutions après correction.

## Ce que ces tests ne prouvent pas

Aucune réponse externe n’est simulée pour prétendre à une collecte réelle. Les tests de normalisation/équilibrage/enrichissement/audit utilisent des fixtures déterministes ; la seule vérification réelle du service Overpass dans cette session a répondu 406. Aucun numéro n’a été appelé, aucun e-mail envoyé, aucun calendrier modifié, aucun rendez-vous pris. Lighthouse mobile/performances réelles, conformité juridique indépendante et exécution Windows restent à vérifier. Voir KNOWN_LIMITATIONS.md et PATCH_V1_1.md.
