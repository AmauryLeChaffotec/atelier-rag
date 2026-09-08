# Ce qui a été vérifié

Vérification locale du **8 septembre 2026**, sous Windows avec Docker Desktop, PostgreSQL 17/pgvector, Ollama 0.33.3, `qwen3-embedding:0.6b` et `gemma4:e4b`.

## Contrôles automatisés

- **82 tests Python réussis**, dont sept parcours d’intégration avec une véritable base PostgreSQL/pgvector dédiée `atelier_tests`.
- Les tests d’intégration couvrent import, preview, indexation, filtres, similarité cosinus, versions courantes, historique, réindexation échouée, isolation des modèles, protection de l’API et validation des descriptions de visuels.
- Les contrats HTTP Ollama et OpenAI sont vérifiés avec des réponses simulées : embeddings, streaming, tokens, transport d’image et sortie JSON. Ils ne facturent aucun appel OpenAI.
- `ruff check` et la vérification TypeScript passent.
- Le build de production Next.js passe dans Docker avec Node.js 22.
- Le proxy HTTP refuse les corps de plus de 16 Mo avec ou sans Content-Length ; la connexion refuse plus de 4 Ko. Les réponses contiennent les en-têtes nosniff, Referrer-Policy, X-Frame-Options et HSTS (actif en HTTPS).
- Les trois conteneurs locaux sont démarrés et leurs health checks réussissent.
- Les deux modèles de tâches ECS sont vérifiés hors ligne contre le contrat `RegisterTaskDefinition` embarqué dans botocore. La configuration applicative est chargée avec des valeurs fictives pour vérifier ses variables, l’usage d’OpenAI/S3, le certificat présent et l’isolation des secrets administrateur. Ce contrôle ne valide pas les permissions réellement déployées dans AWS.
- Carnet AWS : lecture progressive, format UTF-8 avec BOM PowerShell, champs manquants et mauvais numéro de compte vérifiés. Un compte connecté différent bloque les scripts avant toute action de mutation.
- Calculateur : arrêt du calcul RDS sans disparition du stockage, ALB et IP facturés même sans tâche, durées invalides refusées. Les trois exemples du cours sont exécutables entièrement hors ligne.
- Les 36 blocs PowerShell du README et des documents ont une syntaxe valide selon le parseur PowerShell. Les liens locaux sont résolus et aucune des valeurs privées configurées pour les clés IA/l’accès n’est présente dans les fichiers publiables. Une syntaxe valide ne prouve pas qu’une commande réussira avec les droits et ressources de votre compte.
- Reprise d’indexation : bail exclusif, renouvellement, expiration, remplacement du propriétaire, refus d’écriture de l’ancien traitement, remise en attente à l’arrêt gracieux et limite de trois interruptions vérifiés sur PostgreSQL.
- Verrou PostgreSQL commun à deux connexions vérifié ; contrats S3 lecture/écriture/suppression simulés, sans identifiants AWS de production.
- Script de secrets : conservation du mot de passe PostgreSQL quand les clés IA changent. Script de migration : sortie absente ou différente de zéro bloque la suite.
- Image de préparation exécutée deux fois sur une base PostgreSQL 17/pgvector isolée dans Docker : trois migrations présentes, tables appartenant au rôle `atelier`, qui n’est ni superuser ni créateur de bases/rôles. Cela vérifie le SQL ; les permissions spécifiques RDS et sa connexion TLS restent à confirmer sur AWS.

Les commandes pour reproduire ces contrôles sont dans le [README](../README.md#vérifications). Les dépendances sont verrouillées ; les tests utilisent une base distincte de votre bibliothèque.

## Parcours réels avec Ollama

| Parcours | Résultat observé |
|---|---|
| Import Markdown depuis l’interface | Exemple Python importé, six chunks prévisualisés et indexés |
| Embedding réel | Qwen retourne des vecteurs de 1 024 dimensions |
| Après adaptation Fargate | Import via le proxy Next.js, indexation par la file PostgreSQL avec Qwen réel, puis réponse Gemma avec une source ; document temporaire supprimé après vérification |
| Standard RAG | Réponse sur les context managers Python, cinq passages dans le contexte, environ 8 secondes |
| Routing | Détection Python et recherche documentaire filtrée |
| Branching | Deux sous-questions générées, deux retrievals avec résultats, réponse fusionnée en environ 9 secondes |
| Adaptive | « Bonjour ! » reçoit une réponse sans retrieval |
| Historique et sources | Conversation conservée, ouverture du passage exact, consultation du prompt et du contexte dans Pipeline |
| Chunking sémantique | Aperçu et indexation d’un PDF avec de vrais embeddings |
| Visuel décrit à la main | Description indexée et retrouvée avec le lien vers la page PDF |
| Mistral OCR sur PDF scanné | Appel réel sur une page sans couche texte ; texte reconnu, indexation Qwen et retrieval réussis |
| Cache OCR réel | Seconde lecture de cette page : zéro page envoyée à Mistral |
| URL HTTPS | Téléchargement réel de `docs.python.org`, avec validation réseau et IP épinglée |

Les durées sont des observations sur cette machine et ce petit corpus, **pas un benchmark ni une garantie**. Le document Python et le schéma de démonstration ont été rédigés pour le projet.

## Interface vérifiée dans un navigateur

Les parcours ont été exécutés avec Playwright : import de fichier, Studio, aperçu, indexation, chat, sources, Pipeline, Retrieval et changement de thème. Le rendu a été inspecté sur ordinateur (1 440 px) et mobile (390 px). À 390 px, la largeur du document reste de 390 px : aucun débordement horizontal sur l’accueil. Les captures du README proviennent de l’application réellement exécutée.

## Ce qui reste à valider dans l’environnement cible

La lecture automatique d’images par Gemma échoue ici sous Windows : le modèle dit ne pas recevoir l’image, même via son API native. Cela correspond au symptôme du [signalement Ollama #16532](https://github.com/ollama/ollama/issues/16532). La proposition n’est jamais enregistrée automatiquement ; la description manuelle permet d’utiliser cette première brique multimodale.

**Aucun appel payant OpenAI et aucun déploiement AWS n’ont été réalisés.** Le parcours est désormais manuel, sans Terraform. Quotas Fargate, rôles IAM réellement appliqués, connexion TLS RDS, certificats HTTPS publics, mémoire sous Fargate, clés OpenAI et restauration complète restent à vérifier dans le compte AWS. Le [guide AWS](deployer-sur-aws.md) donne les manipulations et contrôles correspondants, à réaliser par vous-même. Les scripts de publication, de secrets et de lancement ECS n’ont pas été exécutés contre un compte réel.

L’OCR Mistral a été testé avec la clé fournie pour cette fonction, sur deux PDF de démonstration d’une page chacun. Au tarif public de référence, ces deux pages correspondent à **0,008 USD**, sous réserve des conditions/crédits du compte. Aucun autre document n’a été envoyé à Mistral pendant ces vérifications.
