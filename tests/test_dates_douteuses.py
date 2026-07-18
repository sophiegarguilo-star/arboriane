# -*- coding: utf-8 -*-
"""Le validateur de dates (« Qualité des sources » → Dates douteuses) doit
accepter le format français JJ/MM/AAAA, sinon toutes les vraies dates stockées
sont signalées à tort. On garde le rejet des formes réellement bancales.

Exécuter :  python -X utf8 tests/test_dates_douteuses.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from services.gedcom_dates import valider, dates_invalides   # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_dates_fr_valides():
    for d in ("19/12/2016", "29/06/1981", "30/10/1953", "01/01/1900", "5/6/1789", "12/2016"):
        ok, raison = valider(d)
        verifie("FR valide : « %s »" % d, ok)
    # avec préfixe français
    ok, _ = valider("vers 12/2016")
    verifie("préfixe + FR : « vers 12/2016 »", ok)
    # intervalle FR
    ok, _ = valider("entre 01/01/1900 et 31/12/1900")
    verifie("intervalle FR", ok)


def test_dates_toujours_rejetees():
    for d in ("45/99/2016", "bonjour", "le 12 du mois"):
        ok, _ = valider(d)
        verifie("rejet attendu : « %s »" % d, not ok)
    # une année seule reste valide
    verifie("année seule valide", valider("1850")[0])
    # date vide = pas de date = valide
    verifie("date vide valide", valider("")[0])


def test_pas_de_faux_positifs_sur_un_arbre():
    donnees = {"individus": {
        "I1": {"id": "I1", "prenoms": "Sophie", "nom": "X",
               "naissance": {"date": "20/07/1984"}, "deces": {}},
    }, "familles": {"F1": {"mari": "I1", "mariage": {"date": "19/12/2016"}}}}
    verifie("aucune date FR signalée", dates_invalides(donnees) == [])


if __name__ == "__main__":
    for fn in (test_dates_fr_valides, test_dates_toujours_rejetees,
               test_pas_de_faux_positifs_sur_un_arbre):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
