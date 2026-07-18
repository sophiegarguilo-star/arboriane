# -*- coding: utf-8 -*-
"""
Test du Lot 7 — Sosa permanent (figer/effacer/lister) + round-trip GEDCOM _SOSA.

Exécuter :  python -X utf8 tests/test_sosa_permanent.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import modele, gedcom                    # noqa: E402
from core.modele import nom_complet                 # noqa: E402
from services import sosa_permanent                 # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _base():
    d = modele.base_vide()
    d["individus"] = {
        "I1": {"id": "I1", "prenoms": "Racine", "nom": "UN", "sexe": "M", "famc": ["F1"]},
        "I2": {"id": "I2", "prenoms": "Pere", "nom": "DEUX", "sexe": "M", "fams": ["F1"], "famc": ["F2"]},
        "I3": {"id": "I3", "prenoms": "Mere", "nom": "TROIS", "sexe": "F", "fams": ["F1"]},
        "I4": {"id": "I4", "prenoms": "Aieul", "nom": "QUATRE", "sexe": "M", "fams": ["F2"]},
    }
    d["familles"] = {
        "F1": {"id": "F1", "mari": "I2", "epouse": "I3", "enfants": ["I1"]},
        "F2": {"id": "F2", "mari": "I4", "enfants": ["I2"]},
    }
    return d


def test_figer_effacer_lister():
    d = _base()
    n = sosa_permanent.figer(d, "I1")
    verifie("sosa perm. : 4 personnes numérotées", n == 4)
    verifie("sosa perm. : racine = 1", d["individus"]["I1"]["sosa"] == 1)
    verifie("sosa perm. : père = 2", d["individus"]["I2"]["sosa"] == 2)
    verifie("sosa perm. : aïeul paternel = 4", d["individus"]["I4"]["sosa"] == 4)
    lst = sosa_permanent.lister(d)
    verifie("sosa perm. : liste triée par numéro",
            [p["sosa"] for p in lst["personnes"]] == [1, 2, 3, 4])
    r = sosa_permanent.effacer(d)
    verifie("sosa perm. : effacement", r == 4 and "sosa" not in d["individus"]["I1"])


def test_round_trip_sosa():
    d = _base()
    sosa_permanent.figer(d, "I1")
    avant = {nom_complet(i): i["sosa"] for i in d["individus"].values() if i.get("sosa")}
    texte = gedcom.exporter(d)
    verifie("_SOSA : présent dans le GEDCOM exporté", "_SOSA" in texte)
    d2 = gedcom.importer(texte)
    apres = {nom_complet(i): i.get("sosa") for i in d2["individus"].values() if i.get("sosa")}
    verifie("_SOSA : round-trip conserve les numéros", apres == avant)


if __name__ == "__main__":
    test_figer_effacer_lister()
    test_round_trip_sosa()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
