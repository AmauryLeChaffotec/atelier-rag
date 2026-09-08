# 2 — Construire et comprendre le réseau

[Précédent](01-comprendre-et-preparer.md) · [Parcours](../deployer-sur-aws.md) · [Suivant](03-stocker-et-publier.md)

**À la fin :** votre réseau sait où envoyer le trafic et quelles connexions autoriser. Aucun serveur n’est encore lancé. Utilisez Paris `eu-west-3` dans la console.

## VPC : votre espace réseau

Un **VPC** est un réseau logique que vous contrôlez. Ses **subnets** sont des portions de ce réseau, chacune placée dans une AZ. Un subnet « public » possède une route vers Internet ; « privé » signifie ici qu’il n’en possède pas. Le mot public ne suffit pas à rendre un service accessible : l’IP et les règles de pare-feu comptent aussi.

Dans **VPC → Your VPCs → Create VPC**, choisissez **VPC only** pour créer chaque élément vous-même :

| Champ | Valeur |
|---|---|
| Name | `atelier-rag` |
| IPv4 CIDR | `10.42.0.0/16` |
| IPv6 | Aucun pour ce cours |
| Tenancy | Default |
| Tag | `Projet = atelier-rag` |

Le `/16` est une notation CIDR : elle décrit la taille du bloc d’adresses. Vous n’avez pas besoin de calculer les adresses à la main pour ce cours. Sur le VPC créé, **Actions → Edit VPC settings** : activez **DNS resolution** et **DNS hostnames**. DNS permet de trouver une adresse IP à partir d’un nom comme l’endpoint RDS.

## Créer quatre subnets

Dans **Subnets → Create subnet**, sélectionnez ce VPC. Créez ces quatre entrées :

| Nom | AZ | CIDR |
|---|---|---|
| `atelier-public-a` | `eu-west-3a` | `10.42.1.0/24` |
| `atelier-public-b` | `eu-west-3b` | `10.42.2.0/24` |
| `atelier-prive-a` | `eu-west-3a` | `10.42.11.0/24` |
| `atelier-prive-b` | `eu-west-3b` | `10.42.12.0/24` |

Chaque `/24` est un bloc plus petit à l’intérieur du `/16`. Les blocs ne se chevauchent pas. Les deux zones permettent à l’ALB et au groupe de subnets RDS de respecter leurs exigences réseau. Cela ne rend pas votre petite base Single-AZ redondante.

## Ajouter la sortie Internet

Dans **Internet gateways**, créez `atelier-internet`, puis **Attach to a VPC** : choisissez `atelier-rag`. Une Internet Gateway est le point de passage vers Internet ; elle ne lance pas de machine.

Dans **Route tables**, créez `atelier-routes-publiques`, dans ce VPC. Dans **Routes → Edit routes**, ajoutez :

| Destination | Cible | Sens |
|---|---|---|
| `0.0.0.0/0` | Internet Gateway `atelier-internet` | Tout ce qui n’a pas de route plus précise peut sortir vers Internet |

Gardez la route `10.42.0.0/16 → local`, créée par AWS : elle sert aux échanges dans le VPC. Dans **Subnet associations**, associez **seulement** `atelier-public-a` et `atelier-public-b`.

Créez ensuite `atelier-routes-privees`. Gardez seulement sa route locale et associez les deux subnets privés. RDS y sera installé, sans route directe vers Internet.

**Ne créez pas de NAT Gateway.** Fargate utilisera une IP publique pour ses appels sortants, avec des entrées strictement limitées. Un NAT est utile dans d’autres architectures mais ajouterait un service facturé à l’heure à cet atelier.

## Les security groups : les portes autorisées

Une route indique **où passer**. Un **security group** indique **si la connexion est autorisée**. Il s’attache à une ressource réseau, pas à tout le subnet. Une réponse à une connexion autorisée est automatiquement permise : c’est un pare-feu à état.

Dans **Security groups**, créez trois groupes vides d’entrées, tous dans votre VPC : `atelier-entree`, `atelier-application`, `atelier-base`. Créez les trois avant de remplir les règles, pour pouvoir les sélectionner comme sources/cibles.

Remplacez leurs règles de sortie par celles du tableau ; n’ajoutez pas ces règles à côté d’une sortie « All traffic » existante.

| Groupe | Entrées | Sorties |
|---|---|---|
| `atelier-entree` | TCP 80 et 443 depuis `0.0.0.0/0` | TCP 3000 vers le groupe `atelier-application` |
| `atelier-application` | TCP 3000 depuis le groupe `atelier-entree` | TCP 80 et 443 vers `0.0.0.0/0` ; TCP 5432 vers `atelier-base` |
| `atelier-base` | PostgreSQL/TCP 5432 depuis le groupe `atelier-application` | Aucune règle nécessaire pour les réponses aux connexions entrantes |

Pour les ports 3000, choisissez **Custom TCP**. Quand la source/cible est un groupe, sélectionnez son identifiant `sg-...` ; ne tapez pas une plage d’IP à sa place. `0.0.0.0/0` signifie toutes les adresses IPv4. C’est attendu pour l’entrée HTTPS publique, mais **pas pour le port PostgreSQL 5432**.

Le port API 8000 n’a pas de règle d’entrée : les deux conteneurs d’une même tâche communiqueront par `localhost`. Vous n’avez pas besoin de SSH ni du port 22.

## Ajouter l’endpoint S3

Un **endpoint** permet ici d’atteindre S3 depuis le VPC par une route AWS prévue pour ce service. Dans **Endpoints → Create endpoint** : services AWS, service `com.amazonaws.eu-west-3.s3`, type **Gateway**, VPC `atelier-rag`, table `atelier-routes-publiques`. Gardez la politique d’endpoint par défaut pour ce cours ; IAM et le bucket limiteront les droits. N’achetez pas par erreur un endpoint **Interface**, qui a une autre facturation.

Le type Gateway S3 n’a pas de coût horaire d’endpoint. Le stockage et les requêtes S3 restent facturables. [Endpoints Gateway S3](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-s3.html).

## Vérifier et terminer

Dans le carnet, remplissez `subnets` avec les deux identifiants **publics** et `security_group` avec celui d’`atelier-application`. Exemple de forme : `"subnets": ["subnet-...", "subnet-..."]`. Conservez aussi les noms/ID privés dans vos notes personnelles pour RDS.

Vous pouvez lire vos subnets depuis PowerShell :

```powershell
# Lecture uniquement : remplacez la valeur par votre VPC.
$vpc = "vpc-VOTRE_IDENTIFIANT"
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc" --query "Subnets[].{Id:SubnetId,Zone:AvailabilityZone,Plage:CidrBlock}" --output table
```

**Checkpoint :** deux routes publiques vers Internet, deux subnets privés sans cette route, trois groupes avec les bons ports, aucune NAT Gateway. Expliquez avec vos mots pourquoi RDS sera joignable depuis Fargate mais pas directement depuis votre PC.

**Fin de séance :** ces VPC, subnets, tables, groupes et Internet Gateway n’ont pas de coût horaire propre dans ce scénario sans trafic. Vous pouvez les laisser pour la suite. Références : [création VPC](https://docs.aws.amazon.com/vpc/latest/userguide/create-vpc.html), [security groups](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html), [tarifs VPC](https://aws.amazon.com/vpc/pricing/).
