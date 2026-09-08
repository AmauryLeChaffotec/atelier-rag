"""Un verrou de session PostgreSQL est partagé par toutes les tâches ECS."""

from contextlib import asynccontextmanager

import psycopg
from fastapi import HTTPException

from application.configuration import configuration


@asynccontextmanager
async def verrou_operation(nom: str):
    # Connexion dédiée : ne jamais remettre un verrou de session dans le pool.
    async with await psycopg.AsyncConnection.connect(
        configuration().connexion_postgres, autocommit=True
    ) as connexion:
        curseur = await connexion.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (nom,))
        if not (await curseur.fetchone())[0]:
            raise HTTPException(409, "Cette opération est déjà en cours. Patientez puis réessayez.")
        try:
            yield
        finally:
            await connexion.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (nom,))
