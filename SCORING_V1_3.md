# Version 1.3 — tri, métiers libres et qualification A/B/C

## Installation de la mise à jour
1. Créer une sauvegarde dans Paramètres, puis arrêter avec Stop.bat.
2. Copier les fichiers du ZIP dans l’installation actuelle, **sans effacer data ou .venv**.
3. Lancer Install.bat puis Start.bat, et recharger la page. La migration additive 0005 crée une sauvegarde préalable ; campagnes, notes, oppositions et corrections ne sont pas remplacées.
4. Cliquer **Préparer la copie suisse** si l’application demande une nouvelle préparation. Le nouvel index v4 couvre davantage d’activités. Le fichier PBF déjà présent est revérifié (MD5 et SHA-256), puis réutilisé sans téléchargement ni mise à jour implicite de sa date. « Mettre à jour » recherche explicitement un nouvel extrait. Sans fichier valide, un téléchargement initial est nécessaire. Prévoir 4 Go libres ; la durée dépend du PC. Le CRM reste séparé de l’index.

Les scripts Windows et l’ancien problème HTTP 500 sur le poste de l’utilisateur ne sont pas déclarés validés/résolus sans son journal. Le lanceur exige un backend, une base et un worker accessibles. Si l’installation échoue, conserver les logs/data et suivre INSTALLATION_WINDOWS.md.

## Tableau et campagnes
Chaque en-tête triable possède une flèche : premier clic croissant, second décroissant. Le serveur trie l’ensemble des résultats avant pagination ; filtres, campagne, colonne et sens restent dans l’URL. Le changement de tri revient à la première page. Les notes inconnues restent à la fin, même en ordre croissant. Tri initial : C décroissant, puis couverture C et confiance identité.

La création/édition accepte jusqu’à 20 activités, séparées par des virgules. Exemples : `fleuriste, fiduciaire, fitness`, ou `office=lawyer`. Les alias français courants ont une correspondance explicite ; sinon recherche littérale dans le nom et les valeurs OSM. Aucun moteur ne comprend arbitrairement tous les synonymes : un libellé inconnu peut ne rien trouver. L’index comprend les objets nommés avec amenity/shop/craft/office/tourism/leisure/healthcare/industrial, pas un registre exhaustif d’entreprises ; des équipements ou organismes non commerciaux peuvent apparaître et doivent être qualifiés.

Campagnes existantes et huit identifiants historiques restent utilisables. Répartition équilibrée ou priorité aux coordonnées conservées. Le formulaire stocke QUICK/DEEP, seuils A/B/C, confiance minimum et budget. Les seuils influencent le compteur de qualification, sans supprimer les résultats collectés. Aucun fournisseur payant n’est activé.

## Notes et preuves
- **A — site** : qualité observée du site confirmé.
- **B — visibilité** : présence mesurée dans des sources autorisées.
- **C — opportunité** : besoin, contactabilité, faisabilité et ciblage ; élevée = intérêt de prospection, sans probabilité de vente revendiquée.
- **Complétude** : ancien indicateur indépendant des coordonnées/adresse/provenance.

Chaque critère conserve mesure, état, points maximum/accordés, méthode, date, seuil et références de preuve. UNKNOWN n’accorde ni ne retire de points ; NOT_APPLICABLE exige une justification et sort du dénominateur. A/B : sous 60 % de couverture, note non évaluable ; de 60 à moins de 80 %, provisoire. C reste provisoire quand des informations nécessaires manquent ou qu’une dépendance est provisoire. Les valeurs exactes sont stockées ; l’interface arrondit uniquement l’affichage.

La grille 1.0 est dans app/rubric_v1.json. Paramètres permet une nouvelle version des seuils/limites ; API `/api/settings/rubric` permet aussi pertinence sectorielle et catalogue code critère → prestation. Les maxima et critères de la version sont immuables. Chaque audit conserve sa configuration complète et son empreinte ; une mise à jour ne réécrit pas les anciennes notes. Les notes historiques V1.1 restent disponibles pour compatibilité et ne sont pas présentées comme les nouveaux A/B/C.

## Identification avant audit
Une URL OSM est seulement un candidat. Depuis la fiche : **Vérifier l’identité et le site**, documenter deux champs concordants (dont adresse/téléphone/e-mail/domaine), sources et raison. Une fiche annuaire/sociale n’est pas assimilée à un site autonome. Le niveau 95/100 désigne une vérification humaine multi-champs déclarée, pas une probabilité statistique mesurée. Un nom seul est refusé ; aucune attribution automatique entre homonymes.

« Site non trouvé » exige une recherche sourcée sur au moins deux hôtes indépendants ; ce n’est pas la preuve d’une absence. A reste non évaluable ; une opportunité de création reste provisoire/à vérifier. Un changement de domaine invalide la confirmation courante et les mesures du domaine précédent, dont l’historique demeure conservé.

La fiche présente Résumé, Preuves, Audit objectif, Audit IA, Visibilité, Opportunités, Historique et Contact. Les actions tel/mailto sont désactivées quand la qualification enregistrée est non éligible, avec explication. L’enregistrement d’activités passées et les notes restent possibles ; aucun appel/e-mail n’est envoyé par le logiciel. L’export ATLAS inclut l’éligibilité et demande une validation humaine avant toute planification d’un prospect non éligible. Oppositions, fermeture vérifiée, client actif et interdiction de contact restent prioritaires ; une réimportation ne retire pas une opposition.

