# Prospect Engine — préversion 0.1.0

Application locale de prospection B2B, en français, développée à partir du cahier des charges fourni. **La V1 intégrale n’est pas encore validée.** Consulter [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) et [TEST_REPORT.md](TEST_REPORT.md) avant utilisation.

## Ce qui est implémenté

- Interface responsive avec six pages métier, diagnostics, thème clair/sombre, recherche et états vides sans données fictives.
- FastAPI + SQLite / SQLAlchemy et migrations Alembic ; données locales accessibles hors ligne.
- Campagnes, worker séparé, file persistante, pause/reprise/arrêt, résultats progressifs et historique des sources.
- Connecteur Overpass / OSM borné, sans clé payante ; **collecte externe non validée depuis ce cloud** (406 / timeout / refus du proxy). L’import JSON autorisé permet de travailler sur ses propres données.
- Détection conservative de doublons par identifiant source ; signaux téléphone/domaine présentés pour revue manuelle ; protection des corrections et liste persistante de non-contact.
- Audit HTML limité avec preuves, robots.txt, validation DNS et adresse publique épinglée, limites et timeouts ; scoring déterministe explicable et pondérations réglables.
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
