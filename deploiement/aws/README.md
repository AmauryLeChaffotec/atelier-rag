# Les trois modèles du parcours AWS

Commencez par le [cours pour débutants](../../documentation/deployer-sur-aws.md). Ces fichiers ne créent pas une infrastructure : les deux définitions de tâche sont le format JSON natif de la console ECS. Vous les remplissez, les lisez, puis les enregistrez vous-même dans AWS.

| Fichier | Où l’utiliser |
|---|---|
| [`configuration.exemple.json`](configuration.exemple.json) | Copiez-le une fois vers `configuration-aws.json` à la racine ; complétez progressivement vos identifiants AWS |
| [`tache-preparation.exemple.json`](tache-preparation.exemple.json) | Copiez-le vers `tache-preparation.json` dans ce dossier ; chapitre 5, tâche ponctuelle qui prépare PostgreSQL |
| [`tache-application.exemple.json`](tache-application.exemple.json) | Copiez-le vers `tache-application.json` dans ce dossier ; chapitre 6, deux conteneurs dans une tâche Fargate |

Remplacez les marqueurs `COMPTE_AWS`, `HOTE_RDS`, `URI_IMAGE_SERVEUR`, `URI_IMAGE_INTERFACE`, `NOM_BUCKET_DOCUMENTS`, `ARN_SECRET_APPLICATION` et `ARN_SECRET_RDS` là où ils sont présents. Chaque chapitre explique où trouver leurs valeurs. Une URI d’image comprend son tag, par exemple `:atelier-01`.

**Aucune clé IA ni aucun mot de passe ne va dans ces JSON.** Les secrets y sont référencés par ARN ; les valeurs restent dans Secrets Manager. Les copies personnelles sont ignorées par Git. Les exemples de ce dossier restent génériques et partageables.

Pour modifier les ressources plus tard, changez-les dans la console. Modifier un JSON local ne modifie pas AWS : une définition de tâche doit être enregistrée comme nouvelle révision, puis sélectionnée par le service.

## Aides facultatives, après le parcours manuel

Les scripts de [`scripts/aws`](../../scripts/aws) évitent de répéter quelques opérations lorsque vous les avez comprises. Ils lisent votre carnet et vérifient le compte AWS connecté. Ils ne créent ni VPC, ni RDS, ni service ECS. L’installation manuelle n’en dépend pas.

Avec Python 3.12, installez `uv` si nécessaire, puis préparez les dépendances depuis la racine du projet :

```powershell
winget install --id astral-sh.uv --exact
uv sync --project serveur --frozen
```

Rouvrez le terminal si `uv` n’est pas encore reconnu. Reconnectez ensuite le profil `atelier` comme au chapitre 1. Les scripts ci-dessous **agissent réellement sur AWS** :

| Commande | Action |
|---|---|
| `uv run --project serveur python scripts/aws/publier_images.py atelier-02` | Construit les deux images et les publie dans vos dépôts ECR existants |
| `uv run --project serveur python scripts/aws/configurer_secrets.py` | Saisit les clés sans affichage et met à jour le secret applicatif existant ; conserve son mot de passe SQL |
| `uv run --project serveur python scripts/aws/preparer_base.py` | Lance la révision de préparation inscrite dans le carnet et attend son résultat |

Publier une image ne met pas automatiquement à jour le service : suivez le [chapitre 7](../../documentation/apprendre-aws/07-observer-et-modifier.md). Le calculateur [`estimer_cout.py`](../../scripts/estimer_cout.py), lui, reste entièrement local et ne demande aucune connexion AWS.
