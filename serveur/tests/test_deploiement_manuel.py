"""Contrats ECS et garde-fous du carnet manuel, sans connexion à AWS."""

import json
import sys
from pathlib import Path
from unittest.mock import Mock

import botocore.session
import pytest
from botocore.validate import validate_parameters
from psycopg.conninfo import conninfo_to_dict

from application.configuration import Configuration

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "aws"))
import commun

RACINE = Path(__file__).resolve().parents[2]


def test_carnet_progressif_et_bom_powershell(tmp_path):
    chemin = tmp_path / "configuration.json"
    carnet = {"compte": "123456789012", "region": "eu-west-3", "secret_application": ""}
    chemin.write_text(json.dumps(carnet), encoding="utf-8-sig")
    assert commun.lire_configuration(chemin) == carnet
    with pytest.raises(ValueError, match="secret_application"):
        commun.lire_configuration(chemin, champs=("secret_application",))


@pytest.mark.parametrize("compte", ["VOTRE_COMPTE_12_CHIFFRES", 123456789012, "١٢٣٤٥٦٧٨٩٠١٢", "123"])
def test_carnet_refuse_compte_inexploitable(tmp_path, compte):
    chemin = tmp_path / "configuration.json"
    chemin.write_text(json.dumps({"compte": compte, "region": "eu-west-3"}), encoding="utf-8")
    with pytest.raises(ValueError, match="12 chiffres"):
        commun.lire_configuration(chemin)


def test_carnet_absent_indique_quel_exemple_copier(tmp_path):
    with pytest.raises(RuntimeError, match="deploiement/aws/configuration.exemple.json"):
        commun.lire_configuration(tmp_path / "absent.json")


def test_mauvais_compte_bloque_avant_toute_action(monkeypatch):
    session = Mock()
    session.client.return_value.get_caller_identity.return_value = {"Account": "999999999999"}
    monkeypatch.setattr(commun.boto3, "Session", Mock(return_value=session))
    monkeypatch.setattr(
        commun, "lire_configuration", lambda **_: {"compte": "123456789012", "region": "eu-west-3"}
    )
    with pytest.raises(RuntimeError, match="diffère"):
        commun.configuration_aws()
    # Seule l'identité a été lue ; aucun client de mutation n'a été demandé.
    session.client.assert_called_once_with("sts")
    session.client.return_value.get_caller_identity.assert_called_once_with()


def charger_tache(nom):
    contenu = (RACINE / "deploiement" / "aws" / f"tache-{nom}.exemple.json").read_text(encoding="utf-8")
    substitutions = {
        "COMPTE_AWS": "123456789012",
        "URI_IMAGE_SERVEUR": "123456789012.dkr.ecr.eu-west-3.amazonaws.com/atelier-rag/serveur:essai",
        "URI_IMAGE_INTERFACE": "123456789012.dkr.ecr.eu-west-3.amazonaws.com/atelier-rag/interface:essai",
        "HOTE_RDS": "atelier-rag.exemple.eu-west-3.rds.amazonaws.com",
        "NOM_BUCKET_DOCUMENTS": "atelier-rag-exemple-documents",
        "ARN_SECRET_RDS": "arn:aws:secretsmanager:eu-west-3:123456789012:secret:rds-exemple-abcdef",
        "ARN_SECRET_APPLICATION": "arn:aws:secretsmanager:eu-west-3:123456789012:secret:atelier-exemple-abcdef",
    }
    for marqueur, valeur in substitutions.items():
        contenu = contenu.replace(marqueur, valeur)
    return json.loads(contenu)


@pytest.mark.parametrize("nom", ["preparation", "application"])
def test_definitions_conformes_au_contrat_api_ecs(nom):
    # Lecture du modèle embarqué dans botocore : aucun client ni requête réseau.
    forme = (
        botocore.session.get_session()
        .get_service_model("ecs")
        .operation_model("RegisterTaskDefinition")
        .input_shape
    )
    tache = charger_tache(nom)
    validate_parameters(tache, forme)
    assert tache["requiresCompatibilities"] == ["FARGATE"]
    assert tache["networkMode"] == "awsvpc"
    assert sum(c.get("memory", 0) for c in tache["containerDefinitions"]) <= int(tache["memory"])
    for conteneur in tache["containerDefinitions"]:
        valeurs = {v["name"]: v["value"] for v in conteneur.get("environment", [])}
        assert (
            not {"OPENAI_API_KEY", "MISTRAL_API_KEY", "POSTGRES_MOT_DE_PASSE", "CLE_ACCES"} & valeurs.keys()
        )
        for secret in conteneur.get("secrets", []):
            assert secret["valueFrom"].startswith("arn:aws:secretsmanager:")
            assert secret["valueFrom"].endswith("::")


def test_tache_applicative_utilise_configuration_reelle_et_isole_administrateur():
    tache = charger_tache("application")
    serveur, interface = tache["containerDefinitions"]
    env = {v["name"].lower(): v["value"] for v in serveur["environment"]}
    # Valeurs fictives à la place de l'injection Secrets Manager, jamais le .env privé.
    env.update({s["name"].lower(): "x" * 40 for s in serveur["secrets"]})
    assert set(env) <= Configuration.model_fields.keys()
    config = Configuration(_env_file=None, **env)
    connexion = conninfo_to_dict(config.connexion_postgres)
    assert config.fournisseur_ia == "openai" and config.stockage == "s3"
    assert not config.migrer_au_demarrage and config.executer_indexations
    assert connexion["user"] == "atelier" and connexion["sslmode"] == "verify-full"
    certificat = RACINE / "serveur" / connexion["sslrootcert"].removeprefix("/projet/")
    assert certificat.is_file()
    assert "rds-exemple" not in json.dumps(tache)
    assert "preparation" not in tache["executionRoleArn"]
    assert not interface.get("secrets")
    assert {v["name"]: v["value"] for v in interface["environment"]}["API_INTERNE"] == "http://127.0.0.1:8000"


def test_preparation_ponctuelle_ne_recoit_pas_role_applicatif():
    tache = charger_tache("preparation")
    assert "taskRoleArn" not in tache
    conteneur = tache["containerDefinitions"][0]
    assert conteneur["command"][-1] == "application.base.preparer"
    secrets = {s["name"]: s["valueFrom"] for s in conteneur["secrets"]}
    assert "rds-exemple" in secrets["POSTGRES_MOT_DE_PASSE"]
    assert "atelier-exemple" in secrets["MOT_DE_PASSE_APPLICATION"]
