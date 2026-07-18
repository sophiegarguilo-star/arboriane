# -*- coding: utf-8 -*-
"""Import GEDCOM « Fusionner » : la parenté doit suivre les personnes.

Bug signalé par un utilisateur (GEDCOM Heredis 2025, fichier conforme) : les
297 individus s'importaient, mais aucun lien familial n'était créé — père, mère,
conjoint et enfants vides partout, arbre réduit à l'individu de départ.

Cause : `fusionner_import` ajoutait les individus, effaçait leurs famc/fams
(« liens non repris »), et n'importait AUCUNE famille. Le fichier n'y était pour
rien : le mode « Remplacer » fonctionnait, le mode « Fusionner » perdait toute
la filiation.

Exécuter :  python -X utf8 tests/test_import_fusionnant.py
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

GED = """0 HEAD
1 SOUR HEREDIS 2025 PC
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Jean /DUPONT/
1 SEX M
1 BIRT
2 DATE 1 JAN 1900
1 FAMS @F1@
0 @I2@ INDI
1 NAME Marie /MARTIN/
1 SEX F
1 BIRT
2 DATE 1 JAN 1902
1 FAMS @F1@
0 @I3@ INDI
1 NAME Paul /DUPONT/
1 SEX M
1 BIRT
2 DATE 1 JAN 1930
1 FAMC @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
1 MARR
2 DATE 12 JUN 1925
0 TRLR
"""


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _arbre_vide():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "P"})
    return app


def _fusionner(app, texte=GED):
    return routes.dispatch(app, "POST", "/api/import/gedcom/fusionner", {},
                           {"texte": texte})


def test_fusion_dans_un_arbre_neuf():
    """Le cas de l'utilisateur : arbre pratiquement vide, on fusionne un GEDCOM."""
    app = _arbre_vide()
    code, r = _fusionner(app)
    verifie("import fusionnant : 200", code == 200)
    d = app.base.donnees
    verifie("les 3 personnes sont là", len(d["individus"]) >= 3)
    verifie("la famille est créée (elle ne l'était pas du tout)",
            len(d["familles"]) == 1)
    fam = next(iter(d["familles"].values()))
    verifie("le couple est complet et l'enfant rattaché",
            bool(fam["mari"]) and bool(fam["epouse"]) and len(fam["enfants"]) == 1)
    verifie("la date de mariage suit", fam["mariage"].get("date") == "12/06/1925")
    verifie("le compte-rendu annonce la famille", r["familles_ajoutees"] == 1)


def test_les_fiches_montrent_la_parente():
    app = _arbre_vide()
    _fusionner(app)
    enfant = [i for i in app.base.donnees["individus"].values()
              if i["prenoms"] == "Paul"][0]
    code, fiche = routes.dispatch(app, "GET", "/api/individus/" + enfant["id"], {}, {})
    verifie("l'enfant a un père et une mère",
            code == 200 and len(fiche["peres"]) == 1 and len(fiche["meres"]) == 1)
    pere = [i for i in app.base.donnees["individus"].values()
            if i["prenoms"] == "Jean"][0]
    _, f2 = routes.dispatch(app, "GET", "/api/individus/" + pere["id"], {}, {})
    verifie("le père a une union avec un enfant",
            len(f2["unions"]) == 1 and len(f2["unions"][0]["enfants"]) == 1)


def test_fusion_sur_personnes_deja_presentes():
    """Les époux existent déjà : on ne duplique ni les personnes ni le couple,
    et l'enfant vient compléter la famille existante."""
    app = _arbre_vide()
    call = lambda m, c, b=None: routes.dispatch(app, m, c, {}, b or {})
    jean = call("POST", "/api/individus",
                {"nom": "DUPONT", "prenoms": "Jean", "sexe": "M",
                 "naissance": {"date": "1 JAN 1900"}})[1]["id"]
    call("POST", "/api/individus/%s/conjoint" % jean,
         {"champs": {"nom": "MARTIN", "prenoms": "Marie", "sexe": "F",
                     "naissance": {"date": "1 JAN 1902"}}})
    avant_i = len(app.base.donnees["individus"])
    avant_f = len(app.base.donnees["familles"])

    code, r = _fusionner(app)
    d = app.base.donnees
    verifie("une seule personne ajoutée (l'enfant)",
            len(d["individus"]) == avant_i + 1 and r["ajoutees"] == 1)
    verifie("aucun couple en double", len(d["familles"]) == avant_f == 1)
    fam = next(iter(d["familles"].values()))
    verifie("l'enfant a rejoint la famille existante", len(fam["enfants"]) == 1)
    verifie("le compte-rendu le dit", r["familles_completees"] == 1
            and r["familles_ajoutees"] == 0)


