import asyncio
import logging
import secrets
from collections import defaultdict, deque
from contextlib import asynccontextmanager, suppress
from time import monotonic

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from application.api.routes import routes
from application.base.connexion import lire, migrer, pool
from application.configuration import configuration
from application.services.travaux import travailler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def duree_de_vie(app):
    await pool.open()
    await pool.wait(timeout=30)
    if configuration().migrer_au_demarrage:
        await migrer()
    travailleur = asyncio.create_task(travailler()) if configuration().executer_indexations else None
    try:
        yield
    finally:
        if travailleur:
            travailleur.cancel()
            with suppress(asyncio.CancelledError):
                await travailleur
        await pool.close()


app = FastAPI(
    title="Atelier RAG",
    description="Un pipeline documentaire explicite, en français.",
    version="1.0.0",
    lifespan=duree_de_vie,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.include_router(routes)
requetes = defaultdict(deque)


@app.middleware("http")
async def protection(request: Request, suivant):
    config = configuration()
    if request.url.path != "/api/sante":
        if config.cle_acces and not secrets.compare_digest(
            request.headers.get("x-cle-acces", "").encode(), config.cle_acces.encode()
        ):
            return JSONResponse({"detail": "Saisissez la clé d’accès de votre atelier."}, status_code=401)
        if request.method in {"POST", "PUT", "DELETE"}:
            # Limite par processus : 30 actions/minute ; chaque tâche Fargate a son compteur.
            cle = "global"
            file = requetes[cle]
            maintenant = monotonic()
            while file and file[0] < maintenant - 60:
                file.popleft()
            if len(file) >= 30:
                return JSONResponse(
                    {"detail": "Limite de 30 actions par minute atteinte."},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            file.append(maintenant)
            taille = request.headers.get("content-length")
            if taille and int(taille) > (config.taille_fichier_mo + 1) * 1024 * 1024:
                return JSONResponse({"detail": "Fichier trop volumineux."}, status_code=413)
    reponse = await suivant(request)
    reponse.headers["X-Content-Type-Options"] = "nosniff"
    reponse.headers["Cache-Control"] = "no-store"
    return reponse


@app.get("/api/sante")
async def sante():
    await lire("SELECT 1")
    return {"statut": "pret", "base": "PostgreSQL + pgvector"}


@app.get("/api/schema")
async def schema():
    return app.openapi()


@app.exception_handler(ValueError)
async def erreur_validation(request, erreur):
    return JSONResponse({"detail": str(erreur)}, status_code=422)


@app.exception_handler(RequestValidationError)
async def champs_invalides(request, erreur):
    champs = sorted({str(e["loc"][-1]) for e in erreur.errors()})
    return JSONResponse(
        {"detail": "Vérifiez les champs suivants et leurs limites : " + ", ".join(champs)}, status_code=422
    )


@app.exception_handler(httpx.HTTPError)
async def erreur_fournisseur(request, erreur):
    logging.getLogger(__name__).warning("appel_externe_echoue type=%s", type(erreur).__name__)
    return JSONResponse(
        {"detail": "Service externe indisponible. Vérifiez l’URL, Ollama ou votre configuration OpenAI."},
        status_code=502,
    )
