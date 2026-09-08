export type Metadata = {
  document_id: string;
  chunk_id: string;
  technology: string;
  version: string;
  source_type: string;
  source_url?: string;
  filename?: string;
  document_title: string;
  title: string;
  subtitle: string;
  heading_path: string[];
  page?: number;
  content_type: string;
  chunk_index: number;
  chunking_strategy: string;
  embedding_model?: string;
  visuel?: string;
  caracteres: number;
  tokens_estimes: number;
};
export type Chunk = {
  id: string;
  contenu: string;
  metadata: Metadata;
  score?: number;
  citation?: number;
};
export type Parametres = {
  strategie: string;
  taille: number;
  overlap: number;
  taille_min: number;
  taille_max: number;
  separateurs: string[];
  preserver_code: boolean;
  seuil_semantique: number;
};
export type Documentation = {
  id: string;
  titre: string;
  technologie: string;
  version: string;
  type_source: string;
  url_source?: string;
  nom_fichier: string;
  type_documentation: string;
  statut: string;
  erreur?: string;
  revision: number;
  nombre_chunks: number;
  nombre_sections: number;
  modele_embedding?: string;
  espace_embedding?: string;
  cree_le: string;
  indexe_le?: string;
  parametres_chunking: Parametres;
  brouillon: Chunk[];
  sections: {
    contenu: string;
    titres: string[];
    page?: number;
    type_contenu: string;
    visuel?: string;
    description_visuelle?: string;
  }[];
};
export type Technologie = {
  nom: string;
  version_courante: string;
  versions: string[];
};
export type Configuration = {
  fournisseur: string;
  embedding: string;
  generation: string;
  espace_embedding: string;
  taille_fichier_mo: number;
  authentification: boolean;
  ocr_disponible: boolean;
  modele_ocr: string;
};
export type Filtres = {
  top_k: number;
  seuil: number;
  technologie: string | null;
  version: string | null;
  type_documentation: string | null;
  document_id: string | null;
  versions_courantes: boolean;
  metadata: Record<string, unknown>;
};
export type Routage = {
  technologies: string[];
  version?: string;
  raison: string;
  methode: string;
};
export type ResultatRecherche = {
  resultats: Chunk[];
  durees: Record<string, number>;
  dimension: number;
  espace_embedding: string;
  filtres: Record<string, unknown>;
  routage?: Routage;
};
export type Trace = {
  id: string;
  question: string;
  strategie: string;
  reponse: string;
  sources: Chunk[];
  statut: string;
  branches: (ResultatRecherche & { question: string; routage: Routage })[];
  durees: Record<string, number>;
  routage: Routage;
  retrieval_necessaire: boolean;
  raison_decision: string;
  contexte: string;
  prompt: { role: string; content: string }[];
  fournisseur: string;
  modele_generation: string;
  usage_generation?: { entree: number; sortie: number };
  erreur?: string;
  avertissement?: string;
  verification_citations?: { absence: boolean; hors_sources: number[] };
};
export type Message = {
  id: string;
  role: string;
  contenu: string;
  execution_id?: string;
  sources?: Chunk[];
};
export const filtresInitiaux: Filtres = {
  top_k: 5,
  seuil: 0.25,
  technologie: null,
  version: null,
  type_documentation: null,
  document_id: null,
  versions_courantes: true,
  metadata: {},
};
