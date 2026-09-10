# AWS expliqué très simplement

Ce document vous donne l’image générale avant de suivre le [guide AWS détaillé](deployer-sur-aws.md). Imaginez que vous construisez une **petite école pour votre application Atelier**. Chaque service AWS a une seule mission.

L’image de l’école aide à comprendre, mais AWS reste un ensemble d’ordinateurs et de services loués sur Internet.

## 1 — Comprendre le cloud et préparer votre atelier

Aujourd’hui, Atelier fonctionne sur votre ordinateur. Quand vous l’éteignez, le site s’arrête.

Le **cloud**, c’est utiliser les ordinateurs d’une grande entreprise, ici AWS. Vous louez seulement ce dont vous avez besoin :

- un endroit pour faire fonctionner Atelier ;
- une armoire pour ranger les PDF ;
- un cahier pour mémoriser les données ;
- des portes pour contrôler les visiteurs.

Votre **compte AWS** est le propriétaire de l’école. La **région Paris**, appelée `eu-west-3`, est la ville où vous la construisez. Votre identité **IAM** est votre badge personnel pour entrer dans la console et faire les réglages.

AWS fait payer certaines ressources tant qu’elles existent ou fonctionnent. Fermer la page AWS ne les arrête pas. C’est pour cela que vous créez d’abord une alerte de budget.

## 2 — Construire et comprendre le réseau

Le réseau est le plan de l’école.

| Mot AWS | Image simple |
|---|---|
| **VPC** | Le terrain privé de votre école |
| **Subnet** | Une salle située sur ce terrain |
| **Route** | Un panneau qui indique où aller |
| **Internet Gateway** | Le portail entre votre terrain et Internet |
| **Security group** | Une porte avec une liste de passages autorisés |

Vous créez des salles **publiques** pour l’entrée du site et l’application. Elles peuvent communiquer avec Internet. Vous créez aussi des salles **privées** pour PostgreSQL. La base n’a pas de porte directe vers Internet.

Les security groups disent précisément : « le visiteur peut entrer sur le site », « l’application peut parler à la base », et « personne sur Internet ne peut ouvrir directement PostgreSQL ».

## 3 — S3 pour les fichiers, ECR pour les images Docker

**S3** est l’armoire à documents. Atelier y range les PDF, fichiers Markdown et images extraites des documents. L’armoire est privée : seul le bon rôle AWS peut l’ouvrir.

**ECR** est une étagère qui conserve les paquets de votre programme. Ces paquets s’appellent des **images Docker**. Une image Docker contient le code et tout ce qu’il faut pour le démarrer.

Une image Docker n’est donc pas une photo. C’est plutôt une boîte fermée contenant une version prête à l’emploi d’Atelier. La déposer dans ECR ne la fait pas fonctionner : elle attend simplement qu’ECS la demande.

## 4 — Créer PostgreSQL et conserver les secrets

**RDS PostgreSQL** est le grand cahier de la bibliothèque. Il mémorise :

- les documents connus par Atelier ;
- les morceaux de texte, appelés chunks ;
- les embeddings qui servent à retrouver les bons passages ;
- les conversations et les travaux en attente.

**pgvector** ajoute à PostgreSQL la capacité de comparer les embeddings. C’est comme retrouver les fiches qui parlent de la même idée, même si elles n’utilisent pas exactement les mêmes mots.

**Secrets Manager** est un petit coffre-fort. Il garde les mots de passe et les clés OpenAI ou Mistral. Le code ne contient pas ces secrets : au démarrage, AWS donne seulement les valeurs nécessaires au bon conteneur.

Dans votre projet, le secret administrateur de RDS sert à préparer la base. Le secret de l’application sert au fonctionnement normal. Atelier n’utilise donc pas tous les pouvoirs de l’administrateur chaque jour.

## 5 — Donner les droits et lancer une première tâche ECS

Un **rôle IAM** est un badge de travail. Chaque badge ouvre seulement certaines portes :

- le badge de préparation peut préparer PostgreSQL ;
- le badge de l’application peut gérer les fichiers de son bucket S3 ;
- le badge d’exécution permet à ECS de prendre les images ECR, les secrets et d’écrire les logs.

**ECS** est le responsable qui organise le travail. **Fargate** fournit l’ordinateur temporaire qui exécute la tâche. Vous n’avez pas à acheter ni administrer cette machine.

La première tâche ECS est un ouvrier qui vient une seule fois préparer la bibliothèque : il crée pgvector, le compte SQL limité et les tables. Quand il a terminé correctement, il s’arrête avec le code `0`. Ce n’est pas une panne : son travail est fini.

## 6 — Donner une adresse HTTPS au site et lancer le service

Le **service ECS** garde Atelier ouvert. Si un conteneur tombe, ECS essaie d’en lancer un autre depuis l’image conservée dans ECR.

Votre tâche contient deux conteneurs :

- **Next.js** affiche les pages du site ;
- **FastAPI** lit les documents, interroge PostgreSQL et appelle OpenAI.

Le **DNS** est l’adresse écrite sur la carte de l’école, par exemple `rag.mondomaine.fr`. Le **certificat HTTPS** est sa carte d’identité : le navigateur peut vérifier qu’il parle au bon site et chiffrer la conversation.

L’**ALB** est l’accueil. Il reçoit les visiteurs en HTTPS, vérifie que l’interface fonctionne et les dirige vers elle. Il garde une adresse stable même si Fargate remplace l’ordinateur qui fait tourner Atelier.

## Le trajet d’une question

Quand vous posez une question, voici le voyage :

1. Le DNS conduit votre navigateur vers l’ALB.
2. L’ALB transmet la demande au conteneur Next.js.
3. Next.js parle au conteneur FastAPI dans la même tâche.
4. FastAPI cherche les bons passages dans RDS PostgreSQL.
5. Il appelle OpenAI avec la question et ces passages.
6. La réponse revient dans votre navigateur, avec ses sources.

S3 garde les fichiers, RDS garde la mémoire organisée, ECR garde le programme, Secrets Manager garde les clés, ECS/Fargate fait travailler le programme et l’ALB accueille les visiteurs.

Vous pouvez maintenant ouvrir le [chapitre 1 du parcours pratique](apprendre-aws/01-comprendre-et-preparer.md). Vous retrouverez les mêmes mots, avec les clics, les commandes et les vérifications à effectuer vous-même.
