# Sauvegarder et restaurer votre atelier AWS

[Retour au parcours](deployer-sur-aws.md) · [Arrêter, reprendre ou supprimer](apprendre-aws/08-arreter-reprendre-supprimer.md)

Ce chapitre est un exercice à faire **après avoir installé et testé le site**. Vous manipulez les ressources vous-même dans la console. Une restauration de base demande une interruption du site ; elle crée une nouvelle instance RDS, donc une dépense supplémentaire tant que l’ancienne existe.

## 1. Comprendre ce qu’il faut sauvegarder

Votre bibliothèque utilise deux endroits : **RDS contient les textes, chunks, embeddings et conversations ; S3 contient les fichiers**. Sauvegarder seulement l’un ne suffit pas à reconstruire l’autre.

| Protection configurée dans le cours | Ce qu’elle permet | Sa limite |
|---|---|---|
| Sauvegardes automatiques RDS, 7 jours | Restaurer la base à un instant proposé par AWS | Fenêtre limitée ; la restauration crée une autre instance |
| Snapshot RDS manuel | Garder une photographie de la base | Reste facturable tant que vous le conservez |
| Versionnement S3, anciennes versions 30 jours | Retrouver un objet remplacé ou masqué par une suppression | Ne protège pas contre la suppression du bucket ou de toutes ses versions |
| Images ECR avec tags immuables | Retrouver le code correspondant à une sauvegarde | Ne contiennent ni la base ni vos documents |

Un **snapshot** est une sauvegarde de l’instance RDS gérée par AWS. Ce n’est pas un fichier SQL à télécharger sur votre PC. Pour votre petit projet, gardez aussi vos documents originaux sur votre ordinateur, dans un dossier privé sauvegardé.

## 2. Faire un point de sauvegarde cohérent

L’objectif est que la base et les fichiers représentent le même moment. Ne lancez plus d’import, d’OCR, de chat ou d’indexation pendant cet exercice.

1. Dans ECS → votre cluster → votre service → **Update**, mettez **Desired tasks = 0**. Attendez l’arrêt de toutes les tâches du service. Vérifiez aussi qu’aucune tâche de préparation indépendante ne tourne. La [fiche d’arrêt](apprendre-aws/08-arreter-reprendre-supprimer.md) détaille ces contrôles.
2. Gardez RDS **Available** pour faire le snapshot. Dans RDS → Databases → votre instance → **Actions → Take snapshot**, choisissez un nom unique, par exemple `atelier-rag-20260908-1800`.
3. Dans **Snapshots → Manual**, attendez **Available**. Notez son identifiant, la date et les tags des deux images ECR dans vos notes privées.
4. Copiez les fichiers S3 et un inventaire de leurs versions sur votre PC avec les commandes ci-dessous. Gardez le fichier `configuration-aws.json` avec vos notes. Ne copiez pas les clés IA dans ce carnet.

Depuis la racine du projet, après `aws sso login --profile atelier` et la configuration du profil expliquée au chapitre 1 :

```powershell
$config = Get-Content configuration-aws.json -Raw | ConvertFrom-Json
$date = Get-Date -Format 'yyyyMMdd-HHmmss'
$dossier = Join-Path 'sauvegardes' $date
New-Item -ItemType Directory -Path $dossier -Force | Out-Null
aws s3 sync "s3://$($config.bucket)" "$dossier/fichiers"
aws s3api list-object-versions --bucket $config.bucket --output json | Out-File "$dossier/versions-s3.json" -Encoding utf8
Copy-Item configuration-aws.json "$dossier/configuration-aws.json"
```

`sync` télécharge les **versions actuellement visibles** des fichiers. Il ne télécharge pas toutes les anciennes versions. L’inventaire conserve leurs identifiants `VersionId`, utiles tant que ces versions existent encore dans S3. Sans option `--delete`, cette commande n’efface pas de fichier local. Ces appels lisent AWS ; ils peuvent entraîner des frais de requêtes et de transfert sortant.

Le dossier `sauvegardes/` est ignoré par Git. Vérifiez néanmoins où vous le stockez : il contient vos documents et peut être confidentiel. Ouvrez quelques fichiers téléchargés et vérifiez que le snapshot est disponible avant de considérer cette étape terminée.

Pour réviser le terminal, voici l’équivalent de la création du snapshot : **choisissez la console ou cette commande**, ne faites pas les deux avec le même nom.

```powershell
$snapshot = "atelier-rag-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
aws rds create-db-snapshot --db-instance-identifier $config.base --db-snapshot-identifier $snapshot --query 'DBSnapshot.DBSnapshotIdentifier'
aws rds wait db-snapshot-available --db-snapshot-identifier $snapshot
```

`wait` attend l’état demandé, sans créer une deuxième sauvegarde. Si l’attente expire, vérifiez l’état dans la console avant de relancer quoi que ce soit. Vous pouvez ensuite rouvrir le service avec une tâche, ou arrêter RDS pour terminer la séance. Un ALB conservé continue de coûter pendant toute cette interruption.

## 3. Récupérer un fichier S3

Pour un seul fichier supprimé, il n’est pas forcément nécessaire de restaurer RDS.

Dans S3 → votre bucket, activez **Show versions** et cherchez la clé exacte de l’objet. Un **delete marker** masque les anciennes versions : si la bonne version est celle juste en dessous, retirer uniquement ce marqueur la rend de nouveau visible. Vérifiez la clé et la version avant de confirmer. Pour un fichier remplacé, téléchargez la version voulue et téléversez-la à nouveau **à la même clé** : elle devient la version courante.

