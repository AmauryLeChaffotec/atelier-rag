from uuid import uuid4

import pymupdf
import pytest

from application.configuration import configuration
from application.parsing.sources import adresse_publique, extraire, extraire_html, telecharger


def test_html_structure_code_liens_tableaux():
    html = """<nav>Menu inutile</nav><main><h1>Guide</h1><h2>Début</h2>
    <p>Lire <a href='/reference'>la référence</a>.</p><ul><li>Un</li><li>Deux</li></ul>
    <pre><code>if x &lt; 2:\n    print(x)</code></pre>
    <table><tr><th>Clé</th><th>Valeur</th></tr><tr><td>a</td><td>1</td></tr></table>
    <script>danger()</script></main>"""
    sections = extraire_html(html, "https://example.com/guide")
    assert len(sections) == 4
    assert sections[0].titres == ["Guide", "Début"]
    assert "https://example.com/reference" in sections[0].contenu
    assert "if x < 2:" in sections[2].contenu
    assert sections[3].type_contenu == "tableau"
    assert not any("Menu inutile" in s.contenu or "danger()" in s.contenu for s in sections)


def test_markdown_code_et_titres():
    sections = extraire(b"# Guide\n\n## Exemple\n\n```python\nprint('oui')\n```", "md", str(uuid4()))
    assert sections[0].type_contenu == "code"
    assert sections[0].titres == ["Guide", "Exemple"]


def test_pdf_visuel_associe_a_la_page(tmp_path, monkeypatch):
    monkeypatch.setattr(configuration(), "repertoire_fichiers", str(tmp_path))
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((50, 50), "Un diagramme")
        page.draw_rect(pymupdf.Rect(40, 80, 140, 180))
        sections = extraire(document.tobytes(), "pdf", str(uuid4()))
    assert sections[0].page == 1
    assert "Un diagramme" in sections[0].contenu
    assert (tmp_path / sections[0].visuel).exists()


@pytest.mark.parametrize(
    "ip", ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "::ffff:127.0.0.1", "224.0.0.1"]
)
def test_adresses_privees_interdites(ip):
    assert not adresse_publique(ip)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://localhost:8000/",
        "https://user:pass@example.com/",
    ],
)
async def test_urls_internes_refusees(url):
    with pytest.raises(ValueError):
        await telecharger(url)
