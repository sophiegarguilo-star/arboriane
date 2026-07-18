# -*- coding: utf-8 -*-
"""
Test du Lot 7 — calculs : implexe, consanguinité, Aboville.

Exécuter :  python -X utf8 tests/test_implexe.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import modele                            # noqa: E402
from services import implexe, consanguinite, aboville  # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _base_fratrie():
    """I1 est l'enfant de I2 et I3, eux-mêmes frère et sœur (parents I4, I5)."""
    d = modele.base_vide()
    d["individus"] = {
        "I1": {"id": "I1", "prenoms": "Enfant", "nom": "X", "famc": ["F1"]},
        "I2": {"id": "I2", "prenoms": "Père", "nom": "X", "fams": ["F1"], "famc": ["F2"]},
        "I3": {"id": "I3", "prenoms": "Mère", "nom": "X", "fams": ["F1"], "famc": ["F2"]},
        "I4": {"id": "I4", "prenoms": "Aïeul", "nom": "X", "fams": ["F2"]},
        "I5": {"id": "I5", "prenoms": "Aïeule", "nom": "X", "fams": ["F2"]},
    }
    d["familles"] = {
        "F1": {"id": "F1", "mari": "I2", "epouse": "I3", "enfants": ["I1"]},
        "F2": {"id": "F2", "mari": "I4", "epouse": "I5", "enfants": ["I2", "I3"]},
    }
    return d


def test_implexe():
    d = _base_fratrie()
    r = implexe.analyser(d, "I1", generations=4)
    verifie("implexe : taux ≈ 28,6 %", abs(r["taux"] - 28.6) < 0.1)
    verifie("implexe : 2 positions redondantes", r["implexe_total"] == 2)
    g2 = next(g for g in r["generations"] if g["generation"] == 2)
    verifie("implexe : génération 2 = 4 positions / 2 distincts", g2["positions"] == 4 and g2["distincts"] == 2)
    par_id = {m["id"]: m["sosas"] for m in r["ancetres_multiples"]}
    verifie("implexe : I4 aux Sosa 4 et 6", par_id.get("I4") == [4, 6])
    verifie("implexe : I5 aux Sosa 5 et 7", par_id.get("I5") == [5, 7])


def test_consanguinite():
    d = _base_fratrie()
    r = consanguinite.coefficient(d, "I2", "I3")
    verifie("consang. : enfant de fratrie → F = 0,25", abs(r["coefficient"] - 0.25) < 1e-9)
    verifie("consang. : 2 ancêtres communs", r["nb_ancetres_communs"] == 2)
    verifie("consang. : marqué consanguin", r["consanguin"] is True)
    verifie("consang. : couple identique → None", consanguinite.coefficient(d, "I2", "I2") is None)
    # couple non apparenté
    d["individus"]["Z1"] = {"id": "Z1", "prenoms": "Sans", "nom": "Lien"}
    d["individus"]["Z2"] = {"id": "Z2", "prenoms": "Autre", "nom": "Lien"}
    verifie("consang. : sans lien → F = 0",
            consanguinite.coefficient(d, "Z1", "Z2")["coefficient"] == 0)


def test_aboville():
    d = modele.base_vide()
    d["individus"] = {
        "J1": {"id": "J1", "prenoms": "Souche", "nom": "A", "fams": ["G1"]},
        "J2": {"id": "J2", "prenoms": "Aîné", "nom": "A", "famc": ["G1"], "fams": ["G2"]},
        "J3": {"id": "J3", "prenoms": "Cadet", "nom": "A", "famc": ["G1"]},
        "J4": {"id": "J4", "prenoms": "Petit", "nom": "A", "famc": ["G2"]},
    }
    d["familles"] = {
        "G1": {"id": "G1", "mari": "J1", "enfants": ["J2", "J3"]},
        "G2": {"id": "G2", "mari": "J2", "enfants": ["J4"]},
    }
    r = aboville.descendance(d, "J1")
    num = {p["id"]: p["numero"] for p in r["personnes"]}
    verifie("aboville : souche = 1", num.get("J1") == "1")
    verifie("aboville : 2e enfant = 1.2", num.get("J3") == "1.2")
    verifie("aboville : petit-enfant = 1.1.1", num.get("J4") == "1.1.1")
    verifie("aboville : total 4 personnes", r["total"] == 4)


def test_routes_l7():
    import tempfile
    from core.application import Application
    from services import demo
    import routes
    routes.charger_modules()
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    pids = list(app.base.donnees["individus"].keys())
    pid = pids[0]
    for path in ("/api/implexe", "/api/aboville"):
        code, _ = routes.dispatch(app, "GET", path, {"id": pid}, {})
        verifie("route " + path + " : 200", code == 200)
    code, _ = routes.dispatch(app, "GET", "/api/consanguinite",
                              {"a": pids[0], "b": pids[1]}, {})
    verifie("route consanguinité : 200", code == 200)
    code, r = routes.dispatch(app, "POST", "/api/sosa-permanent/figer", {}, {"id": pid})
    verifie("route figer : numérotées ≥ 1", code == 200 and r["numerotees"] >= 1)
    code, r = routes.dispatch(app, "GET", "/api/sosa-permanent", {}, {})
    verifie("route liste Sosa : total ≥ 1", r["total"] >= 1)
    code, r = routes.dispatch(app, "POST", "/api/sosa-permanent/effacer", {}, {})
    verifie("route effacer : ok", r["ok"] is True)


if __name__ == "__main__":
    test_implexe()
    test_consanguinite()
    test_aboville()
    test_routes_l7()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
