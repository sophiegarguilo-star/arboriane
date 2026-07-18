# -*- coding: utf-8 -*-
"""
Test L9 — rendu « tableau par génération » (ascendance imprimable).

Exécuter :  python -X utf8 tests/test_arbre_tableau.py
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
    def ind(i, nom, sexe, an, famc=None):
        d = {"id": i, "prenoms": nom, "nom": "X", "sexe": sexe,
             "naissance": {"date": str(an), "lieu": "Tours"}, "deces": {}}
        if famc:
            d["famc"] = [famc]
        return d
    b.donnees["individus"] = {
        "I1": ind("I1", "Enfant", "U", 1900, "F1"),
        "I2": ind("I2", "Pere", "M", 1870, "F2"),
        "I3": ind("I3", "Mere", "F", 1872),
        "I4": ind("I4", "Gpere", "M", 1840),
    }
    b.donnees["familles"] = {
        "F1": {"id": "F1", "mari": "I2", "epouse": "I3", "enfants": ["I1"]},
        "F2": {"id": "F2", "mari": "I4", "epouse": "", "enfants": ["I2"]},
    }
    b._recalc_tous_liens()
    return b


def test_tableau():
    b = _base()
    svg = arbre.rendre(b.donnees, "I1", "tableau",
                       {"dates": True, "lieux": True, "titre": "Ascendance de test"})
    verifie("SVG produit", svg.startswith("<svg") and svg.endswith("</svg>"))
    verifie("regroupé par génération (Parents / Génération)",
            "Parents" in svg or "Génération" in svg)
    verifie("racine présente (gén. 0)", "La personne racine" in svg)
    verifie("période affichée (dates)", "1870" in svg or "1840" in svg)
    verifie("lieu affiché (Tours)", "Tours" in svg)
    verifie("numéros Sosa présents", ">2<" in svg and ">4<" in svg)


def test_mode_inconnu():
    b = _base()
    try:
        arbre.rendre(b.donnees, "I1", "xxx", {})
        verifie("mode inconnu -> ValueError", False)
    except ValueError:
        verifie("mode inconnu -> ValueError", True)


if __name__ == "__main__":
    test_tableau()
    test_mode_inconnu()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
