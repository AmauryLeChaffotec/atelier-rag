"""Extraction de blocs : on conserve la structure avant de créer les chunks."""

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx
import pymupdf
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

from application.configuration import configuration
from application.schemas import Section
from application.services.stockage import enregistrer


def adresse_publique(adresse: str):
    ip = ipaddress.ip_address(adresse)
    return ip.is_global and not ip.is_multicast and not ip.is_unspecified


async def telecharger(url: str) -> bytes:
    """DNS vérifié puis IP épinglée ; chaque redirection est contrôlée séparément."""
    limite = configuration().taille_fichier_mo * 1024 * 1024
    async with httpx.AsyncClient(timeout=25, trust_env=False) as client:
        for _ in range(5):
            morceaux = urlsplit(url)
            if (
                morceaux.scheme not in {"http", "https"}
                or not morceaux.hostname
                or morceaux.username
                or morceaux.password
                or morceaux.port not in {None, 80, 443}
            ):
                raise ValueError("Utilisez une URL publique HTTP ou HTTPS, sans identifiants.")
            hote = morceaux.hostname.encode("idna").decode()
            port = morceaux.port or (443 if morceaux.scheme == "https" else 80)
            adresses = await asyncio.to_thread(socket.getaddrinfo, hote, port, type=socket.SOCK_STREAM)
            ips = list(dict.fromkeys(a[4][0] for a in adresses))
            if not ips or not all(adresse_publique(ip) for ip in ips):
                raise ValueError("Les adresses locales, privées et les metadata AWS sont interdites.")
            cible = httpx.URL(url).copy_with(host=ips[0])
            async with client.stream(
                "GET",
                cible,
                headers={"Host": morceaux.netloc, "User-Agent": "AtelierRAG/1.0"},
                extensions={"sni_hostname": hote},
            ) as reponse:
                if reponse.status_code in {301, 302, 303, 307, 308}:
                    url = urljoin(url, reponse.headers.get("location", ""))
                    continue
                reponse.raise_for_status()
                contenu = bytearray()
                async for bloc in reponse.aiter_bytes():
                    contenu.extend(bloc)
                    if len(contenu) > limite:
                        raise ValueError("Cette page dépasse la taille de fichier autorisée.")
                return bytes(contenu)
    raise ValueError("Cette URL redirige trop de fois.")


def extraire_html(contenu: str, url="") -> list[Section]:
    soupe = BeautifulSoup(contenu, "html.parser")
    for balise in soupe(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        balise.decompose()
    racine = soupe.find("main") or soupe.find("article") or soupe.body or soupe
    titres: list[str] = []
    sections = []
    for bloc in racine.find_all(["h1", "h2", "h3", "h4", "p", "pre", "ul", "ol", "table"]):
        if bloc.find_parent(["pre", "ul", "ol", "table"]):
            continue
        if bloc.name.startswith("h"):
            niveau = int(bloc.name[1])
            titres = titres[: niveau - 1]
            titres.append(bloc.get_text(" ", strip=True))
            continue
        for lien in bloc.find_all("a", href=True):
            cible = urljoin(url, lien["href"])
            if urlsplit(cible).scheme in {"http", "https"}:
                lien.replace_with(f"[{lien.get_text(' ', strip=True)}]({cible})")
        type_contenu = {"pre": "code", "table": "tableau", "ul": "liste", "ol": "liste"}.get(
            bloc.name, "texte"
        )
        if bloc.name == "pre":
            texte = "```\n" + bloc.get_text().strip() + "\n```"
        elif bloc.name in {"ul", "ol"}:
            texte = "\n".join(
                "- " + li.get_text(" ", strip=True) for li in bloc.find_all("li", recursive=False)
            )
        elif bloc.name == "table":
            texte = "\n".join(
                " | ".join(c.get_text(" ", strip=True) for c in ligne.find_all(["th", "td"]))
                for ligne in bloc.find_all("tr")
            )
        else:
            texte = bloc.get_text(" ", strip=True)
        if texte.strip():
            sections.append(Section(contenu=texte, titres=titres.copy(), type_contenu=type_contenu))
    return sections


def extraire(contenu: bytes, extension: str, document_id: str, url="") -> list[Section]:
    if extension == "pdf":
        sections = []
        with pymupdf.open(stream=contenu, filetype="pdf") as document:
            if document.is_encrypted:
                raise ValueError("Ce PDF est protégé par un mot de passe.")
            if len(document) > 150:
                raise ValueError("Limite du petit projet : 150 pages par PDF.")
            for numero, page in enumerate(document, start=1):
                texte = page.get_text(sort=True).strip()
                visuel = None
                if page.get_images() or page.get_drawings() or not texte:
                    visuel = f"{document_id}/page-{numero}.png"
                    # Rendu de la page : schémas vectoriels et captures raster inclus.
                    echelle = min(1.5, 1500 / max(page.rect.width, page.rect.height))
                    enregistrer(
                        visuel,
                        page.get_pixmap(matrix=pymupdf.Matrix(echelle, echelle)).tobytes("png"),
                        "image/png",
                    )
                if texte or visuel:
                    sections.append(
                        Section(
                            contenu=texte or f"[Page {numero} visuelle : description à générer]",
                            titres=[f"Page {numero}"],
                            page=numero,
                            visuel=visuel,
                        )
                    )
        return sections
    texte = contenu.decode("utf-8-sig", errors="replace")
    if extension in {"html", "htm"}:
        return extraire_html(texte, url)
    if extension in {"md", "markdown"}:
        return extraire_html(MarkdownIt("commonmark").enable("table").render(texte), url)
    if extension == "txt":
        return [Section(contenu=p.strip()) for p in texte.split("\n\n") if p.strip()]
    raise ValueError("Formats acceptés : PDF, Markdown, TXT et HTML.")
