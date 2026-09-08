"""Un seul point d’entrée pour les fichiers locaux ou S3, toujours privés."""

from pathlib import Path

import boto3

from application.configuration import configuration


def chemin_local(cle: str) -> Path:
    racine = Path(configuration().repertoire_fichiers).resolve()
    chemin = (racine / cle).resolve()
    if not chemin.is_relative_to(racine):
        raise ValueError("Chemin de fichier invalide.")
    return chemin


def enregistrer(cle: str, contenu: bytes, type_mime="application/octet-stream"):
    config = configuration()
    if config.stockage == "s3":
        boto3.client("s3", region_name=config.aws_default_region).put_object(
            Bucket=config.s3_bucket,
            Key=cle,
            Body=contenu,
            ContentType=type_mime,
            ServerSideEncryption="AES256",
        )
    else:
        chemin = chemin_local(cle)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_bytes(contenu)


def lire_fichier(cle: str) -> bytes:
    config = configuration()
    if config.stockage == "s3":
        return (
            boto3.client("s3", region_name=config.aws_default_region)
            .get_object(Bucket=config.s3_bucket, Key=cle)["Body"]
            .read()
        )
    return chemin_local(cle).read_bytes()


def supprimer(cle: str):
    config = configuration()
    if config.stockage == "s3":
        boto3.client("s3", region_name=config.aws_default_region).delete_object(
            Bucket=config.s3_bucket, Key=cle
        )
    else:
        chemin_local(cle).unlink(missing_ok=True)
