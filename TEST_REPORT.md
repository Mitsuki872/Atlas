# Validation 1.5.1

**171 tests backend réussis**, zéro échec ou test ignoré, un avertissement de dépréciation Starlette/AnyIO. Vérifications de syntaxe JS et compilation Python réussies.

Nouveaux cas : indicateur global absent pour une tâche en attente et présent pour une recherche réellement en cours ; suppression groupée idempotente avec sauvegarde SQLite existante, conservation des coordonnées, notes et opposition, exclusion de la liste/tableau de bord/ATLAS, annulation du travail ; échec volontaire de sauvegarde empêchant toute suppression. Les migrations historiques jusqu’à la nouvelle tête 0008 conservent les anciennes données et créent leurs sauvegardes. Les fixtures anciennes sont insérées avec les colonnes disponibles à leur époque.

Chromium réel, base isolée et fiches synthétiques : Site 2/3 et Présence 2/2 affichés dans la liste ; import d’une nouvelle observation pendant que la liste reste ouverte, Site devient 3/3 sans navigation ni rechargement, le brouillon de filtre reste intact. Indicateur global et ses trois points vérifiés avec une réponse réseau contrôlée (ne constitue pas une analyse d’un vrai site). Sélection de page, sélection de tous les résultats filtrés, barre en bas, annulation et confirmation de suppression, mise en page mobile. Les autres parcours de la 1.5 restent exercés. Aucun site réel ou Windows n’a été utilisé pour ces contrôles d’interface.

# Validation 1.5 — 25 octobre 2026

**168 tests backend réussis, aucun échec ni test ignoré**, un avertissement Starlette/AnyIO. Tests isolés, restauration services arrêtés. Migration 0006→0007 réellement exécutée sur anciennes données : cinq statuts, trace des anciens états, téléphone/corrections conservés, opposition persistante et sauvegarde créée ; fichier de clé obsolète retiré.

Tests nouveaux : collecte rapide avec contrôles gratuits mis en file sans attendre le réseau ; deux lots successifs de 25 identités distinctes (50 entreprises conservées, note antérieure intacte), refus de double relance active, dernier lot SQL 25 lignes ; suggestions Enfants/UAPE → Crèche et tea-room → Boulangerie sans filtrage par le mot saisi ; plus de 50 catégories. Tri commercial réversible, audit 403 jamais assimilé à mauvais site, absence de coordonnées rangée à vérifier, entreprise suffisamment mesurée sans besoin démontré non priorisée ; cinq statuts et opposition indépendante. Contrôles site et présence OSM sourcés ; rapprochement d’un numéro connu en texte simple/JSON-LD ; aucun appel fournisseur payant possible par les anciennes commandes.

**Navigateur Chromium réel :** création du formulaire simplifié, choix des catégories suggérées, menus stylisés et cinq statuts colorés, commande réelle de relance à 25 (les tests de contenu de lots sont backend), sept filtres contacts, Exploitables/À vérifier/Toutes, persistance URL, coordonnées réellement copiées individuellement dans le presse-papiers. Page entreprise, notes, proportions 2/3 et 2/2 sur observations synthétiques déclarées, ATLAS et prompt réellement copié/persisté. Pipeline/Planification absents, aucune commande de clé API. Bureau 1440 px, mobile 390 px sans débordement, aucune erreur JS.

Ouverture du site vérifiée dans un nouvel onglet avec URL et paramètres conservés, sur une page externe contrôlée explicitement. Cela ne valide pas la disponibilité de tous les sites réels. URL sans protocole normalisée côté lien, javascript refusé. La vérification ancienne du domaine des P’tits Loups avait répondu HTTP 403 ; aucun succès d’extraction de ce site n’est revendiqué.

**Données réelles distinctes des fixtures :** trois campagnes sur la copie suisse existante, dans une base temporaire et réseau désactivé, ont à nouveau conservé 12 fiches, correction, note, opposition et export ATLAS. Aucun audit web exécuté pendant cette recette hors ligne. Rapport agrégé sans coordonnées : docs/LOCAL_OSM_REAL_VALIDATION_1_5.json. Windows n’a pas été exécuté. Voir SIMPLE_WORKFLOW_V1_5.md.

---

# Validation 1.4 — 25 octobre 2026

