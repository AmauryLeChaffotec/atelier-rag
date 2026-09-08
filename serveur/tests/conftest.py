import asyncio
import os
import sys

# Les tests ne doivent jamais utiliser les secrets du .env personnel.
os.environ["MISTRAL_API_KEY"] = ""

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Les tests d’intégration ne touchent jamais la bibliothèque personnelle.
if os.environ.get("DATABASE_URL_TEST"):
    if not os.environ["DATABASE_URL_TEST"].split("?")[0].endswith("/atelier_tests"):
        raise RuntimeError("Les tests exigent une base dédiée nommée atelier_tests.")
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_TEST"]
