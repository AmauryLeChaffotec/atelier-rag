"""Garanties nécessaires lorsque ECS remplace une tâche, sans appel AWS ou IA payant."""

import asyncio
import io
import os
from uuid import uuid4

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber
from fastapi import HTTPException
from psycopg.conninfo import conninfo_to_dict
from psycopg.types.json import Jsonb

from test_integration import connexions_par_test as connexions_par_test

integration = pytest.mark.skipif(not os.environ.get("DATABASE_URL_TEST"), reason="DATABASE_URL_TEST absent")


@pytest.fixture
async def document_en_attente(connexions_par_test):
    from application.base.connexion import pool
    from application.configuration import configuration
    from application.principal import app

    identifiant, technologie = uuid4(), "Reprise-" + str(uuid4())
    chunks = [{"id": str(uuid4()), "contenu": "Un index complet", "metadata": {}}]
    async with app.router.lifespan_context(app):
        async with pool.connection() as connexion:
            await connexion.execute("INSERT INTO technologies VALUES (%s,'1')", (technologie,))
            await connexion.execute(
                """INSERT INTO documents (id,titre,technologie,version,type_source,cle_fichier,sections,statut)
                VALUES (%s,'Reprise',%s,'1','fichier','test.md','[]','indexation')""",
                (identifiant, technologie),
            )
            await connexion.execute(
                """INSERT INTO travaux_indexation (id,document_id,revision,chunks,espace_embedding)
                VALUES (%s,%s,1,%s,%s)""",
                (uuid4(), identifiant, Jsonb(chunks), configuration().espace_embedding),
            )
        try:
            yield identifiant
        finally:
            async with pool.connection() as connexion:
                await connexion.execute("DELETE FROM documents WHERE id=%s", (identifiant,))
                await connexion.execute("DELETE FROM technologies WHERE nom=%s", (technologie,))


@integration
async def test_bail_exclusif_reprise_et_ancien_traitement_refuse(document_en_attente):
    from application.base.connexion import lire, migrer, pool
    from application.services.indexation import enregistrer_index
    from application.services.travaux import prendre, renouveler

    premier = await prendre()
    assert premier["document_id"] == document_en_attente
    assert await prendre() is None
    assert await renouveler(premier)
    await migrer()  # Un autre démarrage ne doit pas annuler les travaux de la première tâche.
    assert (await lire("SELECT statut FROM documents WHERE id=%s", (document_en_attente,)))[0][
        "statut"
    ] == "indexation"
    async with pool.connection() as connexion:
        await connexion.execute(
            "UPDATE travaux_indexation SET expire_le=now()-interval '1 second' WHERE id=%s", (premier["id"],)
        )
    assert not await renouveler(premier)
    second = await prendre()
    assert second["proprietaire"] != premier["proprietaire"] and second["tentatives"] == 2
    assert await enregistrer_index(second, [[1.0, 0.0]])
    assert not await enregistrer_index(premier, [[0.0, 1.0]])
    assert (await lire("SELECT embedding::text FROM chunks WHERE document_id=%s", (document_en_attente,)))[0][
        "embedding"
    ] == "[1,0]"


@integration
async def test_arret_gracieux_remet_en_attente(document_en_attente, monkeypatch):
    from application.base.connexion import lire
    from application.services import travaux

    demarre = asyncio.Event()

    async def long_traitement(travail):
        demarre.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(travaux, "indexer", long_traitement)
    tache = asyncio.create_task(travaux.traiter_suivant())
    await asyncio.wait_for(demarre.wait(), timeout=5)
    tache.cancel()
    with pytest.raises(asyncio.CancelledError):
        await tache
    assert (await lire("SELECT statut FROM travaux_indexation WHERE document_id=%s", (document_en_attente,)))[
        0
    ]["statut"] == "attente"
    assert (await travaux.prendre())["tentatives"] == 2


@integration
async def test_trois_interruptions_liberent_document(document_en_attente):
    from application.base.connexion import lire, pool
    from application.services.travaux import prendre

    for tentative in range(1, 4):
        travail = await prendre()
        assert travail["tentatives"] == tentative
        async with pool.connection() as connexion:
            await connexion.execute(
                "UPDATE travaux_indexation SET expire_le=now()-interval '1 second' WHERE id=%s",
                (travail["id"],),
            )
    assert await prendre() is None
    assert (await lire("SELECT statut FROM documents WHERE id=%s", (document_en_attente,)))[0][
        "statut"
    ] == "erreur"


@integration
async def test_verrou_ocr_ou_chat_commun_aux_processus(document_en_attente):
    from application.base.verrous import verrou_operation

    nom = f"ocr:{document_en_attente}"
    async with verrou_operation(nom):
        with pytest.raises(HTTPException) as erreur:
            async with verrou_operation(nom):
                pytest.fail("Un deuxième processus a obtenu le même verrou.")
        assert erreur.value.status_code == 409
    async with verrou_operation(nom):
        pass


def test_connexion_rds_echappe_secret_et_verifie_certificat():
    from application.configuration import Configuration

    secret = "avec ' apostrophe \\ espaces @:/?"
    config = Configuration(
        _env_file=None, postgres_hote="base.rds.amazonaws.com", postgres_mot_de_passe=secret
    )
    valeurs = conninfo_to_dict(config.connexion_postgres)
    assert valeurs["password"] == secret
    assert valeurs["sslmode"] == "verify-full"
    assert valeurs["sslrootcert"].endswith("certificats/rds.pem")
    assert secret not in repr(config)


def test_stockage_s3_prive_contrat_lecture_ecriture_suppression(monkeypatch):
    from application.configuration import configuration
    from application.services import stockage

    client = boto3.client(
        "s3", region_name="eu-west-3", aws_access_key_id="test", aws_secret_access_key="test"
    )
    monkeypatch.setattr(configuration(), "stockage", "s3")
    monkeypatch.setattr(configuration(), "s3_bucket", "bucket-test")

    def client_du_role(service, **options):
        assert service == "s3" and set(options) == {"region_name"}
        return client  # En production : chaîne standard boto3, donc rôle IAM de la tâche.

    monkeypatch.setattr(stockage.boto3, "client", client_du_role)
    with Stubber(client) as bouchon:
        bouchon.add_response(
            "put_object",
            {},
            {
                "Bucket": "bucket-test",
                "Key": "document.pdf",
                "Body": b"PDF",
                "ContentType": "application/pdf",
                "ServerSideEncryption": "AES256",
            },
        )
        bouchon.add_response(
            "get_object",
            {"Body": StreamingBody(io.BytesIO(b"PDF"), 3)},
            {"Bucket": "bucket-test", "Key": "document.pdf"},
        )
        bouchon.add_response("delete_object", {}, {"Bucket": "bucket-test", "Key": "document.pdf"})
        stockage.enregistrer("document.pdf", b"PDF", "application/pdf")
        assert stockage.lire_fichier("document.pdf") == b"PDF"
        stockage.supprimer("document.pdf")
        bouchon.assert_no_pending_responses()
