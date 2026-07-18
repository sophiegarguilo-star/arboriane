# -*- coding: utf-8 -*-
"""Régression Sourçage v2 :
- une source qui PROUVE un fait (citation) est comptée « reliée » (plus seulement
  le tag personnes) ;
- prouver une union rattache la source aux DEUX conjoints ;
- citer une union CIBLE la bonne union (remariage) ;
- citation multi-personnes (acte de naissance → enfant + parents).

Exécuter :  python -X utf8 tests/test_sourcage_v2.py
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


def app_neuve():
    return Application(tempfile.mkdtemp())


def call(app, m, c, corps=None, params=None):
    return routes.dispatch(app, m, c, params or {}, corps or {})


def _arbre(app):
    call(app, "POST", "/api/espaces/creer", {"nom": "S"})


def _source(app, titre):
    return call(app, "POST", "/api/sources", {"titre": titre})[1]["id"]


def _resume(app, sid):
    data = call(app, "GET", "/api/sources")[1]
    return next((s for s in data["sources"] if s["id"] == sid), None)


# ── 1) Une source citée sur un fait est « reliée » (conscient des citations) ──
def test_source_citee_reliee():
    app = app_neuve(); _arbre(app)
    p = call(app, "POST", "/api/individus",
             {"nom": "MARTIN", "prenoms": "Jean", "naissance": {"date": "1900", "lieu": ""}})[1]["id"]
    s = _source(app, "Acte de naissance 1900")
    call(app, "POST", "/api/individus/%s/citer" % p, {"fait": "naissance", "source": s, "quay": 3})
    r = _resume(app, s)
    verifie("source citée = reliée", bool(r) and r["reliee"] is True)
    verifie("source citée compte 1 personne", bool(r) and r["nb_personnes"] == 1)


# ── 2) Prouver une union rattache la source aux DEUX conjoints ────────────
def test_union_citation_partagee():
    app = app_neuve(); _arbre(app)
    gp = call(app, "POST", "/api/individus", {"nom": "GP", "sexe": "M"})[1]["id"]
    gm = call(app, "POST", "/api/individus/%s/conjoint" % gp,
              {"champs": {"nom": "GM", "sexe": "F"}})[1]["id"]
    s = _source(app, "Acte de mariage")
    call(app, "POST", "/api/individus/%s/citer" % gp, {"fait": "union", "source": s, "quay": 3})
    r = _resume(app, s)
    verifie("union : source reliée", bool(r) and r["reliee"])
    verifie("union : comptée pour les 2 conjoints", bool(r) and r["nb_personnes"] == 2)
    fgm = call(app, "GET", "/api/individus/" + gm)[1]
    verifie("union : source visible chez l'autre conjoint",
            any(x["id"] == s for x in fgm.get("sources_liees", [])))


# ── 3) Citer une union cible la BONNE union (remariage) ───────────────────
def test_citer_union_ciblee():
    app = app_neuve(); _arbre(app)
    gp = call(app, "POST", "/api/individus", {"nom": "GP", "sexe": "M"})[1]["id"]
    x = call(app, "POST", "/api/individus/%s/conjoint" % gp,
             {"champs": {"nom": "X", "sexe": "F"}})[1]["id"]
    gm = call(app, "POST", "/api/individus/%s/conjoint" % gp,
              {"champs": {"nom": "GM", "sexe": "F"}})[1]["id"]
    fgp = call(app, "GET", "/api/individus/" + gp)[1]
    fid_gm = next(u["famille"] for u in fgp["unions"] if u["conjoint"] and u["conjoint"]["id"] == gm)
    fid_x = next(u["famille"] for u in fgp["unions"] if u["conjoint"] and u["conjoint"]["id"] == x)
    s = _source(app, "Mariage GP-GM")
    call(app, "POST", "/api/individus/%s/citer" % gp,
         {"fait": "union", "source": s, "quay": 3, "famille": fid_gm})
    fams = app.base.donnees["familles"]
    cite_gm = [c["source"] for c in (fams[fid_gm].get("mariage") or {}).get("citations", [])]
    cite_x = [c["source"] for c in (fams[fid_x].get("mariage") or {}).get("citations", [])]
    verifie("union ciblée : citation sur la bonne union (GM)", s in cite_gm)
    verifie("union ciblée : PAS sur l'autre union (X)", s not in cite_x)


# ── 4) Citation multi-personnes : acte de naissance → enfant + parents ────
def test_multi_personnes():
    app = app_neuve(); _arbre(app)
    enfant = call(app, "POST", "/api/individus", {"nom": "MARTIN", "prenoms": "Bébé"})[1]["id"]
    pere = call(app, "POST", "/api/individus/%s/parent" % enfant,
                {"role": "pere", "champs": {"nom": "MARTIN", "prenoms": "Papa", "sexe": "M"}})[1]["id"]
    mere = call(app, "POST", "/api/individus/%s/parent" % enfant,
                {"role": "mere", "champs": {"nom": "DURAND", "prenoms": "Maman", "sexe": "F"}})[1]["id"]
    s = _source(app, "Acte de naissance")
    call(app, "POST", "/api/individus/%s/citer" % enfant, {"fait": "naissance", "source": s, "quay": 3})
    call(app, "POST", "/api/sources/%s/personne" % s, {"id": pere, "role": "père"})
    call(app, "POST", "/api/sources/%s/personne" % s, {"id": mere, "role": "mère"})
    r = _resume(app, s)
    verifie("multi : 3 personnes rattachées (enfant cité + 2 parents tagués)",
            bool(r) and r["nb_personnes"] == 3)
    fp = call(app, "GET", "/api/individus/" + pere)[1]
    verifie("multi : source visible sur la fiche du père",
            any(x["id"] == s for x in fp.get("sources_liees", [])))


if __name__ == "__main__":
    for t in (test_source_citee_reliee, test_union_citation_partagee,
              test_citer_union_ciblee, test_multi_personnes):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
