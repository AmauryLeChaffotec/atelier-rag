"""Éviter une rotation de mot de passe accidentelle ou un déploiement après migration échouée."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "aws"))
from configurer_secrets import preparer_valeurs
from preparer_base import verifier_resultat


def test_actualiser_cles_conserve_mot_de_passe_base():
    valeurs = {
        "openai_api_key": "ancienne",
        "mistral_api_key": "ocr",
        "cle_acces": "a" * 32,
        "postgres_mot_de_passe": "b" * 48,
    }
    reponses = iter(["nouvelle", "", ""])
    resultat = preparer_valeurs(valeurs, saisir=lambda _: next(reponses))
    assert resultat == {**valeurs, "openai_api_key": "nouvelle"}


def test_secret_initial_complet_et_secret_abime_refuse():
    reponses = iter(["cle-test", "", "a" * 32])
    resultat = preparer_valeurs({}, saisir=lambda _: next(reponses))
    assert len(resultat["postgres_mot_de_passe"]) >= 32 and resultat["mistral_api_key"] == ""
    with pytest.raises(ValueError, match="incomplet"):
        preparer_valeurs({"openai_api_key": "test", "cle_acces": "a" * 32}, saisir=lambda _: "")


@pytest.mark.parametrize(
    "reponse",
    [
        {"tasks": []},
        {"tasks": [{"containers": [{"exitCode": 1}]}]},
        {"tasks": [{"containers": [{}]}]},
        {"tasks": [{"containers": [{"exitCode": 0}]}], "failures": [{"reason": "MISSING"}]},
    ],
)
def test_preparation_non_reussie_bloque_la_suite(reponse):
    with pytest.raises(RuntimeError):
        verifier_resultat(reponse)


def test_preparation_code_zero_autorise_la_suite():
    verifier_resultat({"tasks": [{"containers": [{"exitCode": 0}]}]})
