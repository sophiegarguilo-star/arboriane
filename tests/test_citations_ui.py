# -*- coding: utf-8 -*-
"""PARC-02 — Citations visibles et RETIRABLES depuis la fiche.

Avant : une preuve attachée à un fait était comptée (« 2 source(s) ») mais ni
détaillée ni retirable — la seule issue était de supprimer la source entière.
Désormais :

  - GET /api/individus/<pid>/preuves détaille, pour CHAQUE fait, ses citations
    {source, titre, page, quay} — l'index affiché est celui du stockage ;
  - stockage.retirer_citation(pid, fait, index[, famille]) retire une citation
    précise (même aiguillage que citer(), unions et faits du couple compris) ;
  - POST /api/individus/<pid>/retirer-citation {fait, index, famille?}.

Exécuter :  python -X utf8 tests/test_citations_ui.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application         # noqa: E402
import routes                                    # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _app():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "Citations"})
    routes.dispatch(app, "POST", "/api/individus", {},
                    {"nom": "DUPONT", "prenoms": "Pierre", "sexe": "M",
                     "naissance": {"date": "12/06/1902", "lieu": "Lyon"},
                     "professions": [{"valeur": "menuisier", "date": ""}]})
    routes.dispatch(app, "POST", "/api/individus", {},
                    {"nom": "MARTIN", "prenoms": "Marie", "sexe": "F"})
    routes.dispatch(app, "POST", "/api/individus/I1/conjoint", {}, {"id": "I2"})
    routes.dispatch(app, "POST", "/api/sources", {},
                    {"titre": "Acte de naissance de Pierre", "type": "Naissance"})
    return app


def _fait(preuves, nom):
    return next((f for f in preuves["faits"] if f["fait"] == nom), None)


def test_detail_citations_dans_preuves():
    app = _app()
    routes.dispatch(app, "POST", "/api/individus/I1/citer", {},
                    {"fait": "naissance", "source": "S1", "page": "vue 12/48",
                     "quay": 3})
    routes.dispatch(app, "POST", "/api/individus/I1/citer", {},
                    {"fait": "naissance", "source": "S1", "page": "marge",
                     "quay": 1})
    code, p = routes.dispatch(app, "GET", "/api/individus/I1/preuves", {}, {})
    verifie("preuves : 200", code == 200)
    nais = _fait(p, "naissance")
    verifie("le fait naissance expose ses 2 citations",
            nais and len(nais.get("citations") or []) == 2)
    c0 = (nais.get("citations") or [{}])[0]
    verifie("titre de source résolu", c0.get("titre") == "Acte de naissance de Pierre")
    verifie("page et quay exposés", c0.get("page") == "vue 12/48" and c0.get("quay") == 3)
    verifie("un fait sans preuve a une liste vide",
            (_fait(p, "profession:0") or {}).get("citations") == [])


def test_retirer_citation_naissance():
    app = _app()
    routes.dispatch(app, "POST", "/api/individus/I1/citer", {},
                    {"fait": "naissance", "source": "S1", "page": "A", "quay": 3})
    routes.dispatch(app, "POST", "/api/individus/I1/citer", {},
                    {"fait": "naissance", "source": "S1", "page": "B", "quay": 2})
    code, r = routes.dispatch(app, "POST", "/api/individus/I1/retirer-citation", {},
                              {"fait": "naissance", "index": 0})
    verifie("retrait : 200 + ok", code == 200 and r.get("ok"))
    cits = app.base.donnees["individus"]["I1"]["naissance"]["citations"]
    verifie("la bonne citation est partie (reste « B »)",
            len(cits) == 1 and cits[0]["page"] == "B")
    verifie("la source n'est PAS supprimée",
            "S1" in app.base.donnees["sources"])
    code, _ = routes.dispatch(app, "POST", "/api/individus/I1/retirer-citation", {},
                              {"fait": "naissance", "index": 5})
    verifie("index hors bornes -> 404", code == 404)
    code, _ = routes.dispatch(app, "POST", "/api/individus/I1/retirer-citation", {},
                              {"fait": "naissance", "index": "zut"})
    verifie("index non numérique -> 404", code == 404)
    code, _ = routes.dispatch(app, "POST", "/api/individus/I999/retirer-citation", {},
                              {"fait": "naissance", "index": 0})
    verifie("personne inconnue -> 404", code == 404)


def test_retirer_citation_union():
    """L'union est portée par la FAMILLE : le retrait aussi (via `famille`)."""
    app = _app()
    routes.dispatch(app, "POST", "/api/individus/I1/citer", {},
                    {"fait": "union", "famille": "F1", "source": "S1",
                     "page": "p. 3", "quay": 3})
    code, p = routes.dispatch(app, "GET", "/api/individus/I1/preuves", {}, {})
    union = _fait(p, "union")
    verifie("l'union expose sa citation",
            union and len(union.get("citations") or []) == 1)
    code, r = routes.dispatch(app, "POST", "/api/individus/I1/retirer-citation", {},
                              {"fait": "union", "index": 0, "famille": "F1"})
    verifie("retrait union : 200", code == 200 and r.get("ok"))
    verifie("le mariage n'a plus de citation",
            not app.base.donnees["familles"]["F1"]["mariage"].get("citations"))


