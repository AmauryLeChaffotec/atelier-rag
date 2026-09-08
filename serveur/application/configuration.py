from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from psycopg.conninfo import make_conninfo


class Configuration(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore", hide_input_in_errors=True)
    fournisseur_ia: Literal["ollama", "openai"] = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_embedding: str = "qwen3-embedding:0.6b"
    ollama_generation: str = "gemma4:e4b"
    openai_api_key: str = Field("", repr=False)
    openai_embedding: str = "text-embedding-3-small"
    openai_generation: str = "gpt-4o-mini"
    mistral_api_key: str = Field("", repr=False)
    mistral_ocr: str = "mistral-ocr-latest"
    database_url: str = Field("postgresql://atelier:atelier_local_uniquement@127.0.0.1:5432/atelier", repr=False)
    postgres_hote: str = ""
    postgres_port: int = 5432
    postgres_base: str = "atelier"
    postgres_utilisateur: str = "atelier"
    postgres_mot_de_passe: str = Field("", repr=False)
    postgres_sslmode: str = "verify-full"
    postgres_certificat: str = "/projet/certificats/rds.pem"
    migrer_au_demarrage: bool = True
    executer_indexations: bool = True
    bail_indexation_secondes: int = Field(90, ge=15, le=600)
    intervalle_indexation_secondes: float = Field(2, ge=0.1, le=60)
    repertoire_fichiers: str = "donnees"
    stockage: Literal["local", "s3"] = "local"
    s3_bucket: str = ""
    aws_default_region: str = "eu-west-3"
    taille_fichier_mo: int = 15
    max_chunks: int = 500
    max_tokens_reponse: int = 900
    max_contexte_caracteres: int = 16000
    delai_ia_secondes: int = 300
    cle_acces: str = Field("", repr=False)
    environnement: Literal["local", "production"] = "local"

    @model_validator(mode="after")
    def verifier(self):
        if self.environnement == "production" and len(self.cle_acces) < 32:
            raise ValueError("En production, CLE_ACCES doit contenir au moins 32 caractères.")
        if self.fournisseur_ia == "openai" and not self.openai_api_key:
            raise ValueError("Renseignez OPENAI_API_KEY dans .env en local ou dans Secrets Manager sur AWS.")
        if self.stockage == "s3" and not self.s3_bucket:
            raise ValueError("Renseignez S3_BUCKET pour le stockage S3.")
        return self

    @property
    def modele_embedding(self):
        return self.ollama_embedding if self.fournisseur_ia == "ollama" else self.openai_embedding

    @property
    def connexion_postgres(self):
        # ECS injecte les champs séparément : les caractères spéciaux du secret sont échappés.
        if not self.postgres_hote:
            return self.database_url
        return make_conninfo(
            host=self.postgres_hote,
            port=self.postgres_port,
            dbname=self.postgres_base,
            user=self.postgres_utilisateur,
            password=self.postgres_mot_de_passe,
            sslmode=self.postgres_sslmode,
            sslrootcert=self.postgres_certificat,
            connect_timeout=10,
        )

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
