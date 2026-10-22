# Historique

## 1.1.1 — erreurs temporaires Overpass

Reprises bornées après 502/503/504/timeouts avec attente de 15 puis 30 secondes, respect de Retry-After et refus immédiat des accès interdits. Après épuisement des essais, message explicatif et délai persistant de cinq minutes minimum (ou plus si la source le demande). Le délai s’applique aux autres campagnes utilisant la même source. Une campagne en échec ne redémarre pas automatiquement. Pause/arrêt demandés pendant la découverte conservés. Aucune migration ni nouvelle dépendance. Voir PATCH_V1_1_1.md.

## 1.1.0 — 22 octobre 2026 — qualité des prospects

Filtres contacts et critères complémentaires paginés côté SQL, URL persistante, colonnes et actions rapides ; e-mail principal et contacts sourcés ; corrections Chez Nina / domaine sans schéma / fin de journée 24:00 ; répartition sectorielle configurable ; opportunité indépendante de la qualité des données ; enrichissement autorisé et audit HTML/SEO/accessibilité/liens renforcé ; une relance des timeouts ; migration additive, préservation des corrections et transactions worker hors accès réseau. Lighthouse et collecte externe réelle restent non validés. Voir PATCH_V1_1.md.

## 0.1.0 — 21 octobre 2026 — préversion

Création du backend local, frontend français responsive, migrations SQLite, campagnes et worker persistant, connecteur Overpass non validé en ligne, import JSON autorisé, provenance historisée, audit HTML borné, scoring explicable, CRM, horaires sourcés et filtre jour/heure, exports JSON/CSV/ATLAS, presse-papiers, diagnostics et sauvegarde/restauration. Lanceurs Windows fournis, non validés sur Windows. Tests backend et navigateur réels sur fixtures isolées. La V1 intégrale reste incomplète ; voir KNOWN_LIMITATIONS.
