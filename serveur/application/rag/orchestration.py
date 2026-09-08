import asyncio
import json
import logging
import re
from time import perf_counter
from uuid import uuid4

from fastapi.encoders import jsonable_encoder
from fastapi import HTTPException
from psycopg.types.json import Jsonb

from application.base.connexion import lire, pool
from application.base.verrous import verrou_operation
from application.configuration import configuration
from application.ia.fournisseur import FournisseurIA
from application.rag.prompt import construire
from application.rag.routage import classifier, conversation_simple
from application.retrieval.recherche import rechercher

logger = logging.getLogger(__name__)


def evenement(type_evenement, donnees):
    return f"event: {type_evenement}\ndata: {json.dumps(jsonable_encoder(donnees), ensure_ascii=False)}\n\n"


async def sauvegarder(trace, conversation_id):
    async with pool.connection() as connexion:
        await connexion.execute(
            """INSERT INTO executions_retrieval
            (id,conversation_id,question,strategie,trace) VALUES (%s,%s,%s,%s,%s)""",
            (
                trace["id"],
                conversation_id,
                trace["question"],
                trace["strategie"],
                Jsonb(jsonable_encoder(trace)),
            ),
        )
        for rang, source in enumerate(trace.get("sources", []), 1):
            await connexion.execute(
                "INSERT INTO resultats_retrieval VALUES (%s,%s,%s,%s,%s)",
                (trace["id"], rang, source["id"], source["score"], Jsonb(jsonable_encoder(source))),
            )
        if trace.get("reponse"):
            await connexion.execute(
                "INSERT INTO messages (id,conversation_id,role,contenu,execution_id) VALUES (%s,%s,'assistant',%s,%s)",
                (uuid4(), conversation_id, trace["reponse"], trace["id"]),
            )


async def discuter(demande, conversation_id, liberer):
    try:
        async with verrou_operation(f"chat:{conversation_id}"):
            async for bloc in produire_reponse(demande, conversation_id):
                yield bloc
    except HTTPException as erreur:
        yield evenement("erreur", {"message": erreur.detail})
    finally:
        liberer()


