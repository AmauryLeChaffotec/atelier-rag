# 7 — Observer ce qui se passe et modifier une version

[Précédent](06-mettre-le-site-en-ligne.md) · [Parcours](../deployer-sur-aws.md) · [Suivant : fin de séance](08-arreter-reprendre-supprimer.md)

**À la fin :** vous savez retrouver une erreur, distinguer logs et métriques, créer une alarme et remplacer le code sans recréer tout votre réseau.

## Trois endroits à lire, dans cet ordre

**ECS → votre service → Events** décrit les décisions de la plateforme : lancement d’une tâche, échec de téléchargement, cible non saine. C’est le premier endroit quand le site ne démarre pas.

**ECS → Tasks → votre tâche → Containers** donne l’état de chaque conteneur et son code de sortie. Une tâche de préparation avec code 0 a terminé correctement ; un serveur qui termine n’est plus disponible. Le code 137 indique souvent un arrêt lié à la mémoire, à confirmer avec les raisons d’arrêt et les métriques.

**CloudWatch → Log groups → `/ecs/atelier-rag`** contient les messages du programme. Un log stream correspond à un conteneur et une exécution. Le groupe `/aws/rds/instance/atelier-rag/postgresql` concerne PostgreSQL. Gardez la rétention à 7 jours et évitez de journaliser les clés ou le contenu complet des documents.

Depuis votre terminal connecté :

```powershell
$config = Get-Content -Raw configuration-aws.json | ConvertFrom-Json
aws ecs describe-services --cluster $config.cluster --services $config.service --query "services[0].{Attendues:desiredCount,Actives:runningCount,Evenements:events[0:5]}"
aws logs tail $config.journaux --since 30m
aws logs tail $config.journaux --follow
```

`--since 30m` lit les 30 dernières minutes. `--follow` continue à afficher les nouveaux messages ; `Ctrl+C` arrête seulement ce suivi local. Les lectures de logs ne sont pas des arrêts de tâche. Selon les fonctions utilisées, certaines consultations/requêtes CloudWatch peuvent avoir un coût.

## Logs, métriques, alarmes

Un **log** est un message daté, comme « indexation terminée ». Une **métrique** est une mesure dans le temps, comme la mémoire utilisée. Une **alarme** compare cette mesure à une règle et vous prévient si elle la franchit. Elle ne corrige pas automatiquement le problème.

Commencez par observer les graphiques gratuits standard du service ECS et de RDS. Faites un import, regardez CPU et mémoire, puis attendez que l’activité retombe. Vous reliez ainsi une action de l’utilisateur au travail effectué dans le cloud.

Pour recevoir un email, dans **SNS → Topics**, créez un topic **Standard** nommé `atelier-rag-alertes`. Dans **Subscriptions**, créez un abonnement de protocole **Email** avec votre adresse. **Confirmez le lien reçu par email**, sinon rien n’arrivera.

Dans **CloudWatch → Alarms → Create alarm**, choisissez la métrique, les dimensions de **votre ressource**, la période et le seuil ci-dessous. Pour chaque alarme, envoyez la notification d’état ALARM vers ce topic SNS. Les noms exacts permettent de les retrouver :

| Nom | Métrique / sélection | Règle proposée |
|---|---|---|
| `atelier-rag-cpu` | AWS/ECS, ClusterName=atelier-rag, ServiceName=atelier-rag, CPUUtilization | Moyenne > 80 %, 3 périodes de 60 s |
| `atelier-rag-memoire` | Mêmes dimensions, MemoryUtilization | Moyenne > 85 %, 3 périodes de 60 s |
| `atelier-rag-stockage` | AWS/RDS, DBInstanceIdentifier=atelier-rag, FreeStorageSpace | Minimum < 2 147 483 648 octets, 3 périodes de 60 s |
| `atelier-rag-erreurs` | AWS/ApplicationELB, votre LoadBalancer, HTTPCode_Target_5XX_Count | Somme ≥ 5, 3 périodes de 60 s |
| `atelier-rag-disponibilite` | AWS/ApplicationELB, votre LoadBalancer + TargetGroup, HealthyHostCount | Minimum < 1, 3 périodes de 60 s |

Pour les données manquantes, choisissez **not breaching** pour les quatre premières et **breaching** pour la disponibilité. Une métrique peut n’apparaître qu’après les premiers points envoyés : lancez le service et faites quelques requêtes si nécessaire.

