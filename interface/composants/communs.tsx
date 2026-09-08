"use client";
import { useEffect, useRef } from "react";
import { ArrowUpRight, FileText, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Chunk } from "@/bibliotheque/types";

export function Entete({
  numero,
  etiquette,
  titre,
  description,
  action,
}: {
  numero: string;
  etiquette: string;
  titre: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="entete-page">
      <div>
        <span className="surtitre">
          <span>{numero}</span> {etiquette}
        </span>
        <h1>{titre}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Erreur({ message }: { message: string }) {
  return message ? (
    <div className="erreur" role="alert">
      {message}
    </div>
  ) : null;
}
export function Vide({
  titre,
  texte,
  children,
}: {
  titre: string;
  texte: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="etat-vide">
      <div className="icone-vide">
        <FileText size={26} />
      </div>
      <h3>{titre}</h3>
      <p>{texte}</p>
      {children}
    </div>
  );
}
export function Markdown({ texte }: { texte: string }) {
  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {texte}
      </ReactMarkdown>
    </div>
  );
}
export function CarteSource({
  source,
  ouvrir,
}: {
  source: Chunk;
  ouvrir: (source: Chunk) => void;
}) {
  const m = source.metadata;
  return (
    <button className="carte-source" onClick={() => ouvrir(source)}>
      <div>
        <span className="numero-source">
          {source.citation || m.chunk_index + 1}
        </span>
        <span className="etiquette">
          {m.technology} <b>{m.version}</b>
        </span>
        {source.score !== undefined && (
          <span className="score">{source.score.toFixed(3)}</span>
        )}
      </div>
      <h4>{m.title || m.document_title}</h4>
      <p>
        {source.contenu.slice(0, 150)}
        {source.contenu.length > 150 ? "…" : ""}
      </p>
      <footer>
        <span>
          {m.page ? `Page ${m.page}` : m.source_type.toUpperCase()} ·{" "}
          {m.document_title}
        </span>
        <ArrowUpRight size={15} />
      </footer>
    </button>
  );
}
export function SourceOuverte({
  source,
  fermer,
}: {
  source: Chunk | null;
  fermer: () => void;
}) {
  const dialogue = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (source) dialogue.current?.showModal();
    else dialogue.current?.close();
  }, [source]);
  return (
    <dialog
      ref={dialogue}
      className="dialogue-source"
      onCancel={fermer}
      onClick={(e) => {
        if (e.target === dialogue.current) fermer();
      }}
    >
      <div className="contenu-dialogue">
        {source && (
          <>
            <button
              className="fermer bouton-icone"
              onClick={fermer}
              aria-label="Fermer la source"
            >
              <X />
            </button>
            <span className="surtitre">LE PASSAGE EXACT</span>
            <h2>{source.metadata.title}</h2>
            <p className="fil-ariane">
              {source.metadata.technology} / {source.metadata.version} /{" "}
              {source.metadata.heading_path.join(" / ")}
            </p>
            <div className="texte-source">
              <Markdown texte={source.contenu} />
            </div>
            {source.metadata.visuel && (
              <img
                className="visuel-document"
                src={`/api/documents/${source.metadata.document_id}/visuels/${source.metadata.page}`}
                alt={`Visuel de la page ${source.metadata.page}`}
                loading="lazy"
              />
            )}
            <div className="petites-infos">
              <span>
                {source.metadata.page
                  ? `Page ${source.metadata.page}`
                  : source.metadata.source_type}
              </span>
              <span>{source.contenu.length} caractères</span>
              <span>
                ≈ {Math.ceil(source.contenu.length / 4)} tokens (estimation)
              </span>
            </div>
            {source.metadata.source_url &&
              /^https?:\/\//.test(source.metadata.source_url) && (
                <a
                  className="lien-texte"
                  href={source.metadata.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Consulter la page originale <ArrowUpRight size={15} />
                </a>
              )}
            <details>
              <summary>Métadonnées du chunk</summary>
              <pre>{JSON.stringify(source.metadata, null, 2)}</pre>
            </details>
          </>
        )}
      </div>
    </dialog>
  );
}
