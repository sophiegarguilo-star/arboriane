# -*- coding: utf-8 -*-
"""PARC-11 — Bilan des balises non reconnues à l'import.

Un import « réussi » peut jeter en silence des balises que le lecteur ne
connaît pas (rites LDS, AGE d'un événement, citations au niveau famille…).
core/gedcom/bilan.py les compte (niveaux 1-2, par tag, hors administratif
trivial) et le compte remonte dans la réponse des trois routes d'import.

Exécuter :  python -X utf8 tests/test_bilan_balises.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                          # noqa: E402
from core.gedcom import bilan                    # noqa: E402
from core.application import Application         # noqa: E402
import routes                                    # noqa: E402

routes.charger_modules()
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


_FICHIER_PERTES = _ged(
    "0 @I1@ INDI", "1 NAME Jean /DUPONT/", "1 SEX M",
    "1 BAPL",                       # rite LDS : non lu -> compté (niveau 1)
    "2 DATE 1901",                  # niveau 2 d'une balise déjà comptée : non recompté
    "1 BIRT", "2 DATE 12 MAR 1901",
    "2 AGE 0",                      # AGE sous un événement : non lu -> compté
    "1 CHAN", "2 DATE 1 JAN 2020",  # administratif trivial : ignoré sans bruit
    "1 FAMS @F1@",
    "0 @I2@ INDI", "1 NAME Anne /X/", "1 SEX F", "1 FAMS @F1@",
    "0 @F1@ FAM", "1 HUSB @I1@", "1 WIFE @I2@",
    "1 SOUR @S1@",                  # citation au niveau FAMILLE : non lue -> comptée
    "1 MARR", "2 DATE 1925",
    "0 @S1@ SOUR", "1 TITL Un acte",
)


def test_comptage():
    c = bilan.compter_non_reconnues(_FICHIER_PERTES)
    verifie("BAPL (niveau 1 inconnu) compté", c.get("BAPL") == 1)
    verifie("AGE (niveau 2 d'un événement) compté", c.get("AGE") == 1)
    verifie("SOUR au niveau famille compté", c.get("SOUR") == 1)
    verifie("CHAN (trivial) jamais compté", "CHAN" not in c)
    verifie("le niveau 2 d'une balise déjà comptée ne double pas le compte",
            "DATE" not in c)


def test_fichier_propre_et_meta():
    """Notre propre export ne doit lever AUCUN faux positif, et le compte
    voyage dans meta (posé par importer)."""
    d = gedcom.importer(_FICHIER_PERTES)
    verifie("importer range le compte dans meta",
            d["meta"]["balises_non_lues"].get("BAPL") == 1)
    c = bilan.compter_non_reconnues(gedcom.exporter(d))
    verifie("aller-retour : notre export ressort sans balise inconnue", c == {})


def test_pedi_et_notes_reconnus():
    """Les nouveautés MET-01/GED-01 ne doivent pas être signalées comme pertes."""
    c = bilan.compter_non_reconnues(_ged(
        "0 @I1@ INDI", "1 NAME A /B/",
        "1 BIRT", "2 NOTE une note d'événement",
        "1 FAMC @F1@", "2 PEDI adopted", "2 STAT challenged",
        "0 @F1@ FAM", "1 CHIL @I1@", "2 _FREL Adopted",
    ))
    verifie("PEDI/STAT/NOTE/_FREL sont des balises comprises", c == {})


def test_les_routes_remontent_non_lues():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "P"})

    code, r = routes.dispatch(app, "POST", "/api/import/gedcom/comparer-detaille",
                              {}, {"texte": _FICHIER_PERTES})
    verifie("comparer-detaille : non_lues présent",
            code == 200 and r.get("non_lues", {}).get("BAPL") == 1)

    code, r = routes.dispatch(app, "POST", "/api/import/gedcom/appliquer", {},
                              {"texte": _FICHIER_PERTES})
    verifie("appliquer : non_lues présent",
            code == 200 and r.get("non_lues", {}).get("BAPL") == 1)

    code, r = routes.dispatch(app, "POST", "/api/import/gedcom/fusionner", {},
                              {"texte": _FICHIER_PERTES})
    verifie("fusionner : non_lues présent",
            code == 200 and r.get("non_lues", {}).get("BAPL") == 1)


if __name__ == "__main__":
    for t in (test_comptage, test_fichier_propre_et_meta,
              test_pedi_et_notes_reconnus, test_les_routes_remontent_non_lues):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
