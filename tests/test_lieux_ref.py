# -*- coding: utf-8 -*-
"""
Test du Lot L15 — référentiel de lieux (hiérarchie + noms datés).

Exécuter :  python -X utf8 tests/test_lieux_ref.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import modele                            # noqa: E402
from services import lieux_ref                      # noqa: E402

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
        "I1": {"id": "I1", "naissance": {"date": "1850", "lieu": "Marseille, Bouches-du-Rhône, France"}},
        "I2": {"id": "I2", "naissance": {"date": "1860", "lieu": "Aix, Bouches-du-Rhône, France"}},
        "I3": {"id": "I3", "deces": {"date": "1900", "lieu": "Napoli, Italia"}},
    }
    return d


def test_construire_hierarchie():
    d = _base()
    r = lieux_ref.construire_depuis_evenements(d)
    verifie("construire : 6 lieux (dédoublonnés)", r["crees"] == 6)
    par_nom = {e["nom"]: e for e in lieux_ref.lister(d)["lieux"]}
    verifie("construire : Bouches-du-Rhône = département",
            par_nom["Bouches-du-Rhône"]["type"] == "département")
    verifie("construire : Marseille = commune", par_nom["Marseille"]["type"] == "commune")
    verifie("construire : chemin de Marseille",
            par_nom["Marseille"]["chemin"] == "Marseille, Bouches-du-Rhône, France")
    verifie("construire : Aix et Marseille partagent le même département",
            par_nom["Aix"]["parent"] == par_nom["Marseille"]["parent"])
    verifie("construire : Napoli (2 parties) = commune", par_nom["Napoli"]["type"] == "commune")
    # idempotent
    r2 = lieux_ref.construire_depuis_evenements(d)
    verifie("construire : idempotent (0 nouveau)", r2["crees"] == 0)


def test_resoudre():
    d = _base()
    lieux_ref.construire_depuis_evenements(d)
    r = lieux_ref.resoudre(d, "Marseille, Bouches-du-Rhône, France")
    verifie("résoudre : chaîne -> entrée", r is not None)
    verifie("résoudre : chemin correct", r["chemin"] == "Marseille, Bouches-du-Rhône, France")
    verifie("résoudre : inconnu -> None", lieux_ref.resoudre(d, "Tombouctou, Mali") is None)


def test_noms_dates():
    d = modele.base_vide()
    e = lieux_ref.creer(d, {"nom": "Alpes-de-Haute-Provence", "type": "département"})
    lieux_ref.modifier(d, e["id"], {"noms_dates": [{"nom": "Basses-Alpes", "avant": 1970}]})
    ent = d["lieux_ref"][e["id"]]
    verifie("noms datés : 1850 -> Basses-Alpes", lieux_ref.nom_a_date(ent, 1850) == "Basses-Alpes")
    verifie("noms datés : 2000 -> nom courant",
            lieux_ref.nom_a_date(ent, 2000) == "Alpes-de-Haute-Provence")
    verifie("noms datés : sans année -> nom courant",
            lieux_ref.nom_a_date(ent) == "Alpes-de-Haute-Provence")


def test_supprimer_detache_enfants():
    d = _base()
    lieux_ref.construire_depuis_evenements(d)
    par_nom = {e["nom"]: e["id"] for e in lieux_ref.lister(d)["lieux"]}
    france = par_nom["France"]
    verifie("supprimer : ok", lieux_ref.supprimer(d, france) is True)
    bdr = d["lieux_ref"][par_nom["Bouches-du-Rhône"]]
    verifie("supprimer : enfant détaché (pas d'orphelin en cascade)", bdr["parent"] == "")


def test_routes_lieux_ref():
    import tempfile
    from core.application import Application
    from services import demo
    import routes
    routes.charger_modules()
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    code, r = routes.dispatch(app, "POST", "/api/lieux-ref/construire", {}, {})
    # La démo pré-construit déjà le référentiel (showcase) : route idempotente ici.
    # La création est couverte par test_construire_hierarchie (base synthétique).
    verifie("route construire : 200", code == 200 and "crees" in r)
    code, r = routes.dispatch(app, "GET", "/api/lieux-ref", {}, {})
    verifie("route liste : lieux présents", code == 200 and r["total"] >= 1)
    lid = r["lieux"][0]["id"]
    code, _ = routes.dispatch(app, "PUT", "/api/lieux-ref/" + lid, {},
                              {"noms_dates": [{"nom": "Ancien nom", "avant": 1900}]})
    verifie("route modifier : 200", code == 200)
    code, r = routes.dispatch(app, "POST", "/api/lieux-ref", {}, {"nom": ""})
    verifie("route créer sans nom : 400", code == 400)


if __name__ == "__main__":
    test_construire_hierarchie()
    test_resoudre()
    test_noms_dates()
    test_supprimer_detache_enfants()
    test_routes_lieux_ref()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
