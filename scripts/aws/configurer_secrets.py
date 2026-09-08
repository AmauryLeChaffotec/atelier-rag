"""Saisir les secrets sans écho et les envoyer directement à Secrets Manager."""

import argparse
import getpass
import json
import secrets

from commun import configuration_aws, lancer


def preparer_valeurs(existant, saisir=getpass.getpass, desactiver_ocr=False):
    valeurs = dict(existant)
    for cle, libelle in [
        ("openai_api_key", "Clé API OpenAI"),
        ("mistral_api_key", "Clé API Mistral pour les PDF (facultative)"),
        (
            "cle_acces",
            "Clé d’accès au site (au moins 32 caractères, à garder dans votre gestionnaire de mots de passe)",
        ),
    ]:
        if cle == "mistral_api_key" and desactiver_ocr:
            valeurs[cle] = ""
            continue
        valeur = saisir(f"{libelle} [Entrée = conserver] : ").strip()
        valeurs[cle] = valeur or valeurs.get(cle, "")
    if not valeurs["openai_api_key"]:
        raise ValueError("Une clé OpenAI est nécessaire pour le déploiement AWS.")
    if len(valeurs["cle_acces"]) < 32:
        raise ValueError("La clé d’accès au site doit contenir au moins 32 caractères.")
    # Une mise à jour des clés IA ne change jamais silencieusement le mot de passe RDS.
    if existant and not valeurs.get("postgres_mot_de_passe"):
        raise ValueError(
            "Secret existant incomplet : restaurez son mot de passe PostgreSQL avant de continuer."
        )
    valeurs.setdefault("postgres_mot_de_passe", secrets.token_urlsafe(48))
    return valeurs


def principal():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument("--desactiver-ocr", action="store_true")
    options = arguments.parse_args()
    config, session = configuration_aws(champs=("secret_application",))
    client = session.client("secretsmanager")
    try:
        existant = json.loads(client.get_secret_value(SecretId=config["secret_application"])["SecretString"])
    except client.exceptions.ResourceNotFoundException:
        existant = {}
    valeurs = preparer_valeurs(existant, desactiver_ocr=options.desactiver_ocr)
    client.put_secret_value(SecretId=config["secret_application"], SecretString=json.dumps(valeurs))
    print("Secrets enregistrés. Aucune valeur écrite dans le dépôt ou affichée.")
    print("Si le service existe déjà, forcez un nouveau déploiement ECS pour charger les nouvelles clés.")


if __name__ == "__main__":
    lancer(principal)
