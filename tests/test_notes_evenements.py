# -*- coding: utf-8 -*-
"""GED-01 — Notes d'événements (2 NOTE sous BIRT/DEAT/MARR/RESI).

Avant : la NOTE d'un événement standard était PERDUE à l'import (seuls les
événements génériques — BAPM, BURI… — la lisaient). Un « né à 6h du matin,
déclaré par la sage-femme » disparaissait sans un mot. Désormais :

  - champs._evenement lit le sous-tag NOTE (pointeur @NT@ compris) ;
  - ecriture._ecrire_evenement la réécrit (motif _ecrire_note existant), et un
    événement qui ne porte QU'une note est quand même écrit.

Exécuter :  python -X utf8 tests/test_notes_evenements.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                          # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _ged(*lignes):
    return "\n".join(("0 HEAD", "1 GEDC", "2 VERS 5.5.1", "1 CHAR UTF-8")
                     + lignes + ("0 TRLR",)) + "\n"


_FICHIER = _ged(
    "0 @I1@ INDI", "1 NAME Jean /DUPONT/", "1 SEX M",
    "1 BIRT", "2 DATE 12 MAR 1901", "2 PLAC Lyon",
    "2 NOTE Déclaré par la sage-femme,", "3 CONT à six heures du matin.",
    "1 DEAT", "2 DATE 3 JAN 1980", "2 NOTE Décès à l'hôpital.",
    "1 RESI", "2 DATE 1930", "2 PLAC Paris", "2 NOTE Locataire au 3e étage.",
    "1 FAMS @F1@",
    "0 @I2@ INDI", "1 NAME Anne /MARTIN/", "1 SEX F", "1 FAMS @F1@",
    "0 @F1@ FAM", "1 HUSB @I1@", "1 WIFE @I2@",
    "1 MARR", "2 DATE 5 JUN 1925", "2 NOTE Témoins : les deux frères.",
)


def test_import_notes_evenements():
    d = gedcom.importer(_FICHIER)
    i1 = d["individus"]["I1"]
    verifie("NOTE de BIRT lue (avec CONT)",
            i1["naissance"].get("note")
            == "Déclaré par la sage-femme,\nà six heures du matin.")
    verifie("NOTE de DEAT lue", i1["deces"].get("note") == "Décès à l'hôpital.")
    verifie("NOTE de RESI lue",
            i1["residences"][0].get("note") == "Locataire au 3e étage.")
    verifie("NOTE de MARR lue",
            d["familles"]["F1"]["mariage"].get("note")
            == "Témoins : les deux frères.")


def test_export_note_evenement():
    d = gedcom.importer(_FICHIER)
    texte = gedcom.exporter(d)
    verifie("export : NOTE réécrite sous l'événement",
            "2 NOTE Décès à l'hôpital." in texte.splitlines())
    verifie("export : le CONT de la note de naissance est réémis",
            "3 CONT à six heures du matin." in texte.splitlines())


def test_round_trip_notes():
    d1 = gedcom.importer(_FICHIER)
    d2 = gedcom.importer(gedcom.exporter(d1))
    a, b = d1["individus"]["I1"], d2["individus"]["I1"]
    verifie("round-trip : note de naissance conservée",
            a["naissance"].get("note") == b["naissance"].get("note"))
    verifie("round-trip : note de décès conservée",
            a["deces"].get("note") == b["deces"].get("note"))
    verifie("round-trip : note de résidence conservée",
            a["residences"][0].get("note") == b["residences"][0].get("note"))
    verifie("round-trip : note de mariage conservée",
            d1["familles"]["F1"]["mariage"].get("note")
            == d2["familles"]["F1"]["mariage"].get("note"))


def test_evenement_avec_note_seule():
    """Un événement qui ne porte QU'une note doit quand même être écrit."""
    d = gedcom.importer(_ged(
        "0 @I1@ INDI", "1 NAME Seul /X/", "1 SEX M",
        "1 BIRT", "2 NOTE Naissance signalée sans date ni lieu.",
    ))
    verifie("import : note seule lue",
            d["individus"]["I1"]["naissance"].get("note")
            == "Naissance signalée sans date ni lieu.")
    d2 = gedcom.importer(gedcom.exporter(d))
    verifie("round-trip : événement à note seule non jeté",
            d2["individus"]["I1"]["naissance"].get("note")
            == "Naissance signalée sans date ni lieu.")


if __name__ == "__main__":
    for t in (test_import_notes_evenements, test_export_note_evenement,
              test_round_trip_notes, test_evenement_avec_note_seule):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
