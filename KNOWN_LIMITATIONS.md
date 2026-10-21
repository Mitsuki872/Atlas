# Limites connues — V1 intégrale non livrée

Cette version 0.1.0 est une préversion locale utilisable pour l’import, le CRM, les horaires et les exports. Elle ne satisfait pas encore le critère ultime de la V1 du cahier des charges. Ne pas la commercialiser comme une V1 complète.

## Blocages de validation externe

- Aucun résultat réel Overpass obtenu dans ce cloud : timeout POST, HTTP 406 GET ; proxy initialement restrictif. Le connecteur est implémenté et testé avec fixtures, mais son fonctionnement externe n’est pas prouvé.
- Les conditions d’accès en vigueur d’Overpass et Zefix n’ont pas pu être entièrement consultées/confirmées. Zefix non implémenté ; pas de collecte massive.
- Les URL arbitraires d’audit utilisent une connexion directe avec DNS épinglé ; un cloud imposant un proxy peut les rendre inaccessibles. Pas de contournement de la vérification ou du réseau.
- Aucun test sur Windows : installateur PowerShell, raccourci et scripts batch restent à valider sur poste cible. Pas de binaire autonome signé.
- Recette Vaud → entreprises réelles → audits réels → Windows non exécutée de bout en bout. Les tests navigateur utilisent des fixtures identifiées dans une base temporaire.

## Écarts fonctionnels restants

- Pas de Next.js/TypeScript, shadcn, TanStack Query ; frontend léger servi par FastAPI (choix expliqué dans ARCHITECTURE).
- Paramètres campagne réduits : pas de pays autre que Suisse, rayon, géocodage, types d’opportunités configurables, profondeur d’audit configurable ou choix multiple de connecteurs. Secteurs et cantons explicitement limités. Le budget n’active aucun achat, tous les fournisseurs actuels étant gratuits.
- Une seule source de découverte Internet implémentée. Pas de registre complet de connecteurs activables, connecteur extrait régional, fournisseur commercial ni IA.
- L’import utilisateur est JSON uniquement (pas CSV en entrée), et ne déclenche pas l’audit web automatiquement.
- Audit limité au HTML reçu et robots.txt : pas de Lighthouse, mesures mobiles, performances, Core Web Vitals, analyse du rendu, crawl contact/services, sitemap, vérification active de liens cassés ou tests complets d’accessibilité. Les redirections de l’accueil sont refusées, pas validées comme site en panne. Aucun site officiel n’est identifié par moteur de recherche.
- Pas d’enrichissement Zefix, identifiants officiels, e-mails, réseaux ou vérification indépendante des coordonnées. Données inconnues laissées inconnues. L’interface ne gère pas encore tous les champs détaillés de la fiche entreprise.
- Déduplication automatique limitée au même identifiant source ; pas de fusion manuelle. Les signaux téléphone/domaine permettent de déclarer des fiches distinctes, pas d’affirmer qu’elles sont identiques. Pas de résolution complète des contradictions champ par champ.
- Horaires : sous-ensemble explicite OSM seulement. Pas de moteur de jours fériés, dates exceptionnelles, syntaxe opening_hours complète, multi-jours sélectionnés, filtre intervalle/matin/après-midi/soir, correction/suppression des plages saisies ou gestion d’obsolescence. Les horaires non interprétés restent visibles et ne deviennent pas des disponibilités.
- CRM en table, pas Kanban ; rappels affichés mais sans notification système, marquage « effectué » ou report intégré. Devis/ventes sont des activités déclarées, pas des documents PDF ni un workflow de facturation. Pas de motif de refus structuré. Statuts et activités volontairement indépendants.
- Dashboard réduit : pas de calcul complet du taux de réponse/intérêt ni rapport avancé par campagne/secteur. Compteurs et graphiques présents utilisent exclusivement la base réelle de l’instance.
- Les filtres n’incluent pas encore toutes les dimensions du cahier des charges (région détaillée, source, fiabilité, analyse, opportunité, priorité). Recherche globale limitée aux noms, villes et téléphones.
- États de planification manuels ; pas d’import d’événements ni de synchronisation Notion/Calendar. Le prompt ne garantit pas le comportement d’ATLAS ; validation humaine indispensable.
- Pas de purge automatique, rétention configurable, suppression sélective, chiffrement local ou authentification multi-utilisateur.
- Modèle consolidé : certaines entités demandées sont des champs JSON ou types d’activité, pas des tables indépendantes. PostgreSQL et SaaS non testés ; isolation multi-tenant, quotas distribués, facturation et abonnements absents.
- Le heartbeat est mis à jour entre jobs ; une longue campagne peut apparaître « occupé depuis plus de 90 s » sans être bloquée. La pause/annulation attend la fin du traitement d’une entreprise.
- Pas de rotation automatique des sauvegardes/logs ; surveiller l’espace disque. Ne pas partager les sauvegardes.

## Priorités suivantes

1. Valider légalement et techniquement une source de découverte réelle depuis le réseau cible, puis exécuter la recette Vaud et audit réel avec consentement/conditions appropriés.
2. Valider tous les lanceurs sur Windows 10/11, chemins avec espaces, dépendances absentes, interruptions, mise à jour et restauration.
3. Étendre les horaires avec un moteur complet des exceptions et dates, édition sûre et source vérifiable.
4. Compléter le moteur d’audit, les opportunités configurables, les filtres et la qualification sans confondre estimations et observations.
5. Compléter la gouvernance des données (suppression, conservation), les tests de sécurité indépendants et le modèle métier avant une version commercialisable.
