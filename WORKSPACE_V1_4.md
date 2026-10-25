# Version 1.4 — espace de prospection et recherche de sites

## Mise à jour Windows
1. Créer une sauvegarde avec Backup.bat, puis arrêter avec Stop.bat.
2. Copier les fichiers du ZIP dans l’installation actuelle **sans supprimer data ou .venv**.
3. Lancer Install.bat, puis Start.bat et recharger la page du navigateur.

Migration additive 0006 : historique des recherches de sites. Une sauvegarde est créée avant migration. Campagnes, CRM, corrections, exclusions et audits existants restent conservés. **Aucun changement du fichier suisse ni de son index ; pas de téléchargement ou reconstruction requis.** Les dépendances Python restent identiques à la version précédente. Installation Windows non exécutée dans ce cloud Linux.

## Un parcours, trois espaces distincts
- **Prospects** : table compacte de qualification. Entreprise/localité, contacts, secteur, A/B/C, complétude et CRM ; plus de dix-huit colonnes ni de huit boutons répétés par ligne. Tri serveur dans les en-têtes, pagination, URL et exports conservés. Tri e-mail accessible dans l’en-tête de contacts.
- **Pipeline CRM** : cinq étapes commerciales avec compteurs réels, cartes et changement de statut enregistré. Les colonnes défilent horizontalement ; jusqu’à 30 dossiers par étape, recherche/campagne pour affiner. Les cartes ne sont pas déplaçables par glisser-déposer : utiliser leur menu de statut. Aucun duplicata de la table Prospects.
- **Planification** : échéances CRM enregistrées, relances en retard, sélection ATLAS persistante et historique d’exports. Pas de faux calendrier ni de connexion Calendar/Notion revendiquée. Une relance passée n’est pas automatiquement déclarée effectuée. Jusqu’à 200 échéances affichées.

Filtres principaux visibles : recherche, campagne, contact et statut. Localisation, notes, fraîcheur et horaires sont regroupés sous « Affiner ». Les filtres actifs restent dans l’URL et visibles sous forme de pastilles supprimables ; le panneau avancé est replié au rechargement, sans perdre les paramètres actifs. Les critères historiques sont conservés dans une section secondaire.

## Page entreprise
Cliquer sur une entreprise ouvre une vraie route `#company?id=…`, avec retour à la liste et ses filtres. Le dossier présente trois jauges SVG A/B/C, leur couverture et le caractère provisoire/non évaluable, coordonnées condensées, opportunités prouvées et prochaines actions. Les notes inconnues ont une jauge en tirets et un « — », jamais un zéro fictif.

Notes/rappels et activité récente sont séparés des détails. « Voir plus » donne accès aux critères, preuves, audits et sources ; les corrections restent disponibles dans un panneau dédié. Les actions tel/mailto gardent les protections d’éligibilité existantes. Les sélections ATLAS persistent localement après rechargement et sont réconciliées avec les entreprises encore présentes. Une recherche terminée rafraîchit son panneau sans effacer une note en cours de rédaction.

Design sombre bleu, accents cyan/violet, cartes et navigation compacte ; ajustement du contraste mémorisé. Pages vérifiées à 1440 px et 390 px. Aucune image distante, police externe ou dépendance graphique supplémentaire nécessaire.

## Recherche automatique de sites : fonctionnement réel
La recherche est activée par défaut pour les nouvelles campagnes et les copies d’anciennes campagnes sans préférence explicite. Elle s’exécute après la collecte, dans des tâches persistantes. Pour une entreprise déjà collectée : « Trouver le site officiel ». On peut aussi fournir une URL à vérifier. Il n’existe aucune association codée en dur pour les P’tits Loups.

Ordre des sources : tags/contacts existants, domaine professionnel d’un e-mail (simple candidat, pas preuve), autres objets OSM correspondants dans la même commune ; puis **Brave Search API si elle est configurée et autorisée**. Pas de construction du domaine à partir d’un nom d’entreprise, pas de scraping des pages de résultats Google/Bing/Brave. Sans moteur configuré, la recherche générale est réellement indisponible ; cela est affiché, jamais assimilé à une absence de site.

Pour activer la recherche générale :
1. Disposer d’une clé Brave Search API obtenue selon les conditions et le plan actuel du fournisseur. **Le projet ne promet pas qu’un compte/quota gratuit est proposé.**
2. Paramètres → Recherche automatique de sites : enregistrer la clé, autoriser les requêtes et confirmer qu’elles entrent dans un quota sans coût. Si ce n’est pas le cas, laisser la recherche générale désactivée : la V1.4 ne branche pas de facturation payante.
3. Choisir la limite quotidienne (25 par défaut, 1–500). Un appel réservé compte même si le réseau échoue ; pas de répétitions automatiques de l’appel moteur. Le quota est réservé en base avant requête. Les nouvelles recherches de campagne réutilisent un résultat de moins de 24 h ; une relance depuis le dossier est explicite.

