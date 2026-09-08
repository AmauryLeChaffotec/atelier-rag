"""Construire les deux images Linux/AMD64 puis les publier dans ECR avec un tag unique."""

import argparse
import base64
import re
import shutil

from commun import configuration_aws, executer, lancer


def principal():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("version", help="Tag inédit, par exemple 2026-09-08-01 ; jamais latest")
    options = arguments.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}", options.version) or options.version == "latest":
        raise ValueError("Choisissez un tag de version explicite valide, différent de latest.")
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("Installez et démarrez Docker Desktop.")
    config, session = configuration_aws(champs=("repositories",))
    if set(config["repositories"]) != {"serveur", "interface"} or not all(config["repositories"].values()):
        raise ValueError("Renseignez les deux URI ECR dans repositories : serveur et interface.")
    ecr = session.client("ecr")
    for depot in config["repositories"].values():
        try:
            ecr.describe_images(
                repositoryName=depot.split("/", 1)[1],
                imageIds=[{"imageTag": options.version}],
            )
        except ecr.exceptions.ImageNotFoundException:
            continue
        raise ValueError("Ce tag existe déjà dans ECR. Choisissez une nouvelle version.")
    autorisation = ecr.get_authorization_token()["authorizationData"][0]
    utilisateur, mot_de_passe = base64.b64decode(autorisation["authorizationToken"]).decode().split(":", 1)
    executer(
        [
            docker,
            "login",
            "--username",
            utilisateur,
            "--password-stdin",
            autorisation["proxyEndpoint"],
        ],
        input=mot_de_passe,
        text=True,
    )
    for nom, depot in config["repositories"].items():
        executer(
            [
                docker,
                "build",
                "--platform",
                "linux/amd64",
                "--tag",
                f"{depot}:{options.version}",
                nom,
            ]
        )
    for depot in config["repositories"].values():
        executer([docker, "push", f"{depot}:{options.version}"])
    print(
        f"Images publiées : {options.version}. Étape suivante : préparer la base, puis déployer le service."
    )


if __name__ == "__main__":
    lancer(principal)
