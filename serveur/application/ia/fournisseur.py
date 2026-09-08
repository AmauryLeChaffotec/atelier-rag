"""Le seul module qui appelle Ollama ou OpenAI. Aucune clé dans Next.js."""

import asyncio
import base64
import json
import math

import httpx

from application.configuration import configuration

capacite_ia = asyncio.Semaphore(2)


class FournisseurIA:
    def __init__(self, config=None):
        self.config = config or configuration()
        self.usage = {}

    def client(self):
        local = self.config.fournisseur_ia == "ollama"
        return httpx.AsyncClient(
            base_url=self.config.ollama_url if local else "https://api.openai.com",
            headers={} if local else {"Authorization": f"Bearer {self.config.openai_api_key}"},
            timeout=httpx.Timeout(self.config.delai_ia_secondes, connect=15),
            trust_env=False,
        )

    async def embeddings(self, textes: list[str], question=False):
        vecteurs = []
        local = self.config.fournisseur_ia == "ollama"
        if local and question and self.config.modele_embedding.startswith("qwen3-embedding"):
            textes = [
                f"Instruct: Given a technical question, retrieve relevant documentation passages.\nQuery: {t}"
                for t in textes
            ]
        async with capacite_ia, self.client() as client:
            for debut in range(0, len(textes), 16):
                corps = {"model": self.config.modele_embedding, "input": textes[debut : debut + 16]}
                if local:
                    corps.update(truncate=False, keep_alive="10m")
                reponse = await client.post("/api/embed" if local else "/v1/embeddings", json=corps)
                reponse.raise_for_status()
                donnees = reponse.json()
                lot = (
                    donnees["embeddings"]
                    if local
                    else [d["embedding"] for d in sorted(donnees["data"], key=lambda d: d["index"])]
                )
                if len(lot) != len(textes[debut : debut + 16]):
                    raise ValueError("Le fournisseur a retourné un nombre incorrect d’embeddings.")
                vecteurs.extend(lot)
        if vecteurs and (
            not vecteurs[0]
            or any(
                len(v) != len(vecteurs[0]) or any(not math.isfinite(x) for x in v) or not any(v)
                for v in vecteurs
            )
        ):
            raise ValueError("Le fournisseur a retourné des vecteurs invalides.")
        return vecteurs

    async def generer(self, messages: list[dict], image: bytes | None = None, format_json=False):
        local = self.config.fournisseur_ia == "ollama"
        messages = [m.copy() for m in messages]
        if image:
            encodee = base64.b64encode(image).decode()
            if local:
                messages[-1]["images"] = [encodee]
            else:
                messages[-1]["content"] = [
                    {"type": "text", "text": messages[-1]["content"]},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encodee}"}},
                ]
        corps = {"model": self.config.modele_generation, "messages": messages, "stream": True}
        if format_json:
            if local:
                corps["format"] = "json"
            else:
                corps["response_format"] = {"type": "json_object"}
        if local:
            corps.update(
                think=False,
                keep_alive="10m",
                options={"temperature": 0.15, "num_predict": self.config.max_tokens_reponse, "num_ctx": 8192},
            )
        else:
            corps.update(
                max_completion_tokens=self.config.max_tokens_reponse, stream_options={"include_usage": True}
            )
        async with capacite_ia, self.client() as client:
            async with client.stream(
                "POST", "/api/chat" if local else "/v1/chat/completions", json=corps
            ) as reponse:
                reponse.raise_for_status()
                async for ligne in reponse.aiter_lines():
                    if not ligne or (not local and not ligne.startswith("data: ")):
                        continue
                    if not local:
                        ligne = ligne[6:]
                    if ligne == "[DONE]":
                        break
                    evenement = json.loads(ligne)
                    if evenement.get("error"):
                        raise ValueError("Le fournisseur IA a interrompu la génération.")
                    if local:
                        texte = evenement.get("message", {}).get("content", "")
                        if evenement.get("done"):
                            self.usage = {
                                "entree": evenement.get("prompt_eval_count", 0),
                                "sortie": evenement.get("eval_count", 0),
                            }
                    else:
                        choix = evenement.get("choices", [])
                        texte = choix[0].get("delta", {}).get("content", "") if choix else ""
                        if evenement.get("usage"):
                            self.usage = {
                                "entree": evenement["usage"]["prompt_tokens"],
                                "sortie": evenement["usage"]["completion_tokens"],
                            }
                    if texte:
                        yield texte

    async def texte(self, messages, image=None, format_json=False):
        return "".join([morceau async for morceau in self.generer(messages, image, format_json)])
