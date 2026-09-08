# Où modifier quoi ?

**Commencez par ce fichier lorsque vous cherchez du code.** Il n’y a ni LangChain, ni moteur RAG caché : chaque étape est une fonction que vous pouvez ouvrir.

## Trois répertoires pour l’essentiel

```text
rag/
├── interface/          Ce que l’on voit dans le navigateur (Next.js)
├── serveur/            Ce qui traite les documents et répond (FastAPI)
├── documentation/      Les explications et le guide AWS
├── deploiement/aws/    Carnet d’identifiants et modèles JSON natifs ECS
├── scripts/            Démarrage, commandes AWS et estimation du coût
├── compose.yaml        Les trois services locaux
├── .env.example        Les réglages locaux à copier dans .env
└── README.md           La présentation du projet sur GitHub
```

Les noms sont français, sans accents dans les chemins pour faciliter leur utilisation dans les terminaux. Les conventions imposées par les outils restent inchangées : `app`, `page.tsx`, `layout.tsx`, `route.ts`, `Dockerfile`, `package.json`, `README.md`, `tests`, `metadata`, `chunk`, `embedding`, `retrieval`, `prompt`. Les fichiers de licence de polices tierces restent dans leur texte légal original.

## Je veux changer un comportement

| Ce que vous voulez modifier | Le fichier à ouvrir |
|---|---|
| Passer d’Ollama à OpenAI | `.env` : `FOURNISSEUR_IA` et les modèles |
| Changer les modèles par défaut | [`configuration.py`](../serveur/application/configuration.py) |
| Ajouter un fournisseur IA | [`ia/fournisseur.py`](../serveur/application/ia/fournisseur.py) |
| Modifier les consignes et citations | [`rag/prompt.py`](../serveur/application/rag/prompt.py), constante `CONSIGNE` |
| Comprendre l’enchaînement d’une réponse | [`rag/orchestration.py`](../serveur/application/rag/orchestration.py), fonction `discuter` |
| Ajouter une technologie au routing | [`rag/routage.py`](../serveur/application/rag/routage.py), dictionnaire `ALIASES` |
| Modifier le SQL de recherche ou les filtres | [`retrieval/recherche.py`](../serveur/application/retrieval/recherche.py) |
| Modifier la façon de découper | [`chunking/decoupage.py`](../serveur/application/chunking/decoupage.py) |
| Changer les tailles de chunks proposées | [`schemas.py`](../serveur/application/schemas.py), puis `defaut` dans [`studio.tsx`](../interface/composants/studio.tsx) |
| Changer la lecture PDF/HTML/Markdown/TXT | [`parsing/sources.py`](../serveur/application/parsing/sources.py) |
| Modifier l’OCR Mistral des PDF et son cache | [`services/ocr.py`](../serveur/application/services/ocr.py), puis `MISTRAL_OCR` dans `.env` |
| Modifier l’import ou les métadonnées | [`services/ingestion.py`](../serveur/application/services/ingestion.py) |
| Comprendre le remplacement des embeddings | [`services/indexation.py`](../serveur/application/services/indexation.py) |
| Comprendre la reprise après arrêt Fargate | [`services/travaux.py`](../serveur/application/services/travaux.py) |
| Verrouiller une opération entre tâches | [`base/verrous.py`](../serveur/application/base/verrous.py) |
| Passer les fichiers sur S3 | [`services/stockage.py`](../serveur/application/services/stockage.py) et `.env` |
| Lire/écrire les documents en SQL | [`depots/documents.py`](../serveur/application/depots/documents.py) |
| Ajouter une route HTTP | [`api/routes.py`](../serveur/application/api/routes.py), la logique reste dans les services |
| Modifier les limites d’accès | [`principal.py`](../serveur/application/principal.py) et [`configuration.py`](../serveur/application/configuration.py) |
| Ajouter une table ou colonne | Nouveau fichier SQL dans [`base/migrations`](../serveur/application/base/migrations) : `004_votre_modification.sql` |

## Je veux modifier AWS