**161 tests backend réussis, zéro échec, zéro ignoré**, un avertissement Starlette/AnyIO conservé. Syntaxes JS/Python et cohérence des dépendances vérifiées. Migration 0005→0006 exécutée sur une ancienne base de test avec campagne, note, correction téléphone, opposition, appartenance et audit : tout conservé, sauvegarde créée, fichier source inchangé.

**Navigateur réel Chromium, bases temporaires synthétiques :** thème bleu sombre, table de dix colonnes, filtres avancés repliés et sept modes de contacts SQL, tri/pagination/URL/retour ; dossier pleine page, jauges inconnues explicites, preuves repliables, identification, corrections, notes et relances. Pipeline CRM distinct (cinq colonnes), changement de statut vérifié en base ; planning distinct (aucune table prospects), sélection après rechargement, relance, export ATLAS et vrai presse-papiers. Sauvegarde, réglage versionné et diagnostic Overpass différé conservés. Pages dashboard/prospects/CRM/planning/dossier vérifiées à 390 px sans débordement de page ; bureau 1440 px ; aucune erreur JS. Les captures utilisent des entreprises explicitement synthétiques.

**Recherche de sites, tests contrôlés :** nom/localité/numéro concordants, nom seul insuffisant, mauvaise ville/homonyme rejetés, multi-domaines ambigus, 403/robots/timeout distincts de qualité, exclusion des profils sociaux, domaine d’e-mail professionnel comme candidat seulement. Contrat HTTP de Brave exercé avec MockTransport (pas de vrai moteur), clé absente = aucun appel, quota persistant réservé avant appel, secret jamais renvoyé/exporté/stocké en base. Jobs idempotents/cache, annulation entre candidats, opposition, pause/reprise/arrêt campagne, correction manuelle préservée, audit courant conservé si domaine identique, changement de domaine ne réutilisant jamais les anciennes notes.

Démarrage réel sur la base locale après migration 0006 : diagnostics, pipeline CRM, configuration de recherche et copie suisse ont répondu HTTP 200 ; index suisse prêt, sans reconstruction. Les tests de ports/navigateur ont été relancés avec autorisation d’ouverture des ports locaux après un changement de restrictions du sandbox.

Les téléchargements de préparation et l’interface d’un site refusé utilisent des réponses UI contrôlées, clairement identifiées. Aucun succès de moteur ou collecte réelle du site cible n’est simulé.

**Observation externe réelle :** l’utilisateur a fourni https://www.lesptitsloups.ch ; son robots.txt a répondu HTTP 403 depuis ce cloud. La page d’accueil n’a pas ensuite été collectée et aucune coordonnée extraite. Aucun abonnement/clé Brave réel utilisé. Rapport factuel : docs/WEBSITE_DISCOVERY_REAL_OBSERVATIONS.json. Windows et accès réels depuis le PC utilisateur restent non validés.

Les validations réelles OSM historiques ci-dessous restent distinctes des fixtures de ce patch. Voir WORKSPACE_V1_4.md.

---

# Validation 1.3.1

144 tests backend réussis, aucun échec ni test ignoré (un avertissement Starlette/AnyIO). Sept nouveaux cas couvrent le libellé exact, accents/apostrophes, catégories multiples et exclusion des écoles/seniors/hébergement résidentiel. Recherche réelle hors ligne à Morges : 6 fiches pour le libellé utilisateur, dont 2 childcare et 4 kindergarten ; crèche seule : 2. Détails agrégés dans docs/CHILDCARE_MORGES_REAL_VALIDATION.json. Ni le total national ni les résultats de cet extrait ne sont présentés comme un recensement officiel.

Parcours navigateur conservé avec ajout de l’aperçu activité reconnue/non reconnue. Pas de validation Windows ni d’accès Overpass réussi revendiqués.

---

# Validation 1.3 — 25 octobre 2026

**137 tests backend réussis, 0 échec, 0 ignoré** ; un avertissement de dépréciation Starlette/AnyIO. Syntaxe JS, compilation Python et cohérence des dépendances vérifiées. Les tests de migration/restauration s’exécutent services arrêtés, dans des bases temporaires.

