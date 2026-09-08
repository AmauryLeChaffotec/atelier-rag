from uuid import UUID

from fastapi import HTTPException
from psycopg.types.json import Jsonb

from application.base.connexion import executer, lire, pool


async def obtenir(document_id: UUID):
    document = await lire("SELECT * FROM documents WHERE id=%s", (document_id,), unique=True)
    if not document:
        raise HTTPException(404, "Documentation introuvable.")
    return document


async def lister():
    return await lire("""SELECT id, titre, technologie, version, type_source, url_source, nom_fichier,
        type_documentation, statut, erreur, revision, parametres_chunking, modele_embedding, espace_embedding,
        nombre_chunks, cree_le, indexe_le, jsonb_array_length(sections) AS nombre_sections
        FROM documents ORDER BY cree_le DESC""")


async def creer(document: dict):
    async with pool.connection() as connexion:
        await connexion.execute(
            "INSERT INTO technologies VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (document["technologie"], document["version"]),
        )
        await connexion.execute(
            """INSERT INTO documents
            (id,titre,technologie,version,type_source,url_source,nom_fichier,cle_fichier,
             type_documentation,sections,parametres_chunking)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                document["id"],
                document["titre"],
                document["technologie"],
                document["version"],
                document["type_source"],
                document.get("url_source"),
                document.get("nom_fichier"),
                document["cle_fichier"],
                document["type_documentation"],
                Jsonb(document["sections"]),
                Jsonb(document["parametres_chunking"]),
            ),
        )


async def enregistrer_apercu(document_id, revision, chunks, parametres):
    async with pool.connection() as connexion:
        curseur = await connexion.execute(
            """UPDATE documents SET brouillon=%s, parametres_chunking=%s,
            revision=revision+1 WHERE id=%s AND revision=%s AND statut!='indexation' RETURNING revision""",
            (Jsonb(chunks), Jsonb(parametres), document_id, revision),
        )
        resultat = await curseur.fetchone()
        if not resultat:
            raise HTTPException(409, "Ce document a changé ou est en cours d’indexation. Rechargez-le.")
        return resultat["revision"]


async def changer_version(technologie, version):
    existe = await lire(
        "SELECT id FROM documents WHERE technologie=%s AND version=%s LIMIT 1",
        (technologie, version),
        unique=True,
    )
    if not existe:
        raise HTTPException(404, "Cette version n’existe pas dans la bibliothèque.")
    await executer("UPDATE technologies SET version_courante=%s WHERE nom=%s", (version, technologie))
