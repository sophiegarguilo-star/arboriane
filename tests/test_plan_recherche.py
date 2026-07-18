# -*- coding: utf-8 -*-
"""Plan de recherche : formulation des pistes « Actes à trouver ».

Le libellé était fabriqué par « Trouver l'acte de %s » % libelle.lower(), ce qui
donnait « Trouver l'acte de union » (pas d'élision), « Trouver l'acte de
profession — archiviste » (un acte de profession n'existe pas) et écrasait la
casse des lieux (« à marseille »).

Exécuter :  python -X utf8 tests/test_plan_recherche.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from services import recherche                     # noqa: E402
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


def _arbre():
    app = Application(tempfile.mkdtemp())
    call(app, "POST", "/api/espaces/creer", {"nom": "P"})
    moi = call(app, "POST", "/api/individus",
               {"nom": "DUPONT", "prenoms": "Sophie", "sexe": "F",
                "naissance": {"date": "1980", "lieu": "Lyon, Rhône"},
                "deces": {"date": "2060"},
                "professions": [{"valeur": "archiviste"}],
                "residences": [{"date": "2005", "lieu": "Marseille, Bouches-du-Rhône"}]})[1]["id"]
    call(app, "POST", "/api/individus/%s/conjoint" % moi,
         {"champs": {"nom": "BERNARD", "prenoms": "Marc", "sexe": "M"}})
    return app, moi


def _quoi(app, moi):
    pistes = recherche._actes_a_trouver(app.base.donnees)
    return [p["quoi"] for p in pistes if p["personne"] == moi]


def test_libelles_des_pistes():
    app, moi = _arbre()
    quoi = _quoi(app, moi)
    verifie("acte de naissance", "Trouver l'acte de naissance" in quoi)
    verifie("acte de décès", "Trouver l'acte de décès" in quoi)
    verifie("union -> « acte de mariage » (plus « de union »)",
            "Trouver l'acte de mariage" in quoi)
    verifie("plus aucun « de union »", not any("de union" in q for q in quoi))


def test_pas_d_acte_pour_profession_ni_residence():
    app, moi = _arbre()
    quoi = _quoi(app, moi)
    verifie("profession : « Prouver : … », pas « l'acte de profession »",
            any(q.startswith("Prouver : Profession") for q in quoi)
            and not any("acte de profession" in q for q in quoi))
    verifie("résidence : « Prouver : … », pas « l'acte de résidence »",
            any(q.startswith("Prouver : Résidence") for q in quoi)
            and not any("acte de résidence" in q for q in quoi))


def test_casse_des_lieux_preservee():
    app, moi = _arbre()
    quoi = _quoi(app, moi)
    verifie("le lieu garde ses majuscules (Marseille, pas marseille)",
            any("Marseille" in q for q in quoi))
    verifie("aucun lieu en minuscules", not any("marseille" in q for q in quoi))


def test_route_plan_repond():
    app, moi = _arbre()
    code, r = call(app, "GET", "/api/verif")
    verifie("/api/verif : 200", code == 200)
    verifie("plan par dépôt présent", "plan_depots" in r and r["plan_depots"]["total"] > 0)


if __name__ == "__main__":
    for t in (test_libelles_des_pistes, test_pas_d_acte_pour_profession_ni_residence,
              test_casse_des_lieux_preservee, test_route_plan_repond):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
