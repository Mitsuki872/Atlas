# Version 1.5 — Campagnes → Entreprises → ATLAS

## Mise à jour
Sauvegarder avec Backup.bat, arrêter avec Stop.bat, copier les fichiers du ZIP en conservant data et .venv, puis lancer Install.bat et Start.bat. Recharger la page. **Aucun nouveau téléchargement suisse ni reconstruction d’index requis.** Les dépendances Python restent identiques. Windows n’a pas été exécuté dans ce cloud Linux.

La migration 0007 crée une sauvegarde préalable et regroupe les anciens statuts. Les campagnes, entreprises, corrections, notes, oppositions, anciens audits et exports ATLAS sont conservés. Chaque ancien statut modifié est inscrit dans l’activité avant remplacement. L’ancien fichier de clé local et le module de gestion des clés sont retirés après migration réussie ; aucun compte ou identifiant chez un fournisseur externe n’est modifié.

## Parcours principal
1. **Créer une campagne** : nom, canton, commune, secteur(s), limite. Les résultats sont enregistrés rapidement ; les sites connus sont ensuite contrôlés automatiquement en arrière-plan, dans les limites publiques autorisées.
2. **Choisir une entreprise** depuis la vue d’ensemble ou la liste. Dossier compact : contacts à copier, statut, contrôles mesurés, besoin observé et note. Les preuves et options restent sous « Voir plus ».
3. **Ajouter à ATLAS** : seule la sélection et l’export du prompt restent dans cet espace. Aucun pipeline CRM ou agenda dupliqué. Les anciennes routes CRM/Planification renvoient vers Entreprises/ATLAS.

### Relancer — 25 prospects
Le bouton relance la même campagne sur un **nouveau lot de 25 candidats maximum**, en évitant les identifiants déjà collectés dans cette campagne. Les anciennes lignes ne sont pas effacées. Une tâche précédente conserve ses enregistrements et son curseur ; une relance crée une nouvelle tâche. Une campagne déjà en cours ne peut pas être relancée deux fois.

« Voir les résultats » ouvre le dernier lot par défaut ; retirer la pastille Lot permet de consulter toute la campagne. Si la source est épuisée ou ne contient que quelques entreprises, le lot peut contenir moins de 25 fiches, puis le tri de qualité peut encore réduire les résultats affichés. Aucune fiche inventée pour atteindre 25. En mode Overpass historique, le pool reste borné ; la copie locale est recommandée.

## Secteurs français et mots-clés
Le catalogue propose plus de 50 catégories françaises et des mots-clés. Exemples : Enfants/UAPE → Crèche ; tea-room → Boulangerie et Café. Cliquer sur la catégorie choisit son identifiant stable ; le texte de recherche du menu n’est pas envoyé comme filtre de nom. Les secteurs déjà enregistrés restent reconnus, les anciens identifiants anglais sont affichés en français. Les mots-clés sont une aide à la sélection, pas une promesse de couverture exhaustive OSM ni une détection de toutes les sous-activités.

Les menus sont présentés en listes stylisées, pilotables au clavier (flèches, Entrée, Échap), en conservant les valeurs natives des formulaires. Les cinq statuts disposent de couleurs et de libellés, sans dépendre de la couleur seule.

## Cinq statuts
- **À contacter** — bleu : anciens Nouveau, À qualifier, Qualifié, À appeler et Appel planifié.
- **Contacté** — violet : Contacté, Intéressé, rendez-vous, devis et négociation.
- **À relancer** — ambre : Sans réponse / À relancer.
- **Client** — cyan.
- **Écarté** — rose : Refusé, Archivé et Ne plus contacter.

Une **opposition** reste un indicateur distinct, permanent et protégé. Le statut Écarté seul n’efface ni ne remplace une opposition. La case « Opposition : ne plus contacter » écarte la fiche ; elle ne permet pas de retirer une opposition existante. Les anciens imports et liens de filtre sont normalisés sans perdre l’historique.

## Coordonnées et ouverture des sites
Cliquer sur un numéro ou un e-mail **copie exactement cette valeur** dans le presse-papiers. Le bouton de copie globale et le prompt ATLAS restent disponibles. Aucune application téléphonique/mail ni aucun envoi n’est déclenché.

