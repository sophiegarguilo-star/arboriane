# -*- coding: utf-8 -*-
"""PERF-04 — le plan de recherche est plafonné par catégorie.

Constat d'audit : sur un grand arbre, /api/plan renvoyait 24 000 pistes
(6,6 Mo de JSON) et la page en construisait 155 000 nœuds DOM. Désormais le
serveur plafonne chaque catégorie à 200 pistes (paramètre `limite`, 0 = tout),
en annonçant toujours le TOTAL réel — l'export CSV, lui, redemande le plan
complet avec limite=0.

Exécuter :  python -X utf8 tests/test_plan_limite.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from services import recherche                    # noqa: E402
import routes                                     # noqa: E402

routes.charger_modules()
_ok = _ko = 0

N_PERSONNES = 230       # > 200 pour dépasser le plafond


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _grand_arbre():
    """230 personnes avec date de naissance non prouvée et aucune source :
    chaque catégorie « Actes à trouver » et « Personnes à documenter » dépasse
    le plafond de 200."""
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "P"})
    for i in range(N_PERSONNES):
        routes.dispatch(app, "POST", "/api/individus", {},
                        {"nom": "DUPONT%d" % i, "prenoms": "Jean", "sexe": "M",
                         "naissance": {"date": str(1700 + i)}})
    return app


def test_plan_plafonne_par_categorie():
    app = _grand_arbre()
    p = recherche.plan(app.base.donnees)
    verifie("le total GLOBAL reste le vrai total", p["total"] >= 2 * N_PERSONNES)
    verifie("aucune catégorie ne transporte plus de 200 pistes",
            all(len(c["pistes"]) <= recherche.LIMITE_PISTES for c in p["categories"]))
    grosses = [c for c in p["categories"] if c["total"] > recherche.LIMITE_PISTES]
    verifie("au moins une catégorie dépasse le plafond (jeu d'essai)",
            len(grosses) >= 2)
    verifie("chaque catégorie annonce son total RÉEL",
            all(c["total"] == N_PERSONNES for c in grosses))
    # la liste est triée par priorité : la troncature garde les plus urgentes
    for c in p["categories"]:
        prios = [pi["priorite"] for pi in c["pistes"]]
        verifie("catégorie « %s » : pistes en priorité décroissante" % c["nom"],
                prios == sorted(prios, reverse=True))


def test_limite_zero_rend_tout():
    app = _grand_arbre()
    complet = recherche.plan(app.base.donnees, limite=0)
    verifie("limite=0 : toutes les pistes sont là",
            all(len(c["pistes"]) == c["total"] for c in complet["categories"]))
    verifie("limite=0 : la somme des catégories fait le total",
            sum(c["total"] for c in complet["categories"]) == complet["total"])
    petit = recherche.plan(app.base.donnees, limite=5)
    verifie("limite=5 respectée",
            all(len(c["pistes"]) <= 5 for c in petit["categories"]))
    verifie("limite=5 : totaux réels conservés",
            {c["nom"]: c["total"] for c in petit["categories"]}
            == {c["nom"]: c["total"] for c in complet["categories"]})


def test_route_api_plan():
    app = _grand_arbre()
    code, p = routes.dispatch(app, "GET", "/api/plan", {}, {})
    verifie("/api/plan : 200", code == 200)
    verifie("/api/plan : plafond de 200 appliqué par défaut",
            all(len(c["pistes"]) <= 200 for c in p["categories"])
            and any(c["total"] > len(c["pistes"]) for c in p["categories"]))
    code, tout = routes.dispatch(app, "GET", "/api/plan", {"limite": "0"}, {})
    verifie("/api/plan?limite=0 : export complet",
            code == 200 and all(len(c["pistes"]) == c["total"]
                                for c in tout["categories"]))
    code, p2 = routes.dispatch(app, "GET", "/api/plan", {"limite": "n'importe"}, {})
    verifie("limite illisible : retombe sur le plafond par défaut",
            code == 200 and all(len(c["pistes"]) <= 200 for c in p2["categories"]))
    code, p3 = routes.dispatch(app, "GET", "/api/plan", {"limite": "-3"}, {})
    verifie("limite négative : traitée comme « tout »",
            code == 200 and all(len(c["pistes"]) == c["total"]
                                for c in p3["categories"]))


if __name__ == "__main__":
    for t in (test_plan_plafonne_par_categorie, test_limite_zero_rend_tout,
              test_route_api_plan):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
