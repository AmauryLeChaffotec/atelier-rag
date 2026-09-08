"""Calcul transparent de la configuration Terraform ; aucun appel AWS ou IA."""
import argparse
import json
from pathlib import Path


def principal():
    tarifs = json.loads((Path(__file__).resolve().parents[1] / "documentation" / "tarifs.json").read_text(encoding="utf-8"))
    arguments = argparse.ArgumentParser(description="Estimer Atelier sur ECS Fargate à Paris, en dollars HT.")
    arguments.add_argument("--questions", type=int, default=1000)
    arguments.add_argument("--tokens-entree", type=int, default=3000, help="Question, consignes, contexte et historique par réponse")
    arguments.add_argument("--tokens-sortie", type=int, default=500)
    arguments.add_argument("--tokens-indexation", type=int, default=1_000_000)
    arguments.add_argument("--pages-ocr", type=int, default=100, help="Pages réellement envoyées, hors cache")
    arguments.add_argument("--heures", type=float, default=730, help="Durée du mois ; tous les services restent allumés")
    arguments.add_argument("--heures-fargate", type=float, default=None, help="Heures actives par tâche ; ALB et RDS restent facturés")
    arguments.add_argument("--taches", type=int, choices=[0, 1, 2], default=1)
    arguments.add_argument("--go-rds", type=float, default=20)
    arguments.add_argument("--go-s3", type=float, default=1, help="Documents ET anciennes versions conservées")
    arguments.add_argument("--go-ecr", type=float, default=2, help="Toutes les images et versions conservées")
    arguments.add_argument("--go-journaux", type=float, default=1, help="Ingestion mensuelle, API + RDS réunis")
    arguments.add_argument("--lcu-moyennes", type=float, default=0.1, help="Charge moyenne estimée du load balancer")
    arguments.add_argument("--supplements", type=float, default=0, help="USD supplémentaires : réseau, snapshots, domaine, etc.")
    options = arguments.parse_args()
    if any(v is not None and v < 0 for v in vars(options).values()):
        arguments.error("Toutes les valeurs doivent être positives ou nulles.")
    heures = options.heures
    fargate = heures if options.heures_fargate is None else options.heures_fargate
    if fargate > heures:
        arguments.error("Les heures Fargate ne peuvent pas dépasser la durée du mois.")
    postes = {
        "Fargate (0,5 vCPU / 2 Go)": options.taches * fargate * (0.5 * tarifs["fargate_vcpu_heure"] + 2 * tarifs["fargate_go_heure"]),
        "RDS db.t4g.micro Single-AZ": heures * tarifs["rds_micro_heure"],
        "RDS stockage gp3": options.go_rds * tarifs["rds_gp3_go_mois"],
        "ALB (durée + LCU estimées)": heures * (tarifs["alb_heure"] + options.lcu_moyennes * tarifs["alb_lcu_heure"]),
        "IPv4 (2 ALB + tâches)": (2 * heures + options.taches * fargate) * tarifs["ipv4_heure"],
        "S3 (stockage + requêtes)": options.go_s3 * tarifs["s3_go_mois"] + tarifs["s3_mille_ecritures"] + 10 * tarifs["s3_mille_lectures"],
        "ECR (images conservées)": options.go_ecr * tarifs["ecr_go_mois"],
        "Secrets Manager (2 secrets)": 2 * tarifs["secret_mois"] + 0.1 * tarifs["secrets_dix_mille_appels"],
        "CloudWatch (logs + 5 alarmes)": options.go_journaux * (tarifs["journaux_go_ingere"] + 7 / 30 * tarifs["journaux_go_stocke"]) + 5 * tarifs["alarme_mois"],
        "Génération OpenAI": options.questions * (options.tokens_entree * tarifs["generation_entree_million"] + options.tokens_sortie * tarifs["generation_sortie_million"]) / 1_000_000,
        "Embeddings documents + questions": (options.tokens_indexation + options.questions * 50) * tarifs["embedding_million"] / 1_000_000,
        "OCR Mistral des PDF": options.pages_ocr * tarifs["ocr_mille_pages"] / 1000,
        "Suppléments renseignés": options.supplements,
    }
    for nom, valeur in postes.items():
        print(f"{nom:35} {valeur:8.4f} USD")
    print(f"TOTAL MENSUEL ESTIMÉ                  {sum(postes.values()):8.2f} USD HT")
    print(f"Paris, tarifs vérifiés le {tarifs['date_verification']}, sans crédits AWS.")
    print("Hypothèses : S3 1 000 écritures / 10 000 lectures, Secrets Manager 1 000 appels, logs conservés 7 jours.")
    print("Hors domaine, taxes, réseau, CPU RDS excédentaire, snapshots supplémentaires, vision et branching.")
    print("Les déploiements et migrations ajoutent temporairement des tâches/IP ; le nombre d’IP ALB peut augmenter.")


if __name__ == "__main__":
    principal()
