# 6 — Donner une adresse HTTPS au site et lancer le service

[Précédent](05-roles-et-preparation.md) · [Parcours](../deployer-sur-aws.md) · [Suivant](07-observer-et-modifier.md)

**À la fin :** vous ouvrez Atelier depuis un navigateur en HTTPS. La préparation doit avoir réussi et RDS doit être Available. Un ALB et une tâche permanente vont être facturés : gardez la [fiche de fin de séance](08-arreter-reprendre-supprimer.md) à portée de main.

## DNS et HTTPS, avant de payer un ALB

Une IP de tâche peut changer après son remplacement. L’**ALB** fournit un point d’entrée stable, répartit les requêtes vers les tâches saines et présente le certificat HTTPS. **DNS** associe votre nom lisible à cette entrée. Le certificat prouve au navigateur qu’il parle au bon site et permet de chiffrer l’échange.

Il vous faut un sous-domaine que vous contrôlez, par exemple `rag.mondomaine.fr`. Un domaine s’achète et se renouvelle séparément. Si vous en possédez un, gardez son fournisseur DNS : **Route 53 n’est pas nécessaire**. Si vous n’avez pas encore de domaine, vous pouvez vous arrêter après le chapitre 5 et avoir déjà pratiqué ECS, RDS, IAM, ECR et S3. N’ajoutez pas un ALB en attendant plusieurs jours de choisir un domaine.

Dans **Certificate Manager / ACM**, région **Paris**, choisissez **Request a public certificate** :

- Nom : `rag.mondomaine.fr`, remplacé par votre sous-domaine.
- Validation : **DNS**.
- Type : certificat public **non exportable**, destiné à l’ALB ; pas d’option payante d’export.

ACM affiche un enregistrement CNAME de validation. Chez votre fournisseur DNS, copiez son nom et sa valeur. Un CNAME est un alias DNS. Certains fournisseurs ajoutent automatiquement le domaine au nom : évitez de le doubler. Attendez le statut **Issued** dans ACM. Conservez ce CNAME pour permettre le renouvellement automatique.

