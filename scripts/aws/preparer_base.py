"""Lancer la tâche de migration et vérifier sa réussite avant de déployer le service."""

from botocore.exceptions import WaiterError

from commun import configuration_aws, lancer


def verifier_resultat(reponse):
    taches = reponse.get("tasks", [])
    if reponse.get("failures") or len(taches) != 1:
        raise RuntimeError(
            "La tâche de préparation n’est pas accessible. Consultez ECS."
        )
    conteneurs = taches[0].get("containers", [])
    if len(conteneurs) != 1 or conteneurs[0].get("exitCode") != 0:
        raise RuntimeError(
            "La préparation a échoué. Consultez CloudWatch ; ne déployez pas la nouvelle version."
        )


def principal():
    config, session = configuration_aws()
    if not config["tache_preparation"]:
        raise RuntimeError(
            "Passez d’abord Terraform à l’étape preparation, comme indiqué dans le guide."
        )
    ecs = session.client("ecs")
    reponse = ecs.run_task(
        cluster=config["cluster"],
        taskDefinition=config["tache_preparation"],
        launchType="FARGATE",
        platformVersion="1.4.0",
        count=1,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": config["subnets"],
                "securityGroups": [config["security_group"]],
                "assignPublicIp": "ENABLED",
            }
        },
    )
    if reponse.get("failures") or len(reponse.get("tasks", [])) != 1:
        raise RuntimeError(
            "ECS n’a pas lancé la tâche de préparation. Vérifiez les événements ECS et vos quotas."
        )
    identifiant = reponse["tasks"][0]["taskArn"]
    print("Préparation en cours. Les journaux sont dans", config["journaux"])
    try:
        ecs.get_waiter("tasks_stopped").wait(
            cluster=config["cluster"],
            tasks=[identifiant],
            WaiterConfig={"Delay": 6, "MaxAttempts": 150},
        )
    except WaiterError:
        raise RuntimeError(
            "Résultat non confirmé après attente. Vérifiez la tâche dans ECS avant toute suite."
        ) from None
    verifier_resultat(
        ecs.describe_tasks(cluster=config["cluster"], tasks=[identifiant])
    )
    print(
        "Préparation réussie : rôle PostgreSQL, pgvector et migrations. Le service peut être déployé."
    )


if __name__ == "__main__":
    lancer(principal)
