"""Calcul transparent ; aucun appel AWS/OpenAI et aucune dépense."""
import argparse
import json
from pathlib import Path

tarifs = json.loads((Path(__file__).resolve().parents[1] / "documentation" / "tarifs.json").read_text(encoding="utf-8"))
arguments = argparse.ArgumentParser(description="Estimer le coût mensuel d’Atelier, en dollars HT.")
arguments.add_argument("--questions", type=int, default=100)
arguments.add_argument("--tokens-entree", type=int, default=3000, help="Contexte + question + historique + consignes par réponse")
arguments.add_argument("--tokens-sortie", type=int, default=500)
arguments.add_argument("--tokens-indexation", type=int, default=1_000_000, help="Nouveaux embeddings ou réindexations pendant le mois")
arguments.add_argument("--go-snapshots", type=float, default=5, help="Volume total facturé, tous snapshots conservés réunis")
arguments.add_argument("--prix-machine", type=float, default=tarifs["lightsail_2go"])
arguments.add_argument("--pages-ocr", type=int, default=0, help="Pages PDF réellement envoyées à Mistral pendant le mois, hors cache")
options = arguments.parse_args()
if any(v < 0 for v in vars(options).values()):
    arguments.error("Toutes les valeurs doivent être positives ou nulles.")
generation = options.questions * (options.tokens_entree * tarifs["generation_entree_million"] + options.tokens_sortie * tarifs["generation_sortie_million"]) / 1_000_000
indexation = options.tokens_indexation * tarifs["embedding_million"] / 1_000_000
questions = options.questions * 50 * tarifs["embedding_million"] / 1_000_000
snapshots = options.go_snapshots * tarifs["snapshot_go"]
ocr = options.pages_ocr * tarifs["ocr_mille_pages"] / 1000
for nom, valeur in [("Machine Lightsail", options.prix_machine), ("Snapshots", snapshots), ("Génération OpenAI", generation), ("Embeddings des documents", indexation), ("Embeddings des questions", questions), ("OCR Mistral des PDF", ocr)]:
    print(f"{nom:28} {valeur:8.4f} USD")
print(f"TOTAL MENSUEL ESTIMÉ          {options.prix_machine + snapshots + generation + indexation + questions + ocr:8.2f} USD HT")
print(f"Tarifs vérifiés le {tarifs['date_verification']}. Hors taxes, domaine, dépassements réseau et appels vision/branching.")
