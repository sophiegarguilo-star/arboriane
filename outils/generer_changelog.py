# -*- coding: utf-8 -*-
"""
Génère CHANGELOG.md depuis les notes de version (services/maj.py).

Les notes « Quoi de neuf » existent déjà et sont montrées dans l'application ;
elles sont la source unique. Recopier un journal à la main, c'est le laisser
diverger. Ce script écrit un CHANGELOG.md au format « Keep a Changelog »
(keepachangelog.com) à partir de NOTES, et rien d'autre.

    python -X utf8 outils/generer_changelog.py            # écrit CHANGELOG.md
    python -X utf8 outils/generer_changelog.py --verifier  # échoue s'il est périmé
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from services.maj import NOTES          # noqa: E402

CIBLE = os.path.join(RACINE, "CHANGELOG.md")
DEPOT = "https://github.com/sophiegarguilo-star/arboriane"

ENTETE = """# Journal des versions

Toutes les versions notables d'Arboriane. Format inspiré de
[Keep a Changelog](https://keepachangelog.com/fr/), versions selon
[SemVer](https://semver.org/lang/fr/).

> Ce fichier est **généré** depuis les notes de l'application
> (`services/maj.py`) : ne le modifiez pas à la main, lancez
> `python -X utf8 outils/generer_changelog.py`.
"""


def rendu():
    lignes = [ENTETE]
    for n in NOTES:
        v = n["version"]
        date = n.get("date", "")
        lignes.append("\n## [%s](%s/releases/tag/v%s) — %s\n" % (v, DEPOT, v, date))
        for p in n.get("points", []):
            # une puce par point, texte tel quel (déjà rédigé pour l'utilisateur)
            lignes.append("- %s" % p.strip())
    return "\n".join(lignes).rstrip() + "\n"


def main():
    texte = rendu()
    if "--verifier" in sys.argv[1:]:
        actuel = open(CIBLE, encoding="utf-8").read() if os.path.exists(CIBLE) else ""
        if actuel != texte:
            print("CHANGELOG.md est PÉRIMÉ. Régénérez-le :")
            print("   python -X utf8 outils/generer_changelog.py")
            return 1
        print("CHANGELOG.md à jour.")
        return 0
    with open(CIBLE, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)
    print("CHANGELOG.md écrit (%d versions)." % len(NOTES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
