CREATE TABLE travaux_indexation (
    id uuid PRIMARY KEY,
    document_id uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    revision integer NOT NULL,
    chunks jsonb NOT NULL,
    espace_embedding text NOT NULL,
    statut text NOT NULL DEFAULT 'attente' CHECK (statut IN ('attente','en_cours','termine','erreur')),
    proprietaire uuid,
    expire_le timestamptz,
    tentatives integer NOT NULL DEFAULT 0,
    cree_le timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX un_travail_actif_par_document ON travaux_indexation(document_id)
    WHERE statut IN ('attente','en_cours');
CREATE INDEX travaux_a_traiter ON travaux_indexation(statut, expire_le, cree_le);
-- Transition depuis la première version : seuls les anciens travaux sans journal sont relançables.
UPDATE documents SET statut='erreur', erreur='Ancienne indexation interrompue. Relancez-la.'
WHERE statut='indexation';
