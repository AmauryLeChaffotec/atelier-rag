# 1 — Comprendre le cloud et préparer votre atelier

[Parcours complet](../deployer-sur-aws.md) · [Chapitre suivant : réseau](02-creer-le-reseau.md)

**À la fin :** vous savez où chercher les services, quelle identité vous utilisez et comment lire votre compte depuis le terminal. Vous n’avez encore créé aucun serveur.

## Le cloud, concrètement

Aujourd’hui, Docker lance l’application sur votre ordinateur. Sur AWS, vous louez des ressources dans des centres de données : du calcul pour exécuter le code, du stockage pour garder les fichiers et une base pour les données. « Cloud » décrit ce mode de fourniture ; ce n’est pas un programme particulier à installer.

Vous payez chaque service selon son propre compteur. Une tâche Fargate arrêtée ne consomme plus de calcul. Un disque RDS conservé continue à coûter même si la base est arrêtée. Fermer votre navigateur ou votre ordinateur **n’arrête pas AWS**.

| Mot | Signification dans votre projet |
|---|---|
| Compte AWS | Le périmètre qui possède les ressources et reçoit la facture ; numéro à 12 chiffres |
| Région | Une zone géographique AWS ; vous utilisez Paris, code `eu-west-3` |
| Availability Zone / AZ | Un emplacement isolé à l’intérieur d’une région ; par exemple `eu-west-3a` |
| Service | Une catégorie d’outil AWS : S3, RDS, ECS… |
| Ressource | Un objet créé dans un service : votre bucket S3, votre base RDS… |
| Console | Le site web AWS où vous cliquez pour gérer ces ressources |
| API | L’interface qui reçoit les demandes de création, lecture ou suppression |
| AWS CLI | Le programme `aws` qui appelle ces API depuis votre terminal |
| ARN | L’adresse complète d’une ressource AWS ; ce n’est pas un mot de passe |
| Tag | Une étiquette, par exemple `Projet = atelier-rag`, pour retrouver vos ressources |

Une région différente peut donner l’impression qu’une ressource a disparu. Regardez toujours la région en haut de la console. IAM et la facturation sont des services globaux ; leurs écrans n’ont pas toujours le même sélecteur de région.

## Votre identité : vous et l’application avez des droits différents

Le compte **root** correspond au propriétaire initial. Activez sa MFA dans les paramètres de sécurité, puis utilisez une identité d’administration distincte pour le travail courant. Ne créez pas de clé permanente root.

Pour ce cours, utilisez **IAM Identity Center** :

1. Dans la recherche AWS, ouvrez **IAM Identity Center**. Activez une instance d’organisation. AWS peut vous proposer de créer **AWS Organizations** : cela organise le compte, sans lancer de serveur.
2. Notez la région d’Identity Center et l’URL du portail d’accès. Ce portail est votre porte de connexion ; ce n’est pas l’URL du futur site Atelier.
3. Dans **Users**, créez votre utilisateur. Terminez son inscription depuis l’email reçu et configurez sa MFA.
4. Dans **Permission sets**, créez un ensemble de droits prédéfini **AdministratorAccess**.
5. Dans **AWS accounts**, sélectionnez votre compte, attribuez votre utilisateur et cet ensemble de droits.
6. Depuis le portail, ouvrez la console avec ce rôle. Vous pouvez administrer le compte d’apprentissage.