**Navigateur Chromium réel** : création/édition de campagne avec trois métiers libres et mode DEEP, flèches des en-têtes dans les deux sens, tri serveur avant pagination, conservation de recherche/URL après rechargement, onglets critères/preuves/historique, vérification d’identité multi-champs et réglage versionné du barème. Parcours précédent conservé : contacts, CRM, presse-papiers réel, ATLAS, sauvegarde, mobile sans erreur JS. Préparation de téléchargement et erreur Overpass : réponses UI contrôlées explicitement, pas un nouvel accès source réel.

**Données réelles distinctes des fixtures :** même PBF Geofabrik suisse vérifié, snapshot 20 octobre 2026. Index v4 construit en 74,22 s sur Linux : 202 231 objets nommés avec tags d’activité (inclut des organismes/équipements non commerciaux). Recherche sans réseau de cinq activités hors liste initiale dans Vaud : fleuriste 71, fiduciaire 10, fitness 86, hôtel 224, office=lawyer 9. Rapport sans noms/contacts dans docs/BUSINESS_SEARCH_REAL_VALIDATION.json. Trois campagnes réelles restaurants/plomberie à nouveau exécutées hors ligne : 12 fiches, pas de doublons, correction/note/opposition/export conservés (docs/LOCAL_OSM_REAL_VALIDATION_1_3.json). Aucun audit réel de leurs sites ou appel/e-mail effectué.

## Acceptation du cahier des charges — tests synthétiques explicites

| Cas | Vérification effectuée |
|---|---|
| 1, 8 — domaine absent d’OSM / homonymes | Identification via preuve externe déclarée, deux champs dont téléphone ; nom seul refusé, homonyme distinct sans site attribué |
| 2 — site non trouvé | Deux hôtes documentés exigés, A jamais zéro, création provisoire |
| 3 — Lighthouse absent | A2 UNKNOWN, couverture réduite, statut provisoire/non évaluable |
| 4 — 503 puis 200 | Vrai code de retry exécuté sur transport contrôlé, pas de panne durable déclarée |
| 5 — téléphone sans formulaire | HTML synthétique réellement parsé, A5.1/A5.4 accordés |
| 6 — plombier sans Instagram | Configuration métier traçable, critères sociaux NOT_APPLICABLE |
| 7 — franchise | C3.1 zéro sur déclaration vérifiée, statut commercial distinct |
| 9, 13 — injection / IA sans preuve | Texte de page jamais exécuté ; notes sans références UNKNOWN |
| 10, 12, 17 — calcul | UNKNOWN/NA, normalisation, bornes, totaux A/B/C=100 et répétabilité à entrées/version/date identiques |
| 11 — opposition | Persiste après calcul/réimport, table d’oppositions additive |
| 14 — interruption | Tests existants pause/reprise campagne conservés ; audit persistant en attente, annulation puis nouveau traitement, cache/idempotence |
| 15 — export/import | JSON + historiques/grille/critères/preuves round-trip, colonnes CSV historiques conservées, corrections/opposition locales prioritaires |
| 16 — budget | Adaptateur refuse avant invocation du fournisseur quand plafond dépassé ; aucun fournisseur payant réel branché |
| 18 — UI explicable | Onglets, sous-critères, valeurs/preuves, historique et couverture dans navigateur réel |

Ces tests démontrent les règles et interfaces, **pas l’existence d’une intégration Google, avis, Lighthouse ou IA réelle**. Fournisseurs non configurés : UNKNOWN. Pas de validation humaine de calibration, pas de benchmark IA, pas de validation juridique et pas d’exécution Windows. Voir SCORING_V1_3.md pour les divergences et limites exactes.

---

# Validation — version 1.2 — copie suisse locale

**102 tests backend réussis, zéro échec, zéro ignoré**, avec un avertissement de dépréciation Starlette/AnyIO. Syntaxe JavaScript et compilation Python vérifiées. Les tests supplémentaires couvrent téléchargement interrompu/Range, contrôle d’empreinte et cache corrompu, annulation, URL fixe, création atomique, parsing d’un PBF synthétique avec géométries administratives, coordonnées manquantes, recherche communale, conservation du CRM et corrections plus récentes.

**Essai réel distinct des fixtures :** téléchargement HTTPS Geofabrik de 548 888 071 octets, contrôle du MD5 fournisseur et calcul SHA-256, lecture du PBF daté du 20 octobre 2026, index final construit en 38,95 s sur cette machine Linux. 32 275 objets nommés dans huit catégories, 26 cantons, 2 139 communes. Vaud : 1 557 restaurants et 3 fiches plomberie selon les tags indexés, sans prétention d’exhaustivité.