La clé est fournie par BRAVE_SEARCH_API_KEY ou par le fichier local dédié `data/search-provider.env`, lisible par le processus backend/worker. Ce fichier n’est pas dans SQLite, exports, sauvegardes SQLite ou ZIP source. Ses permissions sont restreintes sur les systèmes POSIX ; sous Windows, elles suivent la protection du dossier. Aucun retour d’API ne renvoie la valeur. Une sauvegarde de base ne sauvegarde donc pas cette clé. Pas de redémarrage requis pour la clé enregistrée depuis l’interface. Remplacer la clé remet les autorisations à zéro : confirmer les préférences et le quota du nouveau compte avant de lancer des recherches.

Par recherche : au plus une requête moteur et cinq domaines candidats. Les candidats annuaires/réseaux sociaux ne sont pas assimilés à un site autonome. Chaque page utilise DNS public épinglé, contrôle robots, délais, limites de taille et jusqu’à trois redirections, chacune contrôlée séparément. Aucun CAPTCHA, refus ou interdiction robots contourné. Un site dépendant du rendu JavaScript peut rester non vérifiable.

## Identification et enrichissement
Un résultat de moteur n’est pas une confirmation. Le nom et la localité doivent être présents sur le site ; téléphone, e-mail ou adresse déjà connus doivent également concorder pour une association automatique. Sinon le domaine reste candidat, visible et à confirmer. Plusieurs domaines concordants restent ambigus. Les scores d’identification 60/95 sont des niveaux de règles explicites, pas des probabilités calibrées.

Après confirmation forte : site associé, coordonnées professionnelles génériques enrichies via le collecteur existant, provenance et date conservées. Les corrections manuelles ne sont pas écrasées. Vérifier à nouveau un domaine saisi manuellement est permis si le domaine est le même ; le texte saisi reste conservé. Une opposition bloque la recherche. Pause/reprise/arrêt d’une campagne contrôle les recherches qu’elle a créées. Une annulation peut attendre la requête déjà en cours mais n’applique pas son résultat ; elle est vérifiée entre candidats.

Un nouveau domaine invalide les mesures courantes du domaine précédent, sans effacer l’historique. Les notes anciennes ne sont jamais réattribuées silencieusement au nouveau site. Une collecte ultérieure avec une coordonnée OSM absente ne supprime pas le site/contacts déjà retrouvés.

Les extraits de preuve limitent le texte conservé au titre et aux signaux de correspondance ; les numéros/e-mails personnels rencontrés dans une page ne sont pas aspirés en masse. L’enrichissement reprend les restrictions du collecteur existant et ne garantit pas la joignabilité.

## Cas P’tits Loups de Morges : résultat observé
Dans notre copie OSM du 20 octobre, le point osm:node:3387878694 contient nom/activité/accessibilité, aucun site ni contact. L’URL https://www.lesptitsloups.ch a été fournie par l’utilisateur. La vérification de son robots.txt depuis ce cloud a renvoyé **HTTP 403** ; la page d’accueil n’a pas ensuite été collectée, aucune coordonnée extraite. Cette URL n’est donc pas présentée comme une découverte automatique réussie.

Aucune clé Brave réelle n’était disponible pour valider une recherche en direct. Les règles d’identification, l’adaptateur, le quota et l’interface ont été testés avec des réponses contrôlées identifiées. Les accès depuis le PC Windows peuvent différer. Pour une recherche générale automatique sur ce poste, la configuration du moteur reste nécessaire ; pour une URL connue, « Indiquer un site à vérifier » est disponible, sous réserve d’accès autorisé.

Rapport factuel : docs/WEBSITE_DISCOVERY_REAL_OBSERVATIONS.json. Captures d’interface : données synthétiques identifiées dans docs/screenshots, aucun contact client réel.

## Limites conservées
Pas de garantie de retrouver tous les sites, de fournisseur de recherche activé sans clé, de découverte sur pages interdites, de mesure Lighthouse/IA ou de validation juridique/calibration nouvelle. Sans coordonnées de référence, une fiche peu renseignée peut nécessiter une confirmation humaine. Les audits avancés restent soumis aux limites documentées en 1.3. Application locale mono-utilisateur, conservation/protection des données à gérer dans le dossier local.
