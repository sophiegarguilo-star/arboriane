# -*- coding: utf-8 -*-
"""Édition d'une union : date/lieu de mariage, divorce, et preuves préservées.

Exécuter :  python -X utf8 tests/test_union_edition.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from core import gedcom                            # noqa: E402
import routes                                      # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def call(app, m, c, corps=None, params=None):
    return routes.dispatch(app, m, c, params or {}, corps or {})


def _couple():
    app = Application(tempfile.mkdtemp())
    call(app, "POST", "/api/espaces/creer", {"nom": "U"})
    a = call(app, "POST", "/api/individus", {"nom": "A", "prenoms": "Marc", "sexe": "M"})[1]["id"]
    b = call(app, "POST", "/api/individus/%s/conjoint" % a,
             {"champs": {"nom": "B", "prenoms": "Sophie", "sexe": "F"}})[1]["id"]
    fid = call(app, "GET", "/api/individus/" + a)[1]["unions"][0]["famille"]
    return app, a, b, fid


def test_mariage_et_divorce():
    app, a, b, fid = _couple()
    code, _ = call(app, "PUT", "/api/familles/" + fid,
                   {"mariage": {"date": "10 JUN 2000", "lieu": "Lyon"},
                    "evenements": [{"type": "DIV", "date": "5 MAY 2015", "lieu": "Lyon", "valeur": ""}]})
    verifie("PUT famille : 200", code == 200)
    fa = call(app, "GET", "/api/individus/" + a)[1]
    u = fa["unions"][0]
    verifie("mariage enregistré (date)", u["mariage"].get("date") == "10 JUN 2000")
    verifie("mariage enregistré (lieu)", u["mariage"].get("lieu") == "Lyon")
    verifie("divorce exposé dans la fiche",
            any(e.get("type") == "DIV" for e in u.get("evenements", [])))
    # visible aussi chez l'autre conjoint (fait du couple)
    fb = call(app, "GET", "/api/individus/" + b)[1]
    verifie("divorce visible chez l'autre conjoint",
            any(e.get("type") == "DIV" for e in fb["unions"][0].get("evenements", [])))


def test_preuves_du_mariage_preservees():
    """Un écran qui n'envoie que date/lieu ne doit PAS effacer les citations."""
    app, a, b, fid = _couple()
    sid = call(app, "POST", "/api/sources", {"titre": "Acte de mariage"})[1]["id"]
    call(app, "POST", "/api/individus/%s/citer" % a,
         {"fait": "union", "source": sid, "quay": 3, "famille": fid})
    call(app, "PUT", "/api/familles/" + fid, {"mariage": {"date": "2000", "lieu": "Lyon"}})
    mar = app.base.donnees["familles"][fid]["mariage"]
    verifie("citations du mariage préservées après édition",
            any(c.get("source") == sid for c in mar.get("citations", [])))
    verifie("date bien mise à jour", mar.get("date") == "2000")


def test_divorce_aller_retour_gedcom():
    app, a, b, fid = _couple()
    call(app, "PUT", "/api/familles/" + fid,
         {"mariage": {"date": "10 JUN 2000", "lieu": "Lyon"},
          "evenements": [{"type": "DIV", "date": "5 MAY 2015", "lieu": "Lyon", "valeur": ""}]})
    texte = call(app, "GET", "/api/export/gedcom")[1]["texte"]
    verifie("GEDCOM : balise MARR", "\n1 MARR" in texte)
    verifie("GEDCOM : balise DIV", "\n1 DIV" in texte)
    verifie("GEDCOM : date du divorce", "5 MAY 2015" in texte)
    # ré-import : le divorce survit
    donnees = gedcom.importer(texte)
    fams = list(donnees["familles"].values())
    verifie("réimport : divorce conservé",
            any(any(e.get("type") == "DIV" for e in f.get("evenements", [])) for f in fams))


if __name__ == "__main__":
    for t in (test_mariage_et_divorce, test_preuves_du_mariage_preservees,
              test_divorce_aller_retour_gedcom):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
