"""Routing explicable, basé sur les technologies présentes et des mots-clés éditables."""

import re

ALIASES = {
    "Python": [r"\bpython\b", r"context manager", r"\bvenv\b", r"\bdecorat"],
    "React": [r"\breact\b", r"\buseeffect\b", r"\busestate\b", r"\bhooks?\b"],
    "Next.js": [r"\bnext(?:\.js|js)?\b", r"server components?", r"app router"],
    "PyTorch": [r"\bpytorch\b", r"\btorch\b", r"\btensors?\b", r"\bcuda\b"],
    "FastAPI": [r"\bfastapi\b", r"\bpydantic\b"],
    "PostgreSQL": [r"\bpostgres(?:ql)?\b", r"\bpgvector\b"],
    "Docker": [r"\bdocker\b", r"\bconteneurs?\b", r"docker compose"],
}


def classifier(question: str, technologies: list[str]):
    texte = question.lower()
    domaines = []
    for technologie in technologies:
        motifs = ALIASES.get(technologie, [re.escape(technologie.lower())])
        if any(re.search(motif, texte, re.I) for motif in motifs):
            domaines.append(technologie)
    correspondance = re.search(r"\b(?:version\s+|v)(\d+(?:\.\d+){0,2})\b", texte)
    if not correspondance:
        correspondance = re.search(
            r"(?:python|next(?:\.js)?|react|pytorch|fastapi|postgresql)\s+(\d+(?:\.\d+){0,2})\b", texte
        )
    return {
        "technologies": domaines,
        "version": correspondance[1] if correspondance else None,
        "methode": "règles explicites",
        "raison": "Mots-clés reconnus dans la question."
        if domaines
        else "Aucune technologie reconnue : recherche dans les versions courantes de la bibliothèque.",
    }


def conversation_simple(question: str):
    return bool(
        re.fullmatch(
            r"\s*(bonjour|salut|bonsoir|merci(?: beaucoup)?|au revoir|qui es[- ]tu)[\s!?.]*", question, re.I
        )
    )
