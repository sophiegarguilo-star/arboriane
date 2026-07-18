# -*- coding: utf-8 -*-
"""Navigateur préféré (retour utilisateur : Arboriane force Edge). Le réglage
« navigateur » doit être respecté, sans ouvrir de vrai navigateur pendant le test.

Exécuter :  python -X utf8 tests/test_navigateur_prefere.py
"""

import json
import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import navigateur   # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_lire_prefere():
    d = tempfile.mkdtemp()
    verifie("réglage absent -> ''", navigateur.lire_prefere(d) == "")
    with open(os.path.join(d, "reglages.json"), "w", encoding="utf-8") as f:
        json.dump({"navigateur": "Firefox"}, f)
    verifie("lit et normalise en minuscules", navigateur.lire_prefere(d) == "firefox")


def test_ordre_essai():
    essais = []
    orig_lancer, orig_web = navigateur._lancer, navigateur.webbrowser.open
    navigateur._lancer = lambda nav, url: (essais.append(nav) or False)  # échoue toujours
    web = {"appelé": False}
    navigateur.webbrowser.open = lambda url: web.__setitem__("appelé", True) or True
    try:
        essais.clear(); navigateur.ouvrir("http://x", "firefox")
        verifie("préféré Firefox essayé en premier", essais[0] == "firefox")

        essais.clear(); navigateur.ouvrir("http://x", None)
        verifie("sans préférence : Edge en premier", essais[0] == "edge")

        essais.clear(); web["appelé"] = False
        navigateur.ouvrir("http://x", "defaut")
        verifie("« defaut » : aucun navigateur nommé essayé", essais == [])
        verifie("« defaut » : navigateur système utilisé", web["appelé"])
    finally:
        navigateur._lancer, navigateur.webbrowser.open = orig_lancer, orig_web


if __name__ == "__main__":
    test_lire_prefere()
    test_ordre_essai()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
