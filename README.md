# Version 1.3 — qualification PME

Tri par flèches dans les colonnes, métiers libres et scores A/B/C explicables avec couverture, preuves et historique. [Installation et limites réelles](SCORING_V1_3.md). Mise à jour additive : conserver data/.venv, lancer Install.bat, puis reconstruire l’index local à la demande. Google/avis/IA/Lighthouse ne sont pas configurés : critères correspondants inconnus. Les sections 1.2 ci-dessous restent un historique.

# Prospect Engine — 1.2.0 — recherche OSM locale

Application locale de prospection B2B, en français. Le patch [V1.1 — Qualité des prospects](PATCH_V1_1.md) améliore le projet existant avec une migration additive et sauvegarde préalable. **La V1 intégrale n’est pas encore validée.** Consulter [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) et [TEST_REPORT.md](TEST_REPORT.md) avant utilisation.

## Commencer avec la copie locale

Voir [LOCAL_OSM_GUIDE.md](LOCAL_OSM_GUIDE.md). Mise à jour : sauvegarder, Stop, copier les fichiers en gardant data/.venv, Install.bat puis Start.bat. Cliquer **Préparer la copie suisse**, attendre **Copie locale prête**, puis lancer une campagne Vaud / restaurant / plumber avec la source locale. Environ 550 Mo au premier téléchargement, 4 Go libres recommandés. Audits désactivés par défaut pour une première découverte entièrement locale.

La découverte a été validée sur un vrai extrait suisse et trois campagnes sans réseau : 12 fiches réelles sélectionnées, pas de doublons au second passage, CRM et corrections conservés. Les scripts Windows restent à confirmer sur la machine cible.

## Correctif 1.1.2

Requêtes Overpass via GET, mémoire de travail serveur distincte de la limite téléchargée, commune filtrée côté source, aire confirmée et bouton de diagnostic minimal à exécuter depuis le PC Windows. Voir [PATCH_V1_1_2.md](PATCH_V1_1_2.md). Aucun rétablissement du service externe n’est revendiqué.

## Correctif 1.1.1

Les pannes Overpass 502/503/504 sont expliquées et les reprises encadrées. Voir [PATCH_V1_1_1.md](PATCH_V1_1_1.md). Ce correctif n’établit pas la disponibilité du service externe.

## Nouveautés V1.1

Filtres de contact côté SQL avec pagination et URL persistante ; e-mail principal et coordonnées sourcées ; collecte équilibrée par secteur ; deux scores indépendants ; enrichissement contact autorisé ; audit HTML renforcé ; actions rapides. Voir PATCH_V1_1.md pour la mise à jour sans perte de données et les limites Lighthouse.

## Ce qui est implémenté

- Interface responsive avec six pages métier, diagnostics, thème clair/sombre, recherche et états vides sans données fictives.
- FastAPI + SQLite / SQLAlchemy et migrations Alembic ; données locales accessibles hors ligne.
- Campagnes, worker séparé, file persistante, pause/reprise/arrêt, résultats progressifs et historique des sources.
- Connecteur **OSM local / Geofabrik réellement validé** ; Overpass reste une option distante non validée dans ce cloud. L’import JSON autorisé permet aussi de travailler sur ses propres données.
- Détection conservative de doublons par identifiant source ; signaux téléphone/domaine présentés pour revue manuelle ; protection des corrections et liste persistante de non-contact.
- Audit HTML limité avec preuves, robots.txt, validation DNS et adresse publique épinglée, limites et timeouts ; scores indépendants d’opportunité et de qualité des données.
- CRM : statuts, notes, appels, résultats, rappels, devis, opportunités et ventes déclarées, statistiques réelles.
- Horaires fractionnés et nocturnes, saisie sourcée des horaires d’appel, filtres jour/heure. Expressions non prises en charge affichées comme non interprétées.
- Sélection et exports CSV/JSON ; prompt ATLAS structuré, prévisualisation, copie réelle avec vérification du résultat, historique et états manuels. Aucune synchronisation calendrier.
- Sauvegarde SQLite cohérente, restauration hors ligne confirmée, lanceurs Windows et superviseur de processus.

## Windows

Voir [INSTALLATION_WINDOWS.md](INSTALLATION_WINDOWS.md). Extraire l’archive, lancer `Install.bat`, puis `Start.bat`. Aucun Docker, Node.js ou service cloud permanent requis. Python 3.12 doit être installé si absent : le programme explique comment. Les lanceurs Windows sont fournis mais n’ont pas été exécutés sur Windows.

## Développement Linux/macOS

Python 3.12 recommandé. Depuis la racine du dépôt :

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app.manage migrate
.venv/bin/python scripts/launcher.py start --no-browser
.venv/bin/python scripts/launcher.py diagnose
.venv/bin/python scripts/launcher.py stop
.venv/bin/python -m pytest -q
```

L’interface écoute uniquement sur la boucle locale, port 8765. Le worker réserve le port local 8766 comme verrou d’instance unique (aucun protocole métier). Utiliser les ports par défaut : la protection Host est volontairement stricte. Une instance par machine. `PROSPECT_DATA_DIR` permet d’isoler les bases de développement ; ne pas lui donner un répertoire partagé avec une autre instance.

Les tests backend utilisent un dossier temporaire. Arrêter les services avant les tests de restauration. Les tests navigateur nécessitent les outils facultatifs :

```sh
npm ci --cache /tmp/prospect-npm-cache
npx playwright install chromium
.venv/bin/python scripts/test_browser.py
```

`CHROMIUM_PATH` peut désigner un navigateur Chromium système déjà installé. Les fixtures synthétiques sont exclusivement dans les bases temporaires de test. Le lanceur de tests vérifie et arrête ses propres services. Aucun jeu de fausses entreprises n’est initialisé dans l’application.

## Documents

[Architecture](ARCHITECTURE.md) · [Connecteurs et licences](CONNECTORS.md) · [Guide utilisateur](USER_GUIDE.md) · [Sécurité](SECURITY.md) · [Tests](TEST_REPORT.md) · [Limites](KNOWN_LIMITATIONS.md) · [Changelog](CHANGELOG.md).
