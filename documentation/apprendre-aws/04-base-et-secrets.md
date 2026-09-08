# 4 — Créer PostgreSQL et conserver les secrets

[Précédent](03-stocker-et-publier.md) · [Parcours](../deployer-sur-aws.md) · [Suivant](05-roles-et-preparation.md)

**À la fin :** RDS contient une base PostgreSQL privée et Secrets Manager conserve deux secrets distincts. **RDS facture du calcul dès sa création, même sans requête.** Prévoyez du temps pour terminer, puis pour l’arrêter.

## À quoi sert PostgreSQL dans un RAG ?

S3 garde les fichiers originaux. PostgreSQL garde les documents décrits par l’application, les morceaux de texte, leurs embeddings, les conversations et les indexations à exécuter. **pgvector** est une extension de PostgreSQL permettant de stocker et comparer les vecteurs ; ce n’est pas un service AWS supplémentaire à créer.

RDS administre l’instance PostgreSQL : stockage, mises à jour et sauvegardes. Votre application continuera à créer ses propres tables. Une **instance RDS** est la machine/base gérée par AWS ; la **base nommée `atelier`** est la base logique à l’intérieur.

## Préparer les deux groupes RDS

Dans **RDS → Subnet groups → Create DB subnet group** : nom `atelier-rag-prive`, VPC `atelier-rag`, zones `eu-west-3a` et `eu-west-3b`, choisissez **les deux subnets privés**. Ce groupe indique où RDS peut placer l’instance.

Dans **Parameter groups → Create parameter group** : famille `postgres17`, type DB Parameter Group, nom `atelier-rag-postgres17`. Après création, éditez `rds.force_ssl` et mettez `1`. Ce paramètre exige des connexions chiffrées. Son application est liée au démarrage/redémarrage ; comme vous créez une nouvelle base avec ce groupe, il sera déjà présent au démarrage. [TLS PostgreSQL sur RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html).

## Créer l’instance avec Standard create

Dans **RDS → Databases → Create database**, choisissez **Standard create**, pour voir les réglages. Suivez ce tableau plutôt qu’un bouton de création simplifiée :

| Rubrique | Valeur et raison |
|---|---|
| Engine | PostgreSQL, version majeure **17**, version mineure disponible et prise en charge |
| Template | Dev/Test ; vérifiez les tailles réelles choisies ensuite |
| Availability | **Single DB instance / Single-AZ**, pour limiter le coût |
| Identifier | `atelier-rag` |
| Master username | `administrateur` |
| Credentials management | **Managed in AWS Secrets Manager** ; clé de chiffrement AWS par défaut |
| Instance class | Burstable classes → **db.t4g.micro** |
| Storage | **gp3**, 20 GiB ; stockage chiffré activé |
| Storage autoscaling | Désactivé pour ce laboratoire borné ; vous surveillerez l’espace libre |
| Compute connection | Ne pas connecter automatiquement à EC2 |
| VPC | `atelier-rag` |
| DB subnet group | `atelier-rag-prive` |
| Public access | **No** |
| VPC security group | **Seulement `atelier-base`**, retirez le groupe default s’il est sélectionné |
| Port | 5432 |
| Initial database name, options supplémentaires | **`atelier`** — ne laissez pas ce champ vide |
| DB parameter group | `atelier-rag-postgres17` |
| Backups | Rétention automatique 7 jours |
| Monitoring | Réglages standard ; ne pas activer Enhanced Monitoring ou une offre Advanced payante pour ce cours |
| Log exports | PostgreSQL log |
| Maintenance | Mise à jour mineure automatique ; pas de souscription Extended Support pour une version 17 encore prise en charge |
| Deletion protection | Activée ; vous la retirerez explicitement pour supprimer la base |

Gardez la clé de chiffrement AWS gérée par défaut ; une clé KMS personnalisée ajouterait une notion et une facturation distinctes. Prenez le temps de relire l’estimation affichée par la console avant **Create database**. Si une option ou classe manque, vérifiez région, PostgreSQL et modèle de création avant de choisir une machine plus chère.

Attendez **Available**. Relevez son **Endpoint**, par exemple `atelier-rag.xxxxxx.eu-west-3.rds.amazonaws.com`, sans `https://` ni port. C’est le nom que le serveur utilisera. Il reste privé : votre PC ne peut pas s’y connecter directement, ce qui est prévu.

Dans la fiche RDS, ouvrez le lien **Master credentials ARN / Manage in Secrets Manager**. Notez l’ARN du secret administrateur dans vos notes, sans afficher ni copier sa valeur dans le dépôt. RDS crée et gère ce mot de passe ; le secret possède notamment les clés JSON `username` et `password`. [Gestion des secrets RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html).

## Créer le secret de l’application, à la main

Dans **Secrets Manager → Store a new secret**, choisissez **Other type of secret**. Saisissez quatre paires clé/valeur :

| Clé exacte | Valeur à saisir |
|---|---|
| `openai_api_key` | La clé API de votre projet OpenAI |
| `mistral_api_key` | Votre clé Mistral, ou une chaîne vide si vous ne testez pas l’OCR |
| `cle_acces` | Une clé de connexion au site de 32 à 128 caractères ASCII, générée dans votre gestionnaire de mots de passe |
| `postgres_mot_de_passe` | Un autre mot de passe aléatoire d’au moins 32 caractères, pour le rôle PostgreSQL `atelier` |

Les clés à gauche doivent être exactement celles du tableau. Choisissez le chiffrement `aws/secretsmanager`, puis nommez le secret **`atelier-rag/application`**. Désactivez la rotation automatique de **ce secret applicatif** : la rotation du mot de passe de base demande une procédure coordonnée, et celle des clés externes appartient à leurs fournisseurs.

Pourquoi deux secrets ? La préparation utilisera l’administrateur RDS pour créer l’extension et le rôle applicatif. Le serveur courant aura seulement le mot de passe de `atelier`, sans privilèges administrateur. Le secret applicatif regroupe quatre valeurs pour éviter de multiplier les secrets facturés.

Copiez l’ARN du secret applicatif dans `secret_application` du carnet. Un ARN n’est pas la clé OpenAI. Ne placez aucune des **valeurs** dans le carnet, dans les JSON ECS ou dans GitHub. Pour vos API, vérifiez les crédits du compte fournisseur ; les crédits AWS ne financent pas OpenAI ou Mistral.

## Logs et vérification

Dans **CloudWatch → Log groups**, cherchez `/aws/rds/instance/atelier-rag/postgresql` une fois l’export démarré. Fixez sa rétention à **7 jours**. RDS peut prendre un peu de temps avant de créer le groupe et d’envoyer les premières lignes.

Lecture depuis le terminal :

```powershell
aws rds describe-db-instances --db-instance-identifier atelier-rag --query "DBInstances[0].{Etat:DBInstanceStatus,Endpoint:Endpoint.Address,Public:PubliclyAccessible,Classe:DBInstanceClass}" --output table
```

**Checkpoint :** statut Available, Public=False, classe db.t4g.micro, base logique `atelier` sélectionnée à la création, deux secrets distincts. Vous comprenez quel secret servira à préparer et lequel servira à l’application.

**Fin de séance :** dans RDS, sélectionnez l’instance, **Actions → Stop temporarily**. Attendez réellement **Stopped**. Le stockage et les secrets restent facturés. AWS redémarre une base arrêtée après **sept jours maximum** : notez la date et ne la laissez pas sans surveillance pendant plusieurs semaines. [Fiche d’arrêt complète](08-arreter-reprendre-supprimer.md).
