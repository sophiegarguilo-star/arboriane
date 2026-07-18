# -*- coding: utf-8 -*-
"""
Test du Lot L16 — calendrier républicain & dates complexes.

Exécuter :  python -X utf8 tests/test_dates_rep.py
"""

import datetime
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from services import dates_rep as dr                # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_conversions_ancres():
    verifie("sextile : an III / VII / XI",
            dr._est_sextile(3) and dr._est_sextile(7) and dr._est_sextile(11) and not dr._est_sextile(4))
    verifie("1 vendémiaire an I = 22/09/1792",
            dr.rep_vers_greg(1, 1, 1) == datetime.date(1792, 9, 22))
    verifie("12 germinal an III = 01/04/1795",
            dr.rep_vers_greg(3, 7, 12) == datetime.date(1795, 4, 1))
    verifie("18 brumaire an VIII = 09/11/1799",
            dr.rep_vers_greg(8, 2, 18) == datetime.date(1799, 11, 9))
    verifie("inverse : 01/04/1795 -> (3, 7, 12)",
            dr.greg_vers_rep(datetime.date(1795, 4, 1)) == (3, 7, 12))


def test_parser_format():
    verifie("parser : 12 germinal an III", dr.parser("12 germinal an III") == (3, 7, 12))
    verifie("parser : accents (nivôse)", dr.parser("5 nivôse an II") == (2, 4, 5))
    verifie("parser : sans accent (nivose)", dr.parser("5 nivose an II") == (2, 4, 5))
    verifie("formater : 12 germinal an III", dr.formater(3, 7, 12) == "12 germinal an III")
    verifie("parser : chaîne quelconque -> None", dr.parser("12 janvier 1850") is None)


def test_convertir():
    c = dr.convertir("12 germinal an III")
    verifie("convertir : rép -> grég", c and c["gregorien"] == "01/04/1795")
    c2 = dr.convertir("01/04/1795")
    verifie("convertir : grég -> rép", c2 and c2["republicain"] == "12 germinal an III")
    c3 = dr.convertir("1 avr 1795")
    verifie("convertir : « 1 avr 1795 » -> rép", c3 and c3["republicain"] == "12 germinal an III")


def test_decrire():
    verifie("decrire : ABT -> vers", dr.decrire("ABT 1850") == "vers 1850")
    verifie("decrire : BEF -> avant", dr.decrire("BEF 1900") == "avant 1900")
    verifie("decrire : AFT -> après", dr.decrire("AFT 1800") == "après 1800")
    verifie("decrire : BET AND -> entre … et",
            dr.decrire("BET 1850 AND 1860") == "entre 1850 et 1860")
    verifie("decrire : rép -> grég entre parenthèses",
            dr.decrire("12 germinal an III") == "12 germinal an III (01/04/1795)")
    verifie("decrire : préfixe + rép",
            dr.decrire("AVANT 12 germinal an III") == "avant 12 germinal an III (01/04/1795)")


def test_gedcom_dfrench():
    from core import gedcom
    texte = ("0 HEAD\n1 GEDC\n2 VERS 5.5.1\n1 CHAR UTF-8\n"
             "0 @I1@ INDI\n1 NAME Jean /MARTIN/\n1 BIRT\n2 DATE @#DFRENCH R@ 12 GERM 3\n"
             "0 TRLR\n")
    d = gedcom.importer(texte)
    ind = list(d["individus"].values())[0]
    # format interne français (« 01/04/1795 »), mais la date républicaine
    # d'origine est conservée dans date_rep pour un aller-retour fidèle.
    verifie("GEDCOM DFRENCH -> grégorien français",
            ind["naissance"]["date"] == "01/04/1795")
    verifie("date républicaine d'origine conservée",
            "@#DFRENCH" in (ind["naissance"].get("date_rep") or "").upper())


if __name__ == "__main__":
    test_conversions_ancres()
    test_parser_format()
    test_convertir()
    test_decrire()
    test_gedcom_dfrench()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
