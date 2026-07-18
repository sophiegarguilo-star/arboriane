# -*- coding: utf-8 -*-
"""
Test du grisage/élagage de l'implexe dans le rendu d'ascendance.

Fixture : les deux grands-pères de la racine sont la MÊME personne (I6, aïeul
commun) — implexe aux Sosa 4 et 6 — et I6 a lui-même des parents (I7, I8), dont
le sous-arbre est donc dupliqué (Sosa 8/9 et 12/13) sans l'option implexe.

Exécuter :  python -X utf8 tests/test_implexe_arbre.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.modele import ascendance_sosa                         # noqa: E402
from services.arbre.base import _implexe_repeats, _elaguer_implexe  # noqa: E402
from services import arbre                                      # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _fixture():
    def ind(i, nom, sexe, famc=None):
        d = {"id": i, "nom": nom, "prenoms": "X", "sexe": sexe}
        if famc:
            d["famc"] = [famc]
        return d
    return {
        "individus": {
            "I1": ind("I1", "RACINE", "U", "F1"),
            "I2": ind("I2", "PERE", "M", "F2"),
            "I3": ind("I3", "MERE", "F", "F3"),
            "I4": ind("I4", "AIEULE_PAT", "F"),
            "I5": ind("I5", "AIEULE_MAT", "F"),
            "I6": ind("I6", "AIEUL_COMMUN", "M", "F4"),
            "I7": ind("I7", "BISAIEUL", "M"),
            "I8": ind("I8", "BISAIEULE", "F"),
        },
        "familles": {
            "F1": {"id": "F1", "mari": "I2", "epouse": "I3", "enfants": ["I1"]},
            "F2": {"id": "F2", "mari": "I6", "epouse": "I4", "enfants": ["I2"]},
            "F3": {"id": "F3", "mari": "I6", "epouse": "I5", "enfants": ["I3"]},
            "F4": {"id": "F4", "mari": "I7", "epouse": "I8", "enfants": ["I6"]},
        },
    }


def test_helpers():
    d = _fixture()
    sosa = ascendance_sosa(d, "I1", 10)
    # I6 aux Sosa 4 et 6 ; I7/I8 aux 8/9 et 12/13
    verifie("Sosa 4 et 6 = même aïeul (implexe)", sosa.get(4) == sosa.get(6) == "I6")
    rep = _implexe_repeats(sosa)
    verifie("repeats = {6:4, 12:8, 13:9}", rep == {6: 4, 12: 8, 13: 9})
    _elaguer_implexe(sosa, rep)
    verifie("élagage : 12 et 13 retirés (au-dessus du répété 6)",
            12 not in sosa and 13 not in sosa)
    verifie("le nœud répété 6 est conservé (feuille)", 6 in sosa)
    verifie("le principal 4 et ses parents 8/9 sont conservés",
            4 in sosa and 8 in sosa and 9 in sosa)


def _compter(svg, motif):
    return svg.count(motif)


def test_rendu():
    d = _fixture()
    sans = arbre.rendre(d, "I1", "ascendance", {"implexe": False})
    avec = arbre.rendre(d, "I1", "ascendance", {"implexe": True})
    verifie("sans implexe : 11 cartes", _compter(sans, 'class="indi"') == 11)
    verifie("avec implexe : 9 cartes (2 élaguées)", _compter(avec, 'class="indi"') == 9)
    verifie("avec implexe : marqueur ↻ vers le principal", "↻4" in avec)
    verifie("sans implexe : aucun marqueur ↻", "↻" not in sans)
    # variante « bas → haut » : même élagage
    avec_bh = arbre.rendre(d, "I1", "ascendance", {"implexe": True, "sens": "bh"})
    verifie("bas-haut avec implexe : 9 cartes", _compter(avec_bh, 'class="indi"') == 9)
    verifie("bas-haut : marqueur ↻ présent", "↻4" in avec_bh)


if __name__ == "__main__":
    test_helpers()
    test_rendu()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
