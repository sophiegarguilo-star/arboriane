# -*- coding: utf-8 -*-
"""Correspondance des lieux à l'import (Palier 2). Analyse des lieux distincts
(sans pays / doublons) + application des corrections AVANT intégration.

Exécuter :  python -X utf8 tests/test_import_lieux.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from services import import_lieux   # noqa: E402
from core import gedcom             # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _donnees():
    return {"individus": {
        "I1": {"id": "I1", "naissance": {"lieu": "Neufchâteau"},
               "deces": {"lieu": "Givet, , Ardennes, France"}},
        "I2": {"id": "I2", "naissance": {"lieu": "Neufchateau"},   # doublon orthographique
               "deces": {"lieu": "Namur, Belgique"}},
    }, "familles": {"F1": {"mari": "I1", "epouse": "I2",
                           "mariage": {"lieu": "Neufchâteau"}, "evenements": []}}, "lieux": {}}


def test_analyser():
    a = import_lieux.analyser(_donnees(), pays_defaut="Belgique")
    noms = {x["nom"]: x for x in a["lieux"]}
    verifie("Neufchâteau : sans pays", noms["Neufchâteau"]["sans_pays"])
    verifie("Neufchâteau : proposition = + Belgique",
            noms["Neufchâteau"]["propose"] == "Neufchâteau, Belgique")
    verifie("Namur, Belgique : a un pays", not noms["Namur, Belgique"]["sans_pays"])
    # doublon : « Neufchateau » (1 occ) rattaché à « Neufchâteau » (2 occ, canonique)
    verifie("doublon détecté", noms["Neufchateau"]["doublon_de"] == "Neufchâteau")
    # « Givet, , Ardennes, France » : champ vide détecté + proposition nettoyée
    g = noms["Givet, , Ardennes, France"]
    verifie("champ vide détecté", g["parties_vides"])
    verifie("proposition = nettoyée", g["propose"] == "Givet, Ardennes, France")
    verifie("compteurs", a["nb_sans_pays"] >= 2 and a["nb_doublons"] >= 1
            and a["nb_parties_vides"] >= 1)


def test_appliquer_corrections():
    d = _donnees()
    n = import_lieux.appliquer_corrections(d, {
        "Neufchâteau": "Neufchâteau, Belgique",
        "Neufchateau": "Neufchâteau, Belgique",       # uniformise l'orthographe
        "Givet, , Ardennes, France": "Givet, Ardennes, France",
    })
    verifie("plusieurs champs réécrits", n >= 3)
    verifie("naissance I1 corrigée",
            d["individus"]["I1"]["naissance"]["lieu"] == "Neufchâteau, Belgique")
    verifie("orthographe I2 uniformisée",
            d["individus"]["I2"]["naissance"]["lieu"] == "Neufchâteau, Belgique")
    verifie("mariage corrigé",
            d["familles"]["F1"]["mariage"]["lieu"] == "Neufchâteau, Belgique")
    verifie("champ vide nettoyé",
            d["individus"]["I1"]["deces"]["lieu"] == "Givet, Ardennes, France")


def test_bout_en_bout():
    src = ("0 HEAD\n1 CHAR UTF-8\n1 GEDC\n2 VERS 5.5.1\n"
           "0 @I1@ INDI\n1 NAME A /B/\n1 BIRT\n2 PLAC Neufchâteau\n0 TRLR\n")
    nouveau = gedcom.importer(src)
    import_lieux.appliquer_corrections(nouveau, {"Neufchâteau": "Neufchâteau, Belgique"})
    verifie("import + correction = lieu normalisé",
            nouveau["individus"]["I1"]["naissance"]["lieu"] == "Neufchâteau, Belgique")


if __name__ == "__main__":
    test_analyser()
    test_appliquer_corrections()
    test_bout_en_bout()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
