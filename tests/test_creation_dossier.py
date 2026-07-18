# -*- coding: utf-8 -*-
"""
Test du choix de l'emplacement à la création d'un arbre (parent libre).

Exécuter :  python -X utf8 tests/test_creation_dossier.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application     # noqa: E402
from core import espace as espace_mod        # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _norm(p):
    return os.path.normcase(os.path.abspath(p))


def test_emplacement():
    app = Application(tempfile.mkdtemp())

    # Par défaut : dans « Mes arbres/ »
    app.creer("Sans emplacement")
    verifie("défaut -> Mes arbres/",
            _norm(app.espace_chemin).startswith(_norm(app.dossier_arbres)))

    # Emplacement personnalisé (ex. « un autre disque »)
    ailleurs = tempfile.mkdtemp()
    app.creer("Chez moi", parent=ailleurs)
    verifie("créé dans le dossier choisi",
            _norm(os.path.dirname(app.espace_chemin)) == _norm(ailleurs))
    verifie("c'est bien un espace Arboriane", espace_mod.est_espace(app.espace_chemin))
    connus = [_norm(c) for c in app._lire_registre()["connus"]]
    verifie("l'arbre ailleurs est mémorisé (chemin absolu)",
            _norm(app.espace_chemin) in connus)


def test_validations():
    app = Application(tempfile.mkdtemp())
    ailleurs = tempfile.mkdtemp()

    # Dossier inexistant
    try:
        app.creer("X", parent=os.path.join(ailleurs, "n_existe_pas"))
        verifie("dossier inexistant -> refus", False)
    except ValueError:
        verifie("dossier inexistant -> refus", True)

    # Arbre imbriqué : parent = un espace existant
    app.creer("Racine", parent=ailleurs)
    espace_existant = app.espace_chemin
    try:
        app.creer("Imbriqué", parent=espace_existant)
        verifie("arbre imbriqué -> refus", False)
    except ValueError:
        verifie("arbre imbriqué -> refus", True)

    # Parent DANS un espace (sous-dossier) : refus aussi
    sous = os.path.join(espace_existant, "Sources")
    try:
        app.creer("DansSources", parent=sous)
        verifie("parent à l'intérieur d'un arbre -> refus", False)
    except ValueError:
        verifie("parent à l'intérieur d'un arbre -> refus", True)


if __name__ == "__main__":
    test_emplacement()
    test_validations()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