Ces opérations modifient les objets. Conservez une copie de la version actuelle avant de la remplacer. Si le document a été supprimé depuis Atelier, ses lignes SQL ont aussi été supprimées : remettre uniquement le fichier dans S3 ne le fera pas réapparaître dans la bibliothèque. Pour quelques documents, les réimporter puis les indexer peut être plus simple qu’une restauration complète.

## 4. Restaurer la base dans une nouvelle instance

Pour apprendre sans écraser votre état actuel, conservez l’ancienne instance jusqu’à validation. **Deux instances disponibles coûtent deux fois le calcul RDS.** Notez clairement leurs deux noms.

1. Refaites le point de sauvegarde de l’état actuel et gardez ECS à zéro pendant la restauration.
2. Dans RDS → Snapshots, sélectionnez le snapshot à récupérer → **Actions → Restore snapshot**. Donnez un **nouvel identifiant**, par exemple `atelier-rag-restaure-20260909`. Ne renommez pas l’ancienne base.
3. Relisez les réglages : PostgreSQL compatible avec le snapshot, `db.t4g.micro`, **Single-AZ**, même VPC, groupe de subnets `atelier-rag-prive`, security group **atelier-base uniquement**, accès public **No**, groupe de paramètres `atelier-rag-postgres17`, chiffrement conservé. Le snapshot contient déjà la base logique `atelier`.
4. Attendez **Available**, puis ouvrez **Modify** sur l’instance restaurée. Activez la gestion du mot de passe administrateur par **Secrets Manager** si elle n’est pas active. Pour PostgreSQL, faites cette configuration après la restauration. Choisissez **Apply immediately** pour cet atelier arrêté.
5. Vérifiez de nouveau : sauvegardes 7 jours, journal PostgreSQL exporté, protection contre suppression active, autoscaling du stockage désactivé, surveillance standard sans options payantes ajoutées. Un écran de restauration ne reprend pas nécessairement tous les réglages de l’ancienne instance.
6. Attendez la fin des modifications. Notez le **nouvel endpoint RDS** et le **nouvel ARN du secret administrateur**. Le nom logique reste `atelier`, mais l’adresse réseau a changé.

Équivalent terminal de l’activation du secret administrateur après restauration :

```powershell
$baseRestauree = 'atelier-rag-restaure-20260909'
aws rds modify-db-instance --db-instance-identifier $baseRestauree --manage-master-user-password --apply-immediately --query 'DBInstance.DBInstanceIdentifier'
aws rds wait db-instance-available --db-instance-identifier $baseRestauree
```

Cette action modifie le mot de passe de l’administrateur. Elle ne remet pas automatiquement à jour le mot de passe du rôle SQL `atelier` restauré depuis le snapshot. C’est le rôle de l’étape suivante.

## 5. Rebrancher et vérifier l’application

1. Dans votre carnet privé `configuration-aws.json`, remplacez `base` par l’identifiant de la nouvelle instance. Gardez l’ancien identifiant dans vos notes pour pouvoir supprimer l’ancienne instance plus tard.
2. Dans IAM → rôle `atelier-rag-preparation`, mettez à jour la permission de lecture du secret administrateur pour autoriser son **nouvel ARN**. Conservez la permission du secret applicatif. Le rôle `atelier-rag-execution` continue à lire seulement le secret applicatif.
3. Choisissez les images correspondant à la sauvegarde. Dans la copie de `tache-preparation.exemple.json`, remplacez l’endpoint, l’ARN administrateur et l’image, puis créez une nouvelle révision ECS. Exécutez cette tâche sur la base restaurée, comme au [chapitre 5](apprendre-aws/05-roles-et-preparation.md). Attendez le **code de sortie 0**. Elle remet le mot de passe applicatif actuel et les migrations de cette image. Ne choisissez pas par accident un code plus récent si vous cherchez à revenir à l’ancien schéma.
4. Mettez à jour `tache_preparation` dans le carnet. Dans la définition applicative, remplacez l’endpoint RDS et les images ; créez une nouvelle révision, puis sélectionnez-la dans la mise à jour du service ECS.
5. Récupérez les versions S3 correspondant au snapshot grâce à votre inventaire ou aux copies locales, pour les objets devenus manquants ou différents. Utilisez leurs clés exactes. **RDS ne restaure pas S3.** Les anciennes versions peuvent avoir expiré après 30 jours : votre copie privée devient alors nécessaire.
6. Remettez le service à une tâche. Vérifiez la connexion, les documents, les téléchargements, les conversations, les sources, une nouvelle indexation et, si vous l’utilisez, le cache OCR.
7. Après validation, supprimez séparément l’ancienne instance RDS et les sauvegardes inutiles en suivant la [fiche de suppression](apprendre-aws/08-arreter-reprendre-supprimer.md). Tant que vous la gardez, elle conserve des coûts, même arrêtée pour le stockage.

Si le test échoue, gardez le site fermé et l’ancienne base intacte pour analyser les logs. Si vous avez déjà modifié des fichiers S3, remettre seulement l’ancien endpoint ne suffit pas forcément : base et fichiers doivent rester cohérents.

Pour une longue pause, conserver un snapshot et supprimer RDS évite le redémarrage automatique après sept jours d’arrêt. Le snapshot reste payant et la reprise demande une restauration. Sauvegardez les fichiers en parallèle, notez les images et protégez vos copies privées.

## Ce que ce cours a réellement vérifié

Cette procédure a été relue à partir des documentations AWS ; elle n’a pas été exécutée dans votre compte. Faites un exercice avec des documents de démonstration avant de vous reposer sur ces sauvegardes pour des données importantes. Sources : [restaurer un snapshot RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_RestoreFromSnapshot.html), [secrets gérés par RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html), [récupérer des versions S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/RestoringPreviousVersions.html).
