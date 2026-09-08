"""OCR des PDF via Mistral, indépendant des modèles d’embedding et de génération."""

import asyncio
import base64
import re

import httpx
import pymupdf
from fastapi import HTTPException
from psycopg.types.json import Jsonb

from application.base.connexion import executer, pool
from application.base.verrous import verrou_operation
from application.configuration import configuration
from application.depots import documents
from application.parsing.sources import extraire
from application.schemas import LectureOCR
from application.services import stockage

capacite_ocr = asyncio.Semaphore(1)


async def appeler_mistral(pdf: bytes, pages: list[int]):
    config = configuration()
    if not config.mistral_api_key:
        raise HTTPException(
            503, "Renseignez MISTRAL_API_KEY dans le .env privé du serveur pour utiliser l’OCR."
        )
    async with httpx.AsyncClient(timeout=config.delai_ia_secondes, trust_env=False) as client:
        reponse = await client.post(
            "https://api.mistral.ai/v1/ocr",
            headers={"Authorization": f"Bearer {config.mistral_api_key}"},
            json={
                "model": config.mistral_ocr,
                "document": {
                    "type": "document_url",
                    "document_url": "data:application/pdf;base64," + base64.b64encode(pdf).decode(),
                },
                "pages": [p - 1 for p in pages],
                "include_image_base64": False,
                "include_blocks": False,
            },
        )
        if reponse.status_code in {401, 403}:
            raise HTTPException(
                502, "Mistral refuse l’accès OCR. Vérifiez la clé et les droits du projet Mistral."
            )
        if reponse.status_code == 429:
            raise HTTPException(
                429, "Limite ou quota Mistral atteint. Réessayez plus tard et vérifiez votre compte Mistral."
            )
        reponse.raise_for_status()
        resultat = reponse.json()
    recues = resultat.get("pages", [])
    if len(recues) != len(pages) or {p.get("index") for p in recues} != {p - 1 for p in pages}:
        raise ValueError(
            "Mistral n’a pas retourné toutes les pages demandées. Le texte existant est conservé."
        )
    if any(not isinstance(p.get("markdown"), str) for p in recues):
        raise ValueError("La réponse OCR ne contient pas le Markdown attendu.")
    if sum(len(p["markdown"]) for p in recues) > 1_000_000:
        raise ValueError("Résultat OCR trop long. Traitez moins de pages à la fois.")
    return {
        "modele": resultat.get("model", config.mistral_ocr),
        "pages": {str(p["index"] + 1): p["markdown"] for p in recues},
    }


def sections_ocr(document, cache, pages):
    sections = [s for s in document["sections"] if s.get("page") not in pages]
    for numero in pages:
        anciennes = [s for s in document["sections"] if s.get("page") == numero]
        visuel = next((s.get("visuel") for s in anciennes if s.get("visuel")), None)
        description = next(
            (s.get("description_visuelle") for s in anciennes if s.get("description_visuelle")), None
        )
        # Les images ne sont pas téléchargées : la page originale reste le visuel de référence.
        markdown = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", cache["pages"][str(numero)])
        nouvelles = extraire(markdown.encode(), "md", str(document["id"]))
        if not nouvelles:
            # Un schéma sans texte OCR ne doit pas effacer une description déjà validée.
            sections.extend(anciennes)
            continue
        for section in nouvelles:
            section.page = numero
            section.visuel = visuel
            section.titres = section.titres or [f"Page {numero}"]
            sections.append(
                {
                    **section.model_dump(),
                    "modele_ocr": cache.get("modeles_pages", {}).get(str(numero), cache["modele"]),
                }
            )
        if description:
            sections.append(
                {
                    "contenu": "[Description visuelle validée par l’utilisateur]\n" + description,
                    "texte_extrait": "",
                    "description_visuelle": description,
                    "titres": [f"Page {numero}", "Description visuelle"],
                    "page": numero,
                    "type_contenu": "visuel",
                    "visuel": visuel,
                }
            )
    if sum(len(s["contenu"]) for s in sections) > 1_000_000 or len(sections) > 10000:
        raise ValueError("Document OCR trop long pour les limites de ce petit projet.")
    return sorted(sections, key=lambda s: s.get("page") or 0)


async def lire_pdf(document_id, demande: LectureOCR):
    async with capacite_ocr, verrou_operation(f"ocr:{document_id}"):
        document = await documents.obtenir(document_id)
        if document["type_source"] != "pdf":
            raise HTTPException(422, "L’OCR Mistral est réservé aux PDF dans cette application.")
        if document["revision"] != demande.revision or document["statut"] == "indexation":
            raise HTTPException(409, "Le document a changé ou est en cours d’indexation. Rechargez-le.")
        contenu = await asyncio.to_thread(stockage.lire_fichier, document["cle_fichier"])
        with pymupdf.open(stream=contenu, filetype="pdf") as pdf:
            nombre_pages = len(pdf)
        pages = sorted(set(demande.pages or range(1, nombre_pages + 1)))
        if not pages or pages[-1] > nombre_pages:
            raise HTTPException(422, f"Ce PDF comporte {nombre_pages} pages. Vérifiez la sélection.")
        modele = configuration().mistral_ocr
        cache = document.get("ocr") or {}
        if cache.get("modele_demande") != modele:
            cache = {"modele_demande": modele, "modele": modele, "pages": {}}
        manquantes = [p for p in pages if str(p) not in cache["pages"]]
        if manquantes:
            resultat = await appeler_mistral(contenu, manquantes)
            cache["modele"] = resultat["modele"]
            cache["pages"].update(resultat["pages"])
            cache.setdefault("modeles_pages", {}).update({str(p): resultat["modele"] for p in manquantes})
            # Garder le cache même si une édition concurrente empêche ensuite l’application du texte.
            await executer("UPDATE documents SET ocr=%s WHERE id=%s", (Jsonb(cache), document_id))
        sections = sections_ocr(document, cache, pages)
        async with pool.connection() as connexion:
            curseur = await connexion.execute(
                """UPDATE documents SET sections=%s, brouillon='[]', revision=revision+1
                WHERE id=%s AND revision=%s AND statut!='indexation' RETURNING revision""",
                (Jsonb(sections), document_id, demande.revision),
            )
            mise_a_jour = await curseur.fetchone()
            if not mise_a_jour:
                raise HTTPException(
                    409, "Document modifié pendant l’OCR. Rechargez-le ; le résultat OCR est en cache."
                )
        return {
            "revision": mise_a_jour["revision"],
            "pages": pages,
            "pages_envoyees": len(manquantes),
            "pages_en_cache": len(pages) - len(manquantes),
            "modele": cache["modele"],
        }
