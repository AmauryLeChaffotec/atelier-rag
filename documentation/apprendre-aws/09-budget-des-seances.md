# 9 — Combien coûtent vos séances ?

[Parcours](../deployer-sur-aws.md) · [Fiche d’arrêt](08-arreter-reprendre-supprimer.md)

**Votre utilisation ne ressemble pas à un hébergement permanent.** L’ancien ordre de grandeur de 75 USD/mois supposait un site allumé 24 h/24. Pour apprendre quelques heures, il faut distinguer les heures de calcul des ressources qui restent entre les séances.

Les exemples ci-dessous utilisent **Paris, tarifs vérifiés le 8 septembre 2026, USD hors taxes, sans crédits ni Free Tier**. Ce sont des estimations de consommation, pas des plafonds. Une conversion en euros dépend du change et de la facturation réelle.

## Lire les compteurs

| Poste | Son compteur | Repère de prix |
|---|---|---:|
| Fargate | Durée de vos tâches × CPU et mémoire | 0,0349 USD/h pour 0,5 vCPU + 2 GiB |
| RDS calcul | Durée de fonctionnement de db.t4g.micro | 0,018 USD/h |
| ALB | Toute sa durée d’existence + charge LCU | 0,02646 USD/h + 0,0084 USD/LCU/h |
| IPv4 | Durée de chaque IP publique | 0,005 USD/h/IP ; au moins 2 ALB + 1 tâche |
| RDS stockage | Volume conservé, même base arrêtée | 0,133 USD/Go/mois, soit 2,66 USD pour 20 Go sur le mois |
| ECR | Volume total d’images conservées | 0,10 USD/Go/mois |
| S3 | Volume, versions et requêtes | 0,024 USD/Go/mois au premier palier Standard à Paris |
| Secrets Manager | Secrets conservés + lectures | 0,40 USD/secret/mois + lectures |
| CloudWatch | Logs ingérés, logs conservés, alarmes | Dépend du volume ; cinq alarmes standard ≈ 0,50 USD/mois |

Une **LCU** est l’unité de charge de l’ALB : elle tient compte de connexions, de données traitées et des règles. Vous n’avez pas besoin de tout optimiser maintenant ; le calcul prend **0,1 LCU moyenne** comme hypothèse de petit trafic. Les déploiements et téléchargements peuvent changer les volumes.

