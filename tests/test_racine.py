# -*- coding: utf-8 -*-
"""La racine (Sosa 1) doit toujours désigner quelqu'un qui existe.

Le manifeste porte « I1 » par défaut : un arbre neuf, un GEDCOM aux identifiants
inhabituels, ou la suppression de la racine, laissaient une racine dans le vide
(Sosa n'affichait plus rien).

Exécuter :  python -X utf8 tests/test_racine.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
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


def app_arbre():
    app = Application(tempfile.mkdtemp())
    call(app, "POST", "/api/espaces/creer", {"nom": "R"})
    return app


def test_premiere_personne_devient_racine():
    app = app_arbre()
    verifie("arbre vide : racine invalide", not app.racine_valide())
    pid = call(app, "POST", "/api/individus", {"nom": "A", "prenoms": "Un"})[1]["id"]
    verifie("1re personne = racine", app.manifeste["racine_id"] == pid)
    verifie("racine valide", app.racine_valide())
    # une 2e personne ne vole pas la racine
    call(app, "POST", "/api/individus", {"nom": "B", "prenoms": "Deux"})
    verifie("la racine ne change pas ensuite", app.manifeste["racine_id"] == pid)


def test_suppression_de_la_racine():
    app = app_arbre()
    a = call(app, "POST", "/api/individus", {"nom": "A", "prenoms": "Un"})[1]["id"]
    b = call(app, "POST", "/api/individus", {"nom": "B", "prenoms": "Deux"})[1]["id"]
    call(app, "DELETE", "/api/individus/" + a)
    verifie("après suppression de la racine : racine valide", app.racine_valide())
    verifie("racine adoptée = personne restante", app.manifeste["racine_id"] == b)
    code, sosa = call(app, "GET", "/api/sosa")
    verifie("/api/sosa répond encore", code == 200)
    # dernier individu supprimé : pas de crash
    call(app, "DELETE", "/api/individus/" + b)
    verifie("arbre vidé : pas de crash", len(app.base.donnees["individus"]) == 0)


_GED = """0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @X7@ INDI
1 NAME Jean /MARTIN/
1 SEX M
0 @X8@ INDI
1 NAME Marie /DURAND/
1 SEX F
0 TRLR
"""


def test_import_gedcom_sans_I1():
    app = app_arbre()
    code, _ = call(app, "POST", "/api/import/gedcom/appliquer", {"texte": _GED})
    verifie("import GEDCOM : 200", code == 200)
    verifie("import sans I1 : racine valide quand même", app.racine_valide())
    code, sosa = call(app, "GET", "/api/sosa")
    verifie("/api/sosa répond après import", code == 200)
    verifie("de cujus renseigné", bool(sosa.get("de_cujus")))


if __name__ == "__main__":
    for t in (test_premiere_personne_devient_racine, test_suppression_de_la_racine,
              test_import_gedcom_sans_I1):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
