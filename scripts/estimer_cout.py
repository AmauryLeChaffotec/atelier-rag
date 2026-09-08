"""Estimation locale : séance, utilisation intermittente ou service permanent. Aucun appel AWS."""

import argparse
import json
import math
from pathlib import Path

PROFILS = {
    "seance": {"fargate": 4, "rds": 4, "alb": 4, "conservation": 4, "journaux": 0.1},
    "intermittent": {"fargate": 8, "rds": 8, "alb": 8, "conservation": 730, "journaux": 0.1},
    "permanent": {"fargate": 730, "rds": 730, "alb": 730, "conservation": 730, "journaux": 1},
}


def calculer(tarifs, options):
    profil = PROFILS[options.profil]
    durees = {nom: getattr(options, "heures_" + nom) for nom in ["fargate", "rds", "alb", "conservation"]}
    durees = {nom: profil[nom] if valeur is None else valeur for nom, valeur in durees.items()}
    if any(not math.isfinite(valeur) or valeur < 0 or valeur > 730 for valeur in durees.values()):
        raise ValueError("Chaque durée doit être comprise entre 0 et 730 heures.")
    if durees["rds"] > durees["conservation"]:
        raise ValueError("Le stockage RDS doit exister au moins aussi longtemps que son calcul.")
    fraction = durees["conservation"] / 730
    logs = profil["journaux"] if options.go_journaux is None else options.go_journaux
    postes = {
        "Fargate (0,5 vCPU / 2 GiB)": options.taches
        * durees["fargate"]
        * (0.5 * tarifs["fargate_vcpu_heure"] + 2 * tarifs["fargate_go_heure"]),
        "RDS : calcul actif": durees["rds"] * tarifs["rds_micro_heure"],
        "RDS : stockage, même arrêté": options.go_rds * tarifs["rds_gp3_go_mois"] * fraction,
        "ALB : existence + charge estimée": durees["alb"]
        * (tarifs["alb_heure"] + options.lcu_moyennes * tarifs["alb_lcu_heure"]),
        "IPv4 : 2 ALB + tâches actives": (2 * durees["alb"] + options.taches * durees["fargate"])
        * tarifs["ipv4_heure"],
        "S3 : stockage et requêtes": options.go_s3 * tarifs["s3_go_mois"] * fraction
        + tarifs["s3_mille_ecritures"]
        + 10 * tarifs["s3_mille_lectures"],
        "ECR : images conservées": options.go_ecr * tarifs["ecr_go_mois"] * fraction,
        "Secrets Manager : 2 secrets": 2 * tarifs["secret_mois"] * fraction
        + 0.1 * tarifs["secrets_dix_mille_appels"],
        "CloudWatch : logs et alarmes": logs
        * (tarifs["journaux_go_ingere"] + min(7 / 30, fraction) * tarifs["journaux_go_stocke"])
        + options.alarmes * tarifs["alarme_mois"] * fraction,
        "OpenAI : réponses": options.questions
        * (
            options.tokens_entree * tarifs["generation_entree_million"]
            + options.tokens_sortie * tarifs["generation_sortie_million"]
        )
        / 1_000_000,
        "OpenAI : embeddings": (options.tokens_indexation + options.questions * 50)
        * tarifs["embedding_million"]
        / 1_000_000,
        "Mistral : pages OCR envoyées": options.pages_ocr * tarifs["ocr_mille_pages"] / 1000,
        "Autres frais renseignés": options.supplements,
    }
    return durees, postes


def arguments():
    analyseur = argparse.ArgumentParser(description=__doc__)
    analyseur.add_argument("--profil", choices=PROFILS, default="seance")
    for nom in ["fargate", "rds", "alb", "conservation"]:
        analyseur.add_argument(
            "--heures-" + nom,
            type=float,
            default=None,
            help="Heures facturables du profil ; arrondir chaque séance ALB à l’heure supérieure ; conservation = stockage, secrets et alarmes",
        )
    analyseur.add_argument("--questions", type=int, default=100)
    analyseur.add_argument("--tokens-entree", type=int, default=3000)
    analyseur.add_argument("--tokens-sortie", type=int, default=500)
    analyseur.add_argument("--tokens-indexation", type=int, default=1_000_000)
    analyseur.add_argument("--pages-ocr", type=int, default=0)
    analyseur.add_argument("--taches", type=int, choices=[0, 1, 2], default=1)
    analyseur.add_argument("--go-rds", type=float, default=20)
    analyseur.add_argument("--go-s3", type=float, default=1, help="Documents et anciennes versions réunis")
    analyseur.add_argument("--go-ecr", type=float, default=2, help="Toutes les images conservées")
    analyseur.add_argument(
        "--go-journaux",
        type=float,
        default=None,
        help="Ingestion réelle estimée sur la période, pas par heure",
    )
    analyseur.add_argument("--alarmes", type=int, default=5)
    analyseur.add_argument("--lcu-moyennes", type=float, default=0.1)
    analyseur.add_argument(
        "--supplements", type=float, default=0, help="USD : snapshots, domaine, trafic supplémentaire, etc."
    )
    return analyseur


def principal():
    analyseur = arguments()
    options = analyseur.parse_args()
    if any(isinstance(v, (int, float)) and (not math.isfinite(v) or v < 0) for v in vars(options).values()):
        analyseur.error("Les quantités doivent être positives ou nulles.")
    tarifs = json.loads(
        (Path(__file__).resolve().parents[1] / "documentation" / "tarifs.json").read_text(encoding="utf-8")
    )
    try:
        durees, postes = calculer(tarifs, options)
    except ValueError as erreur:
        analyseur.error(str(erreur))
    print(f"Profil {options.profil} ; Paris, USD HT, sans crédits AWS. Mois de référence : 730 h.")
    print("Durées : " + ", ".join(f"{nom}={valeur:g} h" for nom, valeur in durees.items()))
    for nom, valeur in postes.items():
        print(f"{nom:36} {valeur:8.4f} USD")
    print(f"TOTAL ESTIMÉ                         {sum(postes.values()):8.2f} USD HT")
    if options.profil == "seance":
        print(
            "Pour ne compter que la séance, les ressources doivent être supprimées ensuite ; augmentez conservation si vous les gardez."
        )
    if options.profil == "intermittent":
        print(
            "Les heures ALB couvrent son existence entière. RDS redémarre automatiquement après 7 jours d’arrêt maximum."
        )
    print(
        "Les durées doivent inclure démarrages, déploiements et arrêts. Fermer le navigateur n’arrête rien."
    )
    print(
        "Incluez les minimums dans les durées : ALB heure entamée, RDS 10 min après démarrage, Fargate Linux 1 min par tâche."
    )
    print(
        "Hypothèses : 1 000 écritures/10 000 lectures S3, 1 000 lectures de secrets, logs gardés au plus 7 jours."
    )
    print(
        "Prorata de stockage/secrets/alarme simplifié ; les durées réelles de ces ressources peuvent différer."
    )
    print(
        "Hors domaine, taxes, trafic, snapshots supplémentaires, CPU RDS excédentaire, vision/branching et tâches/IP transitoires."
    )
    print(
        f"Tarifs de référence vérifiés le {tarifs['date_verification']}. Ce programme ne lance ni n’arrête aucun service."
    )


if __name__ == "__main__":
    principal()
