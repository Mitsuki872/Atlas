# Version 1.4

[Guide de mise à jour et prise en main](WORKSPACE_V1_4.md). Sauvegarder, Stop.bat, conserver data/.venv en copiant les nouveaux fichiers, Install.bat, Start.bat puis recharger la page. Aucun nouveau téléchargement/index suisse nécessaire. La recherche web générale nécessite un moteur configuré ; les refus d’accès restent visibles.

# Mise à jour 1.3

Voir [SCORING_V1_3.md](SCORING_V1_3.md) : sauvegarder, Stop.bat, copier les fichiers en conservant data/.venv, Install.bat, Start.bat puis Préparer la copie suisse pour reconstruire l’index v4 depuis le PBF vérifié existant. Tri par flèches dans les en-têtes ; métiers séparés par des virgules. Les mesures non disponibles restent inconnues. Windows non exécuté dans ce cloud.

# Installation Windows — procédure à valider sur la machine cible

**Les scripts sont fournis et leur logique partagée est testée sur Linux. Leur exécution Windows n’a pas été validée. Il ne s’agit pas d’un installateur autonome signé.**

## Prérequis

Windows 10/11 64 bits, droits d’écriture dans le dossier extrait, navigateur récent, Internet pour l’installation et la collecte. Python 3.12 64 bits. Pas de Docker, Node.js, API IA ou abonnement obligatoire.

## Première installation

1. Extraire le ZIP dans un dossier personnel stable, par exemple Documents\ProspectEngine. Éviter Program Files, OneDrive et les dossiers réseau ; ne pas exécuter le programme à l’intérieur du ZIP.
2. Double-cliquer sur `Install.bat`. L’assistant vérifie Python. S’il manque : télécharger Python 3.12 depuis https://www.python.org/downloads/windows/, installer avec « Add Python to PATH », puis relancer Install.bat. L’alternative winget est indiquée dans l’assistant, sans installation silencieuse non demandée.
3. Le script crée `.venv`, installe les versions verrouillées, initialise la base, démarre backend et worker, vérifie l’API et la base, arrête les services et crée un raccourci Bureau.
4. Double-cliquer `Start.bat`. Le navigateur s’ouvre après vérification des services. Conserver le programme en écoute locale ; ne pas ouvrir les ports au réseau.

Si PowerShell bloque un fichier téléchargé : vérifier l’origine et le contenu de l’archive avant de débloquer les fichiers via leurs Propriétés. La commande utilise `RemoteSigned`, ne désactive pas globalement la politique d’exécution. Respecter les règles du poste géré ; demander à l’administrateur si nécessaire. Ne pas désactiver la vérification TLS pour installer les dépendances.

## Mise à jour V1.2 : annuaire local

Sauvegarder depuis Paramètres puis Stop.bat. Copier les fichiers sans supprimer `data`/`.venv`. **Relancer Install.bat**, car osmium et shapely sont de nouvelles dépendances. Sur une installation existante, Install.bat utilise directement Python et ne lance pas Installer.ps1 ; il arrête les services, installe les roues binaires, migre avec sauvegarde et teste le démarrage. Puis Start.bat → Préparer la copie suisse → attendre Copie locale prête. Prévoir environ 550 Mo de téléchargement et 4 Go libres. Voir LOCAL_OSM_GUIDE.md. La recette Windows elle-même reste non exécutée.

## Mise à jour V1.1 sans perte de données (historique)

Arrêter avec Stop.bat puis exécuter Backup.bat. Copier les nouveaux fichiers dans le dossier existant **sans supprimer ni remplacer `data`**. Relancer Install.bat : la migration 0003 est additive et précédée d’une sauvegarde cohérente automatique. Puis Start.bat et rechargement du navigateur. Les dépendances quotidiennes restent Python seulement. Voir [PATCH_V1_1.md](PATCH_V1_1.md) pour la procédure et les contrôles de contacts.

## Usage quotidien

- `Start.bat` : vérifie la base, démarre backend + worker, ouvre le navigateur. Le frontend est servi par le backend : aucun troisième processus nécessaire.
- `Stop.bat` : arrête seulement les processus enregistrés par le lanceur ; conserve les données.
- `Diagnose.bat` : état des services, chemins et erreurs. Les journaux se trouvent dans `data`.
- `Backup.bat` : copie cohérente datée de la base dans `data\backups`.
- `Restore.bat` : demande le mot RESTAURER puis le chemin d’une sauvegarde, arrête les services et sauvegarde l’état actuel avant restauration. Relancer Start ensuite.
- `Uninstall.bat` : demande DESINSTALLER, arrête les services et supprime uniquement `.venv` et le raccourci. Sources, données et sauvegardes conservées.

Les données se trouvent dans `data\prospect.sqlite` par défaut. Copier régulièrement les sauvegardes sur un support protégé distinct. Le programme n’effectue aucune sauvegarde cloud.

## Mise à jour

Arrêter, sauvegarder, puis mettre à jour les fichiers source en conservant intégralement le dossier `data`. Relancer Install pour les dépendances et migrations. Ne jamais remplacer la base par une base livrée dans une archive. Aucune base de test n’est distribuée.

## Recette Windows obligatoire

Sur un poste cible, consigner la version de Windows, Python et du navigateur :

1. Installation sans Python : vérifier le message d’aide, installer Python puis relancer.
2. Vérifier raccourci, démarrage, ouverture du navigateur et Diagnostics (backend, base, worker).
3. Campagne Vaud → boulangeries, 3 résultats maximum, budget 0 CHF. Vérifier conditions de la source et accès réel avant lancement.
4. Si Overpass refuse l’accès : relever l’erreur et arrêter cette partie de la recette. Ne pas la considérer réussie ; ne pas utiliser un import pour prétendre à une découverte externe.
5. Après une découverte réelle réussie, examiner source et date, contacts, audit, constats et incertitudes. Ne pas qualifier une absence d’audit comme un défaut démontré du site.
6. Filtrer jour/heure, sélectionner plusieurs entreprises, Planification → prévisualisation → copie. Coller dans un éditeur et vérifier JSON, horaires, sources, fuseau et instructions de validation. Aucun événement créé.
7. Modifier un statut, enregistrer un appel et un rappel, arrêter puis redémarrer, vérifier leur persistance.
8. Sauvegarder, modifier une note, restaurer la sauvegarde via Restore après confirmation, vérifier le retour à l’état sauvegardé et la présence de la sauvegarde préalable.
9. Tester les chemins contenant des espaces, démarrage double, port déjà pris, arrêt durant une campagne puis reprise.
10. Depuis PowerShell dans le dossier : `.\.venv\Scripts\python.exe -m pytest -q`, services arrêtés. QA navigateur facultative : installer Node.js, `npm ci`, `npx playwright install chromium`, puis `.\.venv\Scripts\python.exe scripts\test_browser.py`.
11. Désinstaller après sauvegarde ; vérifier que les données sont conservées.

La recette complète demeure non validée tant que la collecte réelle et le passage sur Windows n’ont pas abouti.
