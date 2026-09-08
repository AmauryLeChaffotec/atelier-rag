import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from application.chunking.decoupage import decouper, strategie_suggeree
from application.configuration import configuration
from application.depots import documents
from application.ia.fournisseur import FournisseurIA
from application.parsing.sources import extraire
from application.schemas import ParametresChunking, Section
from application.services import stockage


def metadata_document(document):
    return {
        "document_id": str(document["id"]),
        "technology": document["technologie"],
        "version": document["version"],
        "source_type": document["type_source"],
        "source_url": document.get("url_source"),
        "filename": document.get("nom_fichier"),
        "document_title": document["titre"],
        "type_documentation": document["type_documentation"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def importer(contenu, nom, titre, technologie, version, type_documentation, url=None):
    if not contenu:
        raise ValueError("Ce fichier est vide.")
    if len(contenu) > configuration().taille_fichier_mo * 1024 * 1024:
        raise HTTPException(413, "Ce fichier dépasse la taille autorisée.")
    identifiant = uuid4()
    extension = "html" if url else Path(nom).suffix.lower().lstrip(".")
    sections = await asyncio.to_thread(extraire, contenu, extension, str(identifiant), url or "")
    if not sections:
        raise ValueError("Aucun contenu détecté dans ce document.")
    if sum(len(s.contenu) for s in sections) > 1_000_000 or len(sections) > 10000:
        raise ValueError("Document trop long : importez-le en plusieurs parties.")
    cle = f"{identifiant}/original.{extension}"
    await asyncio.to_thread(stockage.enregistrer, cle, contenu)
    parametres = ParametresChunking(strategie=strategie_suggeree(extension))
    document = {
        "id": identifiant,
        "titre": titre.strip(),
        "technologie": technologie.strip(),
        "version": version.strip(),
        "type_source": extension,
        "url_source": url,
        "nom_fichier": Path(nom).name,
        "cle_fichier": cle,
        "type_documentation": type_documentation,
        "sections": [s.model_dump() for s in sections],
        "parametres_chunking": parametres.model_dump(),
    }
    await documents.creer(document)
    return await documents.obtenir(identifiant)


async def apercu(document_id, demande):
    document = await documents.obtenir(document_id)
    chunks = await decouper(
        [Section(**s) for s in document["sections"]],
        demande.parametres,
        metadata_document(document),
        FournisseurIA(),
    )
    if len(chunks) > configuration().max_chunks:
        raise ValueError(
            f"Plus de {configuration().max_chunks} chunks. Augmentez la taille ou divisez le document."
        )
    donnees = [c.model_dump(mode="json") for c in chunks]
    revision = await documents.enregistrer_apercu(
        document_id, demande.revision, donnees, demande.parametres.model_dump()
    )
    return {"chunks": donnees, "revision": revision, "parametres": demande.parametres.model_dump()}
