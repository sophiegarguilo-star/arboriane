# -*- coding: utf-8 -*-
"""
Test L13 — favoris & ensembles de personnes.

Exécuter :  python -X utf8 tests/test_favoris.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application       # noqa: E402
from core import modele                        # noqa: E402
from services import favoris as fav             # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _base():
    app = Application(tempfile.mkdtemp())
    app.creer("T")
    b = app.base
    b.donnees["individus"] = {
        "I1": {"id": "I1", "prenoms": "Anne", "nom": "MARTIN", "sexe": "F", "naissance": {}, "deces": {}},
        "I2": {"id": "I2", "prenoms": "Paul", "nom": "MARTIN", "sexe": "M", "naissance": {}, "deces": {}},
        "I3": {"id": "I3", "prenoms": "Lise", "nom": "DUR", "sexe": "F", "naissance": {}, "deces": {}},
    }
    b.sauvegarder()
    return b


def test_migration():
    d = modele.garantir_cles({"individus": {}})
    verifie("garantir_cles crée « favoris »", "favoris" in d)
    verifie("garantir_cles crée « ensembles »", "ensembles" in d)


def test_favoris():
    b = _base()
    verifie("pas favori au départ", fav.est_favori(b.donnees, "I1") is False)
    verifie("basculer -> favori", fav.basculer(b, "I1") is True)
    verifie("est_favori après bascule", fav.est_favori(b.donnees, "I1") is True)
    verifie("liste des favoris = 1", len(fav.lister_favoris(b.donnees)) == 1)
    verifie("re-basculer -> retiré", fav.basculer(b, "I1") is False)
    verifie("liste vide après retrait", fav.lister_favoris(b.donnees) == [])
    try:
        fav.basculer(b, "IXX"); verifie("favori d'un inconnu -> refus", False)
    except ValueError:
        verifie("favori d'un inconnu -> refus", True)


def test_ensembles():
    b = _base()
    e = fav.creer_ensemble(b, "Ma branche", ["I1", "I2", "IXX"])
    verifie("créer ensemble (ignore les ids inconnus)", len(e["membres"]) == 2)
    verifie("ensemble listé", len(fav.lister_ensembles(b.donnees)) == 1)
    verifie("membres résolus", len(fav.membres(b.donnees, e["id"])["membres"]) == 2)
    verifie("ajouter un membre", fav.basculer_membre(b, e["id"], "I3") is True)
    verifie("nb membres = 3", fav.lister_ensembles(b.donnees)[0]["nb"] == 3)
    verifie("retirer un membre", fav.basculer_membre(b, e["id"], "I3") is False)
    fav.renommer_ensemble(b, e["id"], "Branche paternelle")
    verifie("renommer", fav.lister_ensembles(b.donnees)[0]["nom"] == "Branche paternelle")
    verifie("supprimer", fav.supprimer_ensemble(b, e["id"]) is True)
    verifie("liste vide après suppression", fav.lister_ensembles(b.donnees) == [])


if __name__ == "__main__":
    test_migration()
    test_favoris()
    test_ensembles()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
