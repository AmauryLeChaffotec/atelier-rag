"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  Braces,
  Check,
  Database,
  FileText,
  GitBranch,
  Layers,
  MessageSquare,
  Search,
  Sparkles,
} from "lucide-react";
import { api, erreurTexte } from "@/bibliotheque/api";
import { Chunk, Trace } from "@/bibliotheque/types";
import {
  CarteSource,
  Entete,
  Erreur,
  Markdown,
  SourceOuverte,
  Vide,
} from "./communs";

const statuts: Record<string, string> = {
  termine: "Terminé",
  en_cours: "En cours",
  interrompu: "Interrompu",
  erreur: "Erreur",
};

export function Explorateur() {
  const [executions, setExecutions] = useState<
    { id: string; question: string; strategie: string; statut: string }[]
  >([]);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [etape, setEtape] = useState(0);
  const [source, setSource] = useState<Chunk | null>(null);
  const [erreur, setErreur] = useState("");
  async function ouvrir(id: string) {
    if (!id) return;
    try {
      setTrace(await api<Trace>(`/executions/${id}`));
    } catch (e) {
      setErreur(erreurTexte(e));
    }
  }
  useEffect(() => {
    api<typeof executions>("/executions")
      .then((r) => {
        setExecutions(r);
        const id =
          new URLSearchParams(location.search).get("execution") || r[0]?.id;
        if (id) ouvrir(id);
      })
      .catch((e) => setErreur(erreurTexte(e)));
  }, []);
  const etapes = [
    { titre: "Question", sous: "Ce que vous cherchez", icone: MessageSquare },
    { titre: "Routing", sous: "Technologie & stratégie", icone: GitBranch },
    {
      titre: "Embedding",
      sous: "La question devient un vecteur",
      icone: Braces,
    },
    { titre: "Retrieval", sous: "La recherche dans pgvector", icone: Database },
    {
      titre: "Passages & scores",
      sous: "La sélection documentaire",
      icone: Search,
    },
    { titre: "Contexte", sous: "Les preuves réunies", icone: Layers },
    {
      titre: "Prompt",
      sous: "L’instruction envoyée au modèle",
      icone: FileText,
    },
    {
      titre: "Réponse & sources",
      sous: "Le résultat vérifiable",
      icone: Sparkles,
    },
  ];
  return (
    <div className="page">
      <Entete
        numero="04"
        etiquette="PIPELINE EXPLORER"
        titre="Suivez le fil de la réponse."
        description="Une vue ouverte sur le RAG. Chaque étape, chaque décision, chaque passage utilisé."
      />
      <Erreur message={erreur} />
      <div className="panneau select-document">
        <GitBranch size={22} />
        <label>
          Conversation à explorer
          <select
            value={trace?.id || ""}
            onChange={(e) => ouvrir(e.target.value)}
          >
            <option value="">Choisir une exécution</option>
            {executions.map((r) => (
              <option key={r.id} value={r.id}>
                {r.question} · {r.strategie} · {statuts[r.statut] || r.statut}
              </option>
            ))}
          </select>
        </label>
        {trace && (
          <span className="pastille">
            {trace.durees.total?.toFixed(2) || "—"} s au total
          </span>
        )}
      </div>
      {!trace ? (
        <Vide
          titre="Les coulisses de votre prochaine réponse."
          texte="Posez une question dans le chat. Son exécution apparaîtra ici avec les données réellement utilisées."
        >
          <Link className="bouton primaire" href="/">
            Poser une question <ArrowRight size={15} />
          </Link>
        </Vide>
      ) : (
        <>
          <div className="bandeau-execution">
            <div>
              <span className="surtitre">QUESTION ORIGINALE</span>
              <h2>{trace.question}</h2>
            </div>
            <span className="etiquette">{trace.strategie} RAG</span>
            <span
              className={`statut ${trace.statut === "erreur" ? "erreur" : "indexe"}`}
            >
              {statuts[trace.statut] || trace.statut}
            </span>
          </div>
          <div className="grille-pipeline">
            <nav className="etapes-pipeline" aria-label="Étapes du pipeline">
              {etapes.map((e, i) => (
                <button
                  key={e.titre}
                  className={etape === i ? "active" : ""}
                  onClick={() => setEtape(i)}
                >
                  <span className="icone-etape">
                    <e.icone size={18} />
                  </span>
                  <span>
                    <small>0{i + 1}</small>
                    <strong>{e.titre}</strong>
                    <small>{e.sous}</small>
                  </span>
                  <ArrowRight size={14} />
                </button>
              ))}
            </nav>
            <section className="panneau inspection-pipeline">
              <span className="surtitre">ÉTAPE 0{etape + 1} / 08</span>
              <h2>{etapes[etape].titre}</h2>
              <p>{etapes[etape].sous}</p>
              {etape === 0 && (
                <>
                  <blockquote>{trace.question}</blockquote>
                  <p>
                    Cette question est conservée telle qu’elle a été envoyée,
                    pour rendre l’exécution consultable.
                  </p>
                </>
              )}
              {etape === 1 && (
                <>
                  <div className="decision">
                    <Check size={19} />
                    <div>
                      <b>
                        Recherche documentaire nécessaire :{" "}
                        {trace.retrieval_necessaire ? "OUI" : "NON"}
                      </b>
                      <p>{trace.raison_decision}</p>
                    </div>
                  </div>
                  <div className="petites-infos">
                    <span>
                      {trace.routage.technologies.join(" + ") ||
                        "Toutes les technologies"}
                    </span>
                    <span>{trace.routage.version || "Versions courantes"}</span>
                    <span>{trace.routage.methode}</span>
                  </div>
                  <p>{trace.routage.raison}</p>
                  {trace.strategie === "standard" && (
                    <p>
                      En Standard RAG, la détection de technologie est
                      informative. Les filtres choisis restent appliqués.
                    </p>
                  )}
                  {trace.branches.length > 1 && (
                    <>
                      <h3>Les sous-questions</h3>
                      {trace.branches.map((b, i) => (
                        <div className="branche" key={i}>
                          <GitBranch size={17} />
                          <div>
                            <strong>Branche {i + 1}</strong>
                            <p>{b.question}</p>
                            <small>
                              {b.resultats.length} passages ·{" "}
                              {b.routage.technologies.join(", ")}
                            </small>
                          </div>
                        </div>
                      ))}
                    </>
                  )}
                </>
              )}
              {etape === 2 && (
                <>
                  <p>
                    Le modèle d’embedding transforme la question en une liste de
                    nombres. Elle peut être comparée aux vecteurs des documents
                    du même modèle.
                  </p>
                  {trace.branches.map((b, i) => (
                    <div className="carte-mesure" key={i}>
                      <b>{b.dimension}</b>
                      <span>dimensions · {b.espace_embedding}</span>
                      <span>{b.durees.embedding} s</span>
                    </div>
                  ))}
                  {!trace.branches.length && (
                    <p>Étape ignorée pour cet échange conversationnel.</p>
                  )}
                  <p className="texte-secondaire">
                    Les vecteurs complets restent dans PostgreSQL ; seules leur
                    dimension et leur provenance sont tracées ici.
                  </p>
                </>
              )}
              {etape === 3 && (
                <>
                  <p>
                    pgvector compare les embeddings avec la distance cosinus.
                    Les filtres sont appliqués avant la sélection du top K.
                  </p>
                  <pre>
                    {
                      "score = 1 - (embedding_document <=> embedding_question)\nORDER BY score DESC\nLIMIT top_k"
                    }
                  </pre>
                  {trace.branches.map((b, i) => (
                    <details open key={i}>
                      <summary>
                        Filtres de la branche {i + 1} · {b.durees.retrieval} s
                      </summary>
                      <pre>{JSON.stringify(b.filtres, null, 2)}</pre>
                    </details>
                  ))}
                </>
              )}
              {etape === 4 && (
                <>
                  <p>
                    Ces passages ont été retrouvés avant la construction du
                    contexte. En Branching RAG, les doublons sont fusionnés en
                    conservant leur meilleur score.
                  </p>
                  {trace.branches.map((b, i) => (
                    <div key={i}>
                      <h3>Branche {i + 1}</h3>
                      <div className="grille-sources">
                        {b.resultats.map((c) => (
                          <CarteSource
                            key={c.id}
                            source={c}
                            ouvrir={setSource}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                  {!trace.branches.length && (
                    <p>Aucun retrieval pour cette exécution.</p>
                  )}
                </>
              )}
              {etape === 5 && (
                <>
                  <p>
                    Les passages entiers sont assemblés dans la limite du
                    contexte configurée. Chaque numéro correspond à une source
                    consultable.
                  </p>
                  <pre>
                    {trace.contexte ||
                      "Aucun contexte documentaire pour cette exécution."}
                  </pre>
                  <span className="pastille">
                    {trace.contexte?.length || 0} caractères ·{" "}
                    {trace.sources.length} sources
                  </span>
                </>
              )}
              {etape === 6 && (
                <>
                  <p>
                    Voici les messages exacts préparés pour{" "}
                    {trace.modele_generation}, dont l’historique limité aux six
                    derniers messages.
                  </p>
                  {trace.prompt?.map((m, i) => (
                    <div key={i}>
                      <h4 className="role-prompt">{m.role}</h4>
                      <pre>{m.content}</pre>
                    </div>
                  ))}
                </>
              )}
              {etape === 7 && (
                <>
                  <Markdown
                    texte={
                      trace.reponse || trace.erreur || "Réponse interrompue."
                    }
                  />
                  <h3>Sources transmises au modèle</h3>
                  <div className="grille-sources">
                    {trace.sources.map((c) => (
                      <CarteSource key={c.id} source={c} ouvrir={setSource} />
                    ))}
                  </div>
                  {trace.verification_citations && (
                    <details>
                      <summary>Vérification des citations</summary>
                      <pre>
                        {JSON.stringify(trace.verification_citations, null, 2)}
                      </pre>
                      <p>
                        Un numéro valide ne garantit pas qu’une affirmation est
                        exacte. Consultez toujours le passage.
                      </p>
                    </details>
                  )}
                  <div className="petites-infos">
                    {Object.entries(trace.durees).map(([nom, v]) => (
                      <span key={nom}>
                        {nom} : {v} s
                      </span>
                    ))}
                  </div>
                  {trace.usage_generation && (
                    <p className="texte-secondaire">
                      Usage retourné par le fournisseur :{" "}
                      {trace.usage_generation.entree} tokens d’entrée,{" "}
                      {trace.usage_generation.sortie} tokens de sortie pour la
                      génération finale.
                    </p>
                  )}
                </>
              )}
              {trace.avertissement && (
                <p className="avertissement">{trace.avertissement}</p>
              )}
              <div className="navigation-etapes">
                <button
                  className="bouton secondaire"
                  disabled={etape === 0}
                  onClick={() => setEtape((e) => e - 1)}
                >
                  Étape précédente
                </button>
                <button
                  className="bouton primaire"
                  disabled={etape === 7}
                  onClick={() => setEtape((e) => e + 1)}
                >
                  Étape suivante <ArrowRight size={15} />
                </button>
              </div>
            </section>
          </div>
        </>
      )}
      <SourceOuverte source={source} fermer={() => setSource(null)} />
    </div>
  );
}
