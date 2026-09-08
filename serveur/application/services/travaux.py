"""Petite file durable dans PostgreSQL : réservation, bail renouvelé et reprise après arrêt."""

import asyncio
import logging
from contextlib import suppress
from uuid import uuid4

from application.base.connexion import pool
from application.configuration import configuration
from application.services.indexation import indexer

logger = logging.getLogger(__name__)


async def prendre():
    async with pool.connection() as connexion:
        # Une machine qui disparaît trois fois ne doit pas laisser un document bloqué indéfiniment.
        await connexion.execute("""WITH abandonnes AS (
            UPDATE travaux_indexation SET statut='erreur',expire_le=NULL
            WHERE statut='en_cours' AND expire_le<=now() AND tentatives>=3 RETURNING document_id
        ) UPDATE documents SET statut='erreur',erreur='Indexation interrompue trois fois. Relancez-la.'
        WHERE id IN (SELECT document_id FROM abandonnes)""")
        curseur = await connexion.execute(
            """WITH candidat AS (
            SELECT id FROM travaux_indexation
            WHERE statut='attente' OR (statut='en_cours' AND expire_le<=now() AND tentatives<3)
            ORDER BY cree_le FOR UPDATE SKIP LOCKED LIMIT 1
        ) UPDATE travaux_indexation t SET statut='en_cours',proprietaire=%s,
            expire_le=now()+make_interval(secs => %s),tentatives=tentatives+1
        FROM candidat c WHERE t.id=c.id RETURNING t.*""",
            (uuid4(), configuration().bail_indexation_secondes),
        )
        return await curseur.fetchone()


async def renouveler(travail):
    async with pool.connection() as connexion:
        curseur = await connexion.execute(
            """UPDATE travaux_indexation
            SET expire_le=now()+make_interval(secs => %s)
            WHERE id=%s AND proprietaire=%s AND statut='en_cours' AND expire_le>now() RETURNING id""",
            (configuration().bail_indexation_secondes, travail["id"], travail["proprietaire"]),
        )
        return bool(await curseur.fetchone())


async def abandonner(travail, erreur=False):
    async with pool.connection() as connexion:
        curseur = await connexion.execute(
            """UPDATE travaux_indexation
            SET statut=%s,proprietaire=NULL,expire_le=NULL
            WHERE id=%s AND proprietaire=%s AND statut='en_cours' AND expire_le>now() RETURNING document_id""",
            ("erreur" if erreur else "attente", travail["id"], travail["proprietaire"]),
        )
        resultat = await curseur.fetchone()
        if erreur and resultat:
            await connexion.execute(
                """UPDATE documents SET statut='erreur',
                erreur='Indexation échouée. Vérifiez le fournisseur IA puis relancez-la.' WHERE id=%s""",
                (resultat["document_id"],),
            )


async def surveiller_bail(travail):
    while True:
        await asyncio.sleep(configuration().bail_indexation_secondes / 3)
        if not await renouveler(travail):
            raise RuntimeError("Bail d’indexation perdu.")


async def traiter_suivant():
    travail = await prendre()
    if not travail:
        return False
    traitement = asyncio.create_task(indexer(travail))
    surveillance = asyncio.create_task(surveiller_bail(travail))
    try:
        termines, _ = await asyncio.wait([traitement, surveillance], return_when=asyncio.FIRST_COMPLETED)
        for termine in termines:
            await termine
    except asyncio.CancelledError:
        # Arrêt gracieux ECS : remise en attente. Arrêt brutal : reprise à expiration du bail.
        traitement.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await traitement
        await abandonner(travail)
        raise
    except Exception as erreur:
        traitement.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await traitement
        logger.error("indexation_echouee travail=%s type=%s", travail["id"], type(erreur).__name__)
        await abandonner(travail, erreur=True)
    finally:
        surveillance.cancel()
        with suppress(asyncio.CancelledError, Exception):
            await surveillance
    return True


async def travailler():
    while True:
        try:
            if await traiter_suivant():
                continue
        except asyncio.CancelledError:
            raise
        except Exception as erreur:
            logger.error("file_indexation_indisponible type=%s", type(erreur).__name__)
        await asyncio.sleep(configuration().intervalle_indexation_secondes)
