"""Tâche ECS ponctuelle : préparer le rôle applicatif, pgvector et les migrations."""

import asyncio
import os

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from application.base.connexion import migrer
from application.configuration import configuration


async def preparer():
    config = configuration()
    mot_de_passe = os.environ["MOT_DE_PASSE_APPLICATION"]
    if len(mot_de_passe) < 32:
        raise ValueError("Le mot de passe applicatif doit contenir au moins 32 caractères.")
    async with await psycopg.AsyncConnection.connect(config.connexion_postgres, autocommit=True) as connexion:
        await connexion.execute("SELECT pg_advisory_lock(748591)")
        existe = await (await connexion.execute("SELECT 1 FROM pg_roles WHERE rolname='atelier'")).fetchone()
        if not existe:
            await connexion.execute(
                "CREATE ROLE atelier LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION"
            )
        await connexion.execute(sql.SQL("ALTER ROLE atelier PASSWORD {}").format(sql.Literal(mot_de_passe)))
        await connexion.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await connexion.execute("GRANT USAGE, CREATE ON SCHEMA public TO atelier")
        await connexion.execute(
            sql.SQL("GRANT CONNECT ON DATABASE {} TO atelier").format(sql.Identifier(config.postgres_base))
        )
        await connexion.execute("SELECT pg_advisory_unlock(748591)")
    # Les tables appartiennent au rôle applicatif, jamais au compte administrateur RDS.
    connexion_application = make_conninfo(config.connexion_postgres, user="atelier", password=mot_de_passe)
    async with AsyncConnectionPool(
        connexion_application, open=False, kwargs={"row_factory": dict_row}
    ) as connexions:
        await connexions.wait()
        await migrer(connexions)
    print("Rôle applicatif, extension pgvector et migrations prêts.")


if __name__ == "__main__":
    asyncio.run(preparer())
