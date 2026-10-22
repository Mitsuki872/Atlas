# Version 1.2 — Annuaire suisse local

## Ce qui change pour vous

L’application conserve OpenStreetMap comme source, mais télécharge une copie suisse depuis Geofabrik puis la prépare sur votre ordinateur. Les recherches locales n’appellent plus Overpass. Internet reste nécessaire pour le premier téléchargement, les mises à jour demandées et les audits/enrichissements de sites ; le CRM et la recherche dans la copie prête restent accessibles sans Internet.

### Mise à jour de votre installation actuelle

1. Dans l’ancienne application : Paramètres → Créer une sauvegarde. Fermer ensuite avec Stop.bat.
2. Extraire le nouveau ZIP, puis copier ses fichiers dans le dossier de l’application **sans supprimer ni remplacer `data` et `.venv`**.
3. Lancer **Install.bat** pour installer les nouvelles bibliothèques et appliquer la migration additive. Si `.venv` existe, cette mise à jour passe directement par Python, sans exécuter Installer.ps1 : le blocage PowerShell rencontré précédemment n’intervient pas dans ce parcours. Les données sont conservées et une sauvegarde de base est créée avant migration.
4. Lancer **Start.bat**, puis recharger la page dans le navigateur.
5. Dans Dashboard, Campagnes ou Paramètres, cliquer **Préparer la copie suisse**. Attendre le message **Copie locale prête**. Le téléchargement initial pèse environ 550 Mo au moment de cette validation ; prévoir au moins 4 Go libres. La taille peut évoluer. La progression affiche les octets téléchargés puis les étapes de lecture et de classement, sans pourcentage inventé pendant l’indexation.
6. Créer une campagne : **Copie suisse locale**, **Vaud**, **restaurant** et **plumber** (plomberie), par exemple 12 prospects, puis Démarrer. La découverte seule est le réglage initial : laisser l’audit et l’enrichissement désactivés pour ce premier essai hors ligne. Ils peuvent être lancés ensuite depuis les fiches avec les autorisations nécessaires.

Une campagne ancienne sans source explicitement enregistrée utilise désormais la copie locale pour sa prochaine découverte. Les résultats déjà collectés sont réutilisés ; ils ne sont pas effacés. Une campagne explicitement configurée Overpass reste Overpass : la dupliquer pour choisir la source locale si nécessaire. Le délai d’Overpass ne bloque pas une reprise locale.

## Ce qui a réellement fonctionné

Validation sur un véritable extrait Geofabrik : **548 888 071 octets**, données OSM au **20 octobre 2026 à 20:23:47 UTC**. Empreinte MD5 fournie par Geofabrik vérifiée, SHA-256 local calculé, puis lecture effective du PBF et des limites administratives.

- 32 275 fiches OSM nommées dans les huit catégories prises en charge.
- 26 limites cantonales et 2 139 limites communales assemblées ; les objets hors canton ou à appartenance ambiguë ne sont pas affectés arbitrairement.
- Vaud : **1 557 fiches restaurant, 3 fiches plomberie** dans cet extrait et ces tags précis. Ce ne sont pas des nombres officiels d’entreprises. Des doublons entre objets OSM peuvent exister et doivent être revus par les outils de déduplication.
- Une sélection réelle de 12 fiches contenait 9 restaurants et les 3 fiches plomberie : 12 avaient un téléphone, 9 un e-mail et 11 un site renseigné. Ces coordonnées sont publiées dans OSM, pas vérifiées auprès des entreprises.
- Trois campagnes dans une base CRM temporaire, réseau désactivé : pas de doublons au second passage ; correction manuelle, note, exclusion de contact et export ATLAS conservés et vérifiés. Aucun appel ou e-mail envoyé. Les audits web étaient désactivés pour cet essai.

Le rapport agrégé sans noms ni coordonnées réelles est dans `docs/LOCAL_OSM_REAL_VALIDATION.json`. Les chiffres correspondent à ce fichier daté, pas aux futurs extraits. Le ZIP n’inclut pas le PBF ni les contacts de test : votre ordinateur prépare sa propre copie via le bouton.

## Fonctionnement et conservation

