"""Une application éteinte ne doit pas masquer le stockage ni un ALB conservé."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from estimer_cout import arguments, calculer

RACINE = Path(__file__).resolve().parents[2]

TARIFS = json.loads((RACINE / "documentation" / "tarifs.json").read_text(encoding="utf-8"))


def test_base_arretee_conserve_cout_disque():
    options = arguments().parse_args(["--profil", "intermittent", "--heures-rds", "0"])
    _, postes = calculer(TARIFS, options)
    assert postes["RDS : calcul actif"] == 0
    assert postes["RDS : stockage, même arrêté"] == pytest.approx(2.66)


def test_alb_sans_tache_conserve_son_cout_et_ses_ip():
    options = arguments().parse_args(["--profil", "intermittent", "--taches", "0", "--heures-alb", "730"])
    _, postes = calculer(TARIFS, options)
    assert postes["Fargate (0,5 vCPU / 2 GiB)"] == 0
    assert postes["ALB : existence + charge estimée"] > 19
    assert postes["IPv4 : 2 ALB + tâches actives"] == pytest.approx(7.30)


def test_supprimer_alb_change_uniquement_alb_et_ip():
    options = arguments().parse_args(["--profil", "intermittent"])
    _, intermittent = calculer(TARIFS, options)
    options.heures_alb = 730
    _, conserve = calculer(TARIFS, options)
    differences = {cle for cle in intermittent if intermittent[cle] != conserve[cle]}
    assert differences == {"ALB : existence + charge estimée", "IPv4 : 2 ALB + tâches actives"}
    assert sum(conserve.values()) - sum(intermittent.values()) == pytest.approx(26.9306)


@pytest.mark.parametrize("duree", ["-1", "731", "nan", "inf"])
def test_duree_invalide_refusee(duree):
    options = arguments().parse_args(["--heures-rds", duree])
    with pytest.raises(ValueError, match="durée"):
        calculer(TARIFS, options)


def test_stockage_ne_peut_disparaitre_avant_base():
    options = arguments().parse_args(["--heures-rds", "8", "--heures-conservation", "4"])
    with pytest.raises(ValueError, match="stockage RDS"):
        calculer(TARIFS, options)