« Ouvrir le site » est un lien externe direct dans un nouvel onglet. Il ne passe pas par le collecteur, une iframe ou un proxy de l’application. Les anciennes URL sans protocole sont préparées en HTTPS pour l’ouverture ; les adresses invalides ne deviennent plus des liens `#` ouvrant l’application. Les paramètres de lien sont conservés. L’action **Analyser le site** reste séparée. Les appels d’interface au serveur local ont un délai maximal de 18 secondes, avec erreur lisible plutôt qu’un chargement indéfini.

Cela ne répare pas un serveur tiers : un vrai refus 403/404, problème de certificat, panne ou blocage dans le navigateur peut persister malgré une URL correcte. Aucun contournement de refus, robots ou CAPTCHA. Le domaine fourni des P’tits Loups a précédemment répondu HTTP 403 depuis ce cloud ; aucun accès réel réussi n’est revendiqué ici.

## Vérifications gratuites et résultats exploitables
Les campagnes vérifient les sites connus : identité multi-champs, réponse HTTP/HTTPS, éléments HTML, contacts, sitemap et échantillon de liens, selon les pages accessibles. Les coordonnées dans le texte et les données structurées JSON-LD sont prises en compte pour rapprocher un contact **déjà connu**, sans exécuter le JavaScript ni aspirer des coordonnées personnelles en masse.

La **présence constatée** peut documenter la fiche OSM, sa catégorie et son lien au site confirmé. Cela ne mesure ni avis, ni rang Google, ni trafic. Les contrôles indisponibles restent inconnus. Si la couverture ne permet pas une note complète, la carte montre les contrôles positifs/mesurés (ex. 2/3) et indique explicitement « partiels » ; elle n’affiche pas une fausse note complète. L’ancien contrat A/B/C et ses preuves restent accessibles dans les détails et exports.

La priorité visible exige un besoin prouvé : une fiche bien remplie ne devient pas automatiquement 100/100 d’opportunité. Le tri principal met les besoins démontrés avant les dossiers à vérifier.

Trois vues SQL paginées :
- **Exploitables** : coordonnées ou site présents, sans exclusion ni décision de masquage.
- **À vérifier / sans besoin démontré** : aucune coordonnée/site, exclusion, ou contrôles suffisamment positifs sans défaut observé.
- **Toutes les fiches** : historique complet, sans suppression.

Un site avec ≥12 contrôles web mesurés sans défaut observé est rangé sans besoin démontré dans ce périmètre limité. A/B suffisamment couverts (≥80 %) et ≥90/100 sans défaut peuvent aussi l’être. Ces seuils sont une règle de tri commerciale, pas une preuve universelle d’absence de besoin. Un audit bloqué avec contact/site disponible n’est pas un échec de qualité et ne suffit pas à écarter la fiche. Les vues et filtres restent dans l’URL ; les compteurs indiquent les fiches à revoir.

## Aucun service payant
Brave, son adaptateur, ses commandes de configuration, les lectures de clé et les appels API associés sont retirés du produit actif. Aucun moteur commercial ni abonnement nécessaire. La collecte utilise OSM et les domaines déjà connus par les tags, contacts, rapprochements locaux ou saisie utilisateur, puis les pages publiques autorisées. **Sans source contenant un domaine, tous les sites ne peuvent pas être retrouvés automatiquement.** Le produit ne prétend pas proposer une recherche Internet universelle gratuite.

Les anciennes observations/imports restent conservés comme historique. Les audits Lighthouse, Google, réseaux sociaux et IA non exécutés restent inconnus ; rien n’est simulé. Le logiciel n’effectue aucun envoi commercial automatique.

## Validation
Voir TEST_REPORT.md. Tests backend sur bases temporaires, navigateur réel avec entreprises synthétiques explicitement identifiées, copie suisse réelle testée hors ligne dans une base séparée. Les liens externes du test navigateur utilisent une page contrôlée pour vérifier l’URL et l’ouverture d’onglet : pas une preuve de disponibilité de tous les sites réels. Les captures d’interface ne représentent pas des clients réels.
