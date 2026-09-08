# 3 — S3 pour les fichiers, ECR pour les images Docker

[Précédent](02-creer-le-reseau.md) · [Parcours](../deployer-sur-aws.md) · [Suivant](04-base-et-secrets.md)

**À la fin :** vous avez un bucket privé et deux images Docker dans AWS. Aucun conteneur n’est encore lancé sur AWS. Les petits volumes stockés commencent à être facturables.

## Comprendre les trois mots qui se ressemblent

Un **fichier documentaire** est un PDF, un Markdown ou un autre document que l’application lit. Il va dans **S3**. Une **image Docker** est le paquet contenant le programme et ses dépendances ; elle va dans **ECR**. Un **conteneur** est une exécution de cette image ; il sera lancé par **Fargate**. Déposer une image dans ECR ne la lance pas.

## Créer le bucket des documents

Dans **S3 → Create bucket**, choisissez un bucket **General purpose**, région Paris :

| Champ | Valeur |
|---|---|
| Nom | `atelier-rag-VOTRE_COMPTE-documents`, avec votre numéro à 12 chiffres |
| Object Ownership | ACLs disabled / Bucket owner enforced |
| Block Public Access | Les quatre protections activées |
| Versioning | Enabled |
| Default encryption | SSE-S3, clés gérées par S3 |
| Object Lock | Désactivé pour ce cours |

Le nom d’un bucket doit être unique globalement. Un bucket contient des **objets** : chaque objet a une clé, son contenu et des métadonnées. Les chemins comme `document/page.png` sont des clés ; S3 n’est pas le disque du conteneur.

Après création, dans **Permissions → Bucket policy**, ajoutez cette règle en remplaçant `NOM_BUCKET_DOCUMENTS` aux deux endroits :

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:*",
    "Resource": ["arn:aws:s3:::NOM_BUCKET_DOCUMENTS", "arn:aws:s3:::NOM_BUCKET_DOCUMENTS/*"],
    "Condition": {"Bool": {"aws:SecureTransport": "false"}}
  }]
}
```

Lisez-la : refuser (`Deny`) à tout demandeur (`Principal`) toute opération S3 si le transport n’est pas chiffré. Cette règle ne donne aucun droit de lecture publique. Les droits de l’application seront définis dans IAM.

Dans **Management → Lifecycle rules**, ajoutez une règle pour tous les objets : supprimer les **versions non courantes après 30 jours** et abandonner les imports multipart incomplets après 7 jours. Ne cochez pas la suppression des versions courantes. Le versionnement aide à récupérer une suppression, mais les anciennes versions occupent du stockage.

Testez avec un petit fichier sans information privée : **Upload**, puis ouvrez sa fiche et utilisez **Download** depuis la console. Copier l’URL de l’objet dans un navigateur non connecté ne doit pas donner un accès public. Supprimez ensuite cet objet de test ; sa version peut rester conservée.

Remplissez `bucket` dans votre carnet. [Créer un bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/create-bucket-overview.html), [gestion des versions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Versioning.html).

## Créer les dépôts ECR

Dans **Elastic Container Registry → Private registry → Repositories**, créez deux dépôts privés à Paris :

- `atelier-rag/serveur`
- `atelier-rag/interface`

Choisissez **Immutable** pour les tags et le chiffrement AES-256. Un tag est un nom de version. Immutable empêche de remplacer silencieusement le contenu d’un tag déjà publié. Pour les analyses, gardez l’analyse **Basic**, éventuellement sur publication ; n’activez pas l’analyse Enhanced/Inspector pour cet exercice sans en examiner le coût.

Copiez l’**URI** de chaque dépôt dans `repositories.serveur` et `repositories.interface` du carnet. Une URI ressemble à `123456789012.dkr.ecr.eu-west-3.amazonaws.com/atelier-rag/serveur`.

## Construire puis publier, commande par commande

Lancez les commandes depuis la racine du projet, dans une session SSO connectée comme au chapitre 1. La connexion Docker à ECR utilise un mot de passe temporaire transmis directement entre les programmes :

```powershell
$config = Get-Content -Raw configuration-aws.json | ConvertFrom-Json
$registre = "$($config.compte).dkr.ecr.$($config.region).amazonaws.com"
aws ecr get-login-password --region $config.region | docker login --username AWS --password-stdin $registre
```

La première ligne lit votre carnet. La deuxième construit le nom du registre. Le symbole `|` envoie la sortie de `aws` à l’entrée de `docker` sans afficher le mot de passe. Le résultat attendu est `Login Succeeded`.

Choisissez un **nouveau** tag, puis construisez les deux images sur votre PC :

```powershell
$version = "atelier-01"
$imageServeur = "$($config.repositories.serveur):$version"
$imageInterface = "$($config.repositories.interface):$version"
docker build --platform linux/amd64 --tag $imageServeur serveur
docker build --platform linux/amd64 --tag $imageInterface interface
```

`serveur` et `interface`, à la fin, sont les dossiers contenant les Dockerfile. `--platform` correspond au processeur X86_64 choisi plus tard dans Fargate. Les modèles Ollama ne sont pas embarqués : sur AWS, le programme appellera OpenAI.

Si les deux constructions réussissent, publiez :

```powershell
docker push $imageServeur
docker push $imageInterface
```

`build` prépare une image localement. `push` la transfère à ECR et commence à occuper du stockage ECR. Aucune de ces commandes ne crée de tâche Fargate. Dans chaque dépôt ECR, vous devez voir le tag `atelier-01` et un **digest**, une empreinte du contenu.

Ne publiez jamais votre `.env` : les Dockerfile et fichiers `.dockerignore` du projet séparent le code des secrets. Vous saisirez les clés dans Secrets Manager au prochain chapitre.

## Vérifier et terminer

**Checkpoint :** le bucket est privé, le téléchargement via console fonctionne, les deux dépôts contiennent votre tag. Vous pouvez expliquer la différence entre un PDF dans S3 et une image Docker dans ECR.

**Fin de séance :** aucun calcul AWS n’est actif. Les fichiers S3, anciennes versions et images ECR restent facturables selon leur taille. Gardez-les pour la suite ; ne confondez pas faible coût et absence totale de coût. [Tarifs S3](https://aws.amazon.com/s3/pricing/), [tarifs ECR](https://aws.amazon.com/ecr/pricing/).

Après avoir compris ce parcours, le raccourci facultatif `uv run --project serveur python scripts/aws/publier_images.py atelier-02` réalise les mêmes constructions/publications à partir du carnet. Il ne crée pas vos dépôts.
