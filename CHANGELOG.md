# 1.3.1 — correction accueil d’enfants

Correspondances explicites pour le libellé utilisateur, distinction crèche/préscolaire, aperçu de reconnaissance, explication des résultats vides et total national clarifié. Aucun changement d’index/base. Voir PATCH_V1_3_1.md.

# 1.3.0 — 25 octobre 2026

Tri SQL ascendant/descendant par en-têtes et URL, champ métiers libre, index suisse général v4 avec reconstruction depuis le PBF vérifié en cache. Migration additive 0005, scores A/B/C versionnés, couvertures/identification, preuves/historiques/opportunités/oppositions, audits manuels persistants QUICK/DEEP et adaptateurs d’observations autorisées. Filtres et exports étendus, réimport compatible. Aucun fournisseur B/IA ni Lighthouse effectif ; voir SCORING_V1_3.md.

# Historique

## 1.2.0 — copie OSM suisse locale

Téléchargement Geofabrik vérifié et reprenable, index séparé atomique, cantons/communes par polygones OSM, découverte hors réseau par défaut, tâches persistantes de préparation avec progression/arrêt/reprise, migration additive 0004, conservation des identités/corrections et préférence aux contacts plus récents. Nouveaux boutons de préparation/actualisation ; audit désactivé par défaut sur les nouvelles campagnes, Overpass reste optionnel. Install.bat met à jour directement une .venv existante sans PowerShell. Validation sur vrai PBF suisse, trois campagnes locales et tests automatisés ; Windows reste non exécuté. Voir LOCAL_OSM_GUIDE.md.

## 1.1.2 — requête Overpass et diagnostic sur le poste cible

Transport GET officiellement accepté par l’API ; mémoire de travail serveur à 64 Mio au lieu de 8 Mio, sans relever la limite de téléchargement ; filtre communal réellement envoyé à la source ; vérification du compteur d’aire et refus des aires non résolues. Nouveau test manuel minimal Overpass dans Diagnostics, avec délai partagé et sans changement automatique d’instance. Aucun schéma ni dépendance ajoutés. Voir PATCH_V1_1_2.md.

## 1.1.1 — erreurs temporaires Overpass

Reprises bornées après 502/503/504/timeouts avec attente de 15 puis 30 secondes, respect de Retry-After et refus immédiat des accès interdits. Après épuisement des essais, message explicatif et délai persistant de cinq minutes minimum (ou plus si la source le demande). Le délai s’applique aux autres campagnes utilisant la même source. Une campagne en échec ne redémarre pas automatiquement. Pause/arrêt demandés pendant la découverte conservés. Aucune migration ni nouvelle dépendance. Voir PATCH_V1_1_1.md.

## 1.1.0 — 22 octobre 2026 — qualité des prospects

Filtres contacts et critères complémentaires paginés côté SQL, URL persistante, colonnes et actions rapides ; e-mail principal et contacts sourcés ; corrections Chez Nina / domaine sans schéma / fin de journée 24:00 ; répartition sectorielle configurable ; opportunité indépendante de la qualité des données ; enrichissement autorisé et audit HTML/SEO/accessibilité/liens renforcé ; une relance des timeouts ; migration additive, préservation des corrections et transactions worker hors accès réseau. Lighthouse et collecte externe réelle restent non validés. Voir PATCH_V1_1.md.

## 0.1.0 — 21 octobre 2026 — préversion

Création du backend local, frontend français responsive, migrations SQLite, campagnes et worker persistant, connecteur Overpass non validé en ligne, import JSON autorisé, provenance historisée, audit HTML borné, scoring explicable, CRM, horaires sourcés et filtre jour/heure, exports JSON/CSV/ATLAS, presse-papiers, diagnostics et sauvegarde/restauration. Lanceurs Windows fournis, non validés sur Windows. Tests backend et navigateur réels sur fixtures isolées. La V1 intégrale reste incomplète ; voir KNOWN_LIMITATIONS.
