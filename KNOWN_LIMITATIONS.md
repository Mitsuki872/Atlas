# Limites ajoutées en 1.3

La qualification A/B/C est implémentée, mais ses collecteurs sont partiels : B/IA/Lighthouse/axe/captures réseau non configurés restent UNKNOWN. DEEP ne les simule pas. Import de mesures autorisées possible ; aucun fournisseur payant branché. Pas de calibration humaine/benchmark IA ni validation juridique réalisés. Le budget est contrôlé à la frontière d’adaptateur ; une future intégration payante exige un registre atomique des dépenses.

Le nouvel index v4 contient les objets nommés des familles OSM d’activité, y compris des organismes/équipements non commerciaux ; pas toutes les entreprises ni tous les synonymes. Une reconstruction est nécessaire depuis le PBF local vérifié. Identification humaine multi-champs requise avant audit officiel ; une URL OSM seule reste candidate. Les actions tel/mailto peuvent être désactivées tant que l’éligibilité est à vérifier. Les exports prospects conservent les nouveaux audits mais ne remplacent pas une sauvegarde complète du CRM. Voir SCORING_V1_3.md.

Les limites ci-dessous documentent la version antérieure ; la limite à huit catégories est remplacée par la recherche libre décrite ci-dessus.

# Limites restantes — version 1.2

La version 1.2 ajoute une découverte locale effectivement validée sur un extrait suisse réel. Elle ne valide pas l’ensemble de la V1 initiale ; les limites ci-dessous restent explicites.

## Sources et validations externes

- Overpass reste non validé en collecte réelle dans ce cloud. Le diagnostic du 22 octobre 2026 répond HTTP 406. Les tests de connecteur utilisent des réponses contrôlées, sans prétendre à un accès externe réussi.
- Les conditions/quotas actuels de chaque source doivent être vérifiés avant usage. Pas de contournement d’un blocage, de Nominatim systématique ou d’extraction massive via une instance publique. Zefix et les fournisseurs commerciaux ne sont pas implémentés.
- La découverte utilise par défaut l’extrait suisse Geofabrik, téléchargé puis indexé localement ; Overpass reste une option explicite. Pas d’import CSV ni de registre commercial exhaustif. La source ne couvre que les objets nommés et les huit catégories actuelles ; les 3 fiches plomberie trouvées dans Vaud ne représentent pas le nombre réel de plombiers.
- Premier téléchargement et mises à jour : Internet requis, environ 550 Mo et au moins 4 Go libres. Mise à jour manuelle, aucun nettoyage automatique des anciens fichiers/index. La préparation monopolise le worker ; les nouvelles campagnes attendent. Une indexation interrompue recommence depuis le début, le téléchargement peut reprendre.
- Les 26 cantons sont indexés, mais le formulaire de campagne reste limité aux six cantons proposés. Le classement utilise les limites administratives et un point représentatif ; les géométries incomplètes/ambiguës sont écartées. Une commune géographique ne certifie pas une adresse postale.
- La sélection équilibrée utilise un pool borné par secteur. Le total local est compté exactement dans l’index pour les critères demandés ; le total Overpass reste inconnu, affiché comme tel. Le mode pertinence ordonne les contacts présents, pas l’intention d’achat. Une entreprise conserve un secteur principal pour le tableau et ses catégories sources ; une entreprise multi-catégories ne compte qu’une seule fois dans la sélection équilibrée. Les succursales nécessitent une revue manuelle.
- L’enrichissement exige confirmation humaine du caractère officiel du site et des droits de consultation/réutilisation. Il est limité à la page principale et deux liens contact du même site, sans redirection ni exécution JavaScript. Pas de découverte automatique de site officiel. Les coordonnées OSM restent déclaratives. Les e-mails personnels sont exclus de l’extraction web automatisée par une liste conservative de boîtes génériques ; celle-ci peut manquer des adresses professionnelles valides.
- La normalisation téléphonique domestique reste orientée Suisse ; utiliser des numéros internationaux pour les entreprises étrangères. Syntaxe et normalisation ne prouvent pas la joignabilité.

## Audit et scores

