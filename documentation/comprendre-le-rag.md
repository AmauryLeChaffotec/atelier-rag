# Comprendre le RAG dans ce projet

Un modèle de langage ne lit pas spontanément votre disque. Le RAG lui prépare un petit dossier de passages utiles avant de lui demander une réponse.

## L’indexation : préparer la bibliothèque

1. **Source** : un PDF, un Markdown, un TXT, du HTML ou une URL.
2. **Parsing** : le serveur extrait des sections avec texte, titres, code, page et éléments visuels.
3. **Chunking** : les sections sont découpées en passages. Le Studio permet de modifier ces passages avant validation.
4. **Embedding** : chaque passage devient un vecteur. Localement, Qwen est utilisé via Ollama ; le modèle demandé produit 1 024 dimensions dans le test local.
5. **Indexation** : PostgreSQL conserve document, métadonnées et vecteurs pgvector. Une réindexation remplace les anciens chunks en une transaction.

Les originaux restent dans un volume de fichiers, ou dans S3 si configuré. Les sections extraites et le brouillon sont dans PostgreSQL. Le brouillon est versionné : deux aperçus concurrents ne peuvent pas s’écraser silencieusement.

## La recherche : préparer le dossier du modèle

La question devient un embedding du **même modèle** que les documents. Les filtres de technologie, version, document, type de documentation et `metadata` limitent les candidats. PostgreSQL calcule alors :

```sql
score = 1 - (embedding_document <=> embedding_question)
```

`<=>` est la distance cosinus pgvector. On garde les passages au-dessus du seuil, puis les `top_k` meilleurs. Le score n’est pas un pourcentage de confiance.

Pour ce petit corpus, la recherche est **exacte** : aucun index ANN approximatif n’est nécessaire. Les index SQL accélèrent les filtres. L’opérateur vectoriel est bien exécuté directement par pgvector. Si le corpus devient volumineux, on pourra mesurer les performances et ajouter un index HNSW par espace de modèle et dimension.

## Le contexte, le prompt et la réponse

Les chunks sont assemblés **entiers** dans une limite de caractères. Chaque passage reçoit un numéro `[1]`, `[2]`, etc. Le prompt contient les consignes, un historique limité et ces passages.

Sans source au-dessus du seuil, l’application répond qu’elle n’a pas trouvé l’information et n’appelle pas le modèle de génération. Avec des sources, elle lui demande de répondre uniquement à partir du contexte et de signaler les manques.

Le résultat arrive en streaming. Le Pipeline conserve le prompt préparé, les filtres réels, les chunks retrouvés, les sources retenues, les durées et la réponse. Les sources des anciennes conversations restent lisibles après une réindexation ou une suppression, grâce à des instantanés textuels. Les fichiers et images originaux d’un document supprimé sont, eux, supprimés.

**Limite à comprendre :** un modèle peut mal interpréter une source ou mal citer malgré les consignes. La vérification automatique porte sur la présence et les numéros de citations ; elle ne prouve pas que chaque affirmation est soutenue. Le lecteur doit pouvoir ouvrir le passage exact.

## Les quatre stratégies de réponse

| Stratégie | Comportement réel |
|---|---|
| Standard | Un embedding de question, un retrieval, un contexte et une génération |
| Routing | Règles de mots-clés visibles dans le code ; recherche restreinte aux technologies détectées dans la bibliothèque |
| Branching | Le modèle propose jusqu’à trois sous-questions ; retrieval de chaque branche, fusion par chunk, conservation du meilleur score, génération commune |
| Adaptive | Une règle conservative reconnaît quelques échanges simples comme « Bonjour » ; ces échanges évitent le retrieval. Les autres questions passent par le RAG |

Le routing repose sur des règles simples, pas sur un classifieur entraîné. Les technologies inconnues restent recherchables, notamment par filtre explicite. L’absence de correspondance ouvre la recherche aux versions courantes. Une version précisée dans le filtre passe avant la version détectée dans une question.

Le Branching actuel fait les retrievals successivement, pour maîtriser la charge sur une petite machine et sur Ollama. Si le modèle ne produit pas un JSON exploitable, l’application revient à une recherche sur la question originale et le signale dans la trace.

## Les six stratégies de chunking

| Stratégie | Ce qui change |
|---|---|
| Taille | Fenêtres de caractères à la taille cible |
| Récursif | Coupures privilégiées selon les séparateurs, puis fenêtres si nécessaire |
| Paragraphes | Un passage par paragraphe ; fusion des petits voisins compatibles |
| Titres | Regroupement sous un même chemin de titres, dans la limite choisie |
| Markdown | Même regroupement structurel après parsing des titres, listes et code Markdown |
| Sémantique | Embeddings réels des sections voisines et regroupement si leur similarité dépasse un seuil |

