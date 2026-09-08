import json

import httpx
import pytest

from application.configuration import Configuration
from application.ia.fournisseur import FournisseurIA


@pytest.mark.parametrize("fournisseur", ["ollama", "openai"])
async def test_contrat_embedding_et_streaming(fournisseur, monkeypatch):
    config = Configuration(_env_file=None, fournisseur_ia=fournisseur, openai_api_key="factice-test")
    ia = FournisseurIA(config)

    def repondre(requete):
        donnees = json.loads(requete.content)
        if "embed" in requete.url.path:
            assert donnees["model"] == config.modele_embedding
            if fournisseur == "ollama":
                assert "Instruct:" in donnees["input"][0]
                return httpx.Response(200, json={"embeddings": [[1, 0, 0]]})
            assert requete.headers["authorization"] == "Bearer factice-test"
            return httpx.Response(200, json={"data": [{"index": 0, "embedding": [1, 0, 0]}]})
        assert donnees["stream"] is True
        if fournisseur == "ollama":
            return httpx.Response(
                200,
                text='{"message":{"content":"Bonjour"}}\n{"done":true,"eval_count":2,"prompt_eval_count":8}\n',
            )
        return httpx.Response(
            200,
            text='data: {"choices":[{"delta":{"content":"Bonjour"}}]}\n\ndata: {"choices":[],"usage":{"prompt_tokens":8,"completion_tokens":2}}\n\ndata: [DONE]\n\n',
        )

    client_original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **options: client_original(**options, transport=httpx.MockTransport(repondre)),
    )
    assert await ia.embeddings(["Question"], question=True) == [[1, 0, 0]]
    assert await ia.texte([{"role": "user", "content": "Bonjour"}]) == "Bonjour"
    assert ia.usage == {"entree": 8, "sortie": 2}


@pytest.mark.parametrize("fournisseur", ["ollama", "openai"])
async def test_contrat_image_et_sortie_json(fournisseur, monkeypatch):
    import base64

    config = Configuration(_env_file=None, fournisseur_ia=fournisseur, openai_api_key="factice-test")
    ia = FournisseurIA(config)
    image = b"octets-png-pour-verifier-le-transport"

    def repondre(requete):
        corps = json.loads(requete.content)
        if fournisseur == "ollama":
            assert corps["format"] == "json"
            assert base64.b64decode(corps["messages"][-1]["images"][0]) == image
            return httpx.Response(200, text='{"message":{"content":"{}"}}\n{"done":true}\n')
        assert corps["response_format"] == {"type": "json_object"}
        contenu = corps["messages"][-1]["content"]
        assert contenu[0] == {"type": "text", "text": "Retourne un objet JSON."}
        assert base64.b64decode(contenu[1]["image_url"]["url"].split(",", 1)[1]) == image
        return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"{}"}}]}\n\ndata: [DONE]\n\n')

    client_original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **options: client_original(**options, transport=httpx.MockTransport(repondre)),
    )
    messages = [{"role": "user", "content": "Retourne un objet JSON."}]
    assert await ia.texte(messages, image=image, format_json=True) == "{}"
    assert messages == [{"role": "user", "content": "Retourne un objet JSON."}]
