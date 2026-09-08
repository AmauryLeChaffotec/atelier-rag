"use client";
import { useState } from "react";
import { ArrowRight, Search, SlidersHorizontal } from "lucide-react";
import { api, corps, erreurTexte } from "@/bibliotheque/api";
import {
  Chunk,
  ResultatRecherche,
  filtresInitiaux,
} from "@/bibliotheque/types";
import { Entete, Erreur, CarteSource, SourceOuverte, Vide } from "./communs";
import { Filtres } from "./filtres";
export function Laboratoire() {
  const [question, setQuestion] = useState("");
  const [filtres, setFiltres] = useState(filtresInitiaux);
  const [resultat, setResultat] = useState<ResultatRecherche | null>(null);
  const [requete, setRequete] = useState("");
  const [source, setSource] = useState<Chunk | null>(null);
  const [actif, setActif] = useState(false);
  const [erreur, setErreur] = useState("");
  async function chercher(e: React.FormEvent) {
    e.preventDefault();
    setActif(true);
    setErreur("");
    try {
      setResultat(
        await api<ResultatRecherche>(
          "/retrieval",
          corps({ ...filtres, question }),
        ),
      );
      setRequete(question);
    } catch (e) {
      setErreur(erreurTexte(e));
    } finally {
      setActif(false);
    }
  }
  return (
    <div className="page">
      <Entete
        numero="03"
        etiquette="RETRIEVAL PLAYGROUND"
        titre="Retrouver avant de répondre."
        description="Testez la recherche de passages, sans générer de réponse. Observez ce que les embeddings rapprochent."
      />
      <div className="grille-laboratoire">
        <aside className="panneau">
          <h3>
            <SlidersHorizontal size={18} /> Affiner la recherche
          </h3>
          <Filtres valeur={filtres} changer={setFiltres} avance />
          <div className="info-embedding">
            <span>COMMENT LIRE LE SCORE ?</span>
            <p>
              La similarité cosinus mesure la proximité entre deux vecteurs. Un
              score plus élevé indique une plus grande proximité de sens.
            </p>
            <p>
              Ce score n’est pas une probabilité de vérité. Le seuil pertinent
              dépend du modèle et de vos documents.
            </p>
          </div>
        </aside>
        <section>
          <form className="recherche-retrieval panneau" onSubmit={chercher}>
            <label htmlFor="requete-retrieval">
              Votre requête documentaire
            </label>
            <div>
              <Search size={20} />
              <input
                id="requete-retrieval"
                placeholder="Par exemple : gérer une ressource avec Python"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                required
                minLength={2}
                maxLength={4000}
              />
              <button className="bouton primaire" disabled={actif}>
                {actif ? "Recherche…" : "Rechercher"}
                <ArrowRight size={16} />
              </button>
            </div>
          </form>
          <Erreur message={erreur} />
          {!resultat ? (
            <Vide
              titre="Quels passages votre question va-t-elle retrouver ?"
              texte="Saisissez une requête pour voir les chunks sélectionnés directement par pgvector."
            />
          ) : (
            <>
              <div className="resume-recherche">
                <span className="surtitre">RÉSULTATS POUR « {requete} »</span>
                <h2>{resultat.resultats.length} passages retrouvés</h2>
                <div className="petites-infos">
                  <span>
                    {resultat.routage?.technologies.join(", ") ||
                      "Technologie non détectée"}
                  </span>
                  <span>{resultat.dimension} dimensions</span>
                  <span>
                    {(
                      resultat.durees.embedding + resultat.durees.retrieval
                    ).toFixed(2)}{" "}
                    s
                  </span>
                </div>
                <p className="texte-secondaire">
                  La détection est informative ici. Les filtres ci-dessous
                  déterminent la recherche.
                </p>
              </div>
              {!resultat.resultats.length ? (
                <Vide
                  titre="Aucun passage au-dessus du seuil."
                  texte="Vérifiez les filtres, la version et le modèle d’indexation, ou réduisez le seuil."
                />
              ) : (
                <div className="resultats-retrieval">
                  {resultat.resultats.map((c, i) => (
                    <div key={c.id} className="resultat-classe">
                      <span className="rang">
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <div>
                        <div className="barre-score">
                          <span
                            style={{
                              width: `${Math.max(0, c.score || 0) * 100}%`,
                            }}
                          />
                        </div>
                        <CarteSource source={c} ouvrir={setSource} />
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <details className="panneau">
                <summary>
                  Inspecter les filtres et les mesures appliqués
                </summary>
                <pre>
                  {JSON.stringify(
                    {
                      espace_embedding: resultat.espace_embedding,
                      filtres: resultat.filtres,
                      durees: resultat.durees,
                    },
                    null,
                    2,
                  )}
                </pre>
              </details>
            </>
          )}
        </section>
      </div>
      <SourceOuverte source={source} fermer={() => setSource(null)} />
    </div>
  );
}
