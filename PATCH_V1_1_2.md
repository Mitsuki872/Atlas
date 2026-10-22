# Correctif 1.1.2 — Requête et diagnostic Overpass

## Constat

La campagne signalée cible **Vaud, restaurants et plomberie**, sans commune. Le message d’attente du correctif précédent gère les erreurs, mais ne résout pas leur cause. Une erreur 502 ne permet pas à elle seule de distinguer charge serveur, problème de requête et intermédiaire réseau.

L’inspection a révélé deux défauts du générateur : mémoire de travail serveur déclarée à 8 Mio seulement et commune appliquée après collecte au lieu de réduire la recherche côté source. Dans la campagne signalée sans commune, seul le premier concerne directement le périmètre existant. Ces défauts sont corrigés, **sans affirmer qu’ils sont la cause prouvée du 502**.

## Changements

- GET avec paramètre `data`, sur le même endpoint HTTPS Overpass. Cette méthode est explicitement gérée par le code officiel de l’API (`src/overpass_api/frontend/cgi-helper.cc`). Pas de changement automatique de serveur, de proxy ou d’identité ; un refus reste un refus.
- `maxsize` fixe maintenant la mémoire de travail du serveur à 64 Mio, au lieu de 8 Mio. Cela n’autorise pas un téléchargement de 64 Mio : la réponse HTTP reste bornée à 8 000 000 octets. Timeout serveur 25 s, client 40 s et nombre maximal de résultats inchangés. La disponibilité n’est pas garantie.
- Lorsqu’une commune est renseignée, seules ses relations administratives de niveau 8, au nom exact insensible à la casse (`name` ou `name:fr`), sont recherchées dans le canton. Conversion en aire avant recherche des secteurs. Une commune introuvable déclenche une erreur explicite ; pas d’élargissement silencieux au canton.
- Le compteur d’aire est demandé et vérifié avant d’accepter les candidats. Un candidat de cette aire n’est pas supprimé simplement parce que son tag `addr:city` manque. Son adresse reste inconnue si la source ne la fournit pas.
- Sans commune, le canton entier reste le périmètre. Les deux secteurs Vaud/restaurants/plomberie figurent dans la requête ; aucune diversité ou entreprise inventée.

## Nouveau test à effectuer depuis votre PC

Après mise à jour, ouvrir **Diagnostics → Tester l’accès à Overpass**, une fois le délai de la source expiré. Ce bouton exécute UNE requête minimale, sur le même endpoint et avec le même transport que la campagne. Ce n’est ni une campagne ni une recherche commerciale.

Le résultat précise méthode, code HTTP, type de réponse, date et conclusion. Il est conservé pour être recopié. Une seconde demande dans la minute est différée ; les délais `Retry-After` et les indisponibilités déjà enregistrées sont respectés. Une erreur 502/503/504/429 au test minimal crée un délai d’attente partagé. Aucun martèlement de la source ni contournement d’un refus.

Interprétation :

- `state: ok` : la requête minimale fonctionne ; cela ne prouve pas qu’une campagne cantonale aboutira. Reprendre la campagne Vaud/restaurants/plomberie après le délai indiqué. En cas de nouvel échec, une copie de campagne limitée à une commune connue, par exemple Lausanne, permet une comparaison de charge ; ce test local ne remplace pas une collecte complète du canton.
- `state: unavailable` avec 502, même pour la requête minimale : le blocage dépasse la taille de la campagne ; transmettre le résultat pour poursuivre le diagnostic réseau/source.
- HTTP 403/406 : refus de la source ou du réseau. Ne pas changer d’identité ni multiplier les reprises pour contourner la restriction.
- `state: deferred` : le délai de la source n’est pas terminé ; attendre `retry_at`, affiché dans le résultat, puis refaire le test.
- Timeout/connexion/TLS : transmettre le message exact ; ne pas désactiver TLS, antivirus ou protections réseau pour faire passer le test.

Le diagnostic réalisé dans le cloud retourne 406 en GET comme en POST. Il ne reflète pas nécessairement la connexion du PC Windows, où le 502 a été constaté. Il manque donc encore cette observation sur la machine cible ; aucune résolution réelle de la collecte n’est prétendue.

## Installation de la mise à jour

Aucune nouvelle dépendance et aucune migration. Stop.bat → sauvegarde → copie des nouveaux fichiers **en conservant `data` et `.venv`** → Start.bat → rechargement de la page. Installer.ps1 n’est pas nécessaire si la version précédente fonctionne déjà. Les campagnes et prospects existants sont conservés. Une reprise avant découverte utilisera le nouveau générateur ; les résultats d’une découverte déjà stockée sont réutilisés sans les effacer.

## Validation

83 tests backend réussis sur Linux et parcours navigateur vérifié. Les cas HTTP automatisés utilisent des fixtures identifiées ; le refus réel 406 du cloud est distingué d’une réussite simulée. Windows et une collecte externe réelle ne sont pas déclarés validés. Voir TEST_REPORT.md.