# Deux mariages du MÊME couple, séparés par un divorce : c'est le cas REMARR.GED
# des exemples officiels de gedcom.org, et il a pris ma correction en défaut.
REMARIAGE = """0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Peter /Sweet/
1 SEX M
0 @I2@ INDI
1 NAME Mary /Encore/
1 SEX F
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 MARR
2 DATE 1 JAN 1900
1 DIV
2 DATE 10 OCT 1910
0 @F3@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 MARR
2 DATE 1 JAN 1912
0 TRLR
"""


def test_remariage_du_meme_couple_reste_deux_unions():
    """Deux FAM du même couple = deux unions. Les replier sur une seule ferait
    disparaître la seconde date de mariage."""
    app = _arbre_vide()
    code, r = _fusionner(app, REMARIAGE)
    d = app.base.donnees
    verifie("les deux unions survivent", len(d["familles"]) == 2)
    dates = sorted((f["mariage"].get("date") or "") for f in d["familles"].values())
    verifie("les deux dates de mariage sont conservées",
            dates == ["01/01/1900", "01/01/1912"])
    verifie("le compte-rendu annonce deux familles", r["familles_ajoutees"] == 2)
    pere = [i for i in d["individus"].values() if i["prenoms"] == "Peter"][0]
    _, fiche = routes.dispatch(app, "GET", "/api/individus/" + pere["id"], {}, {})
    verifie("la fiche montre les deux unions", len(fiche["unions"]) == 2)


# Deux homonymes sans date, et deux anonymes : l'appariement « nom + année » ne
# discrimine rien. Sur GoT.ged, il effaçait 81 individus sur 501, en silence.
HOMONYMES = """0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Aegon /Targaryen/
0 @I2@ INDI
1 NAME Aegon /Targaryen/
0 @I3@ INDI
1 SEX M
0 @I4@ INDI
1 SEX F
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I4@
1 MARR
2 DATE 1 JAN 1400
0 TRLR
"""


def test_homonymes_et_anonymes_ne_sont_pas_fusionnes():
    app = _arbre_vide()
    code, r = _fusionner(app, HOMONYMES)
    d = app.base.donnees
    verifie("les 2 homonymes et les 2 anonymes survivent : 4 personnes",
            len(d["individus"]) == 4 and r["ajoutees"] == 4)
    verifie("aucune personne n'a été « complétée » par une autre",
            r["completees"] == 0)


def test_famille_sans_epoux_connu_est_conservee():
    """« Remplacer » gardait une famille portant une date de mariage sans époux
    identifié ; « Fusionner » la jetait. 267 familles perdues sur Habsburg.ged."""
    texte = """0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @F1@ FAM
1 MARR
2 DATE 10 MAY 1463
2 PLAC Mantua, Lombardei, Italien
0 TRLR
"""
    app = _arbre_vide()
    _fusionner(app, texte)
    fams = app.base.donnees["familles"]
    verifie("la famille sans époux est conservée", len(fams) == 1)
    verifie("sa date de mariage aussi",
            next(iter(fams.values()))["mariage"].get("date") == "10/05/1463")


def test_deux_fusions_de_suite_ne_dupliquent_rien():
    app = _arbre_vide()
    _fusionner(app); _fusionner(app)
    d = app.base.donnees
    verifie("idempotent : 3 personnes", len(d["individus"]) == 3)
    verifie("idempotent : 1 famille", len(d["familles"]) == 1)
    fam = next(iter(d["familles"].values()))
    verifie("idempotent : 1 enfant", len(fam["enfants"]) == 1)


if __name__ == "__main__":
    for t in (test_fusion_dans_un_arbre_neuf, test_les_fiches_montrent_la_parente,
              test_fusion_sur_personnes_deja_presentes,
              test_remariage_du_meme_couple_reste_deux_unions,
              test_homonymes_et_anonymes_ne_sont_pas_fusionnes,
              test_famille_sans_epoux_connu_est_conservee,
              test_deux_fusions_de_suite_ne_dupliquent_rien):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
