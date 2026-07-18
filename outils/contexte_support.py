# -*- coding: utf-8 -*-
"""
Contexte de support : ce qu'on peut affirmer à un utilisateur, aujourd'hui.

Répondre de mémoire à un rapport de bug, c'est promettre des correctifs qui
n'existent pas ou ignorer une version déjà publiée. Ce script lit les sources de
vérité — core/version.py et les NOTES de services/maj.py — et les imprime. Toute
réponse à un utilisateur doit s'appuyer sur cette sortie, pas sur un souvenir.

    python -X utf8 outils/contexte_support.py            # version + 3 dernières notes
    python -X utf8 outils/contexte_support.py --tout     # toutes les notes
    python -X utf8 outils/contexte_support.py --chercher gedcom
"""

import os
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.version import VERSION          # noqa: E402
from services.maj import NOTES            # noqa: E402


def _publiee():
    """Dernière version RÉELLEMENT publiée. La version du code peut être en
    avance : ne jamais annoncer à un utilisateur un correctif qu'il ne peut pas
    encore télécharger. On interroge les releases GitHub ; à défaut, les tags
    strictement numérotés (« v2-restauration » n'est pas une version)."""
    try:
        out = subprocess.run(["gh", "release", "view", "--json", "tagName",
                              "--jq", ".tagName"],
                             cwd=RACINE, capture_output=True, text=True, timeout=20)
        tag = out.stdout.strip()
        if out.returncode == 0 and tag:
            return tag
    except Exception:                       # noqa: BLE001
        pass
    try:
        out = subprocess.run(["git", "tag", "--list", "v[0-9]*.[0-9]*.[0-9]*",
                              "--sort=-v:refname"],
                             cwd=RACINE, capture_output=True, text=True, timeout=10)
        tags = [t for t in out.stdout.split() if t]
        return tags[0] if tags else "(aucune release)"
    except Exception:                       # noqa: BLE001
        return "(git indisponible)"


def _commits(n=8):
    try:
        out = subprocess.run(["git", "log", "--oneline", "-%d" % n],
                             cwd=RACINE, capture_output=True, text=True, timeout=10)
        return out.stdout.rstrip()
    except Exception:                       # noqa: BLE001
        return "(git indisponible)"


def main():
    args = sys.argv[1:]
    tout = "--tout" in args
    motif = ""
    if "--chercher" in args:
        i = args.index("--chercher")
        motif = args[i + 1].lower() if i + 1 < len(args) else ""

    print("VERSION DU CODE     : %s" % VERSION)
    print("DERNIÈRE PUBLIÉE    : %s" % _publiee())
    print("  (si elles diffèrent, le correctif n'est PAS encore chez l'utilisateur)")
    print()

    notes = NOTES
    if motif:
        notes = [n for n in NOTES
                 if any(motif in p.lower() for p in n["points"])
                 or motif in n["version"]]
        print("NOTES CONTENANT %r : %d version(s)\n" % (motif, len(notes)))
    elif not tout:
        notes = NOTES[:3]

    for n in notes:
        print("── %s  (%s)" % (n["version"], n.get("date", "?")))
        for p in n["points"]:
            print("   • %s" % p)
        print()

    print("DERNIERS COMMITS")
    print(_commits())


if __name__ == "__main__":
    main()