Pour la première séance, vous pouvez créer seulement l’alarme CPU et comprendre son fonctionnement, puis compléter les quatre autres. Le calculateur prend par défaut cinq alarmes : `--alarmes 1` permet de refléter ce choix. Couper les notifications d’une alarme ne la supprime pas et ne supprime pas son coût.

L’alarme de disponibilité réagira quand vous éteignez volontairement le site. Désactivez ses actions avant une pause et réactivez-les à la reprise, ou supprimez-la si l’ALB est supprimé. Un nouvel ALB possède de nouvelles dimensions : recréez les alarmes qui le ciblent. [Créer une alarme CloudWatch](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ConsoleAlarms.html).

## Modifier le code, pas tout le cloud

1. Modifiez et testez le projet localement.
2. Construisez/publiez un **nouveau tag**, par exemple `atelier-02`, avec les commandes du chapitre 3.
3. Dans ECS, créez une **nouvelle révision** de `atelier-rag-preparation`, avec la nouvelle image serveur. Notez sa référence dans `tache_preparation` du carnet. Lancez une tâche et vérifiez code 0. Elle applique les éventuelles migrations.
4. Créez une nouvelle révision de `atelier-rag`, avec les deux nouvelles images.
5. Dans le service, **Update service** : choisissez cette révision. Gardez le réseau et l’ALB existants.
6. Attendez la stabilisation, puis testez import, indexation et chat.

Les anciennes et nouvelles tâches peuvent coexister pendant le remplacement. Les migrations doivent donc rester compatibles avec l’ancienne application : ajoutez les nouveaux champs avant de supprimer les anciens. Une migration importante mérite d’abord une [sauvegarde](../sauvegarder-restaurer-aws.md).

Pour revenir au code précédent, mettez le service sur l’ancienne révision de tâche, dont les images doivent toujours exister dans ECR. Cela n’annule **pas** les migrations SQL. Le rollback automatique du service a la même limite.

## Modifier une clé API

Dans Secrets Manager, ouvrez `atelier-rag/application`, puis modifiez la valeur voulue. Ne changez pas `postgres_mot_de_passe` en même temps qu’une clé OpenAI : cela demanderait aussi de changer le mot de passe SQL.

ECS lit les secrets au **démarrage**. Dans le service, cochez **Force new deployment**, ou exécutez :

```powershell
aws ecs update-service --cluster $config.cluster --service $config.service --force-new-deployment --query "service.serviceName"
aws ecs wait services-stable --cluster $config.cluster --services $config.service
```

Ces commandes remplacent les tâches et peuvent brièvement en faire tourner deux. Changer uniquement un secret ne demande pas de reconstruire les images. [Injection des secrets ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/specifying-sensitive-data.html).

## Diagnostic guidé

| Symptôme | Première vérification |
|---|---|
| AccessDenied dans le terminal | Identité SSO et compte retourné par STS |
| CannotPullContainerError | URI avec tag, image ECR publiée, rôle d’exécution, subnet public + route + IP publique |
| ResourceInitializationError / secret | ARN complet, suffixe JSON conservé, clés JSON exactes, policy sur le rôle d’exécution concerné |
| Timeout PostgreSQL | RDS Available, endpoint exact, SG application → base sur 5432, bonne base logique `atelier` |
| Password authentication failed | Préparation réussie et mot de passe applicatif inchangé depuis |
| Erreur de certificat | Endpoint RDS exact et bundle public `serveur/certificats/rds.pem` à jour ; gardez verify-full |
| ALB 503 | Groupe cible IP/3000, chemin /api/sante, bonne tâche/révision, SG entrée → application |
| Site accessible mais connexion impossible | HTTPS, clé d’accès correcte et COOKIE_SECURISE=true |
| OpenAI 401 / 429 | Clé, crédits et quotas côté OpenAI |
| S3 AccessDenied | Rôle **application**, bon nom de bucket et policy sur ses objets |
| Indexation interrompue | Attendre la reprise du bail (90 s) ; après trois interruptions, relancer dans le Studio |

**Checkpoint :** vous retrouvez les trois sources de diagnostic, savez lire une métrique et comprenez pourquoi une clé mise à jour nécessite de nouvelles tâches.

**Fin de séance :** [arrêter proprement](08-arreter-reprendre-supprimer.md). Un onglet CloudWatch fermé ne stoppe aucun service.
