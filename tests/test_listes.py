# -*- coding: utf-8 -*-
"""
Test du Lot 8 — index métiers, unions, ascendance/descendance texte, éphéméride.

Exécuter :  python -X utf8 tests/test_listes.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import modele                            # noqa: E402
from services import index_pro, listes, anniversaires  # noqa: E402

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
        "I1": {"id": "I1", "prenoms": "Jean", "nom": "MARTIN", "sexe": "M",
               "professions": [{"valeur": "Boulanger"}],
               "naissance": {"date": "12 JAN 1850"}, "fams": ["F1"], "famc": ["F2"]},
        "I2": {"id": "I2", "prenoms": "Marie", "nom": "DURAND", "sexe": "F",
               "professions": [{"valeur": "Couturière"}],
               "naissance": {"date": "05 MAR 1852"}, "fams": ["F1"]},
        "I3": {"id": "I3", "prenoms": "Louis", "nom": "MARTIN", "sexe": "M",
               "professions": [{"valeur": "Boulanger"}],
               "naissance": {"date": "1820"}, "fams": ["F2"]},
        "I4": {"id": "I4", "prenoms": "Petit", "nom": "MARTIN",
               "naissance": {"date": "01/06/1875"}, "famc": ["F1"]},
    }
    d["familles"] = {
        "F1": {"id": "F1", "mari": "I1", "epouse": "I2", "enfants": ["I4"],
               "mariage": {"date": "1874", "lieu": "Tours"}},
        "F2": {"id": "F2", "mari": "I3", "enfants": ["I1"], "mariage": {}},
    }
    return d


def test_index_metiers():
    r = index_pro.index(_base())
    par = {m["metier"]: m["nb"] for m in r["metiers"]}
    verifie("métiers : 2 métiers distincts", r["total_metiers"] == 2)
    verifie("métiers : Boulanger regroupe 2 personnes", par.get("Boulanger") == 2)
    verifie("métiers : le plus fréquent en tête", r["metiers"][0]["metier"] == "Boulanger")


def test_unions():
    r = listes.unions(_base())
    verifie("unions : 2 unions", r["total"] == 2)
    verifie("unions : triées, mariage daté d'abord", r["unions"][0]["mari"] == "Jean MARTIN")
    verifie("unions : lieu porté", r["unions"][0]["lieu"] == "Tours")


def test_ascendance_descendance_texte():
    d = _base()
    asc = listes.ascendance_texte(d, "I4")
    par_sosa = {l["sosa"]: l["nom"] for l in asc["lignes"]}
    verifie("ascendance : 4 lignes", asc["total"] == 4)
    verifie("ascendance : Sosa 2 = père", par_sosa.get(2) == "Jean MARTIN")
    desc = listes.descendance_texte(d, "I3")
    par_num = {l["id"]: l["numero"] for l in desc["lignes"]}
    verifie("descendance : arrière-petit = 1.1.1", par_num.get("I4") == "1.1.1")
    verifie("descendance : total 3", desc["total"] == 3)


def test_ephemeride():
    verifie("éphéméride : jour/mois lettres", anniversaires._jour_mois("12 JAN 1850") == (1, 12))
    verifie("éphéméride : jour/mois numérique", anniversaires._jour_mois("01/06/1875") == (6, 1))
    verifie("éphéméride : année seule → None", anniversaires._jour_mois("1820") is None)
    r = anniversaires.ephemeride(_base())
    verifie("éphéméride : 3 dates exploitables (I3 exclu)", r["total"] == 3)
    verifie("éphéméride : classé par jour de l'année (janvier d'abord)",
            r["personnes"][0]["nom"] == "Jean MARTIN")


def test_routes_l8():
    import tempfile
    from core.application import Application
    from services import demo
    import routes
    routes.charger_modules()
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    pid = next(iter(app.base.donnees["individus"]))
    for path, params in (("/api/index-metiers", {}), ("/api/unions", {}),
                         ("/api/ephemeride", {}), ("/api/ascendance-texte", {"id": pid}),
                         ("/api/descendance-texte", {"id": pid})):
        code, _ = routes.dispatch(app, "GET", path, params, {})
        verifie("route " + path + " : 200", code == 200)


if __name__ == "__main__":
    test_index_metiers()
    test_unions()
    test_ascendance_descendance_texte()
    test_ephemeride()
    test_routes_l8()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
