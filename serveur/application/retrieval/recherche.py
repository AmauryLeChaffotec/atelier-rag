"""Recherche exacte pgvector : lisible et suffisante pour quelques milliers de chunks."""

from time import perf_counter

from psycopg.types.json import Jsonb

from application.base.connexion import lire
from application.configuration import configuration
from application.ia.fournisseur import FournisseurIA


async def rechercher(demande, technologies=None):
    config = configuration()
    debut = perf_counter()
    vecteur = (await FournisseurIA().embeddings([demande.question], question=True))[0]
    duree_embedding = perf_counter() - debut
    conditions = ["c.espace_embedding=%s", "c.dimension=%s"]
    valeurs = [config.espace_embedding, len(vecteur)]
    for colonne, valeur in [
        ("d.technologie", demande.technologie),
        ("d.version", demande.version),
        ("d.id", demande.document_id),
        ("d.type_documentation", demande.type_documentation),
    ]:
        if valeur is not None:
            conditions.append(f"{colonne}=%s")
            valeurs.append(valeur)
    if technologies and not demande.technologie:
        conditions.append("d.technologie=ANY(%s)")
        valeurs.append(technologies)
    if demande.versions_courantes and not demande.version and not demande.document_id:
        conditions.append("d.version=t.version_courante")
    if demande.metadata:
        conditions.append("c.metadata @> %s")
        valeurs.append(Jsonb(demande.metadata))
    # MATERIALIZED évite que PostgreSQL calcule la distance avant le filtre de dimension.
    sql = f"""WITH candidats AS MATERIALIZED (
        SELECT c.id,c.document_id,c.contenu,c.metadata,c.embedding FROM chunks c
        JOIN documents d ON d.id=c.document_id JOIN technologies t ON t.nom=d.technologie
        WHERE {" AND ".join(conditions)}
    ), scores AS (
        SELECT id,document_id,contenu,metadata,1-(embedding <=> %s::vector) AS score FROM candidats
    ) SELECT * FROM scores WHERE score >= %s ORDER BY score DESC, id LIMIT %s"""
    resultats = await lire(sql, (*valeurs, str(vecteur), demande.seuil, demande.top_k))
    return {
        "resultats": resultats,
        "durees": {
            "embedding": round(duree_embedding, 3),
            "retrieval": round(perf_counter() - debut - duree_embedding, 3),
        },
        "dimension": len(vecteur),
        "espace_embedding": config.espace_embedding,
        "filtres": {
            **demande.model_dump(mode="json", exclude={"question"}),
            "technologies_routees": technologies or [],
        },
    }
