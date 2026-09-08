from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


class Section(BaseModel):
    contenu: str
    titres: list[str] = []
    page: int | None = None
    type_contenu: str = "texte"
    visuel: str | None = None
    modele_ocr: str | None = None


class ParametresChunking(BaseModel):
    strategie: Literal["recursif", "taille", "paragraphes", "titres", "markdown", "semantique"] = "titres"
    taille: int = Field(1000, ge=100, le=6000)
    overlap: int = Field(120, ge=0, le=1000)
    taille_min: int = Field(80, ge=0, le=2000)
    taille_max: int = Field(2000, ge=100, le=12000)
    separateurs: list[str] = ["\n\n", "\n", ". ", " "]
    preserver_code: bool = True
    seuil_semantique: float = Field(0.72, ge=0, le=1)

    @model_validator(mode="after")
    def verifier(self):
        if self.overlap >= self.taille:
            raise ValueError("L’overlap doit être inférieur à la taille du chunk.")
        if not self.taille_min <= self.taille <= self.taille_max:
            raise ValueError("Respectez taille minimale ≤ taille cible ≤ taille maximale.")
        if any(not s for s in self.separateurs) or len(self.separateurs) > 10:
            raise ValueError("Indiquez au plus 10 séparateurs non vides.")
        return self


class Chunk(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    contenu: str = Field(min_length=1, max_length=12000)
    metadata: dict = Field(default_factory=dict)


class Apercu(BaseModel):
    parametres: ParametresChunking
    revision: int


class Indexation(BaseModel):
    revision: int
    chunks: list[Chunk] = Field(min_length=1, max_length=500)


class SourceURL(BaseModel):
    url: str = Field(max_length=2000)
    titre: str = Field(min_length=1, max_length=200)
    technologie: str = Field(min_length=1, max_length=60)
    version: str = Field(min_length=1, max_length=40)
    type_documentation: str = Field("documentation", min_length=1, max_length=60)


class Recherche(BaseModel):
    question: str = Field(min_length=2, max_length=4000)
    top_k: int = Field(5, ge=1, le=12)
    seuil: float = Field(0.25, ge=-1, le=1)
    technologie: str | None = Field(None, max_length=60)
    version: str | None = Field(None, max_length=40)
    document_id: UUID | None = None
    type_documentation: str | None = Field(None, max_length=60)
    metadata: dict = Field(default_factory=dict)
    versions_courantes: bool = True


class Question(Recherche):
    strategie: Literal["standard", "routing", "branching", "adaptive"] = "standard"
    conversation_id: UUID | None = None


class VersionCourante(BaseModel):
    version: str = Field(min_length=1, max_length=40)


class DescriptionVisuelle(BaseModel):
    revision: int = Field(ge=1)
    description: str = Field(min_length=5, max_length=10000)


class LectureOCR(BaseModel):
    revision: int = Field(ge=1)
    pages: list[Annotated[int, Field(ge=1, le=150)]] | None = Field(None, min_length=1, max_length=150)
