"use client";
import { useEffect, useState } from "react";
import { api } from "@/bibliotheque/api";
import {
  Documentation,
  Filtres as TypeFiltres,
  Technologie,
} from "@/bibliotheque/types";
export function Filtres({
  valeur,
  changer,
  avance = false,
}: {
  valeur: TypeFiltres;
  changer: (valeur: TypeFiltres) => void;
  avance?: boolean;
}) {
  const [technologies, setTechnologies] = useState<Technologie[]>([]);
  const [documents, setDocuments] = useState<Documentation[]>([]);
  const [meta, setMeta] = useState("{}");
  const [erreur, setErreur] = useState("");
  useEffect(() => {
    api<Technologie[]>("/technologies")
      .then(setTechnologies)
      .catch(() => {});
    api<Documentation[]>("/documents")
      .then(setDocuments)
      .catch(() => {});
  }, []);
  const modifier = (attribut: string, v: unknown) =>
    changer({ ...valeur, [attribut]: v });
  const versions = technologies.find((t) => t.nom === valeur.technologie)
    ?.versions || [...new Set(documents.map((d) => d.version))];
  return (
    <div className="filtres">
      <label>
        Technologie
        <select
          value={valeur.technologie || ""}
          onChange={(e) =>
            changer({
              ...valeur,
              technologie: e.target.value || null,
              version: null,
              document_id: null,
            })
          }
        >
          <option value="">Toutes les technologies</option>
          {technologies.map((t) => (
            <option key={t.nom}>{t.nom}</option>
          ))}
        </select>
      </label>
      <label>
        Version
        <select
          value={valeur.version || ""}
          onChange={(e) => modifier("version", e.target.value || null)}
        >
          <option value="">
            {valeur.versions_courantes
              ? "Versions courantes"
              : "Toutes les versions"}
          </option>
          {versions.map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </label>
      <label>
        Passages (top K)
        <input
          type="number"
          min={1}
          max={12}
          value={valeur.top_k}
          onChange={(e) => modifier("top_k", Number(e.target.value))}
        />
      </label>
      {avance && (
        <>
          <label>
            Seuil de similarité · {valeur.seuil.toFixed(2)}
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={valeur.seuil}
              onChange={(e) => modifier("seuil", Number(e.target.value))}
            />
          </label>
          <label>
            Documentation
            <select
              value={valeur.document_id || ""}
              onChange={(e) => modifier("document_id", e.target.value || null)}
            >
              <option value="">Toutes les documentations</option>
              {documents
                .filter(
                  (d) =>
                    !valeur.technologie || d.technologie === valeur.technologie,
                )
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.titre} · {d.version}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Type de documentation
            <select
              value={valeur.type_documentation || ""}
              onChange={(e) =>
                modifier("type_documentation", e.target.value || null)
              }
            >
              <option value="">Tous les types</option>
              {[...new Set(documents.map((d) => d.type_documentation))].map(
                (t) => (
                  <option key={t}>{t}</option>
                ),
              )}
            </select>
          </label>
          <label className="case">
            <input
              type="checkbox"
              checked={valeur.versions_courantes}
              onChange={(e) => modifier("versions_courantes", e.target.checked)}
            />{" "}
            Utiliser les versions courantes par défaut
          </label>
          <label>
            Filtres metadata (JSON)
            <textarea
              value={meta}
              rows={2}
              onChange={(e) => {
                setMeta(e.target.value);
                try {
                  const donnees = JSON.parse(e.target.value);
                  if (
                    !donnees ||
                    Array.isArray(donnees) ||
                    typeof donnees !== "object"
                  )
                    throw new Error();
                  modifier("metadata", donnees);
                  setErreur("");
                } catch {
                  setErreur(
                    "Objet JSON invalide ; les derniers filtres valides restent appliqués.",
                  );
                }
              }}
            />
          </label>
          {erreur && <small className="erreur">{erreur}</small>}
        </>
      )}
    </div>
  );
}
