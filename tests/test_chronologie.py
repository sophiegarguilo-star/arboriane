# -*- coding: utf-8 -*-
"""
Test L11 — chronologie agrégée (frise multi-personnes + contemporains).

Exécuter :  python -X utf8 tests/test_chronologie.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application       # noqa: E402
from services import chronologie as ch          # noqa: E402

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
    def ind(i, nom, an_n, an_d):
        return {"id": i, "prenoms": nom, "nom": "X", "sexe": "U",
                "naissance": {"date": str(an_n) if an_n else "", "lieu": ""},
                "deces": {"date": str(an_d) if an_d else "", "lieu": ""}}
    b.donnees["individus"] = {
        "I1": ind("I1", "Base", 1850, 1910),
        "I2": ind("I2", "Conjoint", 1852, 1920),
        "I3": ind("I3", "Pere", 1800, 1855),
        "I4": ind("I4", "PlusTard", 1950, 2000),
        "I5": ind("I5", "Voisin", 1860, 1900),
    }
    b.donnees["familles"] = {
        "F1": {"id": "F1", "mari": "I3", "epouse": "", "enfants": ["I1"]},
        "F2": {"id": "F2", "mari": "I1", "epouse": "I2", "enfants": []},
    }
    b._recalc_tous_liens(); b.sauvegarder()
    return b


def test_intervalle():
    d = _base().donnees
    verifie("intervalle deux bornes", ch._intervalle(d["individus"]["I1"]) == (1850, 1910, False))
    # seulement naissance -> fin estimée
    seul = {"naissance": {"date": "1900"}, "deces": {}}
    iv = ch._intervalle(seul)
    verifie("intervalle estimé (naissance seule)", iv[0] == 1900 and iv[2] is True)
    verifie("aucune date -> None", ch._intervalle({"naissance": {}, "deces": {}}) is None)


def test_frise():
    d = _base().donnees
    f = ch.frise(d, ["I1", "I2", "I4"])
    verifie("frise : 3 personnes triées par début",
            [p["id"] for p in f["personnes"]] == ["I1", "I2", "I4"])
    verifie("frise : amplitude min/max", f["min"] == 1850 and f["max"] == 2000)


def test_contemporains():
    d = _base().donnees
    c = ch.contemporains(d, "I1")
    ids = {x["id"]: x for x in c["contemporains"]}
    verifie("I2 (conjoint) contemporain et lié", ids.get("I2") and ids["I2"]["lie"] is True)
    verifie("I3 (père) contemporain et lié", ids.get("I3") and ids["I3"]["lie"] is True)
    verifie("I5 (voisin) contemporain sans lien", ids.get("I5") and ids["I5"]["lie"] is False)
    verifie("I4 (postérieur) non contemporain", "I4" not in ids)
    verifie("chevauchement I3 = 1850–1855",
            ids.get("I3") and ids["I3"]["chevauchement"] == [1850, 1855])
    verifie("compteurs liés / sans lien", c["nb_lies"] == 2 and c["nb_sans_lien"] == 1)


if __name__ == "__main__":
    test_intervalle()
    test_frise()
    test_contemporains()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
