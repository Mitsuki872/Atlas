# Patch V1.1 — Qualité des prospects

Date : 22 octobre 2026. Mise à jour de l’application existante, sans reconstruction ni suppression de base. La V1 complète du cahier des charges initial reste une préversion ; ce patch est centré sur l’exploitabilité des prospects.

## Changements opérationnels

### Contacts et filtres

Un e-mail principal, un canton et une liste structurée de coordonnées sont ajoutés aux entreprises. Chaque coordonnée conserve `kind`, `value`, `source`, `verified_at`, `confidence`, `origin`, et le champ OSM d’origine lorsque connu. Les variantes `contact:*` valides priment, avec repli sur les champs simples lorsqu’elles sont vides ou invalides ; toutes les valeurs valides distinctes sont conservées.

Les sept filtres sont disponibles : téléphone, sans téléphone, e-mail, sans e-mail, les deux, au moins un, aucun. Ils se cumulent avec présence du site, canton, commune, secteur, campagne, statut, score d’opportunité minimum, qualité minimum, état d’évaluation et dates de vérification inclusives. Les horaires demeurent cumulables. Le total, le tri et la pagination sont exécutés dans SQLite, avant chargement des lignes. Les exports partagent exactement ces filtres.

Les paramètres figurent dans l’URL, par exemple `#prospects?contact=both&canton=Vaud&sort=quality`. Rechargement, partage de lien, retour navigateur et pagination conservent les paramètres. Un minimum d’opportunité strictement positif exclut les opportunités inconnues ; zéro ne les transforme pas en entreprises de mauvaise qualité. Le filtre d’état distingue explicitement non évalué et évalué.

Le tableau affiche téléphone, e-mail, site, secteur, commune/canton, opportunité, qualité/complétude et statut CRM. Les fiches exposent aussi la provenance des coordonnées, les détails des deux scores et les résultats d’enrichissement/audit.

### Trois régressions corrigées

- Chez Nina : `raw_tags.email` est désormais normalisé, exposé comme e-mail principal et repris lors de la migration. Le test utilise une adresse `.example` synthétique, pas une coordonnée inventée présentée comme réelle.
- `restaurant-delice-angevin.com` est normalisé en `https://restaurant-delice-angevin.com` avant audit. La validation syntaxique ne prétend pas prouver l’accessibilité ; DNS, IP, restrictions robots et TLS sont ensuite contrôlés par le client sécurisé. Le test de domaine n’interroge pas cette entreprise réelle.
- `Mo-Fr 11:30-15:00,18:00-24:00` produit dix plages valides. `24:00` est la borne exclusive de fin de journée, pas le début du jour suivant. Les filtres SQL respectent aussi cette sémantique.

### Collecte multi-secteurs

Chaque secteur dispose d’une sortie bornée propre dans une seule requête Overpass. Une sélection équilibrée alterne les secteurs non vides et redistribue les places inutilisées. Le mode « coordonnées les plus complètes » privilégie les candidats ayant téléphone/e-mail/site dans le pool retourné, sans prétendre mesurer une intention d’achat. La campagne choisit le mode ; les anciennes campagnes sans option utilisent par défaut le mode équilibré.

Les statistiques montrent par secteur les candidats retournés et retenus, ainsi que le risque de troncature. Le nombre total disponible demeure `null` lorsqu’inconnu ; aucun secteur n’est inventé pour remplir un quota. La limite de sortie ne limite pas à elle seule le travail serveur : les extraits régionaux restent préférables aux requêtes de grande ampleur.

### Deux scores indépendants

**Opportunité commerciale** : somme plafonnée à 100 des points de constats techniques vérifiés et pertinents pour la prestation web. Les contacts et la richesse OSM ne modifient pas ce score. Absence de site identifié ou audit impossible : `total: null`, état `unknown`, jamais un zéro artificiel. Un audit exploitable sans problème détecté peut avoir zéro, ce qui signifie uniquement « pas de besoin démontré par ces contrôles ». Les preuves et limites restent consultables ; aucune probabilité de vente n’est calculée.

**Qualité des données** : téléphone 20, e-mail 20, site identifié 15, adresse structurée complète 20 (ville seule 5), provenance documentée 15 (source seule 5), fraîcheur 10 à 30 jours, 5 jusqu’à 180 jours, 0 au-delà. La date la plus ancienne des coordonnées est utilisée de manière conservative. Un recalcul ou une migration ne rajeunit pas les sources. La documentation d’une source n’est pas une certification indépendante de sa fiabilité ; les niveaux de confiance déclaratif/public/utilisateur sont visibles. Les anciennes pondérations sont conservées pour compatibilité/historique, mais ne mélangent plus joignabilité et besoin numérique.

