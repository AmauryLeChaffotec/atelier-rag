"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  Check,
  FileText,
  Globe,
  Plus,
  Search,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { api, corps, erreurTexte } from "@/bibliotheque/api";
import { Documentation, Technologie } from "@/bibliotheque/types";
import { Entete, Erreur, Vide } from "./communs";
import { useConfiguration } from "./cadre";

export function Bibliotheque() {
  const config = useConfiguration();
  const [documents, setDocuments] = useState<Documentation[]>([]);
  const [technologies, setTechnologies] = useState<Technologie[]>([]);
  const [erreur, setErreur] = useState("");
  const [chargement, setChargement] = useState(true);
  const [ajout, setAjout] = useState(false);
  const [recherche, setRecherche] = useState("");
  const [technologie, setTechnologie] = useState("");
  const [version, setVersion] = useState("");
  const [supprimer, setSupprimer] = useState<Documentation | null>(null);
  async function charger() {
    try {
      const [d, t] = await Promise.all([
        api<Documentation[]>("/documents"),
        api<Technologie[]>("/technologies"),
      ]);
      setDocuments(d);
      setTechnologies(t);
    } catch (e) {
      setErreur(erreurTexte(e));
    } finally {
      setChargement(false);
    }
  }
  useEffect(() => {
    charger();
  }, []);
  useEffect(() => {
    if (!documents.some((d) => d.statut === "indexation")) return;
    const intervalle = setInterval(charger, 3000);
    return () => clearInterval(intervalle);
  }, [documents]);
  const selection = documents.filter(
    (d) =>
      (!technologie || d.technologie === technologie) &&
      (!version || d.version === version) &&
      `${d.titre} ${d.technologie} ${d.version}`
        .toLowerCase()
        .includes(recherche.toLowerCase()),
  );
  return (
    <div className="page">
      <Entete
        numero="01"
        etiquette="VOTRE BASE DE CONNAISSANCES"
        titre="Une place pour chaque savoir."
        description="Rassemblez vos documentations. Gardez le fil des technologies et de leurs versions."
        action={
          <button className="bouton primaire" onClick={() => setAjout(true)}>
            <Plus size={17} /> Ajouter une documentation
          </button>
        }
      />
      <Erreur message={erreur} />
      <div className="statistiques">
        <div>
          <BookOpen size={20} />
          <span>
            <b>{documents.length}</b> documentations
          </span>
        </div>
        <div>
          <span className="mini-grille">▦</span>
          <span>
            <b>{documents.reduce((s, d) => s + d.nombre_chunks, 0)}</b> chunks
            indexés
          </span>
        </div>
        <div>
          <Globe size={20} />
          <span>
            <b>{technologies.length}</b> technologies
          </span>
        </div>
        <div>
          <span className="voyant" />
          <span>
            {config?.fournisseur === "openai"
              ? "Embeddings OpenAI"
              : "Embeddings locaux"}
          </span>
        </div>
      </div>
      <div className="barre-bibliotheque">
        <label className="champ-recherche">
          <Search size={17} />
          <input
            aria-label="Rechercher une documentation"
            placeholder="Rechercher une documentation…"
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
          />
        </label>
        <select
          aria-label="Filtrer par technologie"
          value={technologie}
          onChange={(e) => {
            setTechnologie(e.target.value);
            setVersion("");
          }}
        >
          <option value="">Toutes les technologies</option>
          {technologies.map((t) => (
            <option key={t.nom}>{t.nom}</option>
          ))}
        </select>
        <select
          aria-label="Filtrer par version"
          value={version}
          onChange={(e) => setVersion(e.target.value)}
        >
          <option value="">Toutes les versions</option>
          {[
            ...new Set(
              documents
                .filter((d) => !technologie || d.technologie === technologie)
                .map((d) => d.version),
            ),
          ].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </div>
      {chargement ? (
        <p className="chargement">Chargement de votre bibliothèque…</p>
      ) : !selection.length ? (
        <Vide
          titre={
            documents.length
              ? "Aucun résultat"
              : "Votre prochaine réponse commence ici."
          }
          texte="Ajoutez un PDF, une page web, un Markdown ou un fichier TXT. Vous pourrez inspecter le découpage avant l’indexation."
        >
          <button className="bouton secondaire" onClick={() => setAjout(true)}>
            <Upload size={16} /> Importer une première source
          </button>
        </Vide>
      ) : (
        <div className="groupes-documents">
          {[...new Set(selection.map((d) => d.technologie))].map((t) => (
            <section key={t}>
              <div className="titre-groupe">
                <h2>
                  <span className="icone-technologie">{t.slice(0, 2)}</span>
                  {t}
                </h2>
                <label>
                  Version courante
                  <select
                    value={
                      technologies.find((x) => x.nom === t)?.version_courante ||
                      ""
                    }
                    onChange={async (e) => {
                      try {
                        await api(
                          `/technologies/${encodeURIComponent(t)}/version-courante`,
                          {
                            ...corps({ version: e.target.value }),
                            method: "PUT",
                          },
                        );
                        await charger();
                      } catch (e) {
                        setErreur(erreurTexte(e));
                      }
                    }}
                  >
                    {technologies
                      .find((x) => x.nom === t)
                      ?.versions.map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                  </select>
                </label>
              </div>
              <div className="grille-documents">
                {selection
                  .filter((d) => d.technologie === t)
                  .map((d) => (
                    <article className="carte-document" key={d.id}>
                      <header>
                        <span className="icone-fichier">
                          <FileText size={23} />
                        </span>
                        <span className={`statut ${d.statut}`}>
                          {
                            (
                              {
                                indexe: "Indexé",
                                brouillon: "À préparer",
                                indexation: "Indexation…",
                                erreur: "À relancer",
                              } as Record<string, string>
                            )[d.statut]
                          }
                        </span>
                        <button
                          className="bouton-icone danger"
                          disabled={d.statut === "indexation"}
                          onClick={() => setSupprimer(d)}
                          aria-label={`Supprimer ${d.titre}`}
                        >
                          <Trash2 size={16} />
                        </button>
                      </header>
                      <span className="etiquette">
                        {d.type_source.toUpperCase()} <b>v{d.version}</b>
                      </span>
                      <h3>{d.titre}</h3>
                      <p className="origine-document">
                        {d.url_source || d.nom_fichier}
                      </p>
                      <div className="chiffres-document">
                        <span>
                          <b>{d.nombre_sections}</b> sections / pages
                        </span>
                        <span>
                          <b>{d.nombre_chunks}</b> chunks
                        </span>
                      </div>
                      <p className="details-document">
                        {d.parametres_chunking.strategie} ·{" "}
                        {d.modele_embedding || "Pas encore d’embedding"}
                      </p>
                      {d.espace_embedding &&
                        d.espace_embedding !== config?.espace_embedding && (
                          <p className="avertissement">
                            Modèle changé : réindexation nécessaire.
                          </p>
                        )}
                      {d.erreur && <p className="erreur">{d.erreur}</p>}
                      <footer>
                        <span>
                          {d.indexe_le
                            ? `Indexé le ${new Date(d.indexe_le).toLocaleDateString("fr-FR")}`
                            : `Ajouté le ${new Date(d.cree_le).toLocaleDateString("fr-FR")}`}
                        </span>
                        <Link href={`/chunking?document=${d.id}`}>
                          Ouvrir <ArrowRight size={15} />
                        </Link>
                      </footer>
                    </article>
                  ))}
              </div>
            </section>
          ))}
        </div>
      )}
      <div className="note-pedagogique">
        <span>✳</span>
        <div>
          <b>Une bibliothèque qui connaît ses versions.</b>
          <p>
            Sans version précisée, le retrieval utilise la version courante de
            chaque technologie. Vous choisissez laquelle ici.
          </p>
        </div>
      </div>
      {ajout && (
        <Ajout
          fermer={() => setAjout(false)}
          terminer={() => {
            setAjout(false);
            charger();
          }}
        />
      )}
      {supprimer && (
        <div className="fond-modal">
          <div className="modal">
            <h2>Supprimer cette documentation ?</h2>
            <p>
              « {supprimer.titre} » et ses chunks seront supprimés. Les
              anciennes réponses conserveront leurs sources sous forme
              d’instantanés.
            </p>
            <div className="actions">
              <button
                className="bouton secondaire"
                onClick={() => setSupprimer(null)}
              >
                Annuler
              </button>
              <button
                className="bouton destructive"
                onClick={async () => {
                  try {
                    await api(`/documents/${supprimer.id}`, {
                      method: "DELETE",
                    });
                    setSupprimer(null);
                    charger();
                  } catch (e) {
                    setErreur(erreurTexte(e));
                    setSupprimer(null);
                  }
                }}
              >
                Supprimer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
function Ajout({
  fermer,
  terminer,
}: {
  fermer: () => void;
  terminer: () => void;
}) {
  const [mode, setMode] = useState("fichier");
  const [actif, setActif] = useState(false);
  const [erreur, setErreur] = useState("");
  const [nom, setNom] = useState("");
  const config = useConfiguration();
  async function soumettre(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setActif(true);
    setErreur("");
    const formulaire = new FormData(e.currentTarget);
    try {
      if (mode === "url") {
        await api(
          "/documents/url",
          corps(Object.fromEntries(formulaire.entries())),
        );
      } else {
        await api("/documents/fichier", { method: "POST", body: formulaire });
      }
      terminer();
    } catch (e) {
      setErreur(erreurTexte(e));
    } finally {
      setActif(false);
    }
  }
  return (
    <div className="fond-modal">
      <form className="modal" onSubmit={soumettre}>
        <button
          type="button"
          className="fermer bouton-icone"
          onClick={fermer}
          disabled={actif}
          aria-label="Fermer"
        >
          <X />
        </button>
        <span className="surtitre">UNE NOUVELLE SOURCE</span>
        <h2>Enrichissez votre atelier.</h2>
        <p>
          Le document est d’abord ajouté en brouillon. Vous validez les chunks
          avant de créer les embeddings.
        </p>
        <div className="onglets">
          <button
            type="button"
            className={mode === "fichier" ? "actif" : ""}
            onClick={() => setMode("fichier")}
          >
            <Upload size={15} /> Fichier
          </button>
          <button
            type="button"
            className={mode === "url" ? "actif" : ""}
            onClick={() => setMode("url")}
          >
            <Globe size={15} /> Page web
          </button>
        </div>
        {mode === "fichier" ? (
          <label className="depot-fichier">
            <Upload size={25} />
            <strong>{nom || "Choisir un document"}</strong>
            <span>
              PDF, Markdown, TXT, HTML · {config?.taille_fichier_mo || 15} Mo
              maximum
            </span>
            <input
              name="fichier"
              type="file"
              accept=".pdf,.md,.markdown,.txt,.html,.htm"
              required
              onChange={(e) => setNom(e.target.files?.[0]?.name || "")}
            />
          </label>
        ) : (
          <label>
            URL de la page
            <input
              name="url"
              type="url"
              placeholder="https://docs.python.org/…"
              required
            />
          </label>
        )}
        <label>
          Titre de la documentation
          <input
            name="titre"
            placeholder="Par exemple : Le tutoriel Python"
            required
            maxLength={200}
          />
        </label>
        <div className="deux-colonnes">
          <label>
            Technologie
            <input
              name="technologie"
              placeholder="Python"
              required
              maxLength={60}
              list="technologies-suggestions"
            />
            <datalist id="technologies-suggestions">
              {[
                "Python",
                "React",
                "Next.js",
                "PyTorch",
                "FastAPI",
                "PostgreSQL",
                "Docker",
              ].map((t) => (
                <option key={t}>{t}</option>
              ))}
            </datalist>
          </label>
          <label>
            Version
            <input name="version" placeholder="3.14" required maxLength={40} />
          </label>
        </div>
        <label>
          Type de documentation
          <select name="type_documentation">
            <option value="documentation">Documentation</option>
            <option value="tutoriel">Tutoriel</option>
            <option value="reference">Référence API</option>
            <option value="guide">Guide</option>
          </select>
        </label>
        <Erreur message={erreur} />
        <button disabled={actif} className="bouton primaire pleine-largeur">
          {actif ? "Lecture du document…" : "Ajouter à la bibliothèque"}
          {!actif && <Check size={16} />}
        </button>
      </form>
    </div>
  );
}
