# -*- coding: utf-8 -*-
"""Notre export GEDCOM respecte la grammaire 5.5.1.

Nos tests d'aller-retour ne prouvent rien : ils vérifient que notre lecteur
comprend notre écrivain. Ce test-ci confronte notre export au validateur de
grammaire (outils/valider_gedcom.py), qui ne connaît que la norme — pas notre
lecteur.

Il a trouvé, sur des fichiers réels, que nous coupions les titres, noms, pages
et adresses n'importe où : des lignes multi-lignes non conformes et des lignes de
plus de 255 octets, que les autres logiciels refusent ou tronquent. Et une note
de dépôt référencée par pointeur (1 NOTE @N2@) était réexportée vers un
enregistrement qu'on n'écrivait pas — note perdue.

Exécuter :  python -X utf8 tests/test_gedcom_conforme.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                              # noqa: E402
from outils.valider_gedcom import valider            # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _base(individus, familles=None, sources=None, depots=None):
    return {"individus": individus, "familles": familles or {},
            "sources": sources or {}, "depots": depots or {},
            "lieux": {}, "meta": {}}


def _conforme(nom, donnees):
    anos = valider(gedcom.exporter(donnees))
    verifie(nom + " : export conforme", not anos)
    for a in anos[:4]:
        print("      ", a)


def test_titre_multiligne_et_long():
    src = {"id": "S1", "titre": "Un titre\nqui tient sur deux lignes",
           "auteur": "A" * 300, "type": "", "date": "", "lieu": "",
           "cote": "", "note": "", "fichiers": [], "personnes": []}
    _conforme("titre multi-ligne + auteur de 300 caractères",
              _base({}, sources={"S1": src}))


def test_nom_tres_long():
    ind = {"id": "I1", "sexe": "M", "prenoms": "Jean " * 60,
           "nom": "DE LA TRÈS LONGUE LIGNÉE " * 12,
           "naissance": {"date": "", "lieu": ""}, "deces": {"date": "", "lieu": ""}}
    _conforme("nom et prénoms interminables", _base({"I1": ind}))


def test_page_de_citation_longue():
    ind = {"id": "I1", "sexe": "F", "prenoms": "Marie", "nom": "X",
           "naissance": {"date": "1900", "lieu": "",
                         "citations": [{"source": "S1",
                                        "page": "Archive reference: RG13; " * 12}]},
           "deces": {"date": "", "lieu": ""}}
    src = {"id": "S1", "titre": "T", "fichiers": [], "personnes": []}
    _conforme("PAGE de citation trop longue", _base({"I1": ind}, sources={"S1": src}))


def test_lieu_avec_saut_de_ligne():
    ind = {"id": "I1", "sexe": "M", "prenoms": "P", "nom": "N",
           "naissance": {"date": "", "lieu": "Ville\nÉtat\nPays"},
           "deces": {"date": "", "lieu": ""}}
    _conforme("PLAC multi-ligne", _base({"I1": ind}))


def test_note_de_depot_conservee():
    """La note d'un dépôt doit survivre à l'aller-retour, sans devenir un
    pointeur mort à l'export."""
    depot = {"id": "D1", "nom": "Archives", "type": "", "lieu": "Lyon",
             "www": "", "note": "Une note importante sur ce dépôt."}
    d = _base({}, depots={"D1": depot})
    relu = gedcom.importer(gedcom.exporter(d))
    dep = next(iter(relu["depots"].values()), {})
    verifie("la note du dépôt survit à l'aller-retour",
            dep.get("note") == "Une note importante sur ce dépôt.")
    _conforme("dépôt avec note", d)


if __name__ == "__main__":
    for t in (test_titre_multiligne_et_long, test_nom_tres_long,
              test_page_de_citation_longue, test_lieu_avec_saut_de_ligne,
              test_note_de_depot_conservee):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
