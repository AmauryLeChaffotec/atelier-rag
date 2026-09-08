"""Les six stratégies sont visibles ici. Les tailles sont en caractères."""

import math

from application.schemas import Chunk, ParametresChunking, Section


def tokens_estimes(texte: str) -> int:
    # Estimation explicitement affichée : ce n’est pas le tokenizer Qwen/Gemma.
    return max(1, math.ceil(len(texte) / 4))


def similarite(a: list[float], b: list[float]):
    norme = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b, strict=True)) / norme if norme else 0


def couper(texte: str, parametres: ParametresChunking, recursif=True):
    debut = 0
    while debut < len(texte):
        fin = min(debut + parametres.taille, len(texte))
        if recursif and fin < len(texte):
            for separateur in parametres.separateurs:
                position = texte.rfind(separateur, debut + parametres.taille // 2, fin)
                if position >= 0:
                    fin = position + len(separateur)
                    break
        morceau = texte[debut:fin].strip()
        if morceau:
            yield morceau
        if fin == len(texte):
            break
        debut = max(debut + 1, fin - parametres.overlap)


async def decouper(sections: list[Section], p: ParametresChunking, metadata: dict, ia=None):
    if not sections:
        raise ValueError("Aucun texte exploitable dans ce document.")
    groupes: list[Section] = []
    vecteurs = None
    if p.strategie == "semantique":
        if ia is None:
            raise ValueError("Le chunking sémantique nécessite le modèle d’embedding.")
        if len(sections) > 500:
            raise ValueError("Limite du chunking sémantique : 500 sections. Divisez ce document.")
        vecteurs = await ia.embeddings([s.contenu[:6000] for s in sections])
    for i, section in enumerate(sections):
        precedent = groupes[-1] if groupes else None
        meme_origine = precedent and precedent.page == section.page and precedent.titres == section.titres
        peut_fusionner = (
            meme_origine
            and precedent.type_contenu == section.type_contenu
            and precedent.visuel == section.visuel
            and precedent.modele_ocr == section.modele_ocr
            and section.type_contenu != "code"
            and len(precedent.contenu) + len(section.contenu) + 2 <= p.taille
        )
        if p.strategie == "paragraphes":
            peut_fusionner = peut_fusionner and len(precedent.contenu) < p.taille_min
        if vecteurs and i:
            peut_fusionner = peut_fusionner and similarite(vecteurs[i - 1], vecteurs[i]) >= p.seuil_semantique
        if peut_fusionner:
            precedent.contenu += "\n\n" + section.contenu
        else:
            groupes.append(section.model_copy(deep=True))
    chunks = []
    for section in groupes:
        if section.type_contenu == "code" and p.preserver_code and len(section.contenu) <= p.taille_max:
            morceaux = [section.contenu]
        else:
            morceaux = list(couper(section.contenu, p, recursif=p.strategie != "taille"))
        for contenu in morceaux:
            meta = {
                **metadata,
                "title": section.titres[0] if section.titres else metadata.get("document_title", ""),
                "subtitle": section.titres[-1] if len(section.titres) > 1 else "",
                "heading_path": section.titres,
                "page": section.page,
                "content_type": section.type_contenu,
                "visuel": section.visuel,
                "modele_ocr": section.modele_ocr,
                "chunk_index": len(chunks),
                "chunking_strategy": p.strategie,
                "caracteres": len(contenu),
                "tokens_estimes": tokens_estimes(contenu),
            }
            chunk = Chunk(contenu=contenu, metadata=meta)
            chunk.metadata["chunk_id"] = str(chunk.id)
            chunks.append(chunk)
    return chunks


def strategie_suggeree(type_source: str):
    return {
        "md": "markdown",
        "markdown": "markdown",
        "html": "titres",
        "htm": "titres",
        "pdf": "recursif",
    }.get(type_source, "paragraphes")
