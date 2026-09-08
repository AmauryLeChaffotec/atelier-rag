import pytest

from application.configuration import Configuration
from application.rag.prompt import construire
from application.rag.routage import classifier, conversation_simple
from application.schemas import Recherche


@pytest.mark.parametrize(
    "question,attendu",
    [
        ("Comment utiliser useEffect ?", ["React"]),
        ("Un tensor CUDA", ["PyTorch"]),
        ("Un context manager", ["Python"]),
        ("Compare React et Next.js", ["React", "Next.js"]),
        ("Inconnu", []),
    ],
)
def test_routing(question, attendu):
    assert classifier(question, ["Python", "React", "Next.js", "PyTorch"])["technologies"] == attendu


def test_version_et_adaptive():
    assert classifier("Python 3.14", ["Python"])["version"] == "3.14"
    assert classifier("Next.js version 16", ["Next.js"])["version"] == "16"
    assert conversation_simple("Merci beaucoup !")
    assert not conversation_simple("Bonjour, comment fonctionne useEffect ?")


def test_configuration_separe_les_espaces_embedding():
    local = Configuration(_env_file=None)
    distant = Configuration(_env_file=None, fournisseur_ia="openai", openai_api_key="cle-fictive-pour-test")
    assert local.espace_embedding != distant.espace_embedding
    assert local.modele_embedding == "qwen3-embedding:0.6b"
    assert local.modele_generation == "gemma4:e4b"


def test_prompt_garde_passages_entiers_et_ignore_surplus(monkeypatch):
    from application.configuration import configuration

    monkeypatch.setattr(configuration(), "max_contexte_caracteres", 150)
    meta = {"document_title": "Guide", "technology": "Python", "version": "3.14", "heading_path": []}
    messages, contexte, sources = construire(
        "Question",
        [
            {"id": "1", "contenu": "Court", "metadata": meta},
            {"id": "2", "contenu": "x" * 200, "metadata": meta},
        ],
        [],
    )
    assert len(sources) == 1 and sources[0]["citation"] == 1
    assert "Court" in contexte and "xxx" not in contexte
    assert "non fiables" in messages[0]["content"]


@pytest.mark.parametrize("valeurs", [{"top_k": 1000}, {"seuil": 2}, {"question": ""}])
def test_retrieval_valide_les_limites(valeurs):
    with pytest.raises(ValueError):
        Recherche(**{"question": "Question", **valeurs})
