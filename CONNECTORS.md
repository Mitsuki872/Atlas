# Source principale V1.2 — copie suisse locale

Téléchargement réel et vérifié depuis Geofabrik, index administratif local et campagnes hors réseau validés. Voir LOCAL_OSM_GUIDE.md et docs/LOCAL_OSM_REAL_VALIDATION.json. La source par défaut n’appelle plus Overpass. Le nombre total de candidats est connu dans cet index, sans prétendre à un recensement complet. ODbL et attribution obligatoires. Les descriptions Overpass ci-dessous concernent désormais l’option distante et les versions historiques.

# Actualisation 1.1.2

La requête utilise maintenant GET, officiellement pris en charge, et distingue les 64 Mio de mémoire de travail du serveur des 8 Mo maximum téléchargés. La commune est recherchée via son aire administrative de niveau 8 dans le canton ; une aire introuvable est signalée, sans recherche cantonale de remplacement. Un test manuel minimal est disponible dans Diagnostics. Depuis ce cloud, GET et POST reçoivent encore 406 ; aucun succès de collecte externe n’est affirmé. Voir PATCH_V1_1_2.md. Les descriptions de requêtes antérieures ci-dessous sont historiques.

# Mise à jour V1.1

Voir PATCH_V1_1.md pour les contacts normalisés, l’enrichissement de deux pages contact maximum, les reprises contrôlées et la sortie indépendante bornée par secteur. Les descriptions V0.1 ci-dessous sont historiques lorsque contredites par ce patch. Le diagnostic externe du 22 octobre retourne encore HTTP 406 ; aucun accès réel réussi revendiqué.

# Connecteurs, sources et conditions

## OpenStreetMap / Overpass

Connecteur implémenté : `osm-overpass`. Endpoint fixe `https://overpass-api.de/api/interpreter`. Aucune clé requise, aucun service payant. Recherche par zone administrative `ISO3166-2` suisse et catégories explicites, maximum 100 éléments. Le quota limite le résultat, **pas nécessairement le coût serveur de la requête** ; pour un grand volume, préférer un extrait régional autorisé et développer un lecteur dédié.

Cantons : VD, GE, FR, NE, VS, JU. Secteurs : restaurant, café, boulangerie, coiffure, réparation automobile, dentiste, plomberie, électricité. Aucun Nominatim. La ville est un filtre après la requête ; les résultats peuvent être incomplets, signalés lorsque la limite est atteinte. Pas de promesse d’exhaustivité. Un résultat vide n’est pas une preuve d’absence d’entreprise.

Attribution obligatoire : **© OpenStreetMap contributors — ODbL**, https://www.openstreetmap.org/copyright. Les exports conservent les sources et l’application affiche l’attribution. Pour redistribuer des bases dérivées, respecter les obligations ODbL ; vérifier votre usage et les conditions en vigueur de l’instance. Les coordonnées et contacts OSM sont déclaratifs et peuvent être obsolètes ; aucun numéro n’est présenté comme vérifié auprès de l’entreprise.

Limiter à une campagne à la fois, attendre au moins 60 secondes entre les requêtes, ne pas automatiser une extraction régionale exhaustive via une instance publique. Pas de CAPTCHA, d’authentification contournée, de rotation de proxy ou d’identité, ni de contournement de blocage. La V0.1 n’implémente pas de changement automatique d’instance.

### Validation effective le 21 octobre 2026

L’accès initial a été refusé par le proxy (403 CONNECT). Après ajout des domaines au brouillon réseau, `overpass-api.de` a répondu 406 sur GET /api/status et une petite requête GET /api/interpreter, et timeout sur une requête POST pour trois boulangeries du canton de Vaud. Aucune entreprise réelle n’a été obtenue. Une alternative publique, `overpass.private.coffee`, et la documentation wiki ont été refusées par le proxy dans cette session. **Conditions actuelles de l’instance et découverte réelle restent à valider.** Ne pas traiter les tests avec fixtures comme preuve d’accès externe.

## Import JSON autorisé

Import utilisateur fonctionnel sans connexion Internet, indépendant d’Overpass. Choisir Prospects → Importer JSON. Champs requis : `source_id`, `name`, `source_url`. Champs optionnels : `city`, `sector`, `phone`, `website`, `opening_hours`. Maximum 1 000 entreprises par requête, 2 Mo dans l’interface. L’utilisateur confirme disposer des droits de réutilisation. Utiliser des identifiants stables propres à la source. Les réimports du couple source_url/source_id mettent à jour les champs non corrigés manuellement, conservent chaque source et respectent le non-contact.

Cet import **n’est pas une preuve de découverte externe**. Le logiciel ne peut pas vérifier automatiquement les droits du fichier. Ne pas importer d’informations personnelles non nécessaires.

## Sites officiels identifiés dans la source

Seules la page indiquée et robots.txt sont actuellement demandées, sans navigateur automatisé. Le lien de la source n’est pas une certification de propriété du domaine. DNS public épinglé, TLS vérifié, délais et taille limités ; aucune redirection de l’accueil n’est suivie par l’audit V0.1, pour éviter de consulter une origine sans avoir vérifié ses restrictions. Robots indisponible hors 404/410 ou interdiction : audit suspendu avec explication. Robots autorisé ne suffit pas à établir tous les droits de réutilisation : l’opérateur doit vérifier les restrictions applicables. Aucun crawl de coordonnées personnelles ni envoi commercial.

Les accès directs aux sites publics peuvent être bloqués dans le cloud. Le client d’audit n’envoie pas les URL arbitraires via le proxy : il doit pouvoir épingler le DNS lui-même. Une restriction réseau produit un état d’audit non disponible, pas un mauvais score technique inventé.

## Zefix et autres sources

Zefix est signalé non implémenté. L’URL publique consultée n’a pas fourni de documentation exploitable dans cette session. Ni droits, ni quotas, ni modalités d’authentification n’ont pu être validés. Aucune extraction massive n’a été tentée. Références à vérifier :

- https://www.bj.admin.ch/fr/registre-du-commerce-zefix-et-regix
- https://www.zefix.admin.ch/ZefixPublicREST/
- https://opendata.swiss/fr/dataset/zefix-zentraler-firmenindex

Le protocole `Connector` expose actuellement l’identifiant et la découverte, avec métadonnées du connecteur OSM et normalisation. Recherche/enrichissement séparés et registre de connecteurs configurables restent à étendre. Aucun fournisseur commercial activé et aucune API IA.
