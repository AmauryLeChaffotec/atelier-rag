CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE technologies (
    nom text PRIMARY KEY,
    version_courante text NOT NULL
);
CREATE TABLE documents (
    id uuid PRIMARY KEY,
    titre text NOT NULL,
    technologie text NOT NULL REFERENCES technologies(nom),
    version text NOT NULL,
    type_source text NOT NULL,
    url_source text,
    nom_fichier text,
    cle_fichier text NOT NULL,
    type_documentation text NOT NULL DEFAULT 'documentation',
    statut text NOT NULL DEFAULT 'brouillon',
    erreur text,
    sections jsonb NOT NULL,
    brouillon jsonb NOT NULL DEFAULT '[]',
    revision integer NOT NULL DEFAULT 1,
    parametres_chunking jsonb NOT NULL DEFAULT '{}',
    modele_embedding text,
    espace_embedding text,
    nombre_chunks integer NOT NULL DEFAULT 0,
    cree_le timestamptz NOT NULL DEFAULT now(),
    indexe_le timestamptz
);
CREATE TABLE versions_document (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    revision integer NOT NULL,
    espace_embedding text NOT NULL,
    nombre_chunks integer NOT NULL,
    cree_le timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE chunks (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    contenu text NOT NULL,
    metadata jsonb NOT NULL,
    embedding vector NOT NULL,
    dimension integer NOT NULL,
    espace_embedding text NOT NULL,
    cree_le timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX chunks_document ON chunks(document_id);
CREATE INDEX chunks_espace ON chunks(espace_embedding, dimension);
CREATE INDEX chunks_metadata ON chunks USING gin(metadata);
CREATE INDEX documents_filtres ON documents(technologie, version, type_documentation);
CREATE TABLE conversations (
    id uuid PRIMARY KEY,
    titre text NOT NULL,
    cree_le timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE executions_retrieval (
    id uuid PRIMARY KEY,
    conversation_id uuid REFERENCES conversations(id) ON DELETE SET NULL,
    question text NOT NULL,
    strategie text NOT NULL,
    trace jsonb NOT NULL,
    cree_le timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE resultats_retrieval (
    execution_id uuid REFERENCES executions_retrieval(id) ON DELETE CASCADE,
    rang integer NOT NULL,
    chunk_id uuid,
    score double precision NOT NULL,
    instantane jsonb NOT NULL,
    PRIMARY KEY(execution_id, rang)
);
CREATE TABLE messages (
    id uuid PRIMARY KEY,
    conversation_id uuid NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role text NOT NULL CHECK(role IN ('user','assistant')),
    contenu text NOT NULL,
    execution_id uuid REFERENCES executions_retrieval(id) ON DELETE SET NULL,
    cree_le timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX messages_conversation ON messages(conversation_id, cree_le);
