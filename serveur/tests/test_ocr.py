import base64
import json

import httpx
import pytest
from fastapi import HTTPException

from application.configuration import configuration
from application.services.ocr import appeler_mistral, sections_ocr


async def test_contrat_ocr_pdf_pages_et_secret_uniquement_dans_header(monkeypatch):
    monkeypatch.setattr(configuration(), "mistral_api_key", "secret-test-simule")

    def repondre(requete):
        assert str(requete.url) == "https://api.mistral.ai/v1/ocr"
        assert requete.headers["authorization"] == "Bearer secret-test-simule"
        corps = json.loads(requete.content)
        assert corps["model"] == "mistral-ocr-latest"
        assert corps["pages"] == [0, 2]
        assert base64.b64decode(corps["document"]["document_url"].split(",")[1]) == b"PDF de test"
        assert "secret-test" not in str(corps)
        return httpx.Response(
            200,
            json={
                "model": "ocr-version-test",
                "pages": [
                    {"index": 0, "markdown": "# Page un\nTexte"},
                    {"index": 2, "markdown": "Page trois"},
                ],
            },
        )

    client_original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **options: client_original(**options, transport=httpx.MockTransport(repondre)),
    )
    resultat = await appeler_mistral(b"PDF de test", [1, 3])
    assert resultat["pages"]["3"] == "Page trois"


@pytest.mark.parametrize("statut", [401, 403, 429])
async def test_erreurs_ocr_sans_exposer_la_reponse_du_fournisseur(statut, monkeypatch):
    monkeypatch.setattr(configuration(), "mistral_api_key", "secret-test-simule")
    client_original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **options: client_original(
            **options,
            transport=httpx.MockTransport(
                lambda r: httpx.Response(statut, text="detail prive du fournisseur")
            ),
        ),
    )
    with pytest.raises(HTTPException) as erreur:
        await appeler_mistral(b"PDF de test", [1])
    assert "detail prive" not in erreur.value.detail


def test_ocr_conserve_pages_non_selectionnees_structure_et_description():
    document = {
        "id": "exemple",
        "sections": [
            {
                "page": 1,
                "contenu": "Texte initial",
                "visuel": "exemple/page-1.png",
                "description_visuelle": "Une flèche relie deux étapes.",
            },
            {"page": 2, "contenu": "Page non sélectionnée", "visuel": None},
        ],
    }
    cache = {
        "modele": "ocr-test",
        "pages": {
            "1": "# Titre\n\n## Section\n\nTexte reconnu.\n\n```python\nprint('bonjour')\n```\n\n![image](image.jpeg)"
        },
    }
    sections = sections_ocr(document, cache, [1])
    assert sections[-1]["contenu"] == "Page non sélectionnée"
    assert any(s["titres"] == ["Titre", "Section"] and s["type_contenu"] == "code" for s in sections[:-1])
    assert any(s.get("description_visuelle") for s in sections)
    assert all(s.get("visuel") == "exemple/page-1.png" for s in sections[:-1])
