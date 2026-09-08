# Sauvegarder, restaurer et supprimer l’installation AWS

Ce guide concerne uniquement l’installation Terraform du [guide AWS](deployer-sur-aws.md). Il suppose un profil AWS connecté et des commandes lancées à la racine du dépôt. **Une restauration nécessite un arrêt du site.** Ne la faites pas pour tester une simple mise à jour de code ; utilisez d’abord le retour au tag précédent.

## Ce qui est déjà sauvegardé

- RDS conserve les sauvegardes automatiques pendant **7 jours**, avec restauration à un instant disponible de cette fenêtre.
- S3 conserve les anciennes versions des documents pendant **30 jours** après leur remplacement/suppression. Un marqueur de suppression peut masquer un fichier sans détruire son ancienne version.
- Les images ECR taguées restent présentes pour revenir à un ancien code. Seules les images sans tag expirent après 7 jours.
- Le bucket d’état Terraform garde ses versions. Les secrets restent dans Secrets Manager : leur suppression est différée de 7 jours.

Le versionnement S3 ne constitue pas une copie indépendante contre la suppression du bucket ou de toutes ses versions. Pour des données importantes, gardez aussi les originaux dans une sauvegarde privée hors de ce compte. Une suppression dans Atelier supprime le document et l’index actifs ; les anciens extraits des conversations restent en base.

## Créer un point de sauvegarde manuel cohérent

Pour une sauvegarde avant une modification importante, empêchez temporairement les imports et attendez la fin des travaux. Mettez `nombre_taches = 0` dans `terraform.tfvars`, puis :

```powershell
terraform -chdir=deploiement/terraform plan -out=pause.tfplan
terraform -chdir=deploiement/terraform apply pause.tfplan
$config = terraform -chdir=deploiement/terraform output -json configuration | ConvertFrom-Json
aws ecs describe-services --cluster $config.cluster --services $config.service --query "services[0].{actives:runningCount,attendues:desiredCount,en_attente:pendingCount}"
aws ecs list-tasks --cluster $config.cluster --service-name $config.service
```

Attendez **zéro tâche**, y compris celles en cours d’arrêt, dans la console ECS. Vérifiez qu’aucune préparation/migration ponctuelle n’est active non plus. Puis créez un snapshot :

```powershell
$snapshot = "$($config.base)-manuel-$(Get-Date -Format yyyyMMdd-HHmmss)"
aws rds create-db-snapshot --db-instance-identifier $config.base --db-snapshot-identifier $snapshot --query "DBSnapshot.DBSnapshotIdentifier"
aws rds wait db-snapshot-available --db-snapshot-identifier $snapshot
```

Notez le nom du snapshot, la date UTC, le tag applicatif et le tag de préparation dans votre gestionnaire de documentation privé. Pour conserver aussi un manifeste des versions S3 à ce moment :

```powershell
New-Item -ItemType Directory -Force sauvegardes
aws s3api list-object-versions --bucket $config.bucket --output json | Out-File -Encoding utf8 "sauvegardes/$snapshot-versions.json"
```

Ce manifeste référence des versions ; il ne copie pas les fichiers. Conservez les originaux séparément si la sauvegarde doit survivre aux 30 jours de rétention. Le dossier `sauvegardes` est ignoré par Git. Remettez ensuite `nombre_taches = 1`, puis `plan` et `apply`.

## Restaurer un fichier supprimé

Dans **S3 → votre bucket → Show versions**, retrouvez la clé indiquée dans le manifeste. Sur une copie de récupération, téléchargez la version choisie et réimportez-la dans Atelier. C’est l’option la plus simple pour récupérer un document isolé avec un index cohérent.

Pour récupérer exactement une version par terminal, sans modifier le bucket :

```powershell
# Remplacez ces deux exemples par la clé et le VersionId du manifeste.
$cleFichier = "identifiant/document.pdf"
$versionFichier = "VERSION_ID_RELEVE_DANS_S3"
aws s3api get-object --bucket $config.bucket --key $cleFichier --version-id $versionFichier sauvegardes/document-recupere.pdf
```

## Restaurer toute la base

Cette procédure avancée conserve d’abord l’ancienne base. Elle facture temporairement deux instances RDS. Prenez un snapshot de l’état actuel avant de commencer et gardez `nombre_taches = 0` jusqu’à la fin.

1. Dans RDS, renommez la base actuelle en un nom unique, par exemple `atelier-rag-avant-restauration-20260909`. Attendez qu’elle soit disponible sous ce nouveau nom. **Ne lancez pas Terraform pendant cette opération.**
2. Dans **Snapshots**, choisissez le snapshot à récupérer, puis **Restore snapshot**. Réutilisez l’identifiant d’origine (`$config.base`) pour la nouvelle base. Sélectionnez `db.t4g.micro`, Single-AZ, le même VPC, `$config.subnet_group_base`, `$config.security_group_base` et `$config.parametres_base`. Désactivez l’accès public. Conservez le chiffrement.
3. Attendez la disponibilité de la base restaurée. Activez ensuite la gestion du mot de passe administrateur dans Secrets Manager avec cette commande. Elle génère un nouveau secret administrateur ; elle ne change pas le mot de passe du rôle applicatif `atelier` restauré avec les données.