## Collecte objective et jobs
QUICK collecte les contrôles HTTP/HTML effectivement possibles : résolution réussie ou EAI_NONAME confirmé trois fois, certificat explicitement vérifié/invalide, réponse HTTP, viewport, title, description, indexabilité, sitemap, contacts et échantillon de liens. Les contrôles de visibilité réelle d’un H1, rendu mobile, contraste et JS ne sont pas déduits du HTML reçu. Une canonical absente/invalide est mesurable ; sa résolution réussie n’est pas supposée sans mesure externe.

Timeouts/5xx : jusqu’à trois essais bornés, temporisation exponentielle pour 5xx, pas de retry sur refus/politique. Un 503 puis 200 ne devient pas une panne durable. Les erreurs DNS du collecteur restent inconnues. Robots, DNS public épinglé, TLS, bornes de taille et une requête simultanée par domaine restent appliqués. Limites configurables : jusqu’à 5 pages, profondeur au plus 2 (collecteur actuel : un clic), timeout/retries et cache TTL. Redirections non suivies : les destinations non testées restent inconnues.

L’interface met les audits manuels en file persistante ; worker récupère les audits interrompus, respecte annulation/exclusion/changement de site et conserve les étapes. Un audit annulé peut laisser finir la requête réseau en cours, sans appliquer son résultat. Une relance manuelle est explicite ; l’API peut réutiliser un audit frais de même mode/site/grille sans force. La découverte de campagne réutilise l’infrastructure et les curseurs existants. `/api/campaigns/{id}/events` fournit une enveloppe d’événements avec identifiants stables pour polling ; pas de SSE prétendu. Un seul worker traite les tâches successivement.

## Sources B et module IA : disponibilité réelle
Aucun fournisseur Google/SERP, avis, réseaux sociaux ou IA n’a été configuré ou interrogé. Les critères correspondants restent UNKNOWN, sans fausse note B. DEEP expose les blocages et n’affirme pas avoir exécuté Lighthouse, axe-core ou des captures isolées. Installer Chromium seul n’active pas un crawl navigateur protégé contre toutes les sous-requêtes privées.

L’adaptateur autorisé accepte des observations JSON sourcées depuis des outils exécutés ailleurs ; `/api/companies/{id}/observations` ou bouton d’import dans la fiche. Schéma strict, preuves datées, notes IA sans refs/modèle/version/raison ignorées. Les recherches locales B4.2 exigent trois requêtes et protocole (position géographique, langue, date, appareil, moteur, API, résultats). Exemple **synthétique** : docs/SCORING_OBSERVATIONS_EXAMPLE.json. Le prompt immuable optionnel est dans app/audit_adapters.py ; les pages sont des données, jamais des instructions. L’empreinte d’audit couvre les entrées, références, modèle et version importés.

L’adaptateur bloque avant appel si le budget estimé dépasserait le plafond. Aucun fournisseur payant n’est branché dans le worker, coût API réel zéro ; un futur branchement devra ajouter une réservation atomique de dépenses persistantes, facturation réelle et gestion des secrets. Pas de fausse intégration payante annoncée. Calibration humaine, accord inter-évaluateurs, répétabilité IA, captures desktop/mobile et biais sectoriels restent à réaliser avant usage en production.

## Exports, conservation et limites
JSON ajoute identification, qualification et audit_history ; CSV conserve ses colonnes historiques et ajoute les champs JSON de qualification/identification/historique, incluant critères et preuves. Réimporter un export JSON utilise l’import d’archive : champs existants, contacts et historiques sont conservés, scores historiques recalculés avec la grille/les entrées archivées, nouvelles oppositions fusionnées sans effacer les anciennes. Les corrections locales existantes priment. Un export de prospects n’est pas une sauvegarde complète des campagnes/activités : utiliser la sauvegarde SQLite pour cela.

Les tables AuditRun/critères/preuves/instantanés/opportunités/oppositions sont additives. Pas de rotation/rétention automatique, SaaS ni multi-utilisateur ; conserver installation et sauvegardes dans un dossier protégé. Le droit suisse applicable et la calibration commerciale doivent être validés avant toute automatisation de contact. Le projet ne réalise aucune automatisation d’envoi.

## Validation effective
Tests automatisés et navigateur : voir TEST_REPORT.md. Validation réelle du même extrait suisse, daté du 20 octobre : nouvel index de 202 231 objets nommés, construit en 74,22 s sur ce Linux ; il inclut des objets non commerciaux. Recherche réelle hors ligne dans Vaud : 71 fleuristes, 10 fiches comptabilité/fiduciaire, 86 fitness, 224 hôtels et 9 office=lawyer selon les tags et alias utilisés. Chiffres de la copie, pas recensement officiel. Trois campagnes réelles restaurants/plomberie : 12 fiches, doublons/correction/note/opposition/export préservés. Aucun audit réel de ces sites ni installation Windows revendiqués.
