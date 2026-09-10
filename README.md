# Atelier · Le RAG, à livre ouvert

**Une application qui répond à vos questions à partir de vos documentations et rend chaque étape inspectable.**

Next.js · TypeScript · FastAPI · PostgreSQL/pgvector · Ollama en local · OpenAI sur AWS · Mistral OCR pour les PDF · Docker Compose · ECS Fargate

![L’interface de conversation d’Atelier](documentation/captures/conversation.png)

## Pourquoi ce projet ?

Les documentations sont nombreuses et changent de version. Une réponse de modèle seule ne permet pas de savoir quelle documentation a été utilisée. Atelier rassemble les sources, retrouve les passages pertinents et les donne au modèle avant qu’il réponde.

L’objectif est de montrer le pipeline RAG de bout en bout avec du code explicite, des sources consultables et des choix techniques expliqués. **Aucun LangChain, aucune base vectorielle externe : le SQL pgvector, le chunking, les appels d’embedding et la construction du prompt sont visibles.**

## Commencer en local

Prérequis : Docker Desktop démarré et Ollama installé sur l’ordinateur. Les conteneurs tournent sous Linux. La RAM nécessaire dépend surtout de Gemma ; dans cet environnement, le fichier `gemma4:e4b` installé occupait environ 9,6 Go. La mémoire d’exécution est différente de la taille du fichier, et un GPU compatible accélère les réponses.

Depuis la racine du projet :

```powershell
Copy-Item .env.example .env
ollama pull qwen3-embedding:0.6b
ollama pull gemma4:e4b
docker compose up -d --build --wait
```

