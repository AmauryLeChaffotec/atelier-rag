# Images du guide AWS : fichiers et consignes de génération

Ces trois images accompagnent [Comprendre ton installation AWS](../../aws-explique-tres-simplement.md). Elles ont été créées avec l’outil natif **imagegen**, puis contrôlées visuellement et comparées aux configurations du projet. Aucun appel via le script CLI de génération n’a été utilisé.

Les consignes ci-dessous restituent en français les demandes de génération. Elles permettent de refaire ou modifier les schémas sans chercher leur intention dans l’historique de conversation.

## Style commun

Créer une infographie pédagogique pour un débutant complet : format paysage, texte français lisible, fond ivoire clair, cadres simples et flèches nettes. Le bleu représente les échanges ; le vert le réseau et l’organisation ; l’orange le calcul ; le violet les données et identités. Utiliser les vrais noms du projet. Montrer les relations concrètes entre les services, sans métaphore de bâtiment ou d’école. Ne pas surcharger avec des services supplémentaires.

## 1. Réseau et requêtes

Fichier : [01-reseau-et-requetes.png](01-reseau-et-requetes.png).

Titre : « Où passe ma requête ? ». Montrer un navigateur hors du VPC. Dans le VPC, regrouper visuellement les subnets publics contenant l’ALB et une tâche Fargate. Dans cette tâche, placer Next.js et FastAPI. Dans les subnets privés, placer RDS PostgreSQL/pgvector.

Tracer le parcours navigateur → ALB en HTTPS 443 → Next.js en HTTP 3000 → FastAPI par localhost:8000 → RDS en TLS 5432. Faire partir de FastAPI deux autres flèches vers S3 et OpenAI, hors du VPC. Ne pas placer S3 dans un subnet ni faire partir l’appel OpenAI de RDS. DNS aide à trouver l’adresse ; ACM fournit le certificat : ne pas les dessiner comme des relais traversés par chaque requête.

Ajouter les trois règles d’entrée simplifiées des security groups. Préciser que les deux zones sont regroupées pour la lecture, que les réponses utilisent les connexions ouvertes et que public ne signifie pas ouvert à tous. Les détails de routes et d’endpoint restent dans le texte.

## 2. Identités et droits IAM

Fichier : [02-identites-et-droits-iam.png](02-identites-et-droits-iam.png).

Titre : « IAM : qui a le droit de faire quoi ? ». En haut, séparer l’identité humaine : toi → connexion SSO → rôle d’administration → configuration AWS.

En dessous, présenter trois lignes avec les colonnes acteur, rôle IAM et actions permises. ECS au démarrage utilise `atelier-rag-execution` pour ECR, le secret applicatif et les logs. Le code utilise `atelier-rag-application` pour les fichiers de son bucket S3. ECS pour la préparation utilise `atelier-rag-preparation` pour ECR, les logs et les deux secrets.

Ajouter deux encadrés : trust policy = qui peut utiliser le rôle ; permission policy = quelles actions sur quelles ressources. Indiquer qu’un rôle IAM n’ouvre pas un port réseau. Pour PostgreSQL, il faut aussi une connexion autorisée et un utilisateur SQL avec son mot de passe. Le rôle de préparation autorise la lecture des secrets ; les privilèges SQL viennent des identifiants injectés.

## 3. Images Docker, ECS et Fargate

Fichier : [03-images-ecs-et-fargate.png](03-images-ecs-et-fargate.png).

Titre : « Comment le programme se met à tourner ». En haut : PC et Dockerfile → docker build → deux images Docker → docker push → ECR. Les images conservées ne sont pas encore des tâches en exécution.

Au milieu, une définition de tâche référence les images, le CPU, la mémoire, les rôles et les secrets. Le service ECS utilise cette définition pour garder une tâche active. Le cluster est un regroupement logique.

En bas, Fargate fournit le calcul pour une tâche contenant Next.js et FastAPI. Dessiner une flèche de contrôle depuis le service ECS, puis une flèche distincte pour le téléchargement des images ECR. Préciser que S3 et RDS gardent les données et que la préparation est une tâche ponctuelle qui s’arrête après son travail.

Correction finale demandée à imagegen : remplacer le fond sombre par un fond ivoire opaque et remplacer les tags inventés `latest` par `interface:atelier-01` et `serveur:atelier-01`. Les autres éléments restent identiques. Les noms d’images sont abrégés pour la lisibilité ; les vraies URI ECR incluent le registre et le chemin du dépôt.