- Fichier PBF et index séparés de `data/prospect.sqlite`. La migration `0004` ajoute uniquement l’historique des tâches de préparation.
- Téléchargement depuis une destination fixe HTTPS Geofabrik. La redirection vers le fichier daté est vérifiée ; pas d’URL arbitraire, de proxy alternatif ou de désactivation TLS.
- Reprise avec HTTP Range quand le serveur le permet, contrôle de cohérence de la plage, de taille et d’empreinte avant import. Si Range est ignoré, le téléchargement repart proprement au lieu d’ajouter deux fichiers. Une empreinte fausse ne devient jamais une copie utilisable ; le fichier généré est écarté et conservé pour diagnostic, puis un nouvel essai peut télécharger à neuf.
- L’empreinte MD5 du fournisseur contrôle la corruption du transfert ; ce n’est pas une signature numérique. HTTPS vérifie l’identité du serveur. Le SHA-256 local identifie précisément la copie validée, sans être présenté comme une empreinte indépendante fournie par Geofabrik.
- L’index est construit dans un fichier temporaire. Il n’est activé qu’après contrôles SQLite et géographiques. Les anciens index/fichiers ne sont pas supprimés automatiquement. Une préparation interrompue ne détruit ni l’index prêt précédent, ni le CRM.
- Arrêter la préparation conserve les téléchargements partiels. Après fermeture/redémarrage du worker, une préparation interrompue est récupérable : le téléchargement reprend ; une indexation inachevée redémarre depuis le début, ce qui est annoncé par son étape de progression. Les données métier restent accessibles pendant la préparation. Le worker traite la préparation en priorité : les nouvelles campagnes peuvent attendre sa fin ou son arrêt.
- La mise à jour est manuelle, via **Mettre à jour la copie**. Une copie identique est vérifiée et réutilisée. Le logiciel ne télécharge pas à chaque recherche ni au démarrage quotidien.
- Les identifiants `osm:node/way/relation:id` sont les mêmes que pour Overpass. Les corrections manuelles, le non-contact et les activités restent protégés. Une ancienne copie ne remplace pas une coordonnée plus récemment vérifiée dans le CRM.

## Géographie et qualité

Cantons et communes sont déterminés par les polygones administratifs présents dans l’extrait, pas par une simple boîte rectangulaire ni par une supposition de code postal. Un point OSM sert directement ; un objet surfacique utilise un point intérieur représentatif ; une voie ouverte utilise un point médian, signalé dans la provenance. Les géométries incomplètes sont ignorées. Une appartenance ambiguë n’est pas devinée.

Une commune dérivée des limites peut compléter une ville absente ; sa provenance précise que cela ne constitue pas une adresse postale vérifiée. Les tags d’origine restent conservés. La date des contacts/horaires est celle de l’extrait, sans les rajeunir au jour de l’import.

La source reste limitée : seules les fiches nommées correspondant aux huit tags actuels sont indexées. Beaucoup de plombiers ne sont pas répertoriés avec `craft=plumber` et un nom. Zéro dans une commune ne veut pas dire absence d’entreprises. L’annuaire est une base de découverte à compléter, pas un registre exhaustif ni une certification des coordonnées.

## Windows et limites

Les roues binaires Python 3.12 Windows 64 bits des dépendances ont été téléchargées avec succès depuis PyPI : aucune compilation locale n’est prévue. **Les scripts n’ont pas été exécutés sur un PC Windows** ; l’installation complète sur votre poste reste à confirmer. Le lecteur PBF et les recherches ont été exécutés réellement sur Linux.

Pas de Docker, de serveur permanent ni d’API IA payante. Pas de Lighthouse mobile validé, pas de synchronisation calendrier. Les sites web externes restent soumis à leurs restrictions et à leur disponibilité. L’échec d’un audit ne signifie pas un mauvais site et ne remet pas en cause la découverte locale.

Attribution : **© OpenStreetMap contributors — ODbL ; extrait Geofabrik**. Sources : https://download.geofabrik.de/europe/switzerland.html et https://www.openstreetmap.org/copyright . Respecter les obligations ODbL lors de toute redistribution d’une base dérivée.
