"""Calcul hors transaction, remplacement atomique. Une erreur conserve l’index précédent."""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from application.base.connexion import pool
from application.chunking.decoupage import tokens_estimes
from application.configuration import configuration
from application.depots.documents import obtenir
from application.ia.fournisseur import FournisseurIA

logger = logging.getLogger(__name__)


async def reserver(document_id, demande):
    document = await obtenir(document_id)
    brouillon = {c["id"]: c for c in document["brouillon"]}
    identifiants = [str(c.id) for c in demande.chunks]
    if len(identifiants) != len(set(identifiants)) or any(i not in brouillon for i in identifiants):
        raise ValueError("Les chunks doivent provenir du dernier aperçu, avec des identifiants uniques.")
    if len(identifiants) > configuration().max_chunks:
        raise ValueError("Trop de chunks pour une seule indexation.")
    chunks = []
    for rang, chunk in enumerate(demande.chunks):
        # Les métadonnées reçues du navigateur ne font pas autorité.
        contenu = chunk.contenu.strip()
        if not contenu:
            raise ValueError("Un chunk ne peut pas être vide.")
        meta = {
            **brouillon[str(chunk.id)]["metadata"],
            "chunk_index": rang,
            "tokens_estimes": tokens_estimes(contenu),
            "caracteres": len(contenu),
        }
        chunks.append({"id": str(chunk.id), "contenu": contenu, "metadata": meta})
    async with pool.connection() as connexion:
        curseur = await connexion.execute(
            """UPDATE documents SET statut='indexation', erreur=NULL, brouillon=%s
             WHERE id=%s AND revision=%s AND statut!='indexation' RETURNING id""",
            (Jsonb(chunks), document_id, demande.revision),
        )
        if not await curseur.fetchone():
            raise HTTPException(409, "Cet aperçu a changé ou une indexation est déjà en cours.")
        await connexion.execute(
            """INSERT INTO travaux_indexation (id,document_id,revision,chunks,espace_embedding)
            VALUES (%s,%s,%s,%s,%s)""",
            (uuid4(), document_id, demande.revision, Jsonb(chunks), configuration().espace_embedding),
        )
    return chunks


async def enregistrer_index(travail, vecteurs):
    """Le propriétaire du bail est vérifié avant toute modification des anciens chunks."""
    config = configuration()
    document_id, chunks, revision = travail["document_id"], travail["chunks"], travail["revision"]
    async with pool.connection() as connexion:
        curseur = await connexion.execute(
            """SELECT id FROM travaux_indexation WHERE id=%s AND proprietaire=%s
                AND statut='en_cours' AND expire_le>now() FOR UPDATE""",
            (travail["id"], travail["proprietaire"]),
        )
        if not await curseur.fetchone():
            return False
        # Un DELETE/INSERT complet dans la même transaction : aucun index partiel visible.
        await connexion.execute("DELETE FROM chunks WHERE document_id=%s", (document_id,))
        for chunk, vecteur in zip(chunks, vecteurs, strict=True):
            meta = {
                **chunk["metadata"],
                "embedding_model": config.modele_embedding,
                "embedding_provider": config.fournisseur_ia,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await connexion.execute(
                """INSERT INTO chunks
                    (id,document_id,contenu,metadata,embedding,dimension,espace_embedding)
                    VALUES (%s,%s,%s,%s,%s::vector,%s,%s)""",
                (
                    chunk["id"],
                    document_id,
                    chunk["contenu"],
                    Jsonb(meta),
                    str(vecteur),
                    len(vecteur),
                    config.espace_embedding,
                ),
            )
        await connexion.execute(
            """INSERT INTO versions_document
                (id,document_id,revision,espace_embedding,nombre_chunks) VALUES (%s,%s,%s,%s,%s)""",
            (uuid4(), document_id, revision, config.espace_embedding, len(chunks)),
        )
        await connexion.execute(
            """UPDATE documents SET statut='indexe', modele_embedding=%s,
                espace_embedding=%s, nombre_chunks=%s, indexe_le=now() WHERE id=%s""",
            (config.modele_embedding, config.espace_embedding, len(chunks), document_id),
        )
        await connexion.execute(
            "UPDATE travaux_indexation SET statut='termine', expire_le=NULL WHERE id=%s", (travail["id"],)
        )
    logger.info(
        "indexation_terminee document=%s chunks=%s modele=%s",
        document_id,
        len(chunks),
        config.modele_embedding,
    )
    return True


async def indexer(travail):
    if travail["espace_embedding"] != configuration().espace_embedding:
        raise ValueError("Le modèle d’embedding a changé. Relancez l’indexation avec le nouveau modèle.")
    vecteurs = await FournisseurIA().embeddings([c["contenu"] for c in travail["chunks"]])
    return await enregistrer_index(travail, vecteurs)
