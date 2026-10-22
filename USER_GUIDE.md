# Guide utilisateur

**V1.2 :** la source par défaut est la copie OSM locale. Préparer d’abord l’annuaire suisse via le bouton du Dashboard/Campagnes/Paramètres, puis lancer les campagnes. Les anciennes campagnes sans source explicite passent au local pour leur prochaine découverte ; leurs résultats et le CRM sont conservés. L’audit est optionnel et désactivé par défaut pour les nouvelles campagnes. Guide pas à pas : LOCAL_OSM_GUIDE.md.

**V1.1 :** consulter [PATCH_V1_1.md](PATCH_V1_1.md) pour les filtres de contact persistants dans l’URL, la provenance, les actions rapides et les deux scores. Les explications ci-dessous sont complétées par cette mise à jour.

## Premiers pas

Ouvrir l’application via Start. Un dashboard vide est normal : aucune donnée de démonstration n’est ajoutée. Diagnostics permet de vérifier backend, base, worker et erreurs. La recherche en haut s’exécute avec Entrée. Le bouton de thème est dans la navigation.

## Découvrir des entreprises

Campagnes → Nouvelle campagne. Choisir un nom, canton, secteurs, limite, score minimum, budget plafond et éventuellement une ville et des exclusions. Enregistrer, puis Démarrer. La source actuelle est gratuite ; le budget ne déclenche aucun achat. Le filtre ville porte sur les résultats déjà bornés : une recherche peut manquer des entreprises de la ville.

Les compteurs distinguent découverte, normalisation, doublons, enrichissement, audit, qualification et erreurs. Les premiers résultats sont accessibles pendant le traitement. Pause/Reprendre conserve l’avancement ; Arrêter conserve les résultats et demande confirmation. Dupliquer permet de relancer avec de nouveaux critères. Une campagne exécutée ne peut pas être modifiée pour préserver son historique. Archiver ne détruit pas les données.

En cas d’échec, consulter le message et Diagnostics. Corriger le prérequis avant Reprendre. Ne pas contourner un refus de la source. La découverte Overpass n’est pas validée dans l’environnement cloud livré.

## Importer ses propres données

Prospects → Importer JSON. Le fichier est un tableau JSON, sans clé enveloppante, avec `source_id`, `name`, `source_url` pour chaque entreprise. Champs facultatifs : `city`, `sector`, `phone`, `website`, `opening_hours`. Utiliser uniquement des données réelles autorisées et confirmer les droits de réutilisation. Maximum 1 000 entrées et 2 Mo. L’identifiant et l’URL de source doivent rester identiques pour reconnaître un réimport. Aucune recherche Internet n’est effectuée par l’import.

## Examiner un prospect

Cliquer son nom. La fiche présente les contacts connus, source, date, scores d’opportunité et de qualité, justifications, hypothèses, données manquantes et résultats techniques. Un site non identifié n’est pas déclaré inexistant. Son opportunité reste non évaluée, indépendamment de la complétude des contacts. Un audit impossible à réaliser n’est pas un site en panne. Le potentiel commercial est inconnu par défaut ; le score n’invente aucune intention d’achat ou budget.

Les corrections manuelles sont enregistrées dans l’historique et protégées des prochaines collectes. Le changement de site invalide son audit. Les ambiguïtés téléphone/domaine permettent de déclarer deux fiches distinctes après vérification ; il n’existe pas encore de fusion manuelle. L’historique des sources est consultable dans la fiche.

## Horaires

Les horaires d’ouverture issus de la source restent indicatifs. Le parseur gère les jours explicites, plages fractionnées et traversées de minuit. Les expressions complexes et jours fériés ne sont pas interprétés : elles sont affichées comme telles, jamais converties en disponibilités inventées.

Une plage explicitement publiée peut être ajoutée avec jour, début, fin, type et URL de source. Choisir « Appel explicitement publié » seulement si la source le dit réellement. Les plages d’appel priment sur les ouvertures pour les filtres. La saisie manuelle est refusée sur un texte source non interprété pour éviter de masquer une exception. Les plages ne peuvent pas encore être supprimées/corrigées depuis l’interface ; ne pas les saisir sans vérification.

## CRM

Changer le statut puis enregistrer. Choisir Ne plus contacter demande confirmation et exclut durablement la fiche des traitements futurs et des exports ATLAS. Cette exclusion ne peut pas être levée par une simple modification du statut.

Ajouter une note, un appel avec résultat, un rappel avec date, un devis, une opportunité ou une vente déclarée. Montants en CHF. Le champ date de rappel utilise le fuseau local du navigateur, puis est stocké avec décalage explicite et affiché Europe/Zurich. Les activités et statuts sont indépendants : un devis ou un export ne change pas automatiquement le statut.

Les rappels sont affichés dans le dashboard, sans notification système ou envoi automatique. Le suivi s’effectue dans une liste filtrable, pas un tableau Kanban.

## Filtres et exports

Prospects, CRM et Planification partagent la base. Combiner recherche, ville, secteur, statut, campagne, score minimum, type d’horaires et jour/heure. Choisir Filtrer pour appliquer. Le tri propose opportunité, qualité des données, nom, ville et date de vérification. Les filtres et la pagination persistent dans l’URL. Pagination par 50 entreprises.

La sélection se conserve entre les pages ; la sélection de tous les résultats filtrés est limitée à 1 000. Les exports CSV/JSON portent sur les filtres actifs et, lorsqu’une sélection existe, leur intersection avec cette sélection. Pour tout exporter : retirer la sélection ou recharger la page. Le CSV neutralise les chaînes susceptibles d’être interprétées comme formules.

## Préparer ATLAS

Planification → sélectionner les prospects → Prévisualiser. Vérifier le JSON, les notes et les sources. Le bouton COPIER LE PROMPT POUR ATLAS confirme seulement après réussite du presse-papiers. Si le navigateur refuse, télécharger le texte ou le sélectionner dans la zone de prévisualisation.

Coller le prompt dans ATLAS. ATLAS doit vérifier ses accès Notion/Calendar, consulter les engagements réellement accessibles, proposer les plages libres, attendre votre validation puis créer uniquement des blocs personnels autorisés. Cette application n’a aucun accès à ces systèmes. Un export créé ne signifie ni planning validé, ni appel planifié, ni rendez-vous avec une entreprise.

Les états de l’historique sont déclarés manuellement après confirmation. Ils ne changent pas les statuts CRM. Aucun rendez-vous client n’est créé automatiquement.

## Sauvegarde et incidents

Paramètres → Créer une sauvegarde ou Backup.bat. Restauration via Restore.bat, application arrêtée, confirmation explicite. Les erreurs worker possèdent un identifiant, composant et date dans Diagnostics ; les logs techniques sont dans `data`. Conserver les sauvegardes en lieu sûr. Voir INSTALLATION_WINDOWS pour les lanceurs et SECURITY pour les limites.