Ouvrez **[http://localhost:3000](http://localhost:3000)**. Après la première préparation, la seule commande nécessaire est `docker compose up -d --wait`.

Ou utilisez le script qui prépare les modèles et démarre le projet :

```powershell
powershell -ExecutionPolicy Bypass -File scripts/demarrer.ps1
```

Sous macOS/Linux : `bash scripts/demarrer.sh`. Le projet utilise Ollama **sur l’hôte**, via `host.docker.internal` dans les conteneurs. Sur Linux natif, il peut être nécessaire de faire écouter Ollama sur l’interface accessible à Docker et d’autoriser uniquement le réseau Docker dans le pare-feu. N’exposez pas son port 11434 à Internet. Sur Docker Desktop Windows testé ici, la liaison fonctionne avec la configuration fournie.

**Aucune clé OpenAI n’est nécessaire en local.** Les polices sont livrées dans le dépôt : l’interface ne les télécharge pas chez Google à l’utilisation. Après téléchargement des images Docker et des modèles, l’import de fichiers et le RAG local fonctionnent sans service IA distant. L’import d’URL exige naturellement Internet.

**OCR facultatif pour les PDF :** configurez `MISTRAL_API_KEY` dans le `.env` privé, puis utilisez **Lire avec Mistral OCR** dans le Studio. C’est un appel distant facturé à la page, indépendant d’Ollama. L’extraction PDF locale reste le premier traitement gratuit. Le [guide OCR](documentation/utiliser-ocr-pdf.md) explique la sélection de pages, le cache et la validation du texte.

## Une première démonstration en deux minutes

1. Dans **Documentation**, ajoutez [`exemple-python.md`](interface/public/exemple-python.md).
2. Donnez-lui la technologie `Python`, la version `3.14` et le titre de votre choix.
3. Cliquez **Ouvrir**, puis **Générer l’aperçu** dans le Chunking Studio.
4. Inspectez ou modifiez les chunks, puis **Valider et indexer**. Attendez le statut « Indexé ».
5. Dans **Conversation**, demandez : « Comment créer un context manager en Python ? ».
6. Ouvrez une carte de source pour lire le chunk exact.
7. Cliquez **Explorer cette réponse** pour suivre le routing, les embeddings, les scores, le contexte et le prompt.

Le fichier d’exemple a été rédigé pour cette démonstration. Il n’est pas présenté comme une documentation officielle importée. Une installation neuve démarre avec une bibliothèque vide ; les captures montrent une utilisation réelle après import de cet exemple.

![Une réponse réelle avec Gemma et ses passages sources](documentation/captures/reponse-sourcee.png)

Un [PDF scanné d’exemple](interface/public/exemple-pdf-scanne.pdf) est également fourni pour tester l’OCR sur une page sans couche texte.

## Les cinq écrans

| Écran | Ce que l’on peut faire |
|---|---|
| **Conversation** | Chat en streaming, quatre stratégies, filtres, historique PostgreSQL, sources consultables |
| **Documentation** | Import PDF/Markdown/TXT/HTML/URL, technologies et versions, statuts, suppression, version courante |
| **Chunking** | Six stratégies, taille/overlap/séparateurs, aperçu, édition manuelle, indexation/réindexation, pages visuelles |
| **Retrieval** | Recherche pgvector sans appel au modèle de génération, top K, seuil, filtres et scores |
| **Pipeline** | Exécution réelle : décisions, branches, dimensions, filtres, contexte, prompt, réponse, sources et durées |

![Le Chunking Studio](documentation/captures/chunking.png)

## Le pipeline

```mermaid
flowchart LR
    Documents[Documents / URL] --> Parsing[FastAPI : parsing]
    Parsing --> Studio[Chunking Studio]
    Studio --> Embeddings[Qwen local / OpenAI]
    Embeddings --> Base[(PostgreSQL + pgvector)]
    Question[Question] --> Routage[Routing / stratégie]
    Routage --> EmbeddingQuestion[Embedding de la question]
    EmbeddingQuestion --> Retrieval[Retrieval filtré]
    Base --> Retrieval
    Retrieval --> Contexte[Chunks + scores → contexte]
    Contexte --> Prompt[Prompt explicite]
    Prompt --> Modele[Gemma local / OpenAI]
    Modele --> Reponse[Réponse en streaming + citations]
    Reponse --> Interface[Next.js + Pipeline Explorer]
```

- **Parsing** : extraction de blocs structurés, chemins de titres, code, listes, liens, tableaux HTML et pages PDF.
- **Chunking** : taille fixe, récursif, paragraphes, titres, Markdown, sémantique. Le mode sémantique compare réellement les embeddings des sections voisines.
- **Embeddings** : couche IA centralisée. Les vecteurs sont associés à leur fournisseur, modèle et dimension.
- **Retrieval** : requête SQL directe utilisant la distance cosinus pgvector, filtres avant scoring, recherche exacte adaptée à un petit corpus.
- **Contexte** : chunks entiers numérotés dans un budget de caractères ; refus documentaire si aucun résultat ne passe le seuil.
- **Génération** : streaming Ollama ou OpenAI converti en événements SSE, historique borné et citations demandées au modèle.
- **Traçabilité** : prompt, filtres, résultats, sources retenues, réponse et mesures sont enregistrés. Les instantanés textuels des sources survivent aux réindexations.

Les détails, compromis et limites sont expliqués dans **[Comprendre le RAG](documentation/comprendre-le-rag.md)**.

## Un projet facile à modifier

```text
interface/               L’interface : un composant français par écran
serveur/application/
  api/                   Les routes HTTP
  base/                  Connexion PostgreSQL et migrations SQL
  depots/                Accès SQL aux documents
  parsing/               Lecture et nettoyage des sources
  chunking/              Stratégies de découpage
  ia/                    Appels Ollama et OpenAI
  retrieval/             Recherche vectorielle et filtres
  rag/                   Routing, prompt et orchestration
  services/              Ingestion, indexation, stockage local/S3
  configuration.py       Modèles, limites et variables d’environnement
  schemas.py             Contrats et validation des données
  principal.py           Démarrage, authentification et erreurs
documentation/           Explications, captures et tarifs
documentation/apprendre-aws/  Cours pour débutants, une étape à la fois
deploiement/aws/         Carnet d’identifiants et modèles JSON de tâches ECS
scripts/aws/             Publication des images, saisie des secrets et migration
scripts/                 Démarrage local et estimation du coût
```

**[Où modifier quoi ?](documentation/ou-modifier-quoi.md)** donne un lien direct pour chaque changement courant : prompt, modèle, couleur, chunking, SQL, routing, écran, etc.

Les noms de nos fichiers/répertoires et les commentaires sont français. Les conventions des frameworks et termes techniques restent reconnaissables (`app`, `page.tsx`, `Dockerfile`, `embedding`, `chunk`, `metadata`, `retrieval`). Les dépendances Python sont verrouillées dans `uv.lock` et les dépendances JavaScript dans `package-lock.json`.

## Les réglages importants

En local, les variables se trouvent dans le `.env` **à la racine**, ignoré par Git : [exemple](.env.example). Sur AWS, vous configurez les ressources dans la console, complétez votre carnet `configuration-aws.json` et enregistrez les [définitions de tâche ECS](deploiement/aws/README.md). Les clés restent dans Secrets Manager ; les JSON ne contiennent que leurs références.

| Variable | Local | Rôle |
|---|---|---|
| `FOURNISSEUR_IA` | `ollama` | `ollama` ou `openai`, pour embeddings et génération |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Adresse d’Ollama vue depuis Docker |
| `OLLAMA_EMBEDDING` | `qwen3-embedding:0.6b` | Modèle d’embedding demandé |
| `OLLAMA_GENERATION` | `gemma4:e4b` | Modèle de réponse demandé |
| `OPENAI_API_KEY` | Vide | Secret uniquement dans FastAPI, au moment de la bascule |
| `OPENAI_EMBEDDING` | `text-embedding-3-small` | Embeddings économiques sur AWS |
| `OPENAI_GENERATION` | `gpt-4o-mini` | Génération économique et vision sur AWS |
| `MISTRAL_API_KEY` | Vide dans l’exemple | Clé privée pour l’OCR PDF facultatif |
| `MISTRAL_OCR` | `mistral-ocr-latest` | Modèle OCR indépendant du chat et des embeddings |
| `POSTGRES_PASSWORD` | Mot de passe local d’exemple | Réservé au PostgreSQL de Docker Compose ; RDS utilise des secrets distincts |
| `CLE_ACCES` | Facultative en local | Clé de l’espace partagé ; 32 caractères minimum en production |
| `MAX_CHUNKS` | `500` | Limite de chunks par document |
| `TAILLE_FICHIER_MO` | `15` | Limite d’import ; maximum 150 pages PDF |
| `MAX_TOKENS_REPONSE` | `900` | Limite de génération |
| `MAX_CONTEXTE_CARACTERES` | `16000` | Budget de texte documentaire |
| `STOCKAGE` | `local` | `local` ou `s3` |
| `POSTGRES_HOTE` | Vide | Sur AWS : connexion RDS par champs séparés, mot de passe injecté, certificat TLS vérifié |
| `MIGRER_AU_DEMARRAGE` | `true` | `false` sur AWS : migrations exécutées avant le déploiement par une tâche dédiée |
| `BAIL_INDEXATION_SECONDES` | `90` | Délai de reprise d’un travail après disparition de son propriétaire |

**Lors d’un changement de modèle d’embedding, réindexez les documents.** Les embeddings Qwen et OpenAI ne sont jamais comparés entre eux. Le stockage accepte plusieurs dimensions et la recherche isole le bon espace avant le calcul des distances. Le changement de modèle de génération seul ne demande pas de réindexation.

## Développer avec rechargement automatique

Avec Node.js **22** et Python **3.12** installés, vous pouvez garder uniquement PostgreSQL dans Docker. Évitez de lancer simultanément les conteneurs d’interface/API et leurs équivalents natifs sur les mêmes ports.

Depuis la racine :

```powershell
docker compose stop interface serveur
docker compose up -d base
```

Terminal serveur :

```powershell
cd serveur
uv sync --frozen
$env:OLLAMA_URL='http://127.0.0.1:11434'
uv run uvicorn application.principal:app --host 127.0.0.1 --port 8000 --reload
```

Terminal interface :

```powershell
cd interface
npm ci
npm run dev
```

Sur Windows, le mode `--reload` utilise une boucle asyncio compatible avec psycopg dans Uvicorn. L’adresse PostgreSQL native par défaut est `127.0.0.1` pour éviter les ambiguïtés IPv6 de `localhost`. Si vous avez changé le mot de passe, configurez aussi `DATABASE_URL` pour l’exécution native.

## Vérifications

Tests unitaires et contrats HTTP des deux fournisseurs, **sans appel OpenAI réel** :

```powershell
cd serveur
uv sync --frozen
uv run ruff check application tests
uv run pytest -q
```

Avec le PostgreSQL local déjà lancé, ajoutez le test d’intégration sur une base dédiée :

```powershell
docker compose exec -T base createdb -U atelier atelier_tests
$env:DATABASE_URL_TEST='postgresql://atelier:atelier_local_uniquement@127.0.0.1:5432/atelier_tests'
uv run pytest -q
```

Si `atelier_tests` existe déjà, ne la recréez pas. Le garde-fou des tests exige ce nom de base. Les modèles IA sont remplacés par des doubles déterministes pour tester les filtres, le scoring, les versions, l’historique et la résistance à une indexation échouée.

Depuis `interface` : `npm run verifier` et `npm run build`. GitHub Actions vérifie Python/PostgreSQL et Next.js. Les tests de [`serveur/tests`](serveur/tests) couvrent notamment la reprise des indexations, le refus d’un traitement devenu obsolète, le carnet AWS, les contrats JSON ECS et le calcul des coûts après arrêt. Ils ne créent aucune ressource AWS. Le [compte rendu](documentation/verification.md) distingue les tests réels, simulés et les limites.

## AWS et coût

**[Apprendre AWS en installant Atelier à la main](documentation/deployer-sur-aws.md)** : neuf chapitres pour débutants, sans Terraform. Chaque étape explique le rôle du service, les réglages à choisir dans la console, les commandes PowerShell et la vérification à faire avant de continuer. Pour comprendre l’ensemble, commencez par les [trois schémas du réseau, d’IAM et d’ECS/Fargate](documentation/aws-explique-tres-simplement.md). **Pour la première séance pratique, passez ensuite aux chapitres 1 et 2 : compte et réseau.**

L’application est adaptée à **ECR + ECS Fargate + RDS PostgreSQL/pgvector + S3 + Secrets Manager + CloudWatch**, avec ALB/ACM pour HTTPS. Vous mettez ces services en place progressivement. Une tâche de 0,5 vCPU / 2 Go, une petite base privée Single-AZ et aucun NAT Gateway limitent le coût. Les tâches utilisent leur rôle IAM pour S3 ; aucun secret n’est embarqué dans les images. La préparation RDS se lance séparément avant les nouvelles versions.

Pour des séances d’apprentissage, utilisez la **[fiche arrêter/reprendre/supprimer](documentation/apprendre-aws/08-arreter-reprendre-supprimer.md)** et le **[budget des séances](documentation/apprendre-aws/09-budget-des-seances.md)**. Ils distinguent le calcul actif des ressources conservées : RDS arrêté conserve du stockage facturé et redémarre après sept jours maximum ; l’ALB doit être supprimé pour arrêter son coût horaire. Fermer le navigateur n’arrête aucun service.

```powershell
python scripts/estimer_cout.py --profil seance
python scripts/estimer_cout.py --profil intermittent
python scripts/estimer_cout.py --profil intermittent --heures-alb 730
```

Les prix, durées et hypothèses sont détaillés dans le cours et [`tarifs.json`](documentation/tarifs.json). Les estimations excluent les crédits AWS et certains frais précisés dans le guide ; elles ne sont pas des plafonds. Un [exercice de sauvegarde/restauration](documentation/sauvegarder-restaurer-aws.md) complète le parcours. **Aucun service AWS n’est créé par l’installation locale ou le calculateur.**

Le coût OCR est de **0,40 USD pour 100 pages envoyées** dans cette estimation. Les pages déjà en cache ne provoquent pas de nouvel appel, sauf perte du résultat avant son enregistrement lors d’un arrêt brutal.

## Limites et périmètre

Cette version est une application personnelle démontrable, avec un espace partagé. Elle ne fournit pas l’isolation de comptes d’un SaaS. La configuration AWS par défaut n’est pas hautement disponible : une tâche et une base Single-AZ. Le routing et l’adaptive sont des règles explicites ; le multimodal indexe des descriptions textuelles de pages, pas des vecteurs d’image. Les URL importent une page HTML à la fois.

Les indexations passent par une **file durable PostgreSQL**, avec bail renouvelé et reprise après interruption ; un ancien traitement ne peut plus remplacer l’index. Les opérations OCR et les conversations utilisent un verrou PostgreSQL commun aux tâches. Les limites de débit (30 actions/minute, deux générations simultanées) restent par processus. Une génération de chat interrompue se relance manuellement ; un appel IA commencé peut être refacturé à la reprise.

Les citations demandées au modèle peuvent être imparfaites : l’application permet de vérifier les passages et signale les numéros inexistants ou l’absence de citations. Les tokens du Studio sont estimés ; les métriques de génération viennent du fournisseur quand celui-ci les fournit.

**Visuels avec Gemma sous Windows :** dans l’environnement testé, `gemma4:e4b` répond correctement au texte mais indique ne pas voir les images transmises. Un [problème similaire est signalé chez Ollama](https://github.com/ollama/ollama/issues/16532). Le Studio permet de rédiger la description à la main. Les propositions du modèle sont toujours à relire et ne sont enregistrées qu’après votre validation ; la description validée est indexée avec le texte original et le lien vers la page.

La bascule OpenAI est couverte par des tests de contrat avec réponses simulées. Un appel payant réel nécessite votre clé et sera à valider lors du déploiement. Aucun déploiement AWS n’est revendiqué sans l’avoir effectué.