```powershell
aws rds modify-db-instance --db-instance-identifier $config.base --manage-master-user-password --apply-immediately --query "DBInstance.DBInstanceIdentifier"
aws rds wait db-instance-available --db-instance-identifier $config.base
```

4. Rattachez explicitement la nouvelle base à Terraform. `state rm` ci-dessous enlève uniquement son ancienne association dans l’état Terraform : **cela ne supprime aucune base AWS**. L’ancienne base renommée restera à gérer manuellement jusqu’à sa suppression après validation.

```powershell
terraform -chdir=deploiement/terraform state rm aws_db_instance.base
terraform -chdir=deploiement/terraform import aws_db_instance.base $config.base
terraform -chdir=deploiement/terraform plan -out=restauration.tfplan
```

5. Lisez le plan. Il doit remettre sauvegardes, chiffrement/SSL, logs, endpoint et droits du nouveau secret en conformité, **sans remplacer la base restaurée**. S’il propose de détruire/remplacer RDS, arrêtez cette procédure et corrigez les écarts de configuration. Puis appliquez :

```powershell
terraform -chdir=deploiement/terraform apply restauration.tfplan
```

6. Choisissez les tags applicatif et de préparation correspondant au snapshot. Appliquez leur configuration avec `nombre_taches = 0`, puis lancez `preparer_base.py` pour remettre le mot de passe applicatif actuel et les migrations prévues. N’utilisez pas accidentellement les migrations d’une version ultérieure si vous voulez revenir au schéma sauvegardé.
7. Remettez les versions S3 du même point de sauvegarde pour les fichiers qui avaient été supprimés après le snapshot. La base contient les clés exactes ; le manifeste donne les VersionId. Depuis la console S3, restaurez ces objets avant la réouverture. Une base restaurée seule ne recrée pas les fichiers manquants.
8. Remettez `nombre_taches = 1`, puis `plan` et `apply`. Vérifiez documents, téléchargements, chat, sources, indexation et cache OCR.
9. Après validation, supprimez manuellement l’ancienne base renommée et les sauvegardes devenues inutiles. Elle n’est plus suivie par Terraform et continue à être facturée tant qu’elle existe.

La restauration à un instant précis suit le même principe : RDS crée une nouvelle instance, puis on contrôle réseau, secrets, fichiers et rattachement Terraform. Références : [restaurer un snapshot RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_RestoreFromSnapshot.html), [modifier une instance](https://docs.aws.amazon.com/cli/latest/reference/rds/modify-db-instance.html). Cette procédure doit être répétée dans votre compte avant de considérer les sauvegardes comme éprouvées.

## Supprimer l’installation

Ces opérations effacent le projet AWS. Conservez d’abord vos fichiers et les snapshots nécessaires ; gardez la configuration Terraform tant que la suppression n’est pas terminée.

1. Mettez `nombre_taches = 0`, puis `plan` et `apply`. Vérifiez l’arrêt des tâches.
2. Mettez `proteger_donnees = false`, puis `plan` et `apply`. Cela retire la protection contre la suppression de RDS, sans le supprimer immédiatement.
3. Dans S3 Console, videz **uniquement le bucket des documents de ce projet**, y compris ses versions et marqueurs de suppression, après sauvegarde. Dans ECR, supprimez les images des deux dépôts de ce projet. Terraform refuse volontairement de vider ces ressources automatiquement.
4. Vérifiez que le nom de snapshot final `${nom}-sauvegarde-finale` n’existe pas déjà. S’il existe, donnez un nom inédit à `final_snapshot_identifier` dans `donnees.tf` avant la suppression.
5. Préparez puis examinez le plan de suppression :

```powershell
terraform -chdir=deploiement/terraform plan -destroy -out=suppression.tfplan
terraform -chdir=deploiement/terraform apply suppression.tfplan
```

6. Supprimez les enregistrements DNS du site. Le snapshot final et les snapshots manuels conservés restent facturables. Dans Secrets Manager, le secret applicatif attend 7 jours avant suppression ; sa recréation immédiate avec le même nom peut être refusée.
7. Une fois la suppression terminée, archivez l’état Terraform en privé si nécessaire, puis videz/supprimez le bucket d’état distinct depuis S3 Console, avec toutes ses versions. Ne le videz jamais avant la fin de `destroy`.
8. Vérifiez **Billing → Bills** et **Cost Explorer**, ainsi que les ressources conservées ou restaurées manuellement et les autres régions utilisées. Les factures ont un délai de remontée. Un domaine se renouvelle tant que son renouvellement n’est pas désactivé. Les clés/crédits OpenAI et Mistral sont indépendants d’AWS.
