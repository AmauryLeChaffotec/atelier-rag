"""Lecture du carnet AWS rempli à la main ; aucune clé dans les arguments."""

import json
import subprocess
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

RACINE = Path(__file__).resolve().parents[2]


def executer(arguments, **options):
    return subprocess.run(arguments, cwd=RACINE, check=True, **options)


def lire_configuration(chemin=RACINE / "configuration-aws.json", champs=()):
    if not chemin.is_file():
        raise RuntimeError(
            "Copiez deploiement/aws/configuration.exemple.json vers configuration-aws.json et remplissez les identifiants du guide."
        )
    config = json.loads(chemin.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ValueError("Le carnet AWS doit être un objet JSON.")
    compte = config.get("compte", "")
    if not isinstance(compte, str) or len(compte) != 12 or not compte.isascii() or not compte.isdigit():
        raise ValueError("Renseignez votre numéro de compte AWS à 12 chiffres dans configuration-aws.json.")
    manquants = [champ for champ in ("region", *champs) if not config.get(champ)]
    if manquants:
        raise ValueError("Complétez le carnet AWS : " + ", ".join(manquants))
    return config


def configuration_aws(champs=()):
    config = lire_configuration(champs=champs)
    session = boto3.Session(region_name=config["region"])
    compte = session.client("sts").get_caller_identity()["Account"]
    if compte != config["compte"]:
        raise RuntimeError("Le compte AWS connecté diffère de votre carnet. Vérifiez AWS_PROFILE.")
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
        raise SystemExit("Une commande a échoué ; la suite a été interrompue.") from None
