"""API + vrai PostgreSQL/pgvector. IA déterministe injectée pour ne rien facturer."""

import os
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("DATABASE_URL_TEST"), reason="DATABASE_URL_TEST absent")


@pytest.fixture(autouse=True)
def connexions_par_test(monkeypatch):
    """Chaque démarrage FastAPI reçoit un pool neuf sur sa propre boucle asyncio."""
    import sys

    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    from application import principal  # Charge les modules qui partagent le pool.

    ancien = principal.pool
    nouveau = AsyncConnectionPool(
        os.environ["DATABASE_URL_TEST"], open=False, min_size=1, max_size=3, kwargs={"row_factory": dict_row}
    )
    for nom, module in list(sys.modules.items()):
        if nom.startswith("application.") and getattr(module, "pool", None) is ancien:
            monkeypatch.setattr(module, "pool", nouveau)


async def test_parcours_api_pgvector_versions_reindexation_et_historique(monkeypatch, tmp_path):
    from application.base.connexion import lire
    from application.configuration import configuration
    from application.ia.fournisseur import FournisseurIA
    from application.principal import app, requetes

    monkeypatch.setattr(configuration(), "repertoire_fichiers", str(tmp_path))

    async def embeddings(self, textes, question=False):
        return [[1.0, 0.0, 0.0] for _ in textes]

    async def generer(self, messages, image=None, format_json=False):
        self.usage = {"entree": 10, "sortie": 5}
        yield "Le bloc with libère la ressource [1]."

    monkeypatch.setattr(FournisseurIA, "embeddings", embeddings)
    monkeypatch.setattr(FournisseurIA, "generer", generer)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://atelier.test"
        ) as client:
            requetes.clear()
            assert (await client.get("/api/sante")).status_code == 200
            technologie = "Python-test-" + str(uuid4())[:8]
            ids = []
            for version in ["3.13", "3.14"]:
                r = await client.post(
                    "/api/documents/fichier",
                    data={"titre": "Context managers", "technologie": technologie, "version": version},
                    files={
                        "fichier": (
                            "guide.md",
                            b"# Ressources\n\nLe bloc with libere la ressource.",
                            "text/markdown",
                        )
                    },
                )
                assert r.status_code == 201, r.text
                document = r.json()
                ids.append(document["id"])
                r = await client.post(
                    f"/api/documents/{document['id']}/apercu", json={"revision": 1, "parametres": {}}
                )
                assert r.status_code == 200, r.text
                apercu = r.json()
                r = await client.post(
                    f"/api/documents/{document['id']}/indexation",
                    json={"revision": apercu["revision"], "chunks": apercu["chunks"]},
                )
                assert r.status_code == 202, r.text
                assert (await client.get(f"/api/documents/{document['id']}")).json()["statut"] == "indexe"
            demande = {"question": "Comment gérer une ressource ?", "technologie": technologie, "seuil": 0.9}
            r = await client.post("/api/retrieval", json=demande)
            assert r.status_code == 200, r.text
            assert {c["metadata"]["version"] for c in r.json()["resultats"]} == {"3.13"}
            await client.put(f"/api/technologies/{technologie}/version-courante", json={"version": "3.14"})
            r = await client.post("/api/retrieval", json=demande)
            assert {c["metadata"]["version"] for c in r.json()["resultats"]} == {"3.14"}
            assert r.json()["resultats"][0]["score"] == 1.0
            r = await client.post("/api/retrieval", json={**demande, "metadata": {"page": 999}})
            assert r.json()["resultats"] == []
            r = await client.post("/api/retrieval", json={**demande, "version": "3.13"})
            assert r.json()["resultats"][0]["metadata"]["version"] == "3.13"
            r = await client.post("/api/retrieval", json={**demande, "technologie": "' OR TRUE --"})
            assert r.json()["resultats"] == []
            r = await client.post("/api/chat", json=demande)
            assert "event: fin" in r.text and "[1]" in r.text, r.text
            execution = (await lire("SELECT * FROM executions_retrieval ORDER BY cree_le DESC LIMIT 1"))[0]
            assert execution["trace"]["sources"][0]["metadata"]["version"] == "3.14"
            conversation_id = execution["conversation_id"]
            r = await client.get(f"/api/conversations/{conversation_id}")
            assert [m["role"] for m in r.json()] == ["user", "assistant"]
            # Le changement de fournisseur exclut l’ancien espace, même à dimension identique.
            monkeypatch.setattr(configuration(), "fournisseur_ia", "openai")
            r = await client.post("/api/retrieval", json=demande)
            assert r.json()["resultats"] == []
            monkeypatch.setattr(configuration(), "fournisseur_ia", "ollama")
            # Un échec d’indexation ne détruit jamais les anciens vecteurs.
            document = (await client.get(f"/api/documents/{ids[1]}")).json()

            async def echouer(*args, **kwargs):
                raise RuntimeError("Fournisseur indisponible")

            monkeypatch.setattr(FournisseurIA, "embeddings", echouer)
            r = await client.post(
                f"/api/documents/{ids[1]}/indexation",
                json={"revision": document["revision"], "chunks": document["brouillon"]},
            )
            assert r.status_code == 202
            assert len(await lire("SELECT id FROM chunks WHERE document_id=%s", (ids[1],))) == 1
            monkeypatch.setattr(FournisseurIA, "embeddings", embeddings)
            for identifiant in ids:
                assert (await client.delete(f"/api/documents/{identifiant}")).status_code == 204
            # Les sources des anciennes réponses sont des instantanés autonomes.
            r = await client.get(f"/api/executions/{execution['id']}")
            assert "with" in r.json()["sources"][0]["contenu"]
            monkeypatch.setattr(configuration(), "cle_acces", "protection-pour-test")
            assert (await client.get("/api/documents")).status_code == 401
            assert (
                await client.get("/api/documents", headers={"x-cle-acces": "protection-pour-test"})
            ).status_code == 200