| Réglage | Fichier |
|---|---|
| Retrouver vos identifiants et votre région | Votre `configuration-aws.json` à la racine, copié depuis [l’exemple](../deploiement/aws/configuration.exemple.json) |
| CPU/RAM, modèles IA et conteneurs Fargate | [`tache-application.exemple.json`](../deploiement/aws/tache-application.exemple.json), expliqué au [chapitre 6](apprendre-aws/06-mettre-le-site-en-ligne.md) |
| Préparation et migrations PostgreSQL | [`tache-preparation.exemple.json`](../deploiement/aws/tache-preparation.exemple.json) et [`base/preparer.py`](../serveur/application/base/preparer.py) |
| HTTPS, domaine et ALB | Réglages console du [chapitre 6](apprendre-aws/06-mettre-le-site-en-ligne.md) |
| Stockage S3 et images ECR | Réglages console du [chapitre 3](apprendre-aws/03-stocker-et-publier.md) |
| RDS et secrets | Réglages console du [chapitre 4](apprendre-aws/04-base-et-secrets.md) |
| VPC, subnets et security groups | Réglages console du [chapitre 2](apprendre-aws/02-creer-le-reseau.md) |
| Rôles et permissions IAM | Réglages console du [chapitre 5](apprendre-aws/05-roles-et-preparation.md) |
| Budget et alarmes | [Chapitre 1](apprendre-aws/01-comprendre-et-preparer.md) pour le budget, [chapitre 7](apprendre-aws/07-observer-et-modifier.md) pour les alarmes |
| Arrêter les coûts entre deux séances | [Fiche arrêter/reprendre/supprimer](apprendre-aws/08-arreter-reprendre-supprimer.md) |
| Estimer vos durées et volumes | [`estimer_cout.py`](../scripts/estimer_cout.py), tarifs dans [`tarifs.json`](tarifs.json) |
| Images Docker à publier | [`publier_images.py`](../scripts/aws/publier_images.py) |
| Saisir les clés privées | [`configurer_secrets.py`](../scripts/aws/configurer_secrets.py) |
| Lancer les migrations AWS | [`preparer_base.py`](../scripts/aws/preparer_base.py) |

La marche à suivre est dans le [guide AWS](deployer-sur-aws.md). Le `.env` local ne sert pas de configuration de déploiement ECS. Le carnet ne contient aucun mot de passe et ne modifie pas AWS lorsque vous l’éditez. Les scripts sont facultatifs ; commencez par les manipulations du cours.

## Je veux changer l’interface

| Écran ou élément | Fichier |
|---|---|
| Menu, nom de l’application, thème et connexion | [`cadre.tsx`](../interface/composants/cadre.tsx) |
| Chat, suggestions, historique et streaming | [`conversation.tsx`](../interface/composants/conversation.tsx) |
| Bibliothèque et formulaire d’ajout | [`bibliotheque.tsx`](../interface/composants/bibliotheque.tsx) |
| Chunking Studio | [`studio.tsx`](../interface/composants/studio.tsx) |
| Retrieval Playground | [`laboratoire.tsx`](../interface/composants/laboratoire.tsx) |
| Pipeline Explorer | [`explorateur.tsx`](../interface/composants/explorateur.tsx) |
| Cartes de source et fenêtre du chunk exact | [`communs.tsx`](../interface/composants/communs.tsx) |
| Filtres réutilisables | [`filtres.tsx`](../interface/composants/filtres.tsx) |
| Couleurs, tailles, responsive | [`apparence.css`](../interface/app/apparence.css), variables au début |
| Contrats TypeScript | [`types.ts`](../interface/bibliotheque/types.ts) |
| Appels à FastAPI et lecture du streaming | [`api.ts`](../interface/bibliotheque/api.ts) |
| Proxy Next.js vers l’API privée | [`route.ts`](../interface/app/api/[...chemin]/route.ts) |

Les fichiers `interface/app/*/page.tsx` restent très courts : ils indiquent quel composant afficher. Toute la page se retrouve dans le composant français correspondant. Le CSS est commun au projet, pour retrouver les couleurs au même endroit. Cherchez le nom d’une classe avec `rg`, ou avec la recherche de votre éditeur.

## Lire le projet dans un ordre simple

1. `configuration.py` : quels sont les modèles et les limites ?
2. `parsing/sources.py` : comment un document devient-il des sections ?
3. `chunking/decoupage.py` : comment ces sections deviennent-elles des chunks ?
4. `ia/fournisseur.py`, méthode `embeddings` : où apparaissent les vecteurs ?
5. `services/indexation.py` : comment sont-ils enregistrés ?
6. `retrieval/recherche.py` : quelle requête SQL retrouve les passages ?
7. `rag/prompt.py` : quels textes sont envoyés au modèle ?
8. `rag/orchestration.py` : comment la réponse et ses sources sont-elles sauvegardées ?

## Une petite modification complète

Pour ajouter une règle de routing pour Django :

1. Ajoutez une entrée dans `ALIASES` : `"Django": [r"\bdjango\b", r"\bqueryset\b"]`.
2. Importez une documentation avec la technologie `Django`.
3. Ajoutez une ligne au test paramétré de `tests/test_rag.py`.
4. Dans le chat, choisissez **Routing RAG** et posez une question sur les QuerySets.
5. Ouvrez le Pipeline et regardez les technologies détectées, puis les filtres appliqués.

Les alias servent à détecter une technologie ; ils ne créent pas de documents ni de résultats artificiels.