- **Lighthouse mobile n’est pas installé dans l’environnement validé.** Aucun résultat Lighthouse, Core Web Vitals ou rendu mobile n’est revendiqué. Même si un exécutable est ajouté, son lancement automatique reste suspendu tant que toutes les sous-requêtes navigateur ne sont pas protégées contre le SSRF. Chromium seul ne suffit pas.
- L’audit mesure le HTML reçu : SEO/accessibilité partiels, trois liens internes au maximum. Pas de sitemap approfondi, parcours contact complet, liens externes, rendu JS, tests utilisateurs ou audit d’accessibilité exhaustif.
- Le client d’audit utilise des connexions directes DNS épinglées ; un cloud imposant un proxy peut empêcher les audits/enrichissements réels. Une restriction réseau donne un état non disponible, pas un mauvais score.
- Les redirections ne sont pas suivies. Robots indisponible hors 404/410 : accès suspendu. Une autorisation robots ne démontre pas tous les droits de réutilisation.
- Le score d’opportunité concerne actuellement la prestation web et les constats effectivement analysés, pas le potentiel financier ni une probabilité de vente. Aucune intention/budget inventé. Le score de qualité mesure surtout disponibilité, provenance et fraîcheur ; il ne certifie pas la fiabilité indépendante de chaque source.
- Les anciennes pondérations sont conservées dans les paramètres et archives, mais n’influencent pas le nouveau score de besoin ; pas encore de configuration distincte des règles de chaque service.
- Les audits de campagne sont réutilisés 24 h, y compris les états non disponibles ; la fiche propose une relance explicite contrôlée. Les contacts disparus d’une nouvelle source restent dans l’historique structuré : la source/date permet de juger leur fraîcheur.

## Installation et fonctionnalités V1 initiales

- Installation Windows, raccourci et scripts PowerShell/Batch non exécutés sur Windows. Pas de binaire autonome signé. La logique Python partagée est testée sur Linux ; suivre la recette cible dans INSTALLATION_WINDOWS.md.
- La découverte locale sur de vraies données de Vaud et trois campagnes hors ligne sont validées sur Linux (rapport agrégé dans docs/LOCAL_OSM_REAL_VALIDATION.json). La recette sur Windows demeure à exécuter ; le téléchargement des dépendances Windows ne vaut pas validation de leur exécution.
- Frontend léger HTML/CSS/JavaScript, pas de Next.js/TypeScript : choix documenté, pas de reconstruction dans ce patch.
- Campagnes limitées aux cantons/secteurs suisses disponibles : pas de rayon, pays configurable, géocodage, fournisseurs payants ou profondeur libre. Enrichissement par campagne optionnel et autorisé explicitement.
- Pas de fusion manuelle des doublons, ni de résolution exhaustive des contradictions champ par champ. Les corrections manuelles et les déclarations de fiches distinctes sont conservées. Aucune fusion sur simple nom.
- Horaires : plages explicites et 24:00 pris en charge ; pas de syntaxe OSM complète, dates exceptionnelles, jours fériés, filtres multi-jours ou correction/suppression sûre des plages existantes.
- CRM en table, rappels visibles sans notification système ni envoi automatique. Devis/ventes/opportunités sont des activités déclarées, pas des documents de facturation. Pas de motif de refus structuré ni de reporting exhaustif par campagne.
- Exports ATLAS et états de planning manuels uniquement, aucune synchronisation Notion/Calendar ni prise de rendez-vous. Copier un prompt ne modifie pas le CRM.
- Pas de rétention automatique, suppression sélective, rotation de logs/sauvegardes, chiffrement au repos ou authentification multi-utilisateur. Conserver les données et sauvegardes dans un dossier protégé.
- PostgreSQL/SaaS/multi-tenant/facturation non développés. Ne pas exposer l’application sur Internet.
- Une instance par machine. Pause/arrêt attendent la fin de l’entreprise en cours ; le worker ne conserve plus de transaction d’écriture pendant les accès réseau. Son heartbeat peut afficher « occupé depuis plus de 90 s » durant une longue campagne.

Voir LOCAL_OSM_GUIDE.md et PATCH_V1_1.md pour les changements et TEST_REPORT.md pour les validations effectives.
