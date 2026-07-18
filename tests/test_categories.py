# -*- coding: utf-8 -*-
"""Catégorie de parenté (directe / élargie / hors famille) — le calcul qui
permet de distinguer un frère d'ascendant d'un officier d'état civil.

Exécuter :  python -X utf8 tests/test_categories.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from services.personnes import _categories   # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_categories():
    # R = racine (Sosa 1), P = parent (Sosa 2), S = frère de R (collatéral),
    # C = conjoint marié de R, K = enfant de R+C, X = partenaire de PACS (union
    # vide, sans mariage ni enfant), O = officier isolé.
    donnees = {
        "individus": {k: {"id": k} for k in ["R", "P", "S", "C", "K", "X", "O"]},
        "familles": {
            "F1": {"mari": "P", "enfants": ["R", "S"]},              # sang
            "F2": {"mari": "R", "epouse": "C", "mariage": {"date": "01/01/2000"},
                   "enfants": ["K"]},                                # mariage + enfant
            "F3": {"mari": "R", "epouse": "X"},                      # union vide (PACS)
        },
    }
    cats = _categories(donnees, {"R": 1, "P": 2})
    verifie("racine = directe", cats["R"] == "directe")
    verifie("ascendant = directe", cats["P"] == "directe")
    verifie("frère d'ascendant = élargie", cats["S"] == "elargie")
    verifie("conjoint marié = élargie", cats["C"] == "elargie")
    verifie("enfant = élargie", cats["K"] == "elargie")
    verifie("partenaire de PACS (union vide) = hors", cats["X"] == "hors")
    verifie("officier isolé = hors", cats["O"] == "hors")
    # sans lignée directe connue, pas de catégorisation
    verifie("aucune racine -> pas de catégorie", _categories(donnees, {}) == {})


if __name__ == "__main__":
    test_categories()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
