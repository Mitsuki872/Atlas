# Rapport de validation — 21 octobre 2026

## Verdict

Préversion 0.1.0 validée sur Linux pour le fonctionnement local et les parcours sur fixtures isolées. **V1 intégrale non validée.** La découverte d’entreprises réelles et l’installation Windows restent non validées ; la recette obligatoire du cahier des charges est donc incomplète.

## Environnement

Python 3.12.14, Linux, SQLite, versions Python verrouillées dans requirements.txt. Navigateur Chromium système contrôlé par Playwright (outil de QA seulement), Node 24.19.0. Aucun Docker ni service commercial. Base normale initialisée vide ; données synthétiques exclusivement dans des répertoires temporaires préfixés prospect-test-/prospect-browser-.

## Commandes exécutées et résultats

| Contrôle | Résultat observé |
|---|---|
| Installation Python, `pip install -r requirements.txt` (mêmes versions installées puis figées) | Réussie |
| `python -m app.manage migrate` sur base neuve puis existante | Réussi, révisions 0001/0002, sauvegarde préalable |
| `python -m pytest -q` | **34 tests réussis, 0 échec, 0 ignoré** ; 1 avertissement de dépréciation Starlette/AnyIO |
| `node --check app/static/app.js` | Réussi |
| `python -m compileall -q app scripts` | Réussi |
| `CHROMIUM_PATH=/usr/bin/chromium python scripts/test_browser.py` | **1 parcours navigateur complet réussi**, avec base temporaire et vrais appels HTTP locaux |
| Démarrage, GET diagnostics/dashboard, arrêt, redémarrage et second diagnostic | Réussi ; backend, base, worker observés ok |
| Sauvegarde, modification puis restauration et nouvelle ouverture de session | Réussi dans le test d’intégration dédié ; retour à l’état sauvegardé |
| Petite recherche réelle Overpass : 3 boulangeries Vaud | **Échec externe : timeout POST** |
| Diagnostic Overpass GET status / petite requête interpreter | **HTTP 406**, aucune donnée réelle récupérée |
| Alternative publique Overpass et documentation wiki | **403 du proxy**, pas de contournement |
| Audit réel d’un site d’entreprise découvert | **Non exécuté** : aucune entreprise réelle découverte |
| Installation/recette Windows et PowerShell/Batch | **Non exécutées** : machine Linux |
| Publication cloud et restauration dans une nouvelle tâche | **Non exécutées** : à effectuer par l’utilisateur dans le produit |

Les premières tentatives de QA ont révélé une détection Linux incorrecte des processus zombies/ports TIME_WAIT, corrigée et retestée. Le runner navigateur a été isolé de la collecte automatique pytest, puis ses attentes ont été corrigées pour attendre la fin effective des enregistrements avant de poursuivre. Les résultats ci-dessus correspondent aux dernières exécutions après ces corrections, pas aux premiers essais échoués.

## Ce que couvrent les tests backend

Normalisation nom/téléphone ; horaires fractionnés/nocturnes/invalides ; absence d’invention pour les expressions non prises en charge ; scoring et incertitudes ; export ATLAS et priorité des horaires d’appel ; validation entrées et budgets ; SSRF (loopback, métadonnées, privé, port interdit, DNS mixte, redirection privée) ; audits HTML sur réponses contrôlées et refus robots ; pipeline, curseur, pause, déduplication stable, protection des corrections ; suppression de contact propagée aux campagnes et à ATLAS ; API CRM, rappels et montants ; filtres, exports, prévention formules CSV, Host/Origin/jeton local ; paramètres et maintien des pondérations après correction ; migrations, sauvegarde/restauration et persistance ; import autorisé, historique des sources et revue des ambiguïtés.

Les connecteurs et réponses HTML sont **simulés** dans les tests unitaires/intégration afin de rendre les erreurs reproductibles. Ces tests démontrent le traitement des réponses, pas la disponibilité ni l’autorisation d’une source réelle.

## Parcours navigateur réel sur données synthétiques

Création puis modification d’une campagne ; navigation vers une fiche ; modification CRM et note ; ajout d’une plage d’appel sourcée ; import JSON de fixture via le sélecteur de fichier ; sélection ; génération et prévisualisation du prompt ; clic sur COPIER et lecture du vrai presse-papiers Chromium pour vérifier l’égalité exacte ; sauvegarde API depuis l’interface ; dashboard ; capture desktop et mobile ; absence de débordement horizontal à 390 px et absence d’erreur JavaScript non gérée. Aucune requête vers une source externe n’est déclenchée par ce scénario. Les campagnes de QA ne sont pas lancées sur Overpass.

## Non couvert et prochaines validations requises

Disponibilité/licences/conditions actuelles de chaque source, collecte réelle, audit réel sur réseau cible, syntaxe exhaustive des horaires, Lighthouse et performances, simulation exhaustive d’interruption brutale pendant l’écriture, sécurité indépendante, charge importante, migrations PostgreSQL, toutes les variantes Windows, installation sans Python et restauration d’un snapshot publié. Le scénario Windows reproductible se trouve dans INSTALLATION_WINDOWS.md. KNOWN_LIMITATIONS.md détaille les fonctions partielles ou absentes.

## Configuration cloud

`install_script` et `start_skill` ont été enregistrés avec succès dans le brouillon, ainsi que les domaines nécessaires à la recherche des sources/documentations. Cette sauvegarde n’exécute pas les scripts et ne publie pas l’environnement. L’utilisateur doit examiner/enregistrer les paramètres puis publier. Aucun secret n’a été demandé ou ajouté. La publication n’établira pas à elle seule que les opérations externes actuellement en échec fonctionnent : elles doivent être retestées.
