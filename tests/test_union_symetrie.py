# -*- coding: utf-8 -*-
"""Régression : symétrie des unions & ciblage de l'union pour les enfants.

Bug corrigé (rapport utilisateur) : ajouter une conjointe n'apparaissait que
d'un seul côté (visible chez elle, pas chez lui), et « ＋ enfant » envoyait les
enfants dans une union séparée « conjoint·e inconnu·e ».

Exécuter :  python -X utf8 tests/test_union_symetrie.py
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

_ok = 0
_ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1
        print("  ok  ", nom)
    else:
        _ko += 1
        print("  FAIL", nom)


def app_neuve():
    return Application(tempfile.mkdtemp())


def call(app, methode, chemin, corps=None, params=None):
    return routes.dispatch(app, methode, chemin, params or {}, corps or {})


def _arbre(app):
    call(app, "POST", "/api/espaces/creer", {"nom": "U"})


def _union_avec(fiche, cid):
    return next((u for u in fiche["unions"]
                 if u["conjoint"] and u["conjoint"]["id"] == cid), None)


# ── 1) L'union apparaît des DEUX côtés ─────────────────────────────────
def test_union_symetrique():
    app = app_neuve(); _arbre(app)
    gp = call(app, "POST", "/api/individus", {"nom": "GP", "sexe": "M"})[1]["id"]
    gm = call(app, "POST", "/api/individus/%s/conjoint" % gp,
              {"champs": {"nom": "GM", "sexe": "F"}})[1]["id"]
    fgp = call(app, "GET", "/api/individus/" + gp)[1]
    fgm = call(app, "GET", "/api/individus/" + gm)[1]
    verifie("union visible côté GP (mari)", _union_avec(fgp, gm) is not None)
    verifie("union visible côté GM (épouse)", _union_avec(fgm, gp) is not None)


# ── 2) Fix A : une asymétrie fams est réparée à la mutation suivante ───
def test_reparation_asymetrie():
    app = app_neuve(); _arbre(app)
    gp = call(app, "POST", "/api/individus", {"nom": "GP", "sexe": "M"})[1]["id"]
    gm = call(app, "POST", "/api/individus/%s/conjoint" % gp,
              {"champs": {"nom": "GM", "sexe": "F"}})[1]["id"]
    base = app.base
    # Simule un import asymétrique : la famille existe (GP en mari) mais GP a
    # perdu le pointeur dans ses fams (visible chez GM, pas chez GP).
    base.donnees["individus"][gp]["fams"] = []
    base.sauvegarder()
    fgp = call(app, "GET", "/api/individus/" + gp)[1]
    verifie("asymétrie de départ : union invisible côté GP", _union_avec(fgp, gm) is None)
    # Une mutation quelconque doit re-dériver fams/famc ET viser la bonne famille.
    child = call(app, "POST", "/api/individus/%s/enfant" % gp,
                 {"champs": {"nom": "ENF"}})[1]["id"]
    fgp = call(app, "GET", "/api/individus/" + gp)[1]
    u = _union_avec(fgp, gm)
    verifie("asymétrie réparée : GP retrouve son union", u is not None)
    verifie("enfant rattaché à l'union GP+GM (pas fantôme)",
            u is not None and any(e["id"] == child for e in u["enfants"]))
    verifie("une seule famille (pas de fantôme créé)", len(base.donnees["familles"]) == 1)


# ── 3) Fix B : « ＋ enfant » d'une union donnée cible CETTE union ──────
def test_enfant_cible_bonne_union():
    app = app_neuve(); _arbre(app)
    gp = call(app, "POST", "/api/individus", {"nom": "GP", "sexe": "M"})[1]["id"]
    x = call(app, "POST", "/api/individus/%s/conjoint" % gp,
             {"champs": {"nom": "X", "sexe": "F"}})[1]["id"]
    gm = call(app, "POST", "/api/individus/%s/conjoint" % gp,
              {"champs": {"nom": "GM", "sexe": "F"}})[1]["id"]
    fgp = call(app, "GET", "/api/individus/" + gp)[1]
    verifie("GP a bien deux unions", len(fgp["unions"]) == 2)
    f_gm = _union_avec(fgp, gm)["famille"]
    enf = call(app, "POST", "/api/familles/%s/enfant" % f_gm,
               {"champs": {"nom": "ENF"}})[1]["id"]
    fgp = call(app, "GET", "/api/individus/" + gp)[1]
    u_gm = next(u for u in fgp["unions"] if u["famille"] == f_gm)
    u_x = _union_avec(fgp, x)
    verifie("enfant dans l'union ciblée (GM)", any(e["id"] == enf for e in u_gm["enfants"]))
    verifie("enfant PAS dans l'autre union (X)", not any(e["id"] == enf for e in u_x["enfants"]))


# ── 4) Une seule union : « ＋ enfant » générique n'invente pas d'union ─
def test_enfant_generique_pas_fantome():
    app = app_neuve(); _arbre(app)
    gp = call(app, "POST", "/api/individus", {"nom": "GP", "sexe": "M"})[1]["id"]
    gm = call(app, "POST", "/api/individus/%s/conjoint" % gp,
              {"champs": {"nom": "GM", "sexe": "F"}})[1]["id"]
    enf = call(app, "POST", "/api/individus/%s/enfant" % gp,
               {"champs": {"nom": "ENF"}})[1]["id"]
    fgp = call(app, "GET", "/api/individus/" + gp)[1]
    verifie("une seule union (pas de fantôme)", len(fgp["unions"]) == 1)
    u = _union_avec(fgp, gm)
    verifie("enfant dans l'union avec conjoint connu",
            u is not None and any(e["id"] == enf for e in u["enfants"]))


# ── 5) nouvelle=True force une union neuve (autre parent inconnu) ──────
def test_enfant_nouvelle_union():
    app = app_neuve(); _arbre(app)
    gp = call(app, "POST", "/api/individus", {"nom": "GP", "sexe": "M"})[1]["id"]
    call(app, "POST", "/api/individus/%s/conjoint" % gp,
         {"champs": {"nom": "GM", "sexe": "F"}})
    enf = call(app, "POST", "/api/individus/%s/enfant" % gp,
               {"champs": {"nom": "ENF"}, "nouvelle": True})[1]["id"]
    fgp = call(app, "GET", "/api/individus/" + gp)[1]
    verifie("nouvelle union créée (2 unions)", len(fgp["unions"]) == 2)
    verifie("enfant dans une union sans conjoint",
            any((not u["conjoint"]) and any(e["id"] == enf for e in u["enfants"])
                for u in fgp["unions"]))


# ── 6) Famille inexistante -> 404 propre ──────────────────────────────
def test_famille_inexistante_404():
    app = app_neuve(); _arbre(app)
    code, _ = call(app, "POST", "/api/familles/FZZZ/enfant", {"champs": {"nom": "ENF"}})
    verifie("famille inexistante -> 404", code == 404)


# ── 7) Frère / sœur = enfant de plus des mêmes parents ────────────────
def test_frere_soeur():
    app = app_neuve(); _arbre(app)
    moi = call(app, "POST", "/api/individus", {"nom": "X", "prenoms": "Moi"})[1]["id"]
    call(app, "POST", "/api/individus/%s/parent" % moi,
         {"role": "pere", "champs": {"nom": "X", "prenoms": "Papa", "sexe": "M"}})
    call(app, "POST", "/api/individus/%s/parent" % moi,
         {"role": "mere", "champs": {"nom": "Y", "prenoms": "Maman", "sexe": "F"}})
    frere = call(app, "POST", "/api/individus/%s/frere_soeur" % moi,
                 {"champs": {"nom": "X", "prenoms": "Frangin", "sexe": "M"}})[1]["id"]
    fmoi = call(app, "GET", "/api/individus/" + moi)[1]
    ffr = call(app, "GET", "/api/individus/" + frere)[1]
    verifie("frère listé dans la fratrie de l'ancre", any(x["id"] == frere for x in fmoi["fratrie"]))
    verifie("frère a les deux mêmes parents", len(ffr["peres"]) == 1 and len(ffr["meres"]) == 1)


def test_frere_soeur_sans_parents():
    app = app_neuve(); _arbre(app)
    seul = call(app, "POST", "/api/individus", {"nom": "Seul", "sexe": "M"})[1]["id"]
    frere = call(app, "POST", "/api/individus/%s/frere_soeur" % seul,
                 {"champs": {"nom": "Seul", "prenoms": "Frangin"}})[1]["id"]
    fseul = call(app, "GET", "/api/individus/" + seul)[1]
    verifie("fratrie créée même sans parents connus", any(x["id"] == frere for x in fseul["fratrie"]))


# ── 8) Création d'une FICHE COMPLÈTE via un endpoint de lien ──────────
def test_creation_complete_via_lien():
    app = app_neuve(); _arbre(app)
    moi = call(app, "POST", "/api/individus", {"nom": "X", "prenoms": "Moi"})[1]["id"]
    pere = call(app, "POST", "/api/individus/%s/parent" % moi,
                {"role": "pere", "champs": {"nom": "P", "prenoms": "Papa", "sexe": "M",
                 "professions": [{"valeur": "forgeron"}],
                 "naissance": {"date": "1900", "lieu": "Lyon", "heure": ""}}})[1]["id"]
    fp = call(app, "GET", "/api/individus/" + pere)[1]
    verifie("champs détaillés créés via le lien (profession)",
            any(p.get("valeur") == "forgeron" for p in fp.get("professions", [])))
    verifie("champs détaillés créés via le lien (naissance)",
            (fp.get("naissance") or {}).get("lieu") == "Lyon")


# ── 9) « ＋ Père » puis « ＋ Mère » ne laisse PAS d'union fantôme ─────
def test_pere_puis_mere_pas_de_fantome():
    app = app_neuve(); _arbre(app)
    moi = call(app, "POST", "/api/individus", {"nom": "DUPONT", "prenoms": "Sophie"})[1]["id"]
    pere = call(app, "POST", "/api/individus/%s/parent" % moi,
                {"role": "pere", "champs": {"nom": "DUPONT", "prenoms": "Jean", "sexe": "M"}})[1]["id"]
    mere = call(app, "POST", "/api/individus/%s/parent" % moi,
                {"role": "mere", "champs": {"nom": "MARTIN", "prenoms": "Marie", "sexe": "F"}})[1]["id"]
    verifie("père+mère : une seule famille", len(app.base.donnees["familles"]) == 1)
    fp = call(app, "GET", "/api/individus/" + pere)[1]
    verifie("père : une seule union (pas de fantôme)", len(fp["unions"]) == 1)
    verifie("père : union avec la mère",
            fp["unions"] and fp["unions"][0]["conjoint"]
            and fp["unions"][0]["conjoint"]["id"] == mere)
    fmoi = call(app, "GET", "/api/individus/" + moi)[1]
    verifie("enfant : les deux parents", len(fmoi["peres"]) == 1 and len(fmoi["meres"]) == 1)


def test_mere_puis_pere_pas_de_fantome():
    app = app_neuve(); _arbre(app)
    moi = call(app, "POST", "/api/individus", {"nom": "X", "prenoms": "Moi"})[1]["id"]
    call(app, "POST", "/api/individus/%s/parent" % moi,
         {"role": "mere", "champs": {"nom": "M", "prenoms": "Maman", "sexe": "F"}})
    call(app, "POST", "/api/individus/%s/parent" % moi,
         {"role": "pere", "champs": {"nom": "P", "prenoms": "Papa", "sexe": "M"}})
    verifie("mère+père : une seule famille", len(app.base.donnees["familles"]) == 1)


def test_parent_seul_avec_enfants_preserve():
    """Un parent seul qui a DÉJÀ des enfants garde sa famille : ajouter un couple
    ailleurs ne doit pas lui attribuer un conjoint ni voler ses enfants."""
    app = app_neuve(); _arbre(app)
    a = call(app, "POST", "/api/individus", {"nom": "A", "prenoms": "Aine"})[1]["id"]
    pere = call(app, "POST", "/api/individus/%s/parent" % a,
                {"role": "pere", "champs": {"nom": "P", "prenoms": "Papa", "sexe": "M"}})[1]["id"]
    # 2e enfant, d'une autre mère
    b = call(app, "POST", "/api/individus", {"nom": "B", "prenoms": "Cadet"})[1]["id"]
    call(app, "POST", "/api/individus/%s/parent" % b, {"role": "pere", "id": pere})
    call(app, "POST", "/api/individus/%s/parent" % b,
         {"role": "mere", "champs": {"nom": "M2", "prenoms": "Autre", "sexe": "F"}})
    fp = call(app, "GET", "/api/individus/" + pere)[1]
    # l'aîné reste dans la famille SANS la 2e mère
    u_sans = [u for u in fp["unions"] if not u["conjoint"]]
    verifie("parent seul avec enfant : sa famille est préservée",
            any(any(e["id"] == a for e in u["enfants"]) for u in u_sans))
    verifie("l'aîné n'a pas hérité de la 2e mère",
            not any(any(e["id"] == a for e in u["enfants"])
                    for u in fp["unions"] if u["conjoint"]))


if __name__ == "__main__":
    for t in (test_pere_puis_mere_pas_de_fantome, test_mere_puis_pere_pas_de_fantome,
              test_parent_seul_avec_enfants_preserve,
              test_union_symetrique, test_reparation_asymetrie,
              test_enfant_cible_bonne_union, test_enfant_generique_pas_fantome,
              test_enfant_nouvelle_union, test_famille_inexistante_404,
              test_frere_soeur, test_frere_soeur_sans_parents,
              test_creation_complete_via_lien):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
