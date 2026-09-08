# 8 — Finir une séance, reprendre et supprimer

[Parcours](../deployer-sur-aws.md) · [Budget](09-budget-des-seances.md) · [Sauvegardes](../sauvegarder-restaurer-aws.md)

**Cette fiche fait partie de chaque séance.** Elle concerne les ressources que vous avez créées à la main dans le cours. Vous n’êtes pas obligé de construire toute l’architecture avant de pratiquer son arrêt.

## Arrêter n’a pas le même sens selon le service

| Ressource | Action de pause | Ce qui reste facturé |
|---|---|---|
| Service Fargate | Mettre **Desired tasks = 0** | Plus de calcul quand toutes les tâches sont Stopped ; autres services inchangés |
| Tâche ponctuelle | Attendre Stopped ou l’arrêter explicitement | Aucun calcul une fois arrêtée ; logs conservés |
| RDS | **Stop temporarily**, attendre Stopped | Stockage et éventuelles sauvegardes ; redémarrage automatique au plus tard après 7 jours |
| ALB | Il n’a pas de bouton Stop : **Delete** pour arrêter sa facturation horaire | Les autres ressources restent ; DNS et alarmes à remettre à jour lors de la recréation |
| ECR | Ne lance pas de calcul | Images conservées |
| S3 | Ne lance pas de calcul | Objets, anciennes versions et requêtes |
| Secrets Manager | Ne se met pas en veille | Secrets conservés |
| CloudWatch | Arrêter l’application réduit les nouveaux logs | Logs déjà stockés, alarmes conservées ; désactiver leurs actions ne les rend pas gratuites |
| IAM, VPC de ce cours, cluster/définitions ECS | Peuvent rester | Pas de coût horaire propre pour ces seuls objets ; les services associés ont leur propre facture |

**Fermer le PC, se déconnecter d’AWS ou arrêter une seule tâche de service ne suffit pas.** Un service dont Desired tasks vaut 1 essaie de maintenir une tâche active.

## Pause courte, avec reprise facile

Cette option garde l’ALB, donc son coût continue. Utilisez-la si vous reprenez vite et que vous acceptez ce coût.

1. Terminez vos imports/indexations. Évitez d’interrompre une réponse de chat utile.
2. Désactivez les actions de l’alarme de disponibilité pendant la pause.
3. Dans **ECS → service atelier-rag → Update**, mettez **Desired tasks = 0**.
4. Attendez zéro tâche active/en attente. Regardez aussi l’onglet Tasks du cluster pour les préparations ponctuelles qui ne font pas partie du service. Vérifiez que toutes les exécutions de votre atelier sont **Stopped**, y compris celles en cours d’arrêt.
5. Dans **RDS → atelier-rag → Actions → Stop temporarily**, arrêtez la base. Attendez **Stopped**.
6. Notez l’heure, la date et la limite de sept jours. Une base en état Stopping n’est pas encore arrêtée.

Équivalent terminal pour le service et RDS, depuis le projet et une session SSO connectée :

```powershell
$config = Get-Content -Raw configuration-aws.json | ConvertFrom-Json
aws ecs update-service --cluster $config.cluster --service $config.service --desired-count 0 --query "service.desiredCount"
aws ecs wait services-stable --cluster $config.cluster --services $config.service
aws ecs list-tasks --cluster $config.cluster --desired-status RUNNING
```

Vérifiez les éventuelles tâches listées avant de continuer. La commande suivante suppose RDS encore démarré :

```powershell
aws rds stop-db-instance --db-instance-identifier $config.base --query "DBInstance.DBInstanceStatus"
# Lecture de l’état : répétez cette ligne plus tard jusqu’à voir stopped.
aws rds describe-db-instances --db-instance-identifier $config.base --query "DBInstances[0].DBInstanceStatus" --output text
```

AWS CLI affiche une erreur si vous arrêtez une base déjà arrêtée ; lisez l’état avant de répéter. Un waiter peut expirer avant la fin d’une opération lente : vérifiez alors dans la console, sans supposer qu’elle a échoué ni lancer des opérations contradictoires.

Pour reprendre cette pause courte :

```powershell
aws rds start-db-instance --db-instance-identifier $config.base --query "DBInstance.DBInstanceStatus"
aws rds wait db-instance-available --db-instance-identifier $config.base
aws ecs update-service --cluster $config.cluster --service $config.service --desired-count 1 --query "service.desiredCount"
aws ecs wait services-stable --cluster $config.cluster --services $config.service
Invoke-RestMethod "$($config.url)/api/sante"
```

Puis réactivez les actions de l’alarme de disponibilité. Le démarrage RDS précède les tâches pour éviter qu’elles échouent faute de base.

## Pause économique : supprimer aussi l’ALB

Après avoir mis le service à zéro et arrêté les tâches :

1. **Supprimez le service ECS** `atelier-rag` désormais à zéro. Gardez sa dernière task definition : elle décrit votre code et vos paramètres. Les documents/conversations ne vivent pas dans le service.
2. Dans **EC2 → Load balancers**, supprimez **uniquement l’ALB atelier-rag**. Il n’existe pas d’état ALB arrêté.
3. Dans **Target groups**, supprimez le groupe cible atelier-rag après suppression de l’ALB. Cela facilite une recréation propre ; il ne stocke aucun document.
4. Supprimez les alarmes visant cet ALB/groupe cible. Vous les recréerez pour les nouvelles dimensions.
5. Supprimez le CNAME du site `rag` qui pointait vers l’ancien ALB. **Gardez le CNAME de validation ACM** et le certificat si vous réutilisez le domaine.
6. Arrêtez RDS comme dans la pause courte et vérifiez sa date limite.

