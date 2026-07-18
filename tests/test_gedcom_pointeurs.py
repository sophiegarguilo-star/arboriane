# -*- coding: utf-8 -*-
"""Import GEDCOM : robustesse des POINTEURS (@I1@, @F1@).

Bug signalé par un utilisateur (GEDCOM Heredis 2025) : les 297 individus
s'importaient, les enregistrements FAM aussi, mais AUCUN lien de parenté
n'apparaissait — père, mère, conjoint et enfants vides partout.

Cause : les pointeurs étaient nettoyés par `valeur.strip("@")`, sans retirer
d'abord les espaces. Une simple espace en fin de ligne — « 1 HUSB @I1@ » —
donnait l'identifiant « I1@ », qui ne correspond à personne. La famille était
créée, ses pointeurs ne désignaient rien, et rien ne le signalait.

Exécuter :  python -X utf8 tests/test_gedcom_pointeurs.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                          # noqa: E402
from core.application import Application         # noqa: E402
import routes                                    # noqa: E402

routes.charger_modules()
_ok = _ko = 0

PROPRE = """0 HEAD
1 SOUR HEREDIS 2025 PC
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Jean /DUPONT/
1 SEX M
1 FAMS @F1@
0 @I2@ INDI
1 NAME Marie /MARTIN/
1 SEX F
1 FAMS @F1@
0 @I3@ INDI
1 NAME Paul /DUPONT/
1 SEX M
1 FAMC @F1@
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
0 TRLR
"""

TAGS_POINTEURS = ("1 HUSB", "1 WIFE", "1 CHIL", "1 FAMS", "1 FAMC")


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _suffixe(texte, fin):
    """Ajoute `fin` au bout de chaque ligne portant un pointeur."""
    return "\n".join(l + fin if l.startswith(TAGS_POINTEURS) else l
                     for l in texte.splitlines())


def _liens_ok(donnees):
    inds, fams = donnees["individus"], donnees["familles"]
    if len(fams) != 1:
        return False
    fam = next(iter(fams.values()))
    return (fam["mari"] in inds and fam["epouse"] in inds
            and len(fam["enfants"]) == 1 and fam["enfants"][0] in inds)


def test_pointeur_propre():
    verifie("GEDCOM propre : les liens sont lus", _liens_ok(gedcom.importer(PROPRE)))


def test_espace_en_fin_de_pointeur():
    verifie("« 1 HUSB @I1@ » (espace finale) : liens intacts",
            _liens_ok(gedcom.importer(_suffixe(PROPRE, " "))))


def test_tabulation_en_fin_de_pointeur():
    verifie("tabulation finale : liens intacts",
            _liens_ok(gedcom.importer(_suffixe(PROPRE, "\t"))))


def test_espaces_multiples():
    verifie("plusieurs espaces finales : liens intacts",
            _liens_ok(gedcom.importer(_suffixe(PROPRE, "   "))))


def test_crlf_et_bom():
    verifie("fins de ligne Windows (CRLF)", _liens_ok(gedcom.importer(PROPRE.replace("\n", "\r\n"))))
    verifie("BOM UTF-8 en tête", _liens_ok(gedcom.importer("﻿" + PROPRE)))


def test_pointeur_vide_ignore():
    """« 1 CHIL @@ » ou « 1 CHIL » ne doit pas ajouter d'enfant fantôme."""
    texte = PROPRE.replace("1 CHIL @I3@", "1 CHIL @I3@\n1 CHIL \n1 CHIL @@")
    d = gedcom.importer(texte)
    fam = next(iter(d["familles"].values()))
    verifie("un pointeur vide n'ajoute pas d'enfant", fam["enfants"] == ["I3"])


def test_fams_famc_derives_de_la_table_familles():
    """Bout en bout : après import, la fiche expose bien père, mère et enfants."""
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "P"})
    code, _ = routes.dispatch(app, "POST", "/api/import/gedcom/appliquer", {},
                              {"texte": _suffixe(PROPRE, " ")})
    verifie("import : 200", code == 200)
    code, fiche = routes.dispatch(app, "GET", "/api/individus/I3", {}, {})
    verifie("l'enfant a bien un père et une mère",
            code == 200 and len(fiche.get("peres") or []) == 1
            and len(fiche.get("meres") or []) == 1)
    code, pere = routes.dispatch(app, "GET", "/api/individus/I1", {}, {})
    verifie("le père a bien un enfant et une union",
            code == 200 and len(pere.get("unions") or []) == 1
            and len(pere["unions"][0].get("enfants") or []) == 1)


def test_fam_sans_husb_wife_chil():
    """Un FAM qui n'énumère pas ses membres : la parenté est reconstruite depuis
    les FAMS/FAMC des individus. Un GEDCOM la déclare deux fois ; Arboriane ne
    retenait que la table des familles, et perdait donc l'autre écriture."""
    texte = "\n".join(l for l in PROPRE.splitlines()
                      if not l.startswith(("1 HUSB", "1 WIFE", "1 CHIL")))
    verifie("FAM vide + FAMS/FAMC : la parenté est reconstruite",
            _liens_ok(gedcom.importer(texte)))


def test_pointeur_vers_personne_absente_est_compte():
    """Un CHIL qui désigne quelqu'un d'absent du fichier est ignoré ET compté :
    un import qui perd des liens en silence est pire qu'un import qui échoue."""
    d = gedcom.importer(PROPRE.replace("1 CHIL @I3@", "1 CHIL @I3@\n1 CHIL @I99@"))
    fam = next(iter(d["familles"].values()))
    verifie("l'enfant fantôme n'entre pas dans la famille", fam["enfants"] == ["I3"])
    verifie("il est compté dans liens_ignores",
            d["meta"]["liens_ignores"] == 1)


def test_bilan_import_signale_l_absence_de_liens():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "P"})
    code, r = routes.dispatch(app, "POST", "/api/import/gedcom/appliquer", {},
                              {"texte": PROPRE})
    verifie("le bilan compte les liens (2 parents + 1 enfant)", r["liens"] == 3)
    verifie("aucun lien ignoré sur un fichier sain", r["liens_ignores"] == 0)

    # un GEDCOM sans la moindre famille : le bilan doit pouvoir le dire
    sans_fam = "\n".join(l for l in PROPRE.splitlines()
                         if not l.startswith(("0 @F1@", "1 HUSB", "1 WIFE",
                                              "1 CHIL", "1 FAMS", "1 FAMC")))
    app2 = Application(tempfile.mkdtemp())
    routes.dispatch(app2, "POST", "/api/espaces/creer", {}, {"nom": "P"})
    _, r2 = routes.dispatch(app2, "POST", "/api/import/gedcom/appliquer", {},
                            {"texte": sans_fam})
    verifie("un arbre sans parenté annonce 0 lien", r2["liens"] == 0 and r2["personnes"] == 3)


if __name__ == "__main__":
    for t in (test_pointeur_propre, test_espace_en_fin_de_pointeur,
              test_tabulation_en_fin_de_pointeur, test_espaces_multiples,
              test_crlf_et_bom, test_pointeur_vide_ignore,
              test_fam_sans_husb_wife_chil,
              test_pointeur_vers_personne_absente_est_compte,
              test_bilan_import_signale_l_absence_de_liens,
              test_fams_famc_derives_de_la_table_familles):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
