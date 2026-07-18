# -*- coding: utf-8 -*-
"""Descendance : une union SANS enfant (PACS, mariage sans enfant) ne doit pas
apparaître — sinon les conjoints s'alignent et semblent « chaînés » entre eux
(bug repéré sur les partenaires de PACS).

Exécuter :  python -X utf8 tests/test_arbre_descendance.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from services import arbre   # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_descendance_sans_union_sterile():
    # R (racine) : mariage avec EPOUSE -> enfant K ; PACS avec PACSE -> sans enfant.
    donnees = {
        "individus": {
            "R": {"id": "R", "prenoms": "Rac", "nom": "INE", "sexe": "F", "fams": ["F1", "F2"]},
            "EPOUX": {"id": "EPOUX", "prenoms": "Marius", "nom": "MARI", "sexe": "M", "fams": ["F1"]},
            "K": {"id": "K", "prenoms": "Kevin", "nom": "MARI", "sexe": "M", "famc": ["F1"]},
            "PACSE": {"id": "PACSE", "prenoms": "Pat", "nom": "PACS", "sexe": "M", "fams": ["F2"]},
        },
        "familles": {
            "F1": {"id": "F1", "mari": "EPOUX", "epouse": "R",
                   "mariage": {"date": "01/01/2000"}, "enfants": ["K"]},
            "F2": {"id": "F2", "mari": "PACSE", "epouse": "R", "enfants": [],
                   "evenements": [{"type": "EVEN", "precision": "PACS", "date": "01/01/2010"}]},
        },
    }
    svg = arbre.rendre(donnees, "R", mode="descendance")
    verifie("descendance : la racine est présente", "INE" in svg)
    verifie("descendance : le conjoint AVEC enfant est présent", "MARI" in svg)
    verifie("descendance : l'enfant est présent", "Kevin" in svg)
    verifie("descendance : le partenaire de PACS (sans enfant) est ABSENT",
            "PACS" not in svg and "Pat" not in svg)


if __name__ == "__main__":
    test_descendance_sans_union_sterile()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
