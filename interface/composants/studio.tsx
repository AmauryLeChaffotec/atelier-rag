"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  Check,
  Eye,
  Image,
  Play,
  Scissors,
  WandSparkles,
} from "lucide-react";
import { api, corps, erreurTexte } from "@/bibliotheque/api";
import {
  Chunk,
  Configuration,
  Documentation,
  Parametres,
} from "@/bibliotheque/types";
import { Entete, Erreur, SourceOuverte, Vide } from "./communs";

const defaut: Parametres = {
  strategie: "titres",
  taille: 1000,
  overlap: 120,
  taille_min: 80,
  taille_max: 2000,
  separateurs: ["\n\n", "\n", ". ", " "],
  preserver_code: true,
  seuil_semantique: 0.72,
};
const strategies = [
  {
    valeur: "titres",
    nom: "Titres & sous-titres",
    description:
      "Suit la structure du document et conserve le chemin de chaque section.",
  },
  {
    valeur: "recursif",
    nom: "Récursif",
    description:
      "Cherche successivement une coupure entre paragraphes, lignes, phrases et mots.",
  },
  {
    valeur: "taille",
    nom: "Taille fixe",
    description:
      "Découpe par fenêtres de caractères, avec le recouvrement choisi.",
  },
  {
    valeur: "paragraphes",
    nom: "Paragraphes",
    description:
      "Privilégie un passage par paragraphe ; les plus longs sont redécoupés.",
  },
  {
    valeur: "markdown",
    nom: "Markdown",
    description:
      "Utilise les titres Markdown extraits et préserve les blocs de code.",
  },
  {
    valeur: "semantique",
    nom: "Sémantique",
    description:
      "Compare réellement les embeddings des sections voisines avant de les regrouper. Plus lent, et facturé avec OpenAI.",
  },
];
export function Studio() {
  const [documents, setDocuments] = useState<Documentation[]>([]);
  const [document, setDocument] = useState<Documentation | null>(null);
  const [parametres, setParametres] = useState<Parametres>(defaut);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [revision, setRevision] = useState(0);
  const [actif, setActif] = useState("");
  const [erreur, setErreur] = useState("");
  const [message, setMessage] = useState("");
  const [source, setSource] = useState<Chunk | null>(null);
  const [modifie, setModifie] = useState(false);
  const [descriptions, setDescriptions] = useState<Record<number, string>>({});
  const [configuration, setConfiguration] = useState<Configuration | null>(
    null,
  );
  const [pagesOcr, setPagesOcr] = useState("");
  const [separateurs, setSeparateurs] = useState(
    JSON.stringify(defaut.separateurs),
  );
  async function choisir(id: string) {
    if (!id) {
      setDocument(null);
      return;
    }
    setErreur("");
    try {
      const d = await api<Documentation>(`/documents/${id}`);
      setDocument(d);
      setPagesOcr("");
      setDescriptions(
        Object.fromEntries(
          d.sections
            .filter((s) => s.visuel)
            .map((s) => [s.page!, s.description_visuelle || ""]),
        ),
      );
      setParametres({ ...defaut, ...d.parametres_chunking });
      setSeparateurs(
        JSON.stringify(d.parametres_chunking.separateurs || defaut.separateurs),
      );
      setChunks(d.brouillon);
      setRevision(d.revision);
      setModifie(false);
    } catch (e) {
      setErreur(erreurTexte(e));
    }
  }
  useEffect(() => {
    api<Configuration>("/configuration")
      .then(setConfiguration)
      .catch(() => {});
    api<Documentation[]>("/documents")
      .then((d) => {
        setDocuments(d);
        const id = new URLSearchParams(location.search).get("document");
        if (id) choisir(id);
      })
      .catch((e) => setErreur(erreurTexte(e)));
  }, []);
  useEffect(() => {
    if (document?.statut !== "indexation") return;
    const intervalle = setInterval(async () => {
      const d = await api<Documentation>(`/documents/${document.id}`).catch(
        () => null,
      );
      if (d) {
        setDocument(d);
        if (d.statut === "indexe")
          setMessage(
            "Indexation terminée. Votre documentation est prête pour le chat.",
          );
      }
    }, 3000);
    return () => clearInterval(intervalle);
  }, [document?.id, document?.statut]);
  function modifier(attribut: string, valeur: unknown) {
    setParametres((p) => ({ ...p, [attribut]: valeur }));
    setModifie(true);
  }
  async function apercu() {
    if (!document) return;
    setActif("apercu");
    setErreur("");
    setMessage("");
    try {
      const separateursValides = JSON.parse(separateurs);
      if (
        !Array.isArray(separateursValides) ||
        !separateursValides.every((s) => typeof s === "string")
      )
        throw new Error(
          "Les séparateurs doivent être un tableau JSON de textes.",
        );
      const resultat = await api<{
        chunks: Chunk[];
        revision: number;
        parametres: Parametres;
      }>(
        `/documents/${document.id}/apercu`,
        corps({
          revision,
          parametres: { ...parametres, separateurs: separateursValides },
        }),
      );
      setChunks(resultat.chunks);
      setRevision(resultat.revision);
      setParametres(resultat.parametres);
      setModifie(false);
    } catch (e) {
      setErreur(erreurTexte(e));
    } finally {
      setActif("");
    }
  }
  async function indexer() {
    if (!document) return;
    setActif("indexation");
    setErreur("");
    try {
      await api(
        `/documents/${document.id}/indexation`,
        corps({ revision, chunks }),
      );
      setDocument({ ...document, statut: "indexation" });
      setMessage(
        "Indexation lancée. Les embeddings se calculent en arrière-plan.",
      );
    } catch (e) {
      setErreur(erreurTexte(e));
    } finally {
      setActif("");
    }
  }
  const pagesVisuelles =
    document?.sections.filter(
      (s, i, sections) =>
        s.visuel &&
        sections.findIndex((x) => x.page === s.page && x.visuel) === i,
    ) || [];
  async function lireAvecOcr() {
    if (!document) return;
    setActif("ocr");
    setErreur("");
    setMessage("");
    try {
      let pages: number[] | null = null;
      if (pagesOcr.trim()) {
        pages = [];
        for (const morceau of pagesOcr.split(",")) {
          const plage = morceau.trim().match(/^(\d+)(?:\s*-\s*(\d+))?$/);
          if (!plage)
            throw new Error(
              "Indiquez des pages comme 1-3, 5 ou laissez vide pour tout le PDF.",
            );
          const debut = Number(plage[1]),
            fin = Number(plage[2] || plage[1]);
          if (debut < 1 || fin > 150 || fin < debut)
            throw new Error(
              "Les pages doivent être comprises entre 1 et 150, dans l’ordre de la plage.",
            );
          for (let p = debut; p <= fin; p++) pages.push(p);
        }
        pages = [...new Set(pages)];
      }
      const resultat = await api<{
        pages_envoyees: number;
        pages_en_cache: number;
      }>(`/documents/${document.id}/ocr`, corps({ revision, pages }));
      await choisir(document.id);
      setMessage(
        `OCR terminé : ${resultat.pages_envoyees} page(s) traitée(s), ${resultat.pages_en_cache} en cache. Vérifiez les sections puis générez l’aperçu.`,
      );
    } catch (e) {
      setErreur(erreurTexte(e));
    } finally {
      setActif("");
    }
  }
  return (
    <div className="page">
      <Entete
        numero="02"
        etiquette="CHUNKING STUDIO"
        titre="Le bon passage. La bonne taille."
        description="Découpez, observez, ajustez. Rien n’est indexé sans votre validation."
      />
      <Erreur message={erreur} />
      {message && (
        <div className="succes" role="status">
          <Check size={17} />
          {message}
          <Link href="/">
            Ouvrir le chat <ArrowRight size={14} />
          </Link>
        </div>
      )}
      <div className="select-document panneau">
        <Scissors size={21} />
        <label>
          Documentation à préparer
          <select
            value={document?.id || ""}
            onChange={(e) => choisir(e.target.value)}
            disabled={!!actif}
          >
            <option value="">Choisir une documentation</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.titre} · {d.technologie} {d.version}
              </option>
            ))}
          </select>
        </label>
        {document && (
          <span className="pastille">
            {document.statut === "indexation"
              ? "Indexation en cours…"
              : `${document.sections.length} sections extraites`}
          </span>
        )}
      </div>
      {!document ? (
        <Vide
          titre="Chaque bonne réponse commence par un bon découpage."
          texte="Choisissez une documentation pour comparer les stratégies et inspecter chaque passage."
        >
          <Link className="bouton secondaire" href="/documentation">
            Ouvrir la bibliothèque <ArrowRight size={15} />
          </Link>
        </Vide>
      ) : (
        <div className="grille-studio">
          <aside className="panneau parametres-studio">
            <h3>Le découpage, à votre main.</h3>
            <fieldset disabled={!!actif || document.statut === "indexation"}>
              <label>
                Stratégie
                <select
                  value={parametres.strategie}
                  onChange={(e) => modifier("strategie", e.target.value)}
                >
                  {strategies.map((s) => (
                    <option value={s.valeur} key={s.valeur}>
                      {s.nom}
                    </option>
                  ))}
                </select>
              </label>
              <p className="aide-champ">
                {
                  strategies.find((s) => s.valeur === parametres.strategie)
                    ?.description
                }
              </p>
              <label>
                Taille cible <b>{parametres.taille} caractères</b>
                <input
                  type="range"
                  min={100}
                  max={6000}
                  step={100}
                  value={parametres.taille}
                  onChange={(e) => modifier("taille", +e.target.value)}
                />
              </label>
              <label>
                Overlap <b>{parametres.overlap} caractères</b>
                <input
                  type="range"
                  min={0}
                  max={1000}
                  step={20}
                  value={parametres.overlap}
                  onChange={(e) => modifier("overlap", +e.target.value)}
                />
              </label>
              <p className="aide-champ">
                L’overlap répète une partie du texte entre deux morceaux d’une
                même section.
              </p>
              <div className="deux-colonnes">
                <label>
                  Taille minimale
                  <input
                    type="number"
                    min={0}
                    max={2000}
                    value={parametres.taille_min}
                    onChange={(e) => modifier("taille_min", +e.target.value)}
                  />
                </label>
                <label>
                  Taille maximale
                  <input
                    type="number"
                    min={100}
                    max={12000}
                    value={parametres.taille_max}
                    onChange={(e) => modifier("taille_max", +e.target.value)}
                  />
                </label>
              </div>
              <label className="case">
                <input
                  type="checkbox"
                  checked={parametres.preserver_code}
                  onChange={(e) => modifier("preserver_code", e.target.checked)}
                />{" "}
                Préserver les blocs de code
              </label>
              <details>
                <summary>Réglages avancés</summary>
                <label>
                  Séparateurs, dans l’ordre (JSON)
                  <textarea
                    rows={3}
                    value={separateurs}
                    onChange={(e) => {
                      setSeparateurs(e.target.value);
                      setModifie(true);
                    }}
                  />
                </label>
                {parametres.strategie === "semantique" && (
                  <label>
                    Seuil de regroupement sémantique
                    <input
                      type="number"
                      min={0}
                      max={1}
                      step={0.01}
                      value={parametres.seuil_semantique}
                      onChange={(e) =>
                        modifier("seuil_semantique", +e.target.value)
                      }
                    />
                  </label>
                )}
                <p className="aide-champ">
                  La taille minimale est une cible souple : on ne mélange pas
                  deux sections pour l’atteindre. La taille maximale autorise un
                  bloc de code entier.
                </p>
              </details>
              <button
                className="bouton primaire pleine-largeur"
                onClick={apercu}
              >
                <Play size={15} />
                {actif === "apercu"
                  ? "Découpage en cours…"
                  : "Générer l’aperçu"}
              </button>
            </fieldset>
            <div className="info-embedding">
              <span>DOCUMENT → CHUNKS → EMBEDDINGS</span>
              <p>
                Une fois validé, chaque passage devient un vecteur que pgvector
                peut retrouver par proximité de sens.
              </p>
            </div>
          </aside>
          <section className="apercu-studio">
            {document.type_source === "pdf" && (
              <section className="panneau ocr-studio">
                <div>
                  <h3>
                    <WandSparkles size={18} /> Un PDF difficile à lire ?
                  </h3>
                  <p>
                    Mistral OCR extrait le texte des scans et des tableaux. Le
                    PDF est envoyé à Mistral, qui facture les pages traitées.
                    Les résultats déjà en cache sont réutilisés.
                  </p>
                </div>
                <label>
                  Pages à lire{" "}
                  <input
                    value={pagesOcr}
                    onChange={(e) => setPagesOcr(e.target.value)}
                    disabled={!!actif || document.statut === "indexation"}
                    placeholder="Toutes les pages, ou 1-3, 5"
                  />
                </label>
                <button
                  className="bouton secondaire"
                  onClick={lireAvecOcr}
                  disabled={
                    !!actif ||
                    document.statut === "indexation" ||
                    !configuration?.ocr_disponible
                  }
                >
                  <WandSparkles size={15} />
                  {actif === "ocr"
                    ? "Lecture OCR en cours…"
                    : "Lire avec Mistral OCR"}
                </button>
                <p className="aide-champ">
                  {configuration?.ocr_disponible
                    ? "La lecture remplace le texte extrait des pages sélectionnées et remet leur aperçu à préparer. Les chunks déjà indexés restent disponibles jusqu’à la réindexation."
                    : "Ajoutez MISTRAL_API_KEY dans le .env du serveur, puis redémarrez-le pour activer l’OCR."}
                </p>
              </section>
            )}
            <div className="titre-apercu">
              <h2>
                Aperçu des passages{" "}
                <span className="compteur">{chunks.length}</span>
              </h2>
              <button
                className="bouton primaire"
                disabled={
                  !chunks.length ||
                  !!actif ||
                  modifie ||
                  document.statut === "indexation"
                }
                onClick={indexer}
              >
                <Check size={16} />
                {document.statut === "indexation"
                  ? "Indexation…"
                  : document.nombre_chunks
                    ? "Valider et réindexer"
                    : "Valider et indexer"}
              </button>
            </div>
            {modifie && (
              <p className="avertissement">
                Les paramètres ont changé. Régénérez l’aperçu avant l’indexation
                ; cela remplacera vos éditions manuelles.
              </p>
            )}
            {!chunks.length ? (
              <Vide
                titre="Voyez ce que votre modèle va lire."
                texte="Générez un premier aperçu avec les paramètres proposés."
              />
            ) : (
              <>
                <div
                  className="ruban-chunks"
                  aria-label="Tailles relatives des chunks"
                >
                  {chunks.map((c, i) => (
                    <span
                      key={c.id}
                      style={{ flex: c.contenu.length }}
                      title={`Chunk ${i + 1} : ${c.contenu.length} caractères`}
                    >
                      {i + 1}
                    </span>
                  ))}
                </div>
                <p className="texte-secondaire">
                  Les passages sont modifiables. Tokens affichés ≈ caractères ÷
                  4, estimation uniquement.
                </p>
                <div className="liste-chunks">
                  {chunks.map((c, i) => (
                    <article className="chunk-editable" key={c.id}>
                      <header>
                        <span className="numero-source">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span>
                          {c.metadata.heading_path.join(" / ") ||
                            document.titre}
                        </span>
                        <button
                          className="bouton-icone"
                          onClick={() => setSource(c)}
                          aria-label={`Inspecter le chunk ${i + 1}`}
                        >
                          <Eye size={16} />
                        </button>
                      </header>
                      <textarea
                        aria-label={`Contenu du chunk ${i + 1}`}
                        value={c.contenu}
                        maxLength={12000}
                        disabled={!!actif || document.statut === "indexation"}
                        onChange={(e) =>
                          setChunks((t) =>
                            t.map((x) =>
                              x.id === c.id
                                ? { ...x, contenu: e.target.value }
                                : x,
                            ),
                          )
                        }
                      />
                      <footer>
                        <span>{c.contenu.length} caractères</span>
                        <span>≈ {Math.ceil(c.contenu.length / 4)} tokens</span>
                        <span>{c.metadata.content_type}</span>
                        {c.metadata.page && <span>Page {c.metadata.page}</span>}
                      </footer>
                    </article>
                  ))}
                </div>
              </>
            )}
            {pagesVisuelles.length > 0 && (
              <section className="panneau visuels-studio">
                <h3>
                  <Image size={19} /> Les éléments visuels du PDF
                </h3>
                <p>
                  Les pages contenant des images ou des diagrammes sont
                  conservées. Rédigez une description ou demandez une
                  proposition au modèle vision. Relisez-la et enregistrez-la
                  avant de recréer l’aperçu.
                </p>
                {pagesVisuelles.map((s) => (
                  <div className="description-visuelle" key={s.page}>
                    <div className="ligne-visuel">
                      <a
                        href={`/api/documents/${document.id}/visuels/${s.page}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Voir la page {s.page} <Eye size={14} />
                      </a>
                      <button
                        className="bouton secondaire"
                        disabled={!!actif || document.statut === "indexation"}
                        onClick={async () => {
                          setActif("visuel");
                          setErreur("");
                          try {
                            const proposition = await api<{
                              description: string;
                            }>(
                              `/documents/${document.id}/visuels/${s.page}/description`,
                              corps({}),
                            );
                            setDescriptions((d) => ({
                              ...d,
                              [s.page!]: proposition.description,
                            }));
                            setMessage(
                              "Proposition reçue. Vérifiez que le modèle a bien lu l’image, corrigez le texte puis enregistrez-le.",
                            );
                          } catch (e) {
                            setErreur(erreurTexte(e));
                          } finally {
                            setActif("");
                          }
                        }}
                      >
                        <WandSparkles size={14} /> Proposer une description
                      </button>
                    </div>
                    <label>
                      Description de la page {s.page}
                      <textarea
                        rows={4}
                        maxLength={10000}
                        value={descriptions[s.page!] || ""}
                        disabled={!!actif || document.statut === "indexation"}
                        placeholder="Décrivez le schéma, ses éléments et leurs relations…"
                        onChange={(e) =>
                          setDescriptions((d) => ({
                            ...d,
                            [s.page!]: e.target.value,
                          }))
                        }
                      />
                    </label>
                    <button
                      className="bouton secondaire"
                      disabled={
                        !!actif ||
                        document.statut === "indexation" ||
                        (descriptions[s.page!] || "").trim().length < 5
                      }
                      onClick={async () => {
                        setActif("description");
                        setErreur("");
                        try {
                          await api(
                            `/documents/${document.id}/visuels/${s.page}/description`,
                            {
                              ...corps({
                                revision,
                                description: descriptions[s.page!],
                              }),
                              method: "PUT",
                            },
                          );
                          await choisir(document.id);
                          setMessage(
                            "Description enregistrée. Régénérez l’aperçu puis validez l’indexation.",
                          );
                        } catch (e) {
                          setErreur(erreurTexte(e));
                        } finally {
                          setActif("");
                        }
                      }}
                    >
                      <Check size={14} /> Enregistrer cette description
                    </button>
                  </div>
                ))}
              </section>
            )}
            <details className="panneau">
              <summary>
                Consulter les sections extraites et le document original
              </summary>
              <a
                className="lien-texte"
                href={`/api/documents/${document.id}/original`}
              >
                Télécharger l’original
              </a>
              {document.sections.map((s, i) => (
                <div key={i}>
                  <h4>{s.titres.join(" / ")}</h4>
                  <pre>{s.contenu}</pre>
                </div>
              ))}
            </details>
          </section>
        </div>
      )}
      <SourceOuverte source={source} fermer={() => setSource(null)} />
    </div>
  );
}
