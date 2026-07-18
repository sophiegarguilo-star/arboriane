# -*- coding: utf-8 -*-
"""PACS / union libre : événement de couple sans balise GEDCOM standard, stocké
en « EVEN » typé et exporté `1 EVEN / 2 TYPE PACS`. Doit survivre à l'aller-retour.

Exécuter :  python -X utf8 tests/test_pacs.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.gedcom import ecriture, lecture   # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_pacs_aller_retour():
    donnees = {
        "individus": {
            "I1": {"id": "I1", "prenoms": "Sophie", "nom": "X", "sexe": "F", "fams": ["F1"]},
            "I2": {"id": "I2", "prenoms": "Marcin", "nom": "Y", "sexe": "M", "fams": ["F1"]},
        },
        "familles": {"F1": {"id": "F1", "mari": "I2", "epouse": "I1", "enfants": [],
            "evenements": [
                {"type": "EVEN", "precision": "PACS", "date": "04/06/2007",
                 "lieu": "Marseille", "valeur": ""},
                {"type": "EVEN", "precision": "Dissolution de PACS",
                 "date": "15/04/2010", "lieu": "", "valeur": ""}]}},
        "sources": {}, "lieux": {}, "depots": {},
    }
    txt = ecriture.exporter(donnees)
    verifie("export : EVEN + TYPE PACS présents",
            "2 TYPE PACS" in txt and "2 TYPE Dissolution de PACS" in txt)
    d2 = lecture.importer(txt)
    evs = d2["familles"]["F1"]["evenements"]
    debut = next((e for e in evs if e.get("precision") == "PACS"), None)
    fin = next((e for e in evs if (e.get("precision") or "").startswith("Dissolution de PACS")), None)
    verifie("réimport : PACS conservé (date FR)", debut and debut.get("date") == "04/06/2007")
    verifie("réimport : lieu du PACS conservé", debut and debut.get("lieu") == "Marseille")
    verifie("réimport : dissolution conservée", fin and fin.get("date") == "15/04/2010")


if __name__ == "__main__":
    test_pacs_aller_retour()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
