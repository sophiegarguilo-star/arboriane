# -*- coding: utf-8 -*-
"""
Test du Lot L5+ — dépôts d'archives en entité.

Exécuter :  python -X utf8 tests/test_depots.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import modele                            # noqa: E402
from services import depots                         # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _base():
    d = modele.base_vide()
    d["sources"] = {
        "S1": {"id": "S1", "titre": "acte1", "depot": "AD Bouches-du-Rhône", "cote": "1 E 1"},
        "S2": {"id": "S2", "titre": "acte2", "depot": "AD Bouches-du-Rhône"},
        "S3": {"id": "S3", "titre": "acte3", "depot": "Mairie de Marseille"},
        "S4": {"id": "S4", "titre": "acte4"},
    }
    return d


def test_base_vide_depots():
    verifie("modèle : table depots garantie", "depots" in modele.base_vide())


def test_promouvoir_et_lister():
    d = _base()
    r = depots.promouvoir(d)
    verifie("promouvoir : 2 dépôts créés", r["crees"] == 2)
    verifie("promouvoir : 3 sources liées", r["lies"] == 3)
    lst = depots.lister(d)
    par_nom = {x["nom"]: x for x in lst["depots"]}
    verifie("lister : 2 dépôts", lst["total"] == 2)
    verifie("lister : AD compte 2 sources", par_nom["AD Bouches-du-Rhône"]["nb_sources"] == 2)
    verifie("lister : Mairie compte 1 source", par_nom["Mairie de Marseille"]["nb_sources"] == 1)
    verifie("résolution : S1 -> nom du dépôt",
            depots.nom(d, d["sources"]["S1"]) == "AD Bouches-du-Rhône")
    # idempotent
    r2 = depots.promouvoir(d)
    verifie("promouvoir : idempotent (0 nouveau)", r2["crees"] == 0 and r2["lies"] == 0)


def test_modifier_propage():
    d = _base()
    depots.promouvoir(d)
    did = d["sources"]["S1"]["depot_id"]
    depots.modifier(d, did, {"nom": "AD 13", "www": "https://archives13.fr"})
    verifie("modifier : nom propagé aux sources", d["sources"]["S1"]["depot"] == "AD 13")
    verifie("modifier : champ www posé", d["depots"][did]["www"] == "https://archives13.fr")


def test_supprimer_sans_perte():
    d = _base()
    depots.promouvoir(d)
    did = d["sources"]["S1"]["depot_id"]
    verifie("supprimer : ok", depots.supprimer(d, did) is True)
    verifie("supprimer : lien retiré", "depot_id" not in d["sources"]["S1"])
    verifie("supprimer : nom en clair conservé (aucune perte)",
            d["sources"]["S1"]["depot"] == "AD Bouches-du-Rhône")


def test_assigner():
    d = _base()
    dep = depots.creer(d, {"nom": "ANOM", "type": "Archives nationales"})
    depots.assigner_source(d, "S4", dep["id"])
    verifie("assigner : lien + nom posés",
            d["sources"]["S4"]["depot_id"] == dep["id"] and d["sources"]["S4"]["depot"] == "ANOM")
    depots.assigner_source(d, "S4", "")
    verifie("assigner : détachement", "depot_id" not in d["sources"]["S4"])


def test_gedcom_round_trip():
    from core import gedcom
    d = modele.base_vide()
    d["individus"] = {"I1": {"id": "I1", "prenoms": "Jean", "nom": "MARTIN", "sexe": "M"}}
    dep = depots.creer(d, {"nom": "AD Bouches-du-Rhône", "type": "Archives départementales",
                           "lieu": "Marseille", "www": "https://archives13.fr"})
    d["sources"] = {"S1": {"id": "S1", "titre": "acte de naissance", "cote": "1 E 1/5"}}
    depots.assigner_source(d, "S1", dep["id"])
    texte = gedcom.exporter(d)
    verifie("GEDCOM : REPO exporté", "REPO" in texte and "Archives départementales" in texte)
    d2 = gedcom.importer(texte)
    deps2 = list(d2["depots"].values())
    verifie("round-trip : 1 dépôt réimporté", len(deps2) == 1)
    dd = deps2[0]
    verifie("round-trip : nom", dd["nom"] == "AD Bouches-du-Rhône")
    verifie("round-trip : www", dd["www"] == "https://archives13.fr")
    verifie("round-trip : type", dd["type"] == "Archives départementales")
    verifie("round-trip : lieu (ADDR)", dd["lieu"] == "Marseille")
    s2 = list(d2["sources"].values())[0]
    verifie("round-trip : source liée au dépôt", s2.get("depot_id") == dd["id"])
    verifie("round-trip : cote (CALN)", s2.get("cote") == "1 E 1/5")


def test_routes_depots():
    import tempfile
    from core.application import Application
    from services import demo
    import routes
    routes.charger_modules()
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    code, r = routes.dispatch(app, "POST", "/api/depots/promouvoir", {}, {})
    # La démo pré-crée déjà les dépôts (showcase) : la route est donc idempotente ici.
    # La création est couverte par test_promouvoir_et_lister (base synthétique).
    verifie("route promouvoir : 200", code == 200 and "crees" in r)
    code, r = routes.dispatch(app, "GET", "/api/depots", {}, {})
    verifie("route liste : dépôts présents", code == 200 and r["total"] >= 1)
    did = r["depots"][0]["id"]
    code, _ = routes.dispatch(app, "PUT", "/api/depots/" + did, {}, {"www": "https://x.fr"})
    verifie("route modifier : 200", code == 200)
    code, r = routes.dispatch(app, "POST", "/api/depots", {}, {"nom": "Dépôt de test"})
    verifie("route créer : 200", code == 200)
    code, _ = routes.dispatch(app, "DELETE", "/api/depots/" + r["depot"]["id"], {}, {})
    verifie("route supprimer : 200", code == 200)
    code, _ = routes.dispatch(app, "POST", "/api/depots", {}, {"nom": "  "})
    verifie("route créer sans nom : 400", code == 400)


if __name__ == "__main__":
    test_base_vide_depots()
    test_promouvoir_et_lister()
    test_modifier_propage()
    test_supprimer_sans_perte()
    test_assigner()
    test_gedcom_round_trip()
    test_routes_depots()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
