# -*- coding: utf-8 -*-
"""
Test L12 — interopérabilité GEDCOM : détection d'encodage + validation de dates.

Exécuter :  python -X utf8 tests/test_gedcom_interop.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application       # noqa: E402
from services import gedcom_charset as gc       # noqa: E402
from services import gedcom_dates as gd          # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_charset():
    # UTF-8 avec BOM
    t, cs, f = gc.decoder("0 HEAD\n1 CHAR UTF-8\n".encode("utf-8-sig"))
    verifie("BOM UTF-8 détecté", cs == "utf-8-sig")
    # ANSI (cp1252) via balise CHAR
    octets = "0 HEAD\n1 CHAR ANSI\n1 NAME René\n".encode("cp1252")
    t, cs, f = gc.decoder(octets)
    verifie("ANSI (cp1252) : charset détecté", cs == "cp1252")
    verifie("ANSI : accents corrects", "René" in t)
    # ANSEL : « André » = 0xE2 (accent aigu combinant) + 'e'
    ansel = b"0 HEAD\n1 CHAR ANSEL\n1 NAME Andr\xe2e /X/\n"
    t, cs, f = gc.decoder(ansel)
    verifie("ANSEL détecté", cs == "ansel")
    verifie("ANSEL : « André » reconstitué", "André" in t)
    # UTF-8 sans balise fiable
    t, cs, f = gc.decoder("0 HEAD\n1 NAME Zoé\n".encode("utf-8"))
    verifie("UTF-8 deviné (sans balise)", cs == "utf-8" and "Zoé" in t)
    # str direct -> renvoyé tel quel
    t, cs, f = gc.decoder("déjà du texte")
    verifie("texte str renvoyé tel quel", t == "déjà du texte" and f is True)


def test_dates_valider():
    cas_ok = ["", "1850", "12 JAN 1850", "JAN 1850", "ABT 1850",
              "BET 1850 AND 1860", "12 janvier 1850", "vers 1850",
              "@#DFRENCH R@ 12 GERM 3", "1850/51"]
    for c in cas_ok:
        ok, _ = gd.valider(c)
        verifie("valide : %r" % c, ok)
    cas_ko = ["patate", "18xx", "le mois dernier", "vers hier"]
    for c in cas_ko:
        ok, r = gd.valider(c)
        verifie("invalide : %r (%s)" % (c, r), not ok)


def test_dates_scan():
    app = Application(tempfile.mkdtemp())
    app.creer("T")
    b = app.base
    b.donnees["individus"] = {
        "I1": {"id": "I1", "prenoms": "Bon", "nom": "X", "sexe": "U",
               "naissance": {"date": "12 JAN 1850"}, "deces": {"date": "patate"}},
        "I2": {"id": "I2", "prenoms": "OK", "nom": "Y", "sexe": "U",
               "naissance": {"date": "1900"}, "deces": {}},
    }
    b.sauvegarder()
    alertes = gd.dates_invalides(b.donnees)
    verifie("1 date douteuse détectée", len(alertes) == 1)
    verifie("c'est bien le décès « patate »",
            alertes and alertes[0]["contexte"] == "décès" and alertes[0]["date"] == "patate")


if __name__ == "__main__":
    test_charset()
    test_dates_valider()
    test_dates_scan()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