Ces droits sont larges parce que vous allez configurer réseau, IAM, base et calcul. Ils appartiennent à **votre identité d’administration**. Au chapitre 5, vous donnerez à l’application des rôles limités à ce dont elle a besoin. [Parcours officiel Identity Center](https://docs.aws.amazon.com/singlesignon/latest/userguide/getting-started.html).

## Mettre une alerte de coût avant de commencer

Ouvrez **Billing and Cost Management → Budgets → Create budget**. Créez un budget de coût mensuel de **10 USD** nommé `atelier-apprentissage` pour commencer. Ajoutez votre email et une alerte à 50 % et à 100 % du budget consommé. Si les modèles simplifiés proposent une alerte « Zero spend », vous pouvez aussi l’activer pour repérer les premières dépenses.

Si Billing refuse l’accès malgré votre rôle administrateur, reconnectez-vous ponctuellement avec root. Dans **Account → IAM user and role access to Billing information → Edit**, activez **Activate IAM Access**, enregistrez, puis revenez à votre identité d’apprentissage. Ce réglage de compte permet aux rôles déjà autorisés d’ouvrir la facturation ; il n’accorde pas à tout le monde des droits de paiement. [Accès à Billing](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/control-access-billing.html).

Un budget est une **alarme**, pas un plafond qui éteint les services. Les coûts ne remontent pas instantanément. Cette alerte concerne AWS ; OpenAI et Mistral ont leurs propres factures. Sans filtre, elle regarde l’ensemble du compte : c’est utile pour détecter aussi une ressource oubliée. [Créer un budget AWS](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-create.html).

## Préparer le terminal Windows

Ouvrez PowerShell. Docker Desktop doit être installé et démarré pour publier les images plus tard. Installez AWS CLI v2 si nécessaire :

```powershell
winget install --id Amazon.AWSCLI --exact
```

Rouvrez PowerShell après l’installation. Placez-vous dans le projet et vérifiez les outils :

```powershell
cd D:\projet-pro\rag
aws --version
docker version
```

`cd` change le dossier courant. `aws --version` vérifie la présence du client AWS ; `docker version` vérifie aussi que Docker fonctionne. Ces commandes ne créent rien dans le cloud.

Configurez une connexion nommée `atelier` :

```powershell
aws configure sso --profile atelier
```

Répondez avec les informations de votre portail : nom de session `atelier`, URL du portail, région d’Identity Center, scope proposé `sso:account:access`. Choisissez ensuite votre compte et le rôle attribué. Pour la région par défaut des **services**, mettez `eu-west-3`, et pour le format de sortie, `json`.

```powershell
$env:AWS_PROFILE = "atelier"
$env:AWS_DEFAULT_REGION = "eu-west-3"
$env:AWS_PAGER = ""
aws sso login --profile atelier
aws sts get-caller-identity
```

Une variable `$env:...` règle le comportement des programmes dans ce terminal. Le profil dit **qui vous êtes**, la région dit **où travailler**. `AWS_PAGER` évite d’ouvrir les résultats longs dans un lecteur séparé. La connexion SSO ouvre le navigateur ; validez-la. `sts get-caller-identity` lit votre identité : son champ `Account` doit être votre numéro de compte. [Configuration SSO officielle](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).

## Créer votre carnet

Une seule fois, depuis la racine du projet :

```powershell
Copy-Item deploiement/aws/configuration.exemple.json configuration-aws.json
```

Ouvrez `configuration-aws.json` dans votre éditeur. Remplacez `VOTRE_COMPTE_12_CHIFFRES` par le numéro lu dans `Account`, en gardant les guillemets. Laissez les autres valeurs vides pour le moment. Vous les remplirez au fil du cours.

JSON est un format de texte : une clé à gauche, une valeur à droite, séparées par `:`, avec une virgule entre les éléments. N’ajoutez pas de commentaires dans ce fichier. Ce carnet est ignoré par Git et ne contient que des identifiants, **jamais vos clés API ou mots de passe**. Ne le recopiez pas sur lui-même à chaque séance : vous perdriez vos notes.

## Vérifier et terminer

Vous devez savoir répondre : quelle région utilisez-vous ? Que signifie le numéro de compte ? Une alerte de budget arrête-t-elle un serveur ?

**Checkpoint :** la console est accessible avec votre utilisateur, le budget existe, `get-caller-identity` donne le bon compte et votre carnet contient son numéro.

**Fin de séance :** aucun RDS, Fargate ou ALB n’existe encore. Vous pouvez vous arrêter ici. À la prochaine séance, rouvrez PowerShell, revenez dans le dossier, rétablissez les trois variables `$env:...`, puis faites `aws sso login --profile atelier`.
