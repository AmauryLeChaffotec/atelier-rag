"""Actualisation facultative des polices locales ; inutile pour démarrer l’application."""
import re
from pathlib import Path
from urllib.request import Request, urlopen

racine = Path(__file__).resolve().parents[1]
dossier = racine / "interface" / "public" / "polices"
dossier.mkdir(exist_ok=True)
url = "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap"
css = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read().decode()
blocs = []
for bloc in re.findall(r"@font-face\s*\{[^}]+\}", css):
    famille = re.search(r"font-family:\s*'([^']+)'", bloc)[1]
    poids = re.search(r"font-weight:\s*(\d+)", bloc)[1]
    source = re.search(r"url\(([^)]+)\)", bloc)[1]
    nom = famille.lower().replace(" ", "-") + "-" + poids + ".ttf"
    (dossier / nom).write_bytes(urlopen(source, timeout=30).read())
    blocs.append(bloc.replace(source, "/polices/" + nom))
(dossier / "polices.css").write_text("\n".join(blocs), encoding="utf-8")
for famille, chemin in [("dm-sans", "dmsans"), ("manrope", "manrope")]:
    licence = urlopen(f"https://raw.githubusercontent.com/google/fonts/main/ofl/{chemin}/OFL.txt", timeout=30).read()
    (dossier / f"licence-{famille}.txt").write_bytes(licence)
print("Polices et licences enregistrées localement.")