Le certificat ACM non exportable utilisé par l’ALB n’a pas de supplément de certificat ; l’ALB et le domaine sont distincts. [Validation DNS ACM](https://docs.aws.amazon.com/acm/latest/userguide/dns-validation.html), [tarifs ACM](https://aws.amazon.com/certificate-manager/pricing/).

## Créer le groupe cible

Un **target group** dit au load balancer à quel type de destination envoyer les requêtes et comment vérifier qu’elle répond. Dans **EC2 → Target groups → Create target group** :

| Champ | Valeur |
|---|---|
| Target type | **IP addresses**, pas Instances |
| Name | `atelier-rag` |
| Protocol / port | HTTP / 3000 |
| IP version / VPC | IPv4 / `atelier-rag` |
| Health check | HTTP, chemin **`/api/sante`**, code réussi 200 |
| Interval / timeout | 20 secondes / 5 secondes |
| Healthy / unhealthy threshold | 2 / 3 |

Ne saisissez pas d’IP cible à la main : ECS enregistrera les IP de ses tâches. Dans les attributs du groupe, mettez **Deregistration delay = 120 secondes** : lors d’un remplacement, les connexions existantes ont un délai pour se terminer.

## Créer l’ALB

Dans **EC2 → Load balancers → Create → Application Load Balancer** :

| Champ | Valeur |
|---|---|
| Nom | `atelier-rag` |
| Scheme | Internet-facing |
| IP address type | IPv4 |
| VPC | `atelier-rag` |
| Mappings | Les deux zones et leurs deux subnets **publics** |
| Security groups | Seulement **`atelier-entree`** |
| Listener HTTPS 443 | Certificat ACM Issued ; action Forward vers le groupe `atelier-rag` |
| TLS security policy | `ELBSecurityPolicy-TLS13-1-2-2021-06` ou une politique AWS TLS 1.2/1.3 équivalente disponible |
| Listener HTTP 80 | Action **Redirect** vers HTTPS, port 443, code 301 |

Après création, dans **Attributes**, réglez **Idle timeout = 400 secondes** et activez **Drop invalid header fields**. Le timeout laisse de la marge au streaming et aux traitements RAG. Gardez la protection contre suppression désactivée pour pouvoir supprimer l’ALB à la fin d’une séance. N’activez pas WAF pour ce premier exercice sans en étudier les frais.

L’ALB facture des heures et de la capacité utilisée ; il utilise aussi des adresses IPv4 facturées. Il reste payant **sans visiteurs et sans tâche saine**. Son DNS peut momentanément répondre 503 tant qu’aucune tâche applicative n’est enregistrée : cela sera corrigé à l’étape suivante.

Dans la fiche ALB, copiez **DNS name**, qui ressemble à `atelier-rag-....eu-west-3.elb.amazonaws.com`. Chez votre fournisseur DNS, créez un CNAME **`rag`** vers ce DNS. Utilisez le mode DNS seul si votre fournisseur propose un proxy. Ce CNAME du site est différent de celui qui valide le certificat.

## Remplir la définition de l’application

```powershell
Copy-Item deploiement/aws/tache-application.exemple.json deploiement/aws/tache-application.json
```

Dans la copie, remplacez `COMPTE_AWS`, `URI_IMAGE_SERVEUR`, `URI_IMAGE_INTERFACE`, `HOTE_RDS`, `NOM_BUCKET_DOCUMENTS` et `ARN_SECRET_APPLICATION`. Les URI d’images doivent avoir **le tag**. Gardez les suffixes de sélection de clé après les ARN des secrets. Ne remplacez jamais un ARN par la valeur de la clé elle-même.

Dans ECS, créez une définition avec **Create new task definition with JSON**, en collant ce fichier. Prenez le temps de lire les choix :

| Élément | Pourquoi il est présent |
|---|---|
| Fargate, CPU 512, mémoire 2048 | 0,5 vCPU et 2 GiB pour la tâche complète |
| Serveur + interface | Deux conteneurs dans la même tâche ; réseau partagé |
| `executionRoleArn` | ECS charge images, logs et secret applicatif |
| `taskRoleArn` | FastAPI peut gérer les fichiers de son bucket S3 |
| `API_INTERNE=http://127.0.0.1:8000` | Next.js rejoint FastAPI dans la même tâche |
| `COOKIE_SECURISE=true` | Le cookie de connexion est utilisé en HTTPS |
| `FOURNISSEUR_IA=openai` | Bascule cloud vers l’API OpenAI |
| `STOCKAGE=s3` | Les fichiers survivent au remplacement du conteneur |
| `MIGRER_AU_DEMARRAGE=false` | La base a été préparée séparément au chapitre 5 |
| `dependsOn: HEALTHY` | Next.js attend que l’API soit saine |
| `healthCheck` | Commande qu’ECS utilise pour contrôler chaque conteneur |
| `stopTimeout=120` | Temps accordé aux conteneurs lors de leur arrêt |

Les quatre secrets vont au serveur ; l’interface n’a pas la clé OpenAI. Le port 8000 est déclaré à ECS mais le security group n’autorise aucune entrée externe vers ce port.

## Créer un service ECS

Une tâche de préparation s’arrête après son travail. Un **service** maintient un nombre voulu de tâches pour un site : s’il en perd une, il essaie de la remplacer. C’est pourquoi cliquer Stop sur une tâche de service ne suffit pas à couper les coûts : le service en recrée une.

Dans **Cluster atelier-rag → Services → Create** :

| Champ | Valeur |
|---|---|
| Nom | `atelier-rag` |
| Compute / Launch type | **Fargate**, pas Spot, pas EC2 |
| Task definition | Votre révision applicative `atelier-rag:N` |
| Desired tasks | **1** |
| Deployment | Rolling update, minimum sain 100 %, maximum 200 % |
| Failure detection | Circuit breaker activé, rollback activé |
| Networking | VPC atelier, deux subnets publics, groupe `atelier-application` seul |
| Public IP | **Enabled** |
| Load balancing | ALB existant `atelier-rag`, conteneur **interface:3000**, groupe cible existant `atelier-rag` |
| Health check grace period | 120 secondes |
| Service discovery / Service Connect | Désactivés pour ce cours |
| Auto scaling | Désactivé ; vous contrôlez le nombre de tâches |

Le maximum 200 % autorise temporairement deux tâches lors d’un remplacement ; cela ajoute du calcul et une IP pendant ce temps. Le rollback automatique nécessite une précédente version saine : il ne peut pas sauver un tout premier lancement sans version de secours.

Attendez une tâche **Running**, deux conteneurs **Healthy**, puis une cible **Healthy** dans l’ALB. Si le quota Fargate bloque le lancement, consultez **Service Quotas → AWS Fargate → On-Demand vCPU** ; prévoyez au moins 1,25 vCPU pour pouvoir garder une migration et deux tâches pendant un remplacement.

## Vérifier avec un vrai petit parcours

Notez l’adresse HTTPS dans `url` du carnet, puis :

```powershell
$config = Get-Content -Raw configuration-aws.json | ConvertFrom-Json
Invoke-RestMethod "$($config.url)/api/sante"
Start-Process $config.url
```

La première commande HTTP doit afficher le statut `pret`. Ce contrôle ne teste pas encore OpenAI ou S3. Dans le navigateur, connectez-vous avec `cle_acces`, importez un petit Markdown non confidentiel, générez l’aperçu, indexez, puis posez une question sur ce texte. Vérifiez le fichier dans S3 et la source citée dans Atelier.

La bibliothèque AWS est initialement vide. Réimportez vos fichiers et réindexez avec OpenAI ; les embeddings Qwen locaux ne sont pas réutilisables avec un autre modèle. L’OCR PDF Mistral n’est appelé que lorsque vous le demandez.

**Fin de séance :** passez immédiatement à la [fiche d’arrêt](08-arreter-reprendre-supprimer.md). Le site ne s’éteint pas lorsque vous fermez cet onglet. Références : [définitions de tâches ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-task-definition.html), [service ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-service-console-v2.html), [création ALB](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/create-application-load-balancer.html).
