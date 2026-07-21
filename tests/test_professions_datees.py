# -*- coding: utf-8 -*-
"""Professions datables : un métier peut porter une date ({valeur, date}), comme
une résidence. Vérifie l'ALLER-RETOUR GEDCOM (1 OCCU … / 2 DATE …) — la date ne
doit pas être perdue à l'export/import — et qu'un métier sans date reste valide.

Exécuter :  python -X utf8 tests/test_professions_datees.py
"""
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                                 # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_aller_retour_gedcom():
    donnees = {
        "individus": {"I1": {"id": "I1", "nom": "GARGUILO", "prenoms": "Jean-Pierre",
                             "sexe": "M", "naissance": {}, "deces": {},
                             "professions": [
                                 {"valeur": "Employé PTT", "date": "1976"},
                                 {"valeur": "Ingénieur", "date": "1990"},
                                 {"valeur": "Bénévole"}]}},  # sans date : doit rester valide
        "familles": {}, "sources": {}, "lieux": {},
    }
    texte = gedcom.exporter(donnees)
    verifie("export : « 1 OCCU Ingénieur »", "1 OCCU Ingénieur" in texte)
    verifie("export : « 2 DATE 1990 » sous l'OCCU", "2 DATE 1990" in texte)
    verifie("export : « 2 DATE 1976 » sous l'OCCU", "2 DATE 1976" in texte)

    d2 = gedcom.importer(texte)
    profs = next(iter(d2["individus"].values())).get("professions", [])
    def date_de(v):
        return next((p.get("date", "") for p in profs if p.get("valeur") == v), None)
    verifie("import : Employé PTT → date 1976 conservée", date_de("Employé PTT") == "1976")
    verifie("import : Ingénieur → date 1990 conservée", date_de("Ingénieur") == "1990")
    verifie("import : Bénévole présent et sans date",
            any(p.get("valeur") == "Bénévole" for p in profs) and not date_de("Bénévole"))
    verifie("import : 3 professions au total", len(profs) == 3)


if __name__ == "__main__":
    test_aller_retour_gedcom()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
