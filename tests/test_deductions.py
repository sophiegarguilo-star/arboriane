# -*- coding: utf-8 -*-
"""
Test du Lot 5 — déductions & complétude (sexes/noms absents).

Exécuter :  python -X utf8 tests/test_deductions.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import modele                            # noqa: E402
from services import deductions                     # noqa: E402

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
        "I1": {"id": "I1", "prenoms": "Jean", "nom": "MARTIN", "sexe": "U", "fams": ["F1"]},
        "I2": {"id": "I2", "prenoms": "Marie", "nom": "DURAND", "sexe": "U", "fams": ["F1"]},
        "I3": {"id": "I3", "prenoms": "Solo", "nom": "SEUL", "sexe": "U"},
        "I4": {"id": "I4", "prenoms": "", "nom": "", "sexe": "M"},
        "I5": {"id": "I5", "prenoms": "Anne", "nom": "", "sexe": "F"},
        "I6": {"id": "I6", "prenoms": "", "nom": "BROWN", "sexe": "M"},
        "I7": {"id": "I7", "prenoms": "Complet", "nom": "OK", "sexe": "N"},
    }
    d["familles"] = {"F1": {"id": "F1", "mari": "I1", "epouse": "I2", "enfants": []}}
    return d


def test_sexes_absents():
    d = _base()
    r = deductions.sexes_absents(d)
    par_id = {p["id"]: p for p in r["personnes"]}
    verifie("sexes : 3 personnes sans sexe (U)", r["total"] == 3)
    verifie("sexes : mari déduit masculin", par_id["I1"]["sexe_propose"] == "M")
    verifie("sexes : épouse déduite féminin", par_id["I2"]["sexe_propose"] == "F")
    verifie("sexes : isolé sans proposition", par_id["I3"]["sexe_propose"] == "")
    verifie("sexes : 2 déductibles", r["nb_deductibles"] == 2)
    verifie("sexes : N (non consigné) non listé", "I7" not in par_id)


def test_noms_absents():
    d = _base()
    r = deductions.noms_absents(d)
    par_id = {p["id"]: p["manque"] for p in r["personnes"]}
    verifie("noms : sans nom ni prénom", par_id.get("I4") == "nom_et_prenom")
    verifie("noms : sans nom", par_id.get("I5") == "nom")
    verifie("noms : sans prénom", par_id.get("I6") == "prenom")
    verifie("noms : fiche complète exclue", "I7" not in par_id)


def test_appliquer_sexe():
    d = _base()
    deductions.appliquer_sexe(d, "I1", "M")
    verifie("appliquer : sexe posé", d["individus"]["I1"]["sexe"] == "M")
    ok = False
    try:
        deductions.appliquer_sexe(d, "I1", "Z")
    except ValueError:
        ok = True
    verifie("appliquer : sexe invalide refusé", ok)
    ok = False
    try:
        deductions.appliquer_sexe(d, "INCONNU", "M")
    except ValueError:
        ok = True
    verifie("appliquer : personne inconnue refusée", ok)


if __name__ == "__main__":
    test_sexes_absents()
    test_noms_absents()
    test_appliquer_sexe()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