`scripts/validate_local_real.py` a exécuté trois campagnes via le vrai worker et une API sur base temporaire, réseau désactivé : sélection de 12 vraies fiches (9 restaurants, 3 plomberie), non-duplication, correction manuelle, note CRM, exclusion et export ATLAS vérifiés. Les audits/enrichissements étaient désactivés. Aucun contact envoyé. Le rapport agrégé sans coordonnées est dans `docs/LOCAL_OSM_REAL_VALIDATION.json` avec provenance, empreintes et résultats. Le ZIP n’inclut pas ces données réelles.

Un essai supplémentaire backend + worker démarrés via le lanceur a préparé une copie par l’API et terminé en réutilisant le fichier vérifié en cache. Le scénario navigateur contrôle le CRM, les filtres, la préparation/progression/annulation avec réponses UI explicitement contrôlées (pas un nouveau téléchargement réel), et les diagnostics Overpass précédents.

Les dépendances binaires Windows Python 3.12 amd64 ont été téléchargées avec succès. **Aucune exécution Windows effectuée.** Overpass reste indisponible depuis ce cloud ; la copie locale évite cet appel. Aucune mesure Lighthouse réelle revendiquée. Migration additive 0004 avec sauvegarde préalable ; fichiers OSM séparés du CRM.

Les rapports ci-dessous sont historiques et décrivent les versions antérieures.

---

# Validation complémentaire — 1.1.2

**83 tests backend réussis, zéro échec et zéro ignoré** (avertissement Starlette/AnyIO conservé). Douze cas supplémentaires vérifient la requête Vaud/restaurants/plomberie, la mémoire distincte, le GET, le filtre administratif communal et l’échappement de son nom, le contrôle de l’aire confirmée, les candidats sans addr:city, les réponses minimales 200/502/406, le délai partagé et la persistance du résultat de diagnostic. Les réponses utilisées par ces tests sont contrôlées ; aucun 200 de fixture ne prouve un rétablissement réel.

Le scénario navigateur V1.1/1.1.1 est conservé. Il contrôle aussi le nouveau bouton de diagnostic : une campagne synthétique en période d’attente empêche effectivement une requête externe et affiche `deferred`.

**Vérifications externes effectives depuis ce cloud** : requête interpréteur minimale GET → HTTP 406 ; même requête POST → HTTP 406. Cette observation ne permet pas d’expliquer le 502 observé sur le PC Windows de l’utilisateur. Aucune collecte réelle réussie n’est revendiquée. La distinction nécessite le test minimal depuis Diagnostics sur ce PC, après expiration du délai serveur. Le code officiel du frontend Overpass a été consulté : `src/overpass_api/frontend/cgi-helper.cc` lit QUERY_STRING pour GET. Référence : https://github.com/drolbr/Overpass-API/blob/master/src/overpass_api/frontend/cgi-helper.cc .

Aucune migration ni nouvelle dépendance ; données et résultats existants conservés. Les validations précédentes sont gardées ci-dessous comme historique.

---

# Validation complémentaire — correctif 1.1.1

Résultat réel de `.venv/bin/python -m pytest -q` : **71 tests réussis, aucun échec ni test ignoré**, avec l’avertissement Starlette/AnyIO déjà présent. Les 11 cas supplémentaires couvrent 502 puis succès contrôlé, échecs répétés bornés, Retry-After numérique/date, 403/406 sans retry, 429 sans multiplication des requêtes, délai de reprise persistant partagé, préservation des entreprises/curseurs et des pauses/arrêts manuels.

Les réponses HTTP de ces tests sont **contrôlées par MockTransport** ; un 502 puis 200 simulé n’est pas une preuve de rétablissement d’Overpass. Aucun changement d’instance ni de proxy n’est effectué. La disponibilité actuelle du service réel n’est pas revendiquée.

Le scénario navigateur ajoute une campagne synthétique en échec 502 et vérifie le message, l’heure de reprise et le bouton Reprendre désactivé durant l’attente, tout en conservant le parcours V1.1. Aucun accès externe n’est effectué par ces tests.

Aucune migration ni dépendance nouvelle. Le rapport V1.1 ci-dessous est conservé comme historique de sa validation.

---

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
