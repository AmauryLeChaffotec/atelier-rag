"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import {
  BookOpen,
  Boxes,
  ChevronRight,
  GitBranch,
  MessageSquare,
  Moon,
  Scissors,
  Search,
  Sun,
  X,
  LogOut,
  ArrowUpRight,
} from "lucide-react";
import { api } from "@/bibliotheque/api";
import { Configuration } from "@/bibliotheque/types";

const Contexte = createContext<Configuration | null>(null);
export const useConfiguration = () => useContext(Contexte);
const liens = [
  { href: "/", nom: "Conversation", sous: "Chat RAG", icone: MessageSquare },
  {
    href: "/documentation",
    nom: "Documentation",
    sous: "Vos connaissances",
    icone: BookOpen,
  },
  {
    href: "/chunking",
    nom: "Chunking",
    sous: "L’atelier de découpage",
    icone: Scissors,
  },
  {
    href: "/retrieval",
    nom: "Retrieval",
    sous: "Le laboratoire de recherche",
    icone: Search,
  },
  {
    href: "/pipeline",
    nom: "Pipeline",
    sous: "Comprendre chaque étape",
    icone: GitBranch,
  },
];
export function Cadre({ children }: { children: React.ReactNode }) {
  const chemin = usePathname();
  const [config, setConfig] = useState<Configuration | null>(null);
  const [sombre, setSombre] = useState(false);
  const [connexion, setConnexion] = useState(false);
  const [cle, setCle] = useState("");
  const [erreur, setErreur] = useState("");
  function charger() {
    api<Configuration>("/configuration")
      .then(setConfig)
      .catch(() => {});
  }
  useEffect(() => {
    charger();
    const ouvrir = () => setConnexion(true);
    window.addEventListener("connexion-requise", ouvrir);
    const theme = localStorage.getItem("atelier-theme") === "sombre";
    setSombre(theme);
    document.documentElement.dataset.theme = theme ? "sombre" : "clair";
    return () => window.removeEventListener("connexion-requise", ouvrir);
  }, []);
  function changerTheme() {
    const nouveau = !sombre;
    setSombre(nouveau);
    document.documentElement.dataset.theme = nouveau ? "sombre" : "clair";
    localStorage.setItem("atelier-theme", nouveau ? "sombre" : "clair");
  }
  return (
    <Contexte.Provider value={config}>
      <a href="#contenu" className="evitement">
        Aller au contenu
      </a>
      <div className="application">
        <aside className="navigation">
          <Link href="/" className="marque">
            <span className="symbole">
              <Boxes size={24} />
            </span>
            atelier<span className="point-marque">.</span>
          </Link>
          <div className="espace-nom">
            <span className="avatar">A</span>
            <div>
              Mon espace de travail<small>La connaissance, connectée</small>
            </div>
            <ChevronRight size={14} />
          </div>
          <span className="legende-navigation">EXPLORER</span>
          <nav aria-label="Navigation principale">
            {liens.map(({ href, nom, sous, icone: Icone }) => (
              <Link
                key={href}
                href={href}
                aria-current={chemin === href ? "page" : undefined}
                className={chemin === href ? "lien actif" : "lien"}
              >
                <Icone size={19} />
                <span>
                  {nom}
                  <small>{sous}</small>
                </span>
                {chemin === href && <span className="point" />}
              </Link>
            ))}
          </nav>
          <div className="note-navigation">
            <span className="pastille">RAG, en toute transparence</span>
            <p>
              De vos documents à une réponse.
              <br />
              Chaque étape est visible.
            </p>
            <Link href="/pipeline">
              Ouvrir le pipeline <ArrowUpRight size={15} />
            </Link>
          </div>
          <div className="pied-navigation">
            <button
              className="bouton-icone"
              onClick={changerTheme}
              aria-label={
                sombre ? "Activer le thème clair" : "Activer le thème sombre"
              }
            >
              {sombre ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <span>Fait pour comprendre.</span>
            {config?.authentification && (
              <button
                className="bouton-icone"
                aria-label="Se déconnecter"
                onClick={async () => {
                  await fetch("/connexion", { method: "DELETE" });
                  location.reload();
                }}
              >
                <LogOut size={17} />
              </button>
            )}
          </div>
        </aside>
        <div className="espace-principal">
          <header className="barre-superieure">
            <span>
              Mon atelier <ChevronRight size={13} />{" "}
              <strong>
                {liens.find((l) => l.href === chemin)?.nom || "Documentation"}
              </strong>
            </span>
            <div className="etat-connexion">
              <span className={config ? "voyant" : "voyant attente"} />
              {config
                ? config.fournisseur === "ollama"
                  ? "Ollama · en local"
                  : "OpenAI · API"
                : "Connexion au serveur…"}
            </div>
          </header>
          <main id="contenu">{children}</main>
        </div>
        {connexion && (
          <div className="fond-modal">
            <form
              className="modal connexion"
              onSubmit={async (e) => {
                e.preventDefault();
                setErreur("");
                const r = await fetch("/connexion", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ cle }),
                });
                if (r.ok) {
                  setCle("");
                  setConnexion(false);
                  location.reload();
                } else {
                  setErreur("Clé incorrecte ou serveur indisponible.");
                }
              }}
            >
              <button
                type="button"
                className="fermer bouton-icone"
                onClick={() => setConnexion(false)}
                aria-label="Fermer"
              >
                <X />
              </button>
              <span className="surtitre">VOTRE ESPACE PRIVÉ</span>
              <h2>Entrez dans l’atelier.</h2>
              <p>Utilisez la clé d’accès configurée pour cette application.</p>
              <label>
                Clé d’accès
                <input
                  autoFocus
                  type="password"
                  value={cle}
                  onChange={(e) => setCle(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </label>
              {erreur && (
                <p className="erreur" role="alert">
                  {erreur}
                </p>
              )}
              <button className="bouton primaire">
                Se connecter <ArrowUpRight size={16} />
              </button>
            </form>
          </div>
        )}
      </div>
    </Contexte.Provider>
  );
}
