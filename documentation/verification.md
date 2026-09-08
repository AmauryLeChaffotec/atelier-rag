# Ce qui a été vérifié

Vérification locale du **8 septembre 2026**, sous Windows avec Docker Desktop, PostgreSQL 17/pgvector, Ollama 0.33.3, `qwen3-embedding:0.6b` et `gemma4:e4b`.

## Contrôles automatisés

- **50 tests Python réussis**, dont trois parcours d’intégration avec une véritable base PostgreSQL/pgvector dédiée `atelier_tests`.
- Les tests d’intégration couvrent import, preview, indexation, filtres, similarité cosinus, versions courantes, historique, réindexation échouée, isolation des modèles, protection de l’API et validation des descriptions de visuels.
- Les contrats HTTP Ollama et OpenAI sont vérifiés avec des réponses simulées : embeddings, streaming, tokens, transport d’image et sortie JSON. Ils ne facturent aucun appel OpenAI.
- `ruff check` et la vérification TypeScript passent.
- Le build de production Next.js passe dans Docker avec Node.js 22.
- Les trois conteneurs locaux sont démarrés et leurs health checks réussissent.
- La composition AWS a été validée avec des valeurs fictives, sans créer de ressource. Le Caddyfile est accepté par `caddy validate`.

Les commandes pour reproduire ces contrôles sont dans le [README](../README.md#vérifications). Les dépendances sont verrouillées ; les tests utilisent une base distincte de votre bibliothèque.

## Parcours réels avec Ollama

| Parcours | Résultat observé |
|---|---|
| Import Markdown depuis l’interface | Exemple Python importé, six chunks prévisualisés et indexés |
| Embedding réel | Qwen retourne des vecteurs de 1 024 dimensions |
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

**Aucun appel payant OpenAI et aucun déploiement AWS n’ont été réalisés.** La clé, les quotas OpenAI, les certificats HTTPS publics, la mémoire réelle sur Lightsail et une restauration complète sur une nouvelle machine seront à vérifier lors du déploiement. Le [guide AWS](deployer-sur-aws.md) donne les étapes correspondantes.

L’OCR Mistral a été testé avec la clé fournie pour cette fonction, sur deux PDF de démonstration d’une page chacun. Au tarif public de référence, ces deux pages correspondent à **0,008 USD**, sous réserve des conditions/crédits du compte. Aucun autre document n’a été envoyé à Mistral pendant ces vérifications.
