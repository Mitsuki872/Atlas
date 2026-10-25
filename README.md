Mise à jour **1.5.1** : synchronisation des mesures et suppression groupée — voir [PATCH_V1_5_1.md](PATCH_V1_5_1.md).

# Prospect Engine 1.5

Application locale de prospection suisse, sans service payant ni clé API.

**Campagnes → Entreprises → ATLAS** : créer rapidement une collecte, choisir une entreprise et préparer son prompt ATLAS.

- Relancer une campagne sur 25 nouveaux candidats maximum, avec historique conservé.
- Plus de 50 secteurs français et suggestions par mots-clés : UAPE/Enfants → Crèche, tea-room → Boulangerie/Café.
- Cinq statuts colorés et oppositions protégées.
- Téléphone et e-mail copiables en un clic ; sites ouverts directement dans le navigateur.
- Contrôles web gratuits et sourcés, indicateurs partiels explicites, vues Exploitables / À vérifier / Toutes.
- Dossier bleu sombre, preuves repliées, notes et sélection ATLAS.

[Installation et guide complet](SIMPLE_WORKFLOW_V1_5.md) · [Validation](TEST_REPORT.md) · [Limites](KNOWN_LIMITATIONS.md)

Mise à jour : Backup.bat → Stop.bat → copier les fichiers en conservant data/.venv → Install.bat → Start.bat. Aucun nouveau téléchargement suisse requis.

Pour une nouvelle installation Windows : Python 3.12/3.13 64 bits, puis Install.bat et Start.bat. Si Windows bloque Installer.ps1 téléchargé, utiliser Propriétés → Débloquer sur ce fichier puis relancer Install.bat. Scripts non exécutés sur Windows dans cet environnement Linux.

Les données absentes ne sont pas inventées. Une URL correcte peut rester inaccessible sur le site tiers ; sans domaine dans les sources gratuites disponibles, tous les sites ne sont pas retrouvables automatiquement. Pas de mesures Google/Lighthouse/IA prétendument exécutées.

Captures dans docs/screenshots : données synthétiques de test uniquement. Application locale mono-utilisateur, ne pas exposer sur Internet. Sources OSM : © OpenStreetMap contributors — ODbL ; extrait suisse Geofabrik.
