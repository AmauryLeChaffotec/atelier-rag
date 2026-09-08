import pytest
from pydantic import ValidationError

from application.chunking.decoupage import couper, decouper, similarite, strategie_suggeree
from application.schemas import ParametresChunking, Section


def test_overlap_conserve_les_caracteres():
    texte = "abcdefghijklmnopqrstuvwxyz" * 24
    p = ParametresChunking(taille=100, overlap=20, taille_min=0)
    morceaux = list(couper(texte, p, recursif=False))
    reconstruit = morceaux[0] + "".join(m[20:] for m in morceaux[1:])
    assert reconstruit == texte
    assert all(len(m) <= 100 for m in morceaux)


@pytest.mark.parametrize(
    "attributs", [{"overlap": 1000}, {"taille_min": 1100}, {"taille_max": 500}, {"separateurs": [""]}]
)
def test_parametres_invalides(attributs):
    with pytest.raises(ValidationError):
        ParametresChunking(**attributs)


@pytest.mark.parametrize("strategie", ["taille", "paragraphes", "titres", "markdown", "recursif"])
async def test_hierarchie_et_pages_ne_se_melangent_pas(strategie):
    sections = [
        Section(contenu="Premier paragraphe.", titres=["Guide", "Début"], page=1),
        Section(contenu="Second paragraphe.", titres=["Guide", "Fin"], page=2),
    ]
    chunks = await decouper(sections, ParametresChunking(strategie=strategie), {"technology": "Python"})
    assert len(chunks) == 2
    assert chunks[0].metadata["heading_path"] == ["Guide", "Début"]
    assert chunks[1].metadata["page"] == 2
    assert chunks[0].id != chunks[1].id


async def test_bloc_code_preserve_ou_decoupe():
    code = "```python\n" + "print('bonjour')\n" * 20 + "```"
    sections = [Section(contenu=code, type_contenu="code")]
    p = ParametresChunking(taille=100, overlap=0)
    assert len(await decouper(sections, p, {})) == 1
    p.preserver_code = False
    assert len(await decouper(sections, p, {})) > 1


async def test_semantique_utilise_les_embeddings():
    class IA:
        async def embeddings(self, textes):
            assert len(textes) == 3
            return [[1, 0], [1, 0], [0, 1]]

    sections = [Section(contenu=t, titres=["Guide"]) for t in ["Texte A", "Texte B", "Autre sujet"]]
    chunks = await decouper(sections, ParametresChunking(strategie="semantique"), {}, IA())
    assert [c.contenu for c in chunks] == ["Texte A\n\nTexte B", "Autre sujet"]


def test_cosinus_et_suggestion():
    assert similarite([1, 0], [0, 1]) == 0
    assert similarite([1, 0], [1, 0]) == 1
    assert similarite([0, 0], [1, 0]) == 0
    assert strategie_suggeree("md") == "markdown"