def test_retirer_fait_du_couple_et_secondaires():
    app = _app()
    # un divorce (événement de couple) prouvé
    routes.dispatch(app, "PUT", "/api/familles/F1", {},
                    {"evenements": [{"type": "DIV", "date": "01/02/1930",
                                     "lieu": "", "valeur": ""}]})
    routes.dispatch(app, "POST", "/api/individus/I1/citer", {},
                    {"fait": "union_evenement:0", "famille": "F1",
                     "source": "S1", "page": "jugement", "quay": 3})
    # une profession prouvée
    routes.dispatch(app, "POST", "/api/individus/I1/citer", {},
                    {"fait": "profession:0", "source": "S1", "page": "recensement",
                     "quay": 2})
    ok = app.base.retirer_citation("I1", "union_evenement:0", 0, famille="F1")
    verifie("retirer_citation (fait du couple) directe", bool(ok))
    verifie("l'événement DIV n'a plus de citation",
            not app.base.donnees["familles"]["F1"]["evenements"][0].get("citations"))
    ok = app.base.retirer_citation("I1", "profession:0", 0)
    verifie("retirer_citation (profession) directe", bool(ok))
    verifie("la profession n'a plus de citation",
            not app.base.donnees["individus"]["I1"]["professions"][0].get("citations"))
    verifie("retirer sur fait inexistant -> None",
            app.base.retirer_citation("I1", "residence:4", 0) is None)


def test_citer_reste_intact():
    """Le refactor (_fam_visee) ne change pas le comportement de citer()."""
    app = _app()
    ind = app.base.citer("I1", "union", {"source": "S1", "page": "x", "quay": 3})
    verifie("citer union sans `famille` vise la 1re union",
            ind and app.base.donnees["familles"]["F1"]["mariage"]["citations"])
    verifie("citer union pour un non-parent -> None",
            app.base.citer("I1", "union",
                           {"source": "S1", "page": "", "quay": None},
                           famille="F999") is not None)  # famille inconnue : repli 1re union
    # un pid sans aucune union : rien à citer
    routes.dispatch(app, "POST", "/api/individus", {},
                    {"nom": "SEUL", "prenoms": "Jean"})
    verifie("citer union sans union -> None",
            app.base.citer("I3", "union",
                           {"source": "S1", "page": "", "quay": None}) is None)


if __name__ == "__main__":
    for t in (test_detail_citations_dans_preuves, test_retirer_citation_naissance,
              test_retirer_citation_union, test_retirer_fait_du_couple_et_secondaires,
              test_citer_reste_intact):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
