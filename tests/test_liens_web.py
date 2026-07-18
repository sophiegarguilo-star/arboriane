# -*- coding: utf-8 -*-
"""
Test du Lot 6 — liens de recherche web (URL construites localement).

Exécuter :  python -X utf8 tests/test_liens_web.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from services import demo, liens_web              # noqa: E402
import routes                                       # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


_IND = {"id": "I1", "prenoms": "Jean Pierre", "nom": "MARTIN",
        "naissance": {"date": "1850", "lieu": "Marseille, Bouches-du-Rhône"}}


def test_liens_pour():
    liens = liens_web.liens_pour(_IND)
    urls = {l["id"]: l["url"] for l in liens}
    verifie("liens : tous les sites par défaut", len(liens) == len(liens_web.SITES))
    verifie("liens : Geneanet présent", "geneanet" in urls)
    verifie("liens : nom substitué et encodé", "nom=MARTIN" in urls["geneanet"])
    verifie("liens : prénom usuel substitué", "prenom=Jean" in urls["geneanet"])
    verifie("liens : Gallica présent et nom substitué", "MARTIN" in urls.get("gallica", ""))
    verifie("liens : Géopatronyme (mort) retiré", "geopatronyme" not in urls)
    verifie("liens : Filae → page patronyme", urls.get("filae", "").endswith("/MARTIN"))
    verifie("liens : lieu encodé dans Google", "Marseille" in urls["google"] and "%2C" in urls["google"])


def test_liens_vides_et_perso():
    verifie("liens : sans nom ni prénom → aucun",
            liens_web.liens_pour({"id": "I9", "prenoms": "", "nom": ""}) == [])
    reglages = {"liens_web_perso": [{"nom": "Mon cercle", "gabarit": "https://cercle.fr/?n={nom}"}]}
    liens = liens_web.liens_pour(_IND, reglages)
    perso = [l for l in liens if l["nom"] == "Mon cercle"]
    verifie("liens : site personnel ajouté", len(perso) == 1)
    verifie("liens : site personnel substitué", perso and "n=MARTIN" in perso[0]["url"])


def test_route_liens():
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    pid = next(iter(app.base.donnees["individus"]))
    code, r = routes.dispatch(app, "GET", "/api/liens", {"id": pid}, {})
    verifie("route /api/liens : 200", code == 200)
    verifie("route /api/liens : liste de liens", isinstance(r.get("liens"), list))
    code2, _ = routes.dispatch(app, "GET", "/api/liens", {"id": "INCONNU"}, {})
    verifie("route /api/liens : personne inconnue → 400", code2 == 400)


if __name__ == "__main__":
    test_liens_pour()
    test_liens_vides_et_perso()
    test_route_liens()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
