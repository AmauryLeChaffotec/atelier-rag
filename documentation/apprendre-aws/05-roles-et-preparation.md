# 5 — Donner les droits et lancer une première tâche ECS

[Précédent](04-base-et-secrets.md) · [Parcours](../deployer-sur-aws.md) · [Suivant](06-mettre-le-site-en-ligne.md)

**À la fin :** une tâche Fargate s’est connectée à RDS, a préparé PostgreSQL et s’est arrêtée avec succès. Vous comprenez les rôles IAM et la différence entre une définition de tâche et une tâche en cours d’exécution. Redémarrez RDS si vous l’aviez arrêté, puis attendez **Available**.

## IAM : qui peut faire quoi ?

Une **policy** énumère les opérations autorisées sur des ressources. Un **rôle** porte ces permissions et peut être utilisé temporairement par un service. Une **trust policy** dit qui peut utiliser le rôle. Exemple : Fargate peut utiliser un rôle d’exécution, mais une personne anonyme ne le peut pas.

Vous créez trois rôles, sans clés AWS permanentes dans les conteneurs :

| Rôle | Qui l’utilise ? | Droits utiles |
|---|---|---|
| `atelier-rag-execution` | ECS au démarrage du service | Télécharger les images ECR, écrire les logs, injecter le secret applicatif |
| `atelier-rag-application` | Votre code FastAPI une fois lancé | Lire, écrire et supprimer les fichiers de son bucket S3 |
| `atelier-rag-preparation` | ECS au démarrage de la tâche ponctuelle | Télécharger l’image, écrire les logs, injecter les secrets administrateur et applicatif |

Le rôle d’exécution n’est pas le rôle utilisé par `boto3` dans votre code. Cette distinction explique beaucoup de messages AccessDenied : il faut corriger les droits du **bon rôle**.

## Créer les trois rôles

Dans **IAM → Roles → Create role**, choisissez **Custom trust policy**. Pour chacun des trois rôles, utilisez cette même confiance :

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ecs-tasks.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

À l’étape des permissions, attachez la policy AWS gérée **AmazonECSTaskExecutionRolePolicy** à `atelier-rag-execution` et `atelier-rag-preparation`. Elle couvre les opérations standard ECR/logs. Ne l’attachez pas à `atelier-rag-application` : ce rôle reçoit seulement les droits S3 ci-dessous.

Après création d’un rôle, ouvrez **Permissions → Add permissions → Create inline policy → JSON** pour ajouter ses droits spécifiques. Une policy inline est attachée à ce rôle seulement.

### Rôle d’exécution courant : le secret applicatif

Remplacez `ARN_SECRET_APPLICATION` par l’ARN **complet** copié dans Secrets Manager, sans suffixe de clé JSON :

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": ["ARN_SECRET_APPLICATION"]
  }]
}
```

Nommez cette policy `lire-secret-application` dans le rôle `atelier-rag-execution`.

### Rôle de préparation : les deux secrets

Dans `atelier-rag-preparation`, ajoutez la policy `lire-secrets-preparation` :

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["secretsmanager:GetSecretValue"],
    "Resource": ["ARN_SECRET_APPLICATION", "ARN_SECRET_RDS"]
  }]
}
```

Remplacez les deux valeurs. Le secret RDS est celui géré par RDS, pas un autre secret créé à la main. Les clés KMS AWS gérées par défaut du cours ne demandent pas de policy personnelle KMS supplémentaire ; ce serait différent avec une clé personnalisée.

### Rôle du code : les fichiers S3

