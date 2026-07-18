# -*- coding: utf-8 -*-
"""
Test L9 — rendu « sablier » (ascendance haut + descendance bas, racine au centre).

Exécuter :  python -X utf8 tests/test_arbre_sablier.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application       # noqa: E402
from services import arbre                      # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _base():
    app = Application(tempfile.mkdtemp())
    app.creer("T")
    b = app.base
    def ind(i):
        return {"id": i, "prenoms": i, "nom": "X", "sexe": "U",
                "naissance": {"date": "1900", "lieu": "Tours"}, "deces": {}}
    b.donnees["individus"] = {x: ind(x) for x in
                              ["I1", "I2", "I3", "I4", "I5", "I6", "I7"]}
    b.donnees["familles"] = {
        "FA": {"id": "FA", "mari": "I2", "epouse": "I3", "enfants": ["I1"]},   # parents de I1
        "FB": {"id": "FB", "mari": "I4", "epouse": "", "enfants": ["I2"]},     # grand-père
        "FC": {"id": "FC", "mari": "I1", "epouse": "", "enfants": ["I5", "I6"]},  # enfants de I1
        "FD": {"id": "FD", "mari": "I5", "epouse": "", "enfants": ["I7"]},     # petit-enfant
    }
    b._recalc_tous_liens()
    return b


def test_sablier():
    b = _base()
    svg = arbre.rendre(b.donnees, "I1", "sablier",
                       {"dates": True, "sosa": True, "titre": "Sablier de test"})
    verifie("SVG produit", svg.startswith("<svg") and svg.endswith("</svg>"))
    verifie("racine dessinée UNE seule fois (data-root)",
            svg.count('data-root="1"') == 1)
    verifie("7 cartes (racine partagée)", svg.count('class="indi"') == 7)
    verifie("ancêtre I4 présent (branche haute)", 'data-id="I4"' in svg)
    verifie("descendant I7 présent (branche basse)", 'data-id="I7"' in svg)
    # racine sans ascendance ni descendance -> une seule carte, pas d'erreur
    svg1 = arbre.rendre(b.donnees, "I7", "sablier", {"dates": False})
    verifie("racine isolée : rend sans erreur", svg1.startswith("<svg"))


if __name__ == "__main__":
    test_sablier()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