Toutes conservent les pages et chemins de titres : on ne mélange pas deux versions ou sections pour remplir artificiellement une taille minimale. `Titres` et `Markdown` partagent volontairement l’algorithme de regroupement, le parsing fournissant la structure. L’overlap concerne les morceaux découpés dans une même section ; il n’est pas imposé entre deux titres distincts.

La taille minimale est souple. La taille maximale permet de conserver un bloc de code un peu plus long que la cible. Un bloc dépassant la limite maximale est redécoupé. Les tokens du Studio sont une estimation `caractères / 4`, pas le tokenizer exact de chaque fournisseur.

Le chunking sémantique compare une représentation limitée aux 6 000 premiers caractères de chaque section et accepte jusqu’à 500 sections. Les textes des chunks restent complets dans leurs limites de taille. Le calcul sémantique peut entraîner un coût OpenAI avant l’indexation finale : l’interface le précise.

## La première brique multimodale

Pour les PDF scannés, un bouton du Studio utilise **Mistral OCR**, indépendamment du fournisseur de chat. On choisit les pages à lire ; leur texte est conservé en cache dans PostgreSQL, puis découpé et indexé après validation. Voir [l’utilisation de l’OCR](utiliser-ocr-pdf.md). Les pages déjà en cache ne déclenchent pas de nouvel appel.

Les pages PDF contenant images ou dessins vectoriels sont rendues en PNG et associées à leurs chunks. Dans le Studio, on peut rédiger une description ou demander une proposition au modèle vision : Gemma en local, le modèle OpenAI configuré dans le cloud. La proposition reste un brouillon à l’écran. L’utilisateur relit, corrige et clique **Enregistrer cette description**, puis régénère l’aperçu et valide l’indexation. Le texte extrait du PDF est conservé.

**Limite locale constatée le 8 septembre 2026 :** sur cette machine Windows, Ollama 0.33.3 avec `gemma4:e4b` ne reconnaît pas l’image reçue, y compris avec un appel direct à Ollama hors de l’application. Un [signalement similaire](https://github.com/ollama/ollama/issues/16532) existe dans son dépôt. La description manuelle a été testée jusqu’au retrieval avec le visuel associé. Aucun autre modèle n’est substitué silencieusement ; la vision OpenAI sera à valider avec une clé lors de la bascule.

C’est un RAG **sur descriptions textuelles de visuels**. Il n’emploie pas d’embeddings d’images. Les PDF scannés peuvent nécessiter cette étape ; les tableaux et diagrammes complexes peuvent être mal interprétés. Il n’y a pas de promesse d’OCR exhaustif. Les originaux sont consultables pour vérifier.

## Les tables principales

| Table | Contenu |
|---|---|
| `technologies` | Nom et version courante |
| `documents` | Identité, version documentaire, source, sections, brouillon, statut |
| `versions_document` | Journal des indexations et de leur espace d’embedding |
| `travaux_indexation` | File durable, chunks validés, propriétaire, expiration du bail et tentatives |
| `chunks` | Texte, métadonnées, vecteur, dimension et espace d’embedding |
| `conversations`, `messages` | Historique et lien vers l’exécution RAG |
| `executions_retrieval` | Trace complète d’une réponse |
| `resultats_retrieval` | Sources envoyées au modèle, avec instantané et score |
| `migrations` | Migrations SQL déjà appliquées |

Les versions d’une technologie sont des documents distincts ; `versions_document` est le journal des indexations d’un document, pas une copie complète de chaque ancien index. Les noms de metadata techniques demandés (`document_id`, `chunk_id`, `technology`, `heading_path`, `embedding_model`, etc.) sont conservés pour faciliter l’interopérabilité.

## Les limites assumées d’un petit projet

Application personnelle, un seul espace partagé protégé par une clé. Chaque processus FastAPI accepte deux générations de chat simultanées et 30 actions d’écriture par minute. Ces limites ne constituent pas un quota global entre plusieurs tâches Fargate.

L’indexation est enregistrée dans une file PostgreSQL avant de répondre à l’interface. Un travailleur réserve le travail avec un bail de 90 secondes renouvelé pendant le calcul. S’il disparaît, un autre reprend après expiration. Le propriétaire est vérifié dans la transaction avant de remplacer les vecteurs : un ancien traitement ne peut pas écraser un nouveau résultat. Après trois interruptions brutales, le document devient relançable manuellement. Une réponse de chat en streaming, elle, n’est pas reprise automatiquement.

Des verrous PostgreSQL partagés empêchent deux OCR du même document ou deux générations de la même conversation de s’exécuter simultanément. Les appels IA externes restent potentiellement répétés après un arrêt brutal avant enregistrement de leur résultat. Utilisateurs séparés, permissions fines, crawl complet et import de dépôts GitHub restent des évolutions.

Une URL importe une seule page HTML rendue côté serveur ; les sites nécessitant JavaScript ou authentification ne sont pas parcourus automatiquement. Les liens privés et les metadata AWS sont interdits, avec vérification DNS et IP épinglée pendant le téléchargement.