Dans `atelier-rag-application`, ajoutez `gerer-fichiers-atelier`, en remplaçant le nom du bucket :

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
    "Resource": ["arn:aws:s3:::NOM_BUCKET_DOCUMENTS/*"]
  }]
}
```

`/*` désigne les objets dans ce bucket. Le code connaît leurs clés exactes ; il n’a pas besoin de lister tous vos buckets. Gardez le nom précis du bucket au lieu d’ouvrir les droits à tous les buckets.

**Vérification :** le rôle courant ne peut pas charger le secret administrateur RDS. Le rôle applicatif n’a pas AdministratorAccess. [Rôle d’exécution ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html), [rôle de tâche](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html).

## Créer les logs et le cluster

Dans **CloudWatch → Log groups → Create log group**, créez `/ecs/atelier-rag`, classe **Standard**, rétention **7 jours**. Le conteneur y écrira sa sortie console ; vous pourrez donc lire les erreurs sans entrer dans la machine.

Dans **ECS → Clusters → Create cluster**, nommez le cluster `atelier-rag`. Choisissez l’exécution **AWS Fargate**, sans instances EC2, sans Managed Instances, sans Fargate Spot pour ce premier test. Désactivez Container Insights pour commencer. Le **cluster** est le regroupement logique ; le créer ne lance pas encore une tâche et n’ajoute pas de coût horaire de cluster Fargate.

## Lire et remplir la définition de préparation

Une **task definition** est une fiche d’exécution : quelle image, quelle mémoire, quelle commande, quels secrets. Une **task** est une exécution de cette fiche. Chaque modification de fiche crée une **révision**, comme `atelier-rag-preparation:1`, puis `:2`.

Sur votre PC :

```powershell
Copy-Item deploiement/aws/tache-preparation.exemple.json deploiement/aws/tache-preparation.json
```

Ouvrez la copie. Remplacez les marqueurs suivants, partout où ils apparaissent :

| Marqueur | Votre valeur |
|---|---|
| `COMPTE_AWS` | Numéro de compte à 12 chiffres ; le reste de l’ARN du rôle reste intact |
| `URI_IMAGE_SERVEUR` | URI ECR du serveur **avec le tag**, par exemple `.../atelier-rag/serveur:atelier-01` |
| `HOTE_RDS` | Endpoint RDS, sans protocole ni port |
| `ARN_SECRET_RDS` | ARN complet du secret administrateur ; gardez `:username::` ou `:password::` après lui |
| `ARN_SECRET_APPLICATION` | ARN complet du secret applicatif ; gardez `:postgres_mot_de_passe::` après lui |

Les suffixes `:nom_de_cle::` demandent à ECS une valeur précise dans le secret JSON. Exemple : `:password::` sélectionne `password`. Les deux `:` finaux gardent la version courante par défaut. Ce suffixe appartient à la référence ECS, pas à l’ARN utilisé dans la policy IAM. Fargate Linux **1.4.0 ou ultérieur** prend en charge cette sélection.

Lisez aussi les paramètres déjà remplis : `cpu: "256"` correspond à 0,25 vCPU ; `memory: "512"` à 512 MiB ; `command` lance `application.base.preparer`. Les variables PostgreSQL imposent `verify-full` : le serveur contrôle le certificat TLS et le nom RDS à l’aide du bundle public inclus dans l’image.

Dans **ECS → Task definitions → Create new task definition → Create new task definition with JSON**, collez le contenu de **votre copie remplie** et créez la définition. C’est une saisie native AWS, pas un outil de déploiement externe. Lisez la fiche obtenue : l’image et le rôle doivent être ceux attendus. Notez `atelier-rag-preparation:NUMERO` dans `tache_preparation` du carnet.

## Exécuter une tâche, une seule fois

Depuis la définition ou **Cluster → Tasks → Run new task** :

| Réglage | Valeur |
|---|---|
| Cluster | `atelier-rag` |
| Launch type | Fargate, Linux/X86_64, plateforme 1.4.0 ou ultérieure |
| Task definition | Votre dernière révision de `atelier-rag-preparation` |
| Nombre | 1 |
| VPC | `atelier-rag` |
| Subnets | Les deux **publics** |
| Security group | Seulement `atelier-application` |
| Auto-assign public IP | **Enabled** |

Cette IP sert à télécharger ECR et les secrets. Le groupe autorise la tâche à rejoindre RDS sur 5432, mais n’ouvre pas PostgreSQL à Internet. Fargate est facturé pendant l’exécution de la tâche, y compris son démarrage selon ses règles de facturation.

Cliquez **Run task**. Suivez les états : Provisioning/Pending → Running → Stopped. **Stopped n’est pas forcément une erreur** : ce programme se termine volontairement. Ouvrez le conteneur `preparation` : vous devez voir **Exit code: 0**. Dans ses logs, cherchez « Rôle applicatif, extension pgvector et migrations prêts. ».

Le programme crée le rôle SQL `atelier`, l’extension et les tables, puis note les migrations appliquées. Il ne lance pas l’interface et n’appelle aucun modèle IA. Une deuxième exécution vérifie le même état sans recréer toutes les tables. En cas de code différent de 0, lisez le chapitre [diagnostic](07-observer-et-modifier.md) avant de poursuivre.

## Vérifier et terminer

**Checkpoint :** les trois rôles existent, une tâche ponctuelle a terminé avec code 0 et vous avez trouvé ses logs. Vous savez pourquoi il ne faut pas créer un service permanent pour cette commande ponctuelle : ECS chercherait à la relancer quand elle se termine.

**Fin de séance :** la tâche de préparation doit être Stopped. Arrêtez RDS si vous ne continuez pas maintenant. Le cluster, les rôles et les task definitions peuvent rester. Les logs/secrets/fichiers continuent à occuper leurs services. [Arrêter/reprendre](08-arreter-reprendre-supprimer.md).

Raccourci facultatif pour les prochaines migrations, une fois le carnet complet : `uv run --project serveur python scripts/aws/preparer_base.py`. Il lance et vérifie une tâche ; il ne crée ni cluster, ni rôle, ni définition.