async def produire_reponse(demande, conversation_id):
    debut = perf_counter()
    ia = FournisseurIA()
    trace = {
        "id": str(uuid4()),
        "question": demande.question,
        "strategie": demande.strategie,
        "reponse": "",
        "sources": [],
        "statut": "en_cours",
        "branches": [],
        "durees": {},
        "fournisseur": configuration().fournisseur_ia,
        "modele_generation": configuration().modele_generation,
    }
    sauvegardee = False
    try:
        historique = await lire(
            """SELECT role,contenu FROM
            (SELECT role,contenu,cree_le FROM messages WHERE conversation_id=%s ORDER BY cree_le DESC LIMIT 6) m
            ORDER BY cree_le""",
            (conversation_id,),
        )
        historique = [{"role": m["role"], "content": m["contenu"][:2000]} for m in historique]
        async with pool.connection() as connexion:
            await connexion.execute(
                "INSERT INTO messages (id,conversation_id,role,contenu) VALUES (%s,%s,'user',%s)",
                (uuid4(), conversation_id, demande.question),
            )
        technologies = [t["nom"] for t in await lire("SELECT nom FROM technologies")]
        routage = classifier(demande.question, technologies)
        trace["routage"] = routage
        trace["retrieval_necessaire"] = not (
            demande.strategie == "adaptive" and conversation_simple(demande.question)
        )
        trace["raison_decision"] = (
            "Question documentaire : recherche nécessaire."
            if trace["retrieval_necessaire"]
            else "Salutation ou échange simple reconnu."
        )
        yield evenement(
            "debut",
            {"conversation_id": str(conversation_id), "execution_id": trace["id"], "routage": routage},
        )
        if trace["retrieval_necessaire"]:
            sous_questions = [demande.question]
            if demande.strategie == "branching":
                depart = perf_counter()
                decomposer = [
                    {
                        "role": "system",
                        "content": 'Décompose la demande en 2 ou 3 questions documentaires autonomes en français. Retourne uniquement un objet JSON de la forme {"questions":["question 1","question 2"]}. N’invente aucune technologie ni version.',
                    },
                    {"role": "user", "content": demande.question},
                ]
                sortie = await ia.texte(decomposer, format_json=True)
                trace["decomposition"] = {"prompt": decomposer, "sortie": sortie, "usage": ia.usage.copy()}
                try:
                    candidats = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", sortie.strip()))
                    if isinstance(candidats, dict):
                        candidats = candidats.get("questions")
                    if (
                        not isinstance(candidats, list)
                        or not 1 <= len(candidats) <= 3
                        or not all(isinstance(q, str) and 2 <= len(q) <= 4000 for q in candidats)
                    ):
                        raise ValueError()
                    sous_questions = candidats
                except (ValueError, TypeError):
                    trace["avertissement"] = (
                        "Décomposition non exploitable : recherche sur la question originale."
                    )
                trace["durees"]["decomposition"] = round(perf_counter() - depart, 3)
            fusion = {}
            for sous_question in sous_questions:
                routes = classifier(sous_question, technologies)
                filtres = demande.model_copy(
                    update={
                        "question": sous_question,
                        "version": demande.version or routes["version"] or routage["version"],
                    }
                )
                selection = routes["technologies"] if demande.strategie in {"routing", "branching"} else None
                recherche = await rechercher(filtres, selection)
                trace["branches"].append({"question": sous_question, "routage": routes, **recherche})
                for resultat in recherche["resultats"]:
                    identifiant = str(resultat["id"])
                    if identifiant not in fusion or resultat["score"] > fusion[identifiant]["score"]:
                        fusion[identifiant] = resultat
            resultats = sorted(fusion.values(), key=lambda c: c["score"], reverse=True)[: demande.top_k]
            messages, contexte, sources = construire(demande.question, resultats, historique)
            trace.update(prompt=messages, contexte=contexte, sources=sources)
            for nom in ["embedding", "retrieval"]:
                trace["durees"][nom] = round(sum(b["durees"][nom] for b in trace["branches"]), 3)
        else:
            messages = [
                {
                    "role": "system",
                    "content": "Tu es Atelier, un assistant pour explorer des documentations. Réponds en français à cet échange simple, en une ou deux phrases. Ne donne pas d’information technique sans documentation.",
                },
                {"role": "user", "content": demande.question},
            ]
            trace.update(prompt=messages, contexte="")
        yield evenement("sources", {"sources": trace["sources"], "trace": trace})
        depart = perf_counter()
        if trace["retrieval_necessaire"] and not trace["sources"]:
            trace["reponse"] = (
                "Je n’ai pas trouvé de passage suffisamment pertinent dans la documentation sélectionnée. Ajoutez une source, vérifiez la version ou ajustez le seuil de recherche."
            )
            yield evenement("texte", {"texte": trace["reponse"]})
        else:
            ia.usage = {}
            async for texte in ia.generer(messages):
                trace["reponse"] += texte
                yield evenement("texte", {"texte": texte})
            if not trace["reponse"].strip():
                raise ValueError("Le modèle a retourné une réponse vide.")
            trace["usage_generation"] = ia.usage.copy()
        trace["durees"]["generation"] = round(perf_counter() - depart, 3)
        citations = [int(n) for n in re.findall(r"\[(\d+)\]", trace["reponse"])]
        trace["verification_citations"] = {
            "citations": citations,
            "hors_sources": sorted(set(n for n in citations if n < 1 or n > len(trace["sources"]))),
            "absence": bool(trace["sources"] and not citations),
            "limite": "Vérification des numéros uniquement ; ne prouve pas que les affirmations sont exactes.",
        }
        trace["statut"] = "termine"
        trace["durees"]["total"] = round(perf_counter() - debut, 3)
        await sauvegarder(trace, conversation_id)
        sauvegardee = True
        logger.info(
            "rag_termine execution=%s strategie=%s duree=%s chunks=%s",
            trace["id"],
            demande.strategie,
            trace["durees"]["total"],
            len(trace["sources"]),
        )
        yield evenement("fin", {"trace": trace})
    except asyncio.CancelledError:
        trace["statut"] = "interrompu"
        raise
    except Exception as erreur:
        logger.error("rag_echoue execution=%s type=%s", trace["id"], type(erreur).__name__)
        trace["statut"] = "erreur"
        trace["erreur"] = "La requête a échoué. Vérifiez Ollama ou la configuration OpenAI et réessayez."
        yield evenement("erreur", {"message": trace["erreur"]})
    finally:
        if not sauvegardee:
            trace["durees"]["total"] = round(perf_counter() - debut, 3)
            await asyncio.shield(sauvegarder(trace, conversation_id))
