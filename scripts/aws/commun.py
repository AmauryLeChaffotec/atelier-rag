"""Lecture des sorties Terraform et session AWS ; aucune clé dans les arguments."""

import json
import shutil
import subprocess
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

RACINE = Path(__file__).resolve().parents[2]


def executer(arguments, **options):
    return subprocess.run(arguments, cwd=RACINE, check=True, **options)


def configuration_aws():
    terraform = shutil.which("terraform")
    if not terraform:
        raise RuntimeError("Installez Terraform et rouvrez le terminal.")
    resultat = executer(
        [terraform, "-chdir=deploiement/terraform", "output", "-json", "configuration"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    config = json.loads(resultat.stdout)
    session = boto3.Session(region_name=config["region"])
    compte = session.client("sts").get_caller_identity()["Account"]
    if compte != config["compte"]:
        raise RuntimeError(
            "Le compte AWS connecté diffère de celui de Terraform. Vérifiez AWS_PROFILE."
        )
    return config, session


def lancer(fonction):
    try:
        fonction()
    except ClientError as erreur:
        # Le code suffit au diagnostic sans risquer d’afficher une valeur transmise à AWS.
        raise SystemExit(
            f"AWS : {erreur.response['Error']['Code']}. Consultez le guide de dépannage."
        ) from None
    except (RuntimeError, ValueError) as erreur:
        raise SystemExit(str(erreur)) from None
    except subprocess.CalledProcessError:
        raise SystemExit(
            "Une commande a échoué ; la suite a été interrompue."
        ) from None