### Enrichissement et audit

Sur une fiche, « Enrichir les coordonnées » nécessite de confirmer que le site est officiel et que la consultation/réutilisation est autorisée. Même option explicite dans une campagne, désactivée par défaut. Au plus la page principale et deux pages contact du même site ; robots, IP publique épinglée, TLS, taille et délai sont vérifiés. Les redirections ne sont pas suivies. Seules les adresses de boîtes génériques et les liens `tel:` non marqués privés/mobiles/directs sont extraits. Pas de collecte des adresses personnelles nom/prénom ni de balayage d’autres domaines. Les corrections manuelles et les contacts principaux non vides ne sont pas remplacés par cet enrichissement. Les autres coordonnées restent sourcées dans la liste structurée.

L’audit ajoute canonique, langue, robots meta, titres, structure, données structurées, libellés de formulaires, alt des images et contrôle de trois liens internes maximum. Chaque page respecte robots et le débit. Les timeouts de transport sont retentés une seule fois ; refus robots, URL invalide et restrictions ne sont pas contournés. Un refus d’accès 401/403/408/429 ne devient pas un constat de mauvais site. Les durées HTTP sont étiquetées, sans les présenter comme mesure de rendu mobile.

**Lighthouse n’est pas disponible dans l’installation validée. Aucun score Lighthouse ou performance mobile n’est inventé.** Le lancement automatique de Lighthouse demeure non activé, même si un exécutable est ajouté ultérieurement : il faut d’abord protéger toutes les sous-requêtes du navigateur contre le SSRF et respecter les restrictions des sources. C’est la principale limite restante de la partie audit V1.1.

### Actions rapides

Appeler (`tel:`), e-mail (`mailto:`), ouvrir le site, copie effective des coordonnées, statut Contacté, note, relance et sélection ATLAS. Les actions sans donnée sont désactivées avec une explication. Le non-contact désactive les actions de prospection et reste imposé par le backend. L’ouverture d’un lien n’envoie rien automatiquement. Les notes/rappels ouvrent le formulaire existant ; aucun rappel n’est inventé. La copie confirme seulement après succès du presse-papiers.

## Mise à jour sans perte des données

1. Arrêter avec Stop.bat puis créer une sauvegarde via Backup.bat. Ne pas supprimer l’ancien dossier.
2. Copier les fichiers de la nouvelle archive dans le dossier existant en conservant intégralement `data`, `.env` éventuel et les sauvegardes. L’archive ne contient ni base, ni secrets, ni environnement virtuel.
3. Relancer Install.bat (ou `.venv/bin/python -m pip install -r requirements.txt` puis `.venv/bin/python -m app.manage migrate` sur Linux).
4. Le gestionnaire crée une nouvelle sauvegarde cohérente avant migration. La révision additive `0003` conserve les UUID, campagnes, activités, suppressions, jobs et corrections. Elle reprend les contacts/horaires depuis les éléments déjà stockés, avec leurs dates d’origine. Les valeurs normalisées et l’ancien score sont archivés dans `facts.legacy_contact_values` et `facts.legacy_score_v01`.
5. Lancer Start.bat, recharger la page, contrôler les coordonnées et filtres. En cas de retour arrière, arrêter, restaurer le code de la version précédente ET sa sauvegarde de base préalable ; ne pas simplement supprimer les nouvelles colonnes.

Sous Windows, les scripts sont fournis mais cette validation a lieu sur Linux. Voir INSTALLATION_WINDOWS.md pour la recette cible. Aucun Docker ni API payante nécessaire.

## Validation et limites

Voir TEST_REPORT.md pour les commandes et résultats réellement obtenus. Les tests de connecteurs et enrichissement sur fixtures sont distingués de l’accès externe. Overpass a encore répondu HTTP 406 dans le diagnostic réel de cette session ; aucune collecte réelle réussie n’est revendiquée. Les horaires exceptionnels et toute la syntaxe opening_hours ne sont pas encore couverts. La normalisation domestique des téléphones reste orientée Suisse : utiliser des numéros internationaux pour les entreprises étrangères. Zefix et les fournisseurs commerciaux restent non implémentés. Les restrictions de la V1 initiale non concernées par ce patch sont détaillées dans KNOWN_LIMITATIONS.md.
