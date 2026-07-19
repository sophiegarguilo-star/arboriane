# -*- coding: utf-8 -*-
"""
Génère CHANGELOG.md depuis les notes de version (services/maj.py).

Les notes « Quoi de neuf » existent déjà et sont montrées dans l'application ;
elles sont la source unique. Recopier un journal à la main, c'est le laisser
diverger. Ce script écrit un CHANGELOG.md au format « Keep a Changelog »
(keepachangelog.com) à partir de NOTES, et rien d'autre.

Les titres de version sont de simples en-têtes Markdown (ancres internes
générées automatiquement par GitHub) : on ne pointe PLUS vers les pages de
tags/releases, car une release peut être dépubliée (politique de rétention :
seules N-1 et N-2 restent en ligne, voir BUILD.md) et le lien deviendrait mort.

    python -X utf8 outils/generer_changelog.py            # écrit CHANGELOG.md
    python -X utf8 outils/generer_changelog.py --verifier  # échoue s'il est périmé
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from services.maj import NOTES          # noqa: E402
from core.version import VERSION        # noqa: E402

CIBLE = os.path.join(RACINE, "CHANGELOG.md")

ENTETE = """# Journal des versions

Toutes les versions notables d'Arboriane. Format inspiré de
[Keep a Changelog](https://keepachangelog.com/fr/), versions selon
[SemVer](https://semver.org/lang/fr/).

> Ce fichier est **généré** depuis les notes de l'application
> (`services/maj.py`) : ne le modifiez pas à la main, lancez
> `python -X utf8 outils/generer_changelog.py`.
"""


def verifier_coherence(notes=NOTES, version=VERSION):
    """'' si tout va bien, sinon le message d'erreur.

    La première entrée de NOTES doit être la version courante : publier sans
    avoir écrit les notes de la version, c'est exactement comme ça que les
    versions 1.9.6 → 1.9.10 se sont retrouvées sans « Quoi de neuf »."""
    if not notes:
        return "NOTES est vide (services/maj.py)."
    if notes[0]["version"] != version:
        return ("NOTES[0] est en version %s mais core/version.py dit %s : "
                "ajoutez l'entrée « %s » en TÊTE de NOTES (services/maj.py)."
                % (notes[0]["version"], version, version))
    return ""


def rendu():
    lignes = [ENTETE]
    for n in NOTES:
        v = n["version"]
        date = n.get("date", "")
        # En-tête simple : GitHub en fait une ancre interne (#190--2026-07-13
        # etc.), qui survit à la suppression des vieilles releases — un lien
        # /releases/tag/vX.Y.Z, lui, meurt avec la rétention N-1/N-2.
        lignes.append("\n## %s — %s\n" % (v, date))
        for p in n.get("points", []):
            # une puce par point, texte tel quel (déjà rédigé pour l'utilisateur)
            lignes.append("- %s" % p.strip())
    return "\n".join(lignes).rstrip() + "\n"


def main():
    erreur = verifier_coherence()
    if erreur:
        print("INCOHÉRENCE des notes de version : " + erreur)
        return 1
    texte = rendu()
    if "--verifier" in sys.argv[1:]:
        actuel = open(CIBLE, encoding="utf-8").read() if os.path.exists(CIBLE) else ""
        if actuel != texte:
            print("CHANGELOG.md est PÉRIMÉ. Régénérez-le :")
            print("   python -X utf8 outils/generer_changelog.py")
            return 1
        print("CHANGELOG.md à jour (notes alignées sur la version %s)." % VERSION)
        return 0
    with open(CIBLE, "w", encoding="utf-8", newline="\n") as f:
        f.write(texte)
    print("CHANGELOG.md écrit (%d versions)." % len(NOTES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