async def test_visuel_propose_sans_enregistrer_et_validation_conserve_texte(monkeypatch, tmp_path):
    import pymupdf

    from application.configuration import configuration
    from application.ia.fournisseur import FournisseurIA
    from application.principal import app, requetes

    monkeypatch.setattr(configuration(), "repertoire_fichiers", str(tmp_path))

    async def texte(self, messages, image=None, format_json=False):
        assert image.startswith(b"\x89PNG")
        return "Je ne vois aucune image."  # Une erreur du modèle ne devient pas une source.

    monkeypatch.setattr(FournisseurIA, "texte", texte)
    with pymupdf.open() as pdf:
        page = pdf.new_page()
        page.insert_text((40, 40), "Texte original du document")
        page.draw_rect(pymupdf.Rect(50, 80, 200, 180))
        contenu = pdf.tobytes()
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://atelier.test"
        ) as client:
            requetes.clear()
            r = await client.post(
                "/api/documents/fichier",
                data={"titre": "Un schema", "technologie": "Visuel-test", "version": "1"},
                files={"fichier": ("schema.pdf", contenu, "application/pdf")},
            )
            assert r.status_code == 201, r.text
            identifiant = r.json()["id"]
            chemin = f"/api/documents/{identifiant}"
            avant = (await client.get(chemin)).json()
            proposition = await client.post(chemin + "/visuels/1/description")
            assert proposition.status_code == 200, proposition.text
            apres = (await client.get(chemin)).json()
            assert avant["sections"] == apres["sections"] and avant["revision"] == apres["revision"]
            r = await client.put(
                chemin + "/visuels/1/description",
                json={"revision": avant["revision"], "description": "Un rectangle représente un document."},
            )
            assert r.status_code == 200, r.text
            enregistre = (await client.get(chemin)).json()
            assert "Texte original" in enregistre["sections"][0]["contenu"]
            assert "Un rectangle" in enregistre["sections"][0]["contenu"]
            assert "aucune image" not in enregistre["sections"][0]["contenu"]
            assert enregistre["sections"][0]["visuel"]
            assert (
                await client.put(
                    chemin + "/visuels/1/description",
                    json={"revision": avant["revision"], "description": "Description devenue obsolète"},
                )
            ).status_code == 409
            assert (await client.delete(chemin)).status_code == 204


async def test_ocr_cache_et_revision_evitent_double_facturation(monkeypatch, tmp_path):
    import pymupdf
    from application.configuration import configuration
    from application.principal import app, requetes
    from application.services import ocr

    monkeypatch.setattr(configuration(), "repertoire_fichiers", str(tmp_path))
    appels = []

    async def mistral(pdf, pages):
        appels.append(pages)
        return {
            "modele": "ocr-test",
            "pages": {str(p): f"# Page {p}\n\nTexte reconnu pour la page {p}." for p in pages},
        }

    monkeypatch.setattr(ocr, "appeler_mistral", mistral)
    with pymupdf.open() as pdf:
        for _ in range(2):
            pdf.new_page().insert_text((40, 40), "Texte initial du PDF")
        contenu = pdf.tobytes()
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://atelier.test"
        ) as client:
            requetes.clear()
            r = await client.post(
                "/api/documents/fichier",
                data={"titre": "OCR test", "technologie": "OCR-test", "version": "1"},
                files={"fichier": ("lecture.pdf", contenu, "application/pdf")},
            )
            assert r.status_code == 201, r.text
            chemin = f"/api/documents/{r.json()['id']}"
            r = await client.post(chemin + "/ocr", json={"revision": 1, "pages": [1]})
            assert r.status_code == 200, r.text
            assert r.json()["pages_envoyees"] == 1
            doc = (await client.get(chemin)).json()
            assert doc["sections"][-1]["contenu"] == "Texte initial du PDF"
            assert (await client.post(chemin + "/ocr", json={"revision": 1, "pages": [2]})).status_code == 409
            r = await client.post(chemin + "/ocr", json={"revision": doc["revision"], "pages": [1, 2]})
            assert r.status_code == 200, r.text
            assert r.json()["pages_en_cache"] == 1 and r.json()["pages_envoyees"] == 1
            r = await client.post(chemin + "/ocr", json={"revision": r.json()["revision"], "pages": [1, 2]})
            assert r.status_code == 200 and r.json()["pages_envoyees"] == 0
            assert appels == [[1], [2]]
            assert (await client.delete(chemin)).status_code == 204
