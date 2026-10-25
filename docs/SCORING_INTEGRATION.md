# Intégration incrémentale — 1.3

## Inventaire avant modification
FastAPI, SQLAlchemy/SQLite, migrations Alembic 0001–0004 ; campagnes et jobs persistants, worker mono-processus ; frontend JS sans framework ; index suisse PBF séparé, huit catégories ; filtres SQL paginés et exports CSV/JSON. Le score historique de besoin web et la complétude doivent rester lisibles. Les appels HTTP utilisent DNS public épinglé et robots, sans navigateur réseau non isolé.

## Plan
1. Migration additive 0005 : qualification actuelle sur l’entreprise et tables d’audits, critères, preuves, instantanés, opportunités et oppositions ; sauvegarde automatique existante avant migration. Aucun effacement de campagne/CRM/index.
2. Grille versionnée A/B/C, UNKNOWN et couverture, identification distincte, preuves, calcul déterministe et exclusions ; l’ancien score est conservé pour compatibilité.
3. Collecteur QUICK sur HTTP/DOM autorisé ; DEEP expose les outils non disponibles. Données B et IA par adaptateur JSON strict sourcé, sans fournisseur payant ni recherche Google supposés accessibles.
4. Texte métier libre : alias explicites, valeurs OSM et recherche littérale par nom ; index général des objets nommés avec tags d’activité (nouvelle préparation depuis le fichier déjà téléchargé). Aucune traduction sémantique arbitraire ni garantie que tout métier existe dans OSM.
5. API, filtres, tris dans les en-têtes, fiches explicables et exports compatibles ; tests d’acceptation et limites documentées.

## Divergences et disponibilité
Lighthouse, axe-core réseau, captures navigateur isolées, fournisseur IA et API de recherche/avis ne sont pas configurés. Leurs critères restent UNKNOWN ; aucun score B ni avis visuel inventé. Importer des observations autorisées avec preuves permet de les évaluer. Pas d’appel payant effectué : coût réel zéro, budget contrôlé à l’adaptateur. La validation juridique et la calibration sectorielle restent humaines.
