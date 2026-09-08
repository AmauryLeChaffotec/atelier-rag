from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from application.configuration import configuration

pool = AsyncConnectionPool(
    configuration().connexion_postgres, open=False, min_size=1, max_size=5, kwargs={"row_factory": dict_row}
)


async def migrer(connexions=None):
    """Migrations SQL ordonnées, transactionnelles, protégées par un verrou PostgreSQL."""
    async with (connexions or pool).connection() as connexion:
        await connexion.execute("SELECT pg_advisory_xact_lock(748592)")
        await connexion.execute("CREATE TABLE IF NOT EXISTS migrations (nom text PRIMARY KEY)")
        for fichier in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
            curseur = await connexion.execute("SELECT nom FROM migrations WHERE nom=%s", (fichier.name,))
            if not await curseur.fetchone():
                await connexion.execute(fichier.read_text(encoding="utf-8"))
                await connexion.execute("INSERT INTO migrations VALUES (%s)", (fichier.name,))


async def lire(sql, parametres=(), unique=False):
    async with pool.connection() as connexion:
        curseur = await connexion.execute(sql, parametres)
        return await curseur.fetchone() if unique else await curseur.fetchall()


async def executer(sql, parametres=()):
    async with pool.connection() as connexion:
        await connexion.execute(sql, parametres)
