"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BookOpen,
  Check,
  ChevronDown,
  GitBranch,
  History,
  Layers,
  Plus,
  SlidersHorizontal,
  Sparkles,
  Square,
} from "lucide-react";
import { api, erreurTexte, flux } from "@/bibliotheque/api";
import {
  Chunk,
  Filtres as TypeFiltres,
  Message,
  Trace,
  filtresInitiaux,
} from "@/bibliotheque/types";
import { CarteSource, Erreur, Markdown, SourceOuverte } from "./communs";
import { Filtres } from "./filtres";
import { useConfiguration } from "./cadre";

const suggestions = [
  "Comment créer un context manager en Python ?",
  "À quoi sert le chunking dans un RAG ?",
  "Compare les documentations de React et Next.js.",
];
const etapes = [
  { nom: "Votre question", texte: "Le point de départ", icone: Sparkles },
  {
    nom: "Recherche documentaire",
    texte: "Les passages les plus proches",
    icone: BookOpen,
  },
  {
    nom: "Contexte & génération",
    texte: "Une réponse ancrée dans vos sources",
    icone: Layers,
  },
  {
    nom: "Réponse & citations",
    texte: "Des explications vérifiables",
    icone: Check,
  },
];
export function Conversation() {
  const config = useConfiguration();
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [actif, setActif] = useState(false);
  const [erreur, setErreur] = useState("");
  const [conversation, setConversation] = useState<string | null>(null);
  const [conversations, setConversations] = useState<
    { id: string; titre: string }[]
  >([]);
  const [historique, setHistorique] = useState(false);
  const [strategie, setStrategie] = useState("standard");
  const [filtres, setFiltres] = useState<TypeFiltres>(filtresInitiaux);
  const [reglages, setReglages] = useState(false);
  const [source, setSource] = useState<Chunk | null>(null);
  const [trace, setTrace] = useState<Trace | null>(null);
  const annulation = useRef<AbortController | null>(null);
  const fin = useRef<HTMLDivElement>(null);
  useEffect(() => {
    api<{ id: string; titre: string }[]>("/conversations")
      .then(setConversations)
      .catch(() => {});
  }, [actif]);
  useEffect(() => {
    fin.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages.length]);
  useEffect(() => () => annulation.current?.abort(), []);
  async function envoyer() {
    if (!question.trim() || actif) return;
    const texte = question.trim();
    const identifiant = crypto.randomUUID();
    setErreur("");
    setActif(true);
    setQuestion("");
    setTrace(null);
    setMessages((m) => [
      ...m,
      { id: crypto.randomUUID(), role: "user", contenu: texte },
      { id: identifiant, role: "assistant", contenu: "" },
    ]);
    annulation.current = new AbortController();
    const modifier = (modification: Partial<Message>) =>
      setMessages((m) =>
        m.map((message) =>
          message.id === identifiant
            ? { ...message, ...modification }
            : message,
        ),
      );
    try {
      await flux(
        {
          ...filtres,
          question: texte,
          strategie,
          conversation_id: conversation,
        },
        (type, evenement) => {
          const donnees = evenement as {
            conversation_id: string;
            execution_id: string;
            texte: string;
            sources: Chunk[];
            trace: Trace;
            message: string;
          };
          if (type === "debut") {
            setConversation(donnees.conversation_id);
            modifier({ execution_id: donnees.execution_id });
          }
          if (type === "sources") {
            modifier({ sources: donnees.sources });
            setTrace(donnees.trace);
          }
          if (type === "texte")
            setMessages((m) =>
              m.map((message) =>
                message.id === identifiant
                  ? { ...message, contenu: message.contenu + donnees.texte }
                  : message,
              ),
            );
          if (type === "fin") setTrace(donnees.trace);
          if (type === "erreur") setErreur(donnees.message);
        },
        annulation.current.signal,
      );
    } catch (e) {
      setErreur(
        e instanceof Error && e.name === "AbortError"
          ? "Génération interrompue. La réponse partielle reste consultable."
          : erreurTexte(e),
      );
    } finally {
      setActif(false);
    }
  }
  return (
    <div className="page-conversation">
      <div className="outils-conversation">
        <span className="surtitre">VOTRE ESPACE DE CONNAISSANCE</span>
        <div>
          <button
            className="bouton discret"
            onClick={() => setHistorique(!historique)}
          >
            <History size={16} /> Historique
          </button>
          <button
            className="bouton discret"
            disabled={actif}
            onClick={() => {
              setMessages([]);
              setConversation(null);
              setTrace(null);
              setErreur("");
            }}
          >
            <Plus size={16} /> Nouvelle conversation
          </button>
        </div>
      </div>
      {historique && (
        <div className="historique panneau">
          <h3>Vos conversations</h3>
          {!conversations.length && <p>Aucune conversation pour le moment.</p>}
          {conversations.map((c) => (
            <button
              key={c.id}
              disabled={actif}
              onClick={async () => {
                try {
                  setMessages(await api<Message[]>(`/conversations/${c.id}`));
                  setConversation(c.id);
                  setTrace(null);
                  setHistorique(false);
                } catch (e) {
                  setErreur(erreurTexte(e));
                }
              }}
            >
              {c.titre}
              <ArrowRight size={15} />
            </button>
          ))}
        </div>
      )}
      <div className="grille-conversation">
        <section className="zone-conversation">
          {!messages.length ? (
            <div className="accueil-conversation">
              <div className="label-accueil">
                <span className="petite-etoile">✳</span> Moins de recherche.
                Plus de compréhension.
              </div>
              <h1>
                Votre documentation.
                <br />
                <span>Des réponses sourcées.</span>
              </h1>
              <p>
                Posez une question à vos documents.
                <br />
                Découvrez la réponse, ses sources et le chemin qui les relie.
              </p>
              <div className="suggestions">
                {suggestions.map((s, i) => (
                  <button key={s} onClick={() => setQuestion(s)}>
                    <span>0{i + 1}</span>
                    {s}
                    <ArrowUp size={16} />
                  </button>
                ))}
              </div>
              <Link href="/documentation" className="lien-texte">
                <Plus size={15} /> Commencez par ajouter une documentation
              </Link>
            </div>
          ) : (
            <div className="messages">
              {messages.map((m) => (
                <article key={m.id} className={`message ${m.role}`}>
                  <div className="identite-message">
                    {m.role === "user" ? (
                      <span className="avatar">V</span>
                    ) : (
                      <span className="avatar assistant">✳</span>
                    )}
                    <strong>{m.role === "user" ? "Vous" : "Atelier"}</strong>
                    {m.role === "assistant" && (
                      <span className="modele-message">
                        {config?.generation}
                      </span>
                    )}
                  </div>
                  {m.contenu ? (
                    <Markdown texte={m.contenu} />
                  ) : actif ? (
                    <div className="chargement">
                      <span />
                      <span />
                      <span /> Lecture de la documentation…
                    </div>
                  ) : (
                    <p className="texte-secondaire">Aucune réponse générée.</p>
                  )}
                  {m.sources && m.sources.length > 0 && (
                    <div className="sources-message">
                      <span className="petit-titre">
                        {m.sources.length} passages dans le contexte
                      </span>
                      <div className="grille-sources">
                        {m.sources.map((s) => (
                          <CarteSource
                            key={s.id}
                            source={s}
                            ouvrir={setSource}
                          />
                        ))}
                      </div>
                    </div>
                  )}
                  {m.execution_id && m.contenu && (
                    <Link
                      className="lien-texte"
                      href={`/pipeline?execution=${m.execution_id}`}
                    >
                      <GitBranch size={14} /> Explorer cette réponse{" "}
                      <ArrowRight size={14} />
                    </Link>
                  )}
                </article>
              ))}
              <div ref={fin} />
            </div>
          )}
          <div className="composeur-zone">
            <Erreur message={erreur} />
            {reglages && (
              <div className="panneau reglages-conversation">
                <Filtres valeur={filtres} changer={setFiltres} avance />
              </div>
            )}
            <form
              className="composeur"
              onSubmit={(e) => {
                e.preventDefault();
                envoyer();
              }}
            >
              <label className="sr-seulement" htmlFor="question">
                Votre question
              </label>
              <textarea
                id="question"
                placeholder="Que souhaitez-vous comprendre ?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                rows={2}
                maxLength={4000}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    envoyer();
                  }
                }}
              />
              <div className="outils-composeur">
                <label className="select-strategie">
                  <GitBranch size={14} />
                  <select
                    aria-label="Stratégie RAG"
                    disabled={actif}
                    value={strategie}
                    onChange={(e) => setStrategie(e.target.value)}
                  >
                    <option value="standard">Standard RAG</option>
                    <option value="routing">Routing RAG</option>
                    <option value="branching">Branching RAG</option>
                    <option value="adaptive">Adaptive RAG</option>
                  </select>
                  <ChevronDown size={12} />
                </label>
                <button
                  type="button"
                  className={`bouton discret ${reglages ? "selectionne" : ""}`}
                  onClick={() => setReglages(!reglages)}
                  aria-expanded={reglages}
                >
                  <SlidersHorizontal size={15} /> Filtres
                </button>
                {actif ? (
                  <button
                    className="envoyer"
                    type="button"
                    aria-label="Arrêter la génération"
                    onClick={() => annulation.current?.abort()}
                  >
                    <Square size={17} />
                  </button>
                ) : (
                  <button
                    className="envoyer"
                    disabled={!question.trim()}
                    aria-label="Envoyer la question"
                  >
                    <ArrowUp size={20} />
                  </button>
                )}
              </div>
            </form>
            <p className="note-composeur">
              <span className="voyant" />
              {config?.fournisseur === "openai"
                ? "Génération via l’API OpenAI"
                : "Vos modèles s’exécutent sur votre ordinateur"}
              <span>Entrée pour envoyer ↵</span>
            </p>
          </div>
        </section>
        <aside className="explication-conversation">
          <span className="surtitre">LA RÉPONSE A UN CHEMIN</span>
          <h2>Rien dans l’ombre.</h2>
          <p>Un RAG retrouve les bons passages avant de rédiger sa réponse.</p>
          <div className="chemin-rag">
            {etapes.map((etape, i) => (
              <div key={etape.nom} className={actif ? "etape animee" : "etape"}>
                <span className="icone-etape">
                  <etape.icone size={17} />
                </span>
                <div>
                  <span className="numero-etape">0{i + 1}</span>
                  <h4>{etape.nom}</h4>
                  <p>{etape.texte}</p>
                </div>
                {i < 3 && <ArrowDown className="fleche-etape" size={13} />}
              </div>
            ))}
          </div>
          {trace && (
            <div className="resume-trace">
              <span className="pastille">
                {trace.sources.length} sources retrouvées
              </span>
              <p>{trace.raison_decision}</p>
              {trace.verification_citations &&
                (trace.verification_citations.absence ||
                  trace.verification_citations.hors_sources.length > 0) && (
                  <p className="erreur">
                    Les citations de cette réponse nécessitent une vérification.
                  </p>
                )}
            </div>
          )}
          <Link
            href={trace ? `/pipeline?execution=${trace.id}` : "/pipeline"}
            className="bouton secondaire"
          >
            Voir le pipeline <ArrowUpRightLocal />
          </Link>
          <div className="info-embedding">
            <span>SOUS LE CAPOT</span>
            <p>
              <b>Embedding</b>
              <br />
              {config?.embedding || "Chargement…"}
            </p>
            <p>
              <b>Génération</b>
              <br />
              {config?.generation || "Chargement…"}
            </p>
            <span className="stockage-label">
              <span className="voyant" /> PostgreSQL + pgvector
            </span>
          </div>
        </aside>
      </div>
      <SourceOuverte source={source} fermer={() => setSource(null)} />
    </div>
  );
}
function ArrowUpRightLocal() {
  return <ArrowUp size={15} style={{ transform: "rotate(45deg)" }} />;
}
