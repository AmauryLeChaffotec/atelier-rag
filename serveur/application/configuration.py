from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    fournisseur_ia: Literal["ollama", "openai"] = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_embedding: str = "qwen3-embedding:0.6b"
    ollama_generation: str = "gemma4:e4b"
    openai_api_key: str = ""
    openai_embedding: str = "text-embedding-3-small"
    openai_generation: str = "gpt-4o-mini"
    mistral_api_key: str = ""
    mistral_ocr: str = "mistral-ocr-latest"
    database_url: str = "postgresql://atelier:atelier_local_uniquement@127.0.0.1:5432/atelier"
    repertoire_fichiers: str = "donnees"
    stockage: Literal["local", "s3"] = "local"
    s3_bucket: str = ""
    aws_default_region: str = "eu-west-3"
    taille_fichier_mo: int = 15
    max_chunks: int = 500
    max_tokens_reponse: int = 900
    max_contexte_caracteres: int = 16000
    delai_ia_secondes: int = 300
    cle_acces: str = ""
    environnement: Literal["local", "production"] = "local"

    @model_validator(mode="after")
    def verifier(self):
        if self.environnement == "production" and len(self.cle_acces) < 32:
            raise ValueError("En production, CLE_ACCES doit contenir au moins 32 caractères.")
        if self.fournisseur_ia == "openai" and not self.openai_api_key:
            raise ValueError("Renseignez OPENAI_API_KEY dans le fichier .env du serveur.")
        if self.stockage == "s3" and not self.s3_bucket:
            raise ValueError("Renseignez S3_BUCKET pour le stockage S3.")
        return self

    @property
    def modele_embedding(self):
        return self.ollama_embedding if self.fournisseur_ia == "ollama" else self.openai_embedding

    @property
    def modele_generation(self):
        return self.ollama_generation if self.fournisseur_ia == "ollama" else self.openai_generation

    @property
    def espace_embedding(self):
        # Ne jamais comparer des vecteurs issus de deux modèles différents.
        return f"{self.fournisseur_ia}:{self.modele_embedding}:v1"


@lru_cache
def configuration():
    return Configuration()
