# Sécurité et utilisation responsable

## Portée

Application privée mono-utilisateur sur la machine locale. Le backend écoute uniquement sur 127.0.0.1 ; le Host autorisé est strictement limité à localhost/127.0.0.1 port 8765. Pas d’accès réseau partagé ni d’exposition Internet. Aucun appel, SMS, e-mail ou événement externe automatique.

## Protections implémentées

- Entrées Pydantic bornées, types et statuts validés ; requêtes SQLAlchemy paramétrées.
- Jeton aléatoire par processus pour les mutations ; contrôle Origin/Host contre les requêtes provenant de pages étrangères et DNS rebinding du serveur local. Aucun CORS permissif.
- CSP, refus de framing, nosniff et pas de cache ; rendu des textes via échappement HTML et valeurs DOM, aucune exécution de contenu collecté.
- Audit : HTTP/HTTPS seulement, ports 80/443, pas d’identifiants URL, refus des IP privées/loopback/réservées/link-local et des réponses DNS mixtes. Connexion à l’IP publique validée avec SNI et validation du certificat du domaine original ; validation à chaque redirection du client réseau. Accueil non redirigé dans l’audit V0.1.
- TLS, signatures des distributions pip et vérifications des gestionnaires de paquets non désactivés ; aucune clé stockée dans les sources.
- Timeouts, limite de réponse 1,5 Mo pour les audits, 8 Mo pour Overpass. Pas de moteur JavaScript sur les sites collectés.
- CSV neutralise les formules à l’export. Prompt ATLAS sérialisé et instructions séparées des données ; cela réduit les risques, sans garantir le comportement d’un assistant externe face aux injections.
- Liste persistante de non-contact, historique des corrections et sources, copies ATLAS sans changement de statut automatique.
- Sauvegardes SQLite cohérentes, validation intégrité et tables avant restauration ; refus si les services sont actifs ; sauvegarde avant remplacement.
- Le superviseur vérifie PID, heure de création et commande avant arrêt ; ne tue pas les autres applications ni de force.

## Limites

Pas de chiffrement au repos, authentification, gestion des utilisateurs, signature d’exécutable Windows, sandbox navigateur ou audit de sécurité indépendant. Les autres programmes du même compte local peuvent accéder à la base et au jeton local. Le blocage SSRF limite les accès au réseau interne, sans garantir que le contenu d’un domaine public soit sûr ou autorisé. Les conditions juridiques de la prospection suisse doivent être vérifiées pour l’usage effectif ; ce document ne certifie pas une conformité légale.

Ne placer ni secrets, ni exports de clients réels dans Git. Protéger le dossier `data` et ses sauvegardes avec les droits du système d’exploitation. Les sauvegardes contiennent la même information que la base. Pas de collecte d’e-mails personnels. Respecter refus de contact, finalité, minimisation et durée de conservation.

Pas de purge automatique ou suppression sélective en V0.1. Pour effacer totalement les données : arrêter l’application, exporter/sauvegarder si souhaité, puis supprimer explicitement le dossier de données et les sauvegardes. Cette opération doit être effectuée consciemment par l’utilisateur. Uninstall.bat conserve les données.

## Incident

Arrêter les services via Stop. Conserver les logs et sauvegardes hors partage public ; consulter Diagnostics pour l’identifiant, le composant et la date. Ne jamais copier de secrets ou de bases réelles dans un ticket public. Ne pas modifier les règles TLS ou contourner un refus d’une source pour obtenir un audit positif.

## V1.1

Les enrichissements demandent une autorisation et une confirmation du caractère officiel du site ; seules les pages du même site et les boîtes génériques sont considérées. Les numéros marqués privés/mobiles/directs ne sont pas extraits. Les liens mailto encodent les caractères réservés. Les accès réseau conservent le DNS épinglé et ne suivent aucune redirection d’accueil/contact. Les timeouts ont un seul nouvel essai, sans retry des refus. Lighthouse automatique reste désactivé faute de contrôle de ses sous-requêtes réseau ; la présence de Chromium seule ne suffit pas à garantir l’isolation. Migration 0003 précédée d’une sauvegarde via le gestionnaire supporté, aucun rajeunissement artificiel des sources.

## Source locale V1.2

Destination de téléchargement fixe, redirections HTTPS limitées au même fournisseur et aux chemins suisses attendus ; aucune URL libre. Empreinte MD5 fournisseur conservée, SHA-256 local identifié, jamais de contournement de TLS ou d’empreinte attendue. Limites de taille et d’espace disque, Range validé, fichiers corrompus générés mis à l’écart. PBF/index séparés du CRM ; publication atomique, pas de remplacement de base métier. La lecture du PBF passe par des bibliothèques natives maintenues, sans exécution de contenu OSM. Les noms/contacts restent échappés et non fiables. Les fichiers locaux contiennent des coordonnées professionnelles publiques : protéger data et les sauvegardes, respecter les finalités de réutilisation et le non-contact. Aucun extrait ni contact réel de recette distribué dans le ZIP/Git.