Pour reprendre : démarrez RDS, attendez Available, puis refaites la création du groupe cible, de l’ALB et du service au [chapitre 6](06-mettre-le-site-en-ligne.md), en sélectionnant votre définition applicative existante. Recréez le CNAME du site vers le **nouveau DNS ALB**, puis les alarmes ALB. Vous n’avez pas à recréer le VPC, S3, ECR, les rôles ou les tables.

Pour apprendre, cette répétition est utile : vous voyez ce qui décrit le programme, ce qui l’exécute et ce qui conserve les données. La suppression de l’ALB évite son coût entre les séances, au prix de quelques manipulations à la reprise.

## Une absence de plus de sept jours

**RDS se redémarre automatiquement après sept jours d’arrêt.** Une estimation qui le suppose arrêté un mois entier serait trompeuse sans actions supplémentaires. [Règle officielle RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_StopInstance.html).

Pour une longue pause, choisissez consciemment : conserver la base et suivre ses redémarrages/frais, ou sauvegarder puis **supprimer l’instance RDS**. Un snapshot conservé reste payant mais évite le calcul de l’instance supprimée. La reprise devient une restauration, avec un nouvel endpoint et potentiellement un nouveau secret administrateur : [procédure](../sauvegarder-restaurer-aws.md).

Ne supprimez pas une base utile pour économiser quelques heures sans avoir vérifié vos sauvegardes. Si tous vos documents de test sont jetables et conservés sur le PC, vous pouvez repartir d’une base vide et les réimporter/réindexer.

## Tout supprimer après le laboratoire

Procédez dans cet ordre pour éviter les dépendances qui bloquent la suppression. Chaque fois, sélectionnez les ressources de **votre projet** dans **Paris**.

1. Sauvegardez ce qui doit rester. Mettez le service à zéro et vérifiez l’arrêt des tâches ponctuelles et de service.
2. Supprimez le service ECS, l’ALB, ses listeners et le groupe cible. Retirez le CNAME du site.
3. Dans RDS, **Modify → Deletion protection off**, appliquez. Si AWS exige que la base soit disponible pour cette modification, redémarrez-la, puis attendez. **Actions → Delete** : choisissez un snapshot final si vous voulez garder les données, avec un nom inédit. Lisez explicitement les options de sauvegardes conservées ; ne comptez pas sur des valeurs par défaut.
4. Après disparition de RDS, supprimez ses groupes de paramètres/subnets. Le secret administrateur géré par RDS est supprimé avec l’instance ; vérifiez dans Secrets Manager. Le secret applicatif est distinct : planifiez sa suppression si vous ne le réutilisez pas. Le délai minimal proposé est généralement 7 jours ; le même nom ne peut pas être recréé normalement tant que cette suppression est en attente. Vous pouvez annuler une suppression planifiée si vous reprenez avant sa fin.
5. Videz le bucket documentaire S3 **avec toutes ses versions et marqueurs de suppression**, puis supprimez-le. Le bouton Empty de la console aide à traiter un bucket versionné. Cette action efface les fichiers conservés : vérifiez votre sauvegarde avant.
6. Supprimez les images puis les deux dépôts ECR si vous ne les gardez pas pour une reprise. Désenregistrez les définitions de tâches inutiles et supprimez le cluster ECS vide.
7. Supprimez les alarmes, les groupes de logs et le topic SNS si vous ne voulez pas les conserver. Gardez l’alerte AWS Budgets jusqu’à avoir contrôlé les coûts restants.
8. Dans VPC, attendez la disparition des interfaces réseau utilisées par ECS, ALB et RDS. Supprimez l’endpoint S3. Retirez les règles entre les trois security groups, puis supprimez-les. Supprimez les subnets et tables de routes personnalisées, détachez/supprimez l’Internet Gateway, puis supprimez le VPC. La console peut proposer de traiter plusieurs dépendances ; lisez leur liste.
9. Supprimez les trois rôles IAM dédiés devenus inutiles. Gardez votre utilisateur d’apprentissage. Supprimez le certificat ACM uniquement s’il ne sert plus ; ses enregistrements DNS de validation peuvent alors être retirés.
10. Vérifiez les snapshots manuels/finals, sauvegardes retenues, domaines, éventuelles IP allouées manuellement et ressources d’autres régions. Ils ne disparaissent pas forcément avec le site.

## Votre contrôle de fin de séance

Notez dans un petit journal privé : date, ressources encore présentes, état RDS, date de redémarrage automatique, ALB supprimé ou conservé, coût résiduel accepté.

Dans **Billing → Bills** puis **Cost Explorer**, regardez les coûts par service et région le lendemain ou une fois les données remontées. Un montant déjà facturé ne disparaît pas après suppression ; ce sont les **nouvelles dépenses** qui doivent cesser pour les ressources supprimées. Les crédits gratuits éventuels peuvent masquer le montant dû sans faire disparaître la consommation.

Un domaine garde son renouvellement annuel tant que vous ne le désactivez pas chez son fournisseur. OpenAI et Mistral restent des comptes séparés. Aucun script du dépôt ne programme d’arrêt automatique : vous contrôlez vous-même ces actions pour les apprendre.