Les sources détaillées sont dans [`tarifs.json`](../tarifs.json), notamment les catalogues AWS de Paris pour [Fargate](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonECS/current/eu-west-3/index.json), [RDS](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonRDS/current/eu-west-3/index.json) et [ALB](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AWSELB/current/eu-west-3/index.json). Les [IPv4](https://aws.amazon.com/vpc/pricing/) et les [secrets](https://aws.amazon.com/secrets-manager/pricing/) sont facturés séparément du calcul.

## Trois situations à comparer

Même petit usage IA dans les trois cas : **100 questions** avec 3 000 tokens d’entrée et 500 de sortie, **1 million de tokens à indexer**, **aucune page OCR**. Stockage supposé : 20 Go RDS, 1 Go S3 toutes versions incluses, 2 Go ECR. Logs : 0,1 Go ingéré ; cinq alarmes. Les requêtes S3 et lectures de secrets sont incluses selon les quantités affichées par le calculateur.

| Scénario | Ce que vous faites réellement | Estimation |
|---|---|---:|
| Laboratoire de 4 heures, puis suppression | Tous les services existent 4 h, puis vous supprimez calcul **et stockage**, sans snapshot conservé | **0,57 USD HT pour le laboratoire** |
| 8 heures actives dans le mois | Vous supprimez l’ALB entre les séances, arrêtez RDS et conservez les données/images/secrets/alarmes sur 730 h | **5,12 USD HT/mois** |
| Les mêmes 8 heures, mais ALB conservé | Le load balancer et ses IP existent 730 h, même si ECS est à zéro presque tout le mois | **32,05 USD HT/mois** |

**L’exemple à 5,12 USD suppose que RDS n’est réellement actif que 8 heures.** Il ne doit pas redémarrer automatiquement et rester oublié. Les pauses doivent être suivies : RDS se redémarre après sept jours maximum. Pour une absence longue, sauvegarder puis supprimer la base est une autre procédure, avec des coûts de snapshots à ajouter.

L’exemple à 0,57 USD est un calcul de laboratoire court, pas une promesse de première facture : vous consacrerez probablement plus de temps à apprendre et conserverez des ressources d’un jour à l’autre. Saisissez ces durées réelles. Supprimer les ressources utiles uniquement pour atteindre cet exemple n’est pas l’objectif.

Les ressources se créent et se suppriment à des moments différents. Le prorata commun de conservation simplifie les calculs ; il faut ajouter le domaine, les snapshots conservés, le trafic Internet/inter-AZ, éventuels crédits CPU RDS excédentaires, services optionnels, requêtes Logs Insights, frais SNS hors franchise et taxes. Les redéploiements/migrations créent temporairement d’autres tâches et IP. Les opérations de démarrage/arrêt prennent du temps ; incluez-les dans les durées.

**Pour les séances courtes, comptez les durées facturables :** une heure ALB entamée est due en entier. Deux séances de 1 h 10 min correspondent donc à **4 heures ALB**, même si vous avez travaillé 2 h 20 min. Pour RDS, la facturation du calcul a un minimum de **10 minutes après une création, un démarrage ou un changement de classe**. Fargate Linux a un minimum de **1 minute par tâche**. Le calculateur ne connaît pas le nombre de démarrages : renseignez des durées qui incluent ces minimums. Les exemples de 4 h et 8 h utilisent déjà des heures entières. Sources : [règles ALB](https://aws.amazon.com/elasticloadbalancing/pricing/), [règles RDS](https://aws.amazon.com/rds/postgresql/pricing/), [règles Fargate](https://aws.amazon.com/fargate/pricing/).

## Utiliser la calculatrice du projet

Le programme fonctionne sur votre PC sans compte AWS connecté. Il ne crée, n’arrête et ne supprime rien. Depuis la racine :

```powershell
python scripts/estimer_cout.py --profil seance
python scripts/estimer_cout.py --profil intermittent
python scripts/estimer_cout.py --profil intermittent --heures-alb 730
```

Pour simuler 12 heures actives avec conservation entre séances :

```powershell
python scripts/estimer_cout.py --profil intermittent --heures-fargate 12 --heures-rds 12 --heures-alb 12
```

Pour ne garder qu’une alarme, et tester 20 pages OCR :

```powershell
python scripts/estimer_cout.py --profil intermittent --alarmes 1 --pages-ocr 20
```

`--heures-conservation` règle la durée de conservation du stockage RDS/S3/ECR, des secrets et des alarmes dans ce modèle simplifié. `--supplements 2` ajoute 2 USD pour des postes supplémentaires que vous avez estimés. `--go-ecr` et `--go-s3` doivent inclure les anciennes versions. Pour voir tous les paramètres :

```powershell
python scripts/estimer_cout.py --help
```

Les prix IA de référence du projet sont `gpt-4o-mini`, `text-embedding-3-small` et `mistral-ocr-latest`. Mistral ajoute **0,004 USD par page envoyée**, soit 0,08 USD pour 20 pages ; un résultat en cache évite habituellement un nouvel appel. Un arrêt brutal avant sauvegarde du résultat peut conduire à répéter un appel facturé. Les fournisseurs facturent indépendamment d’AWS.

## Votre exercice

Calculez votre propre séance : combien de temps pour RDS ? Combien pour l’ALB ? Que gardez-vous jusqu’au lendemain ? Comparez ensuite avec Cost Explorer lorsque les données sont disponibles. Cherchez les écarts par service au lieu de regarder uniquement un total.

Vous maîtrisez le coût lorsque vous pouvez expliquer **quelle ressource continue de coûter, pourquoi et pendant combien de temps**. Gardez l’alerte de budget à 10 USD au début, puis ajustez-la consciemment à vos expériences.
