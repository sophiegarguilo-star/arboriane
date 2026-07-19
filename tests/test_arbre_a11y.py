# -*- coding: utf-8 -*-
"""
Tests d'accessibilité des rendus d'arbre (A11Y-02, côté serveur) : chaque carte
cliquable (``<g class="indi" data-id=…>``) doit porter un ``<title>`` avec le
nom ET la période — lu par les lecteurs d'écran et affiché en info-bulle native.

Exécuter :  python -X utf8 tests/test_arbre_a11y.py
"""

import os
import re
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application     # noqa: E402
from core import modele                      # noqa: E402
from services import arbre, demo             # noqa: E402
from services.arbre.base import _titre_carte  # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1
        print("  ok  ", nom)
    else:
        _ko += 1
        print("  FAIL", nom)


def base_demo():
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    return app


def id_prenom(d, p):
    return next(pid for pid, i in d["individus"].items() if p in i.get("prenoms", ""))


# Une carte cliquable = <g class="indi" …> ; son contenu jusqu'au 1er sous-tag.
_CARTE = re.compile(r'<g class="indi"[^>]*data-id="([^"]+)"[^>]*>(<title>([^<]*)</title>)?')


def _cartes(svg):
    """Liste de (pid, titre_ou_None) pour chaque carte cliquable du SVG."""
    return [(m.group(1), m.group(3) if m.group(2) else None)
            for m in _CARTE.finditer(svg)]


def test_titres_par_mode():
    app = base_demo()
    d = app.base.donnees
    lucie = id_prenom(d, "Lucie")
    for mode in ("eventail", "ascendance", "descendance", "sablier"):
        svg = arbre.rendre(d, lucie, mode, {"generations": 5})
        cartes = _cartes(svg)
        verifie("%s : au moins une carte cliquable" % mode, len(cartes) > 0)
        verifie("%s : chaque carte a un <title> non vide" % mode,
                all(t for _pid, t in cartes))
        # le <title> reprend bien nom + période de la personne
        coherents = True
        for pid, t in cartes:
            ind = d["individus"].get(pid)
            if not ind:
                continue
            per = modele.periode(ind)
            nom = modele.nom_de_famille(ind)
            if nom and nom not in (t or ""):
                coherents = False
            if per and ("(%s)" % per) not in (t or ""):
                coherents = False
        verifie("%s : <title> = Nom (période)" % mode, coherents)


def test_titre_carte_helper():
    ind = {"prenoms": "Jeanne", "nom": "D'ARC & CIE",
           "naissance": {"date": "1412"}, "deces": {"date": "1431"}}
    t = _titre_carte(ind)
    verifie("helper : nom présent", "Jeanne" in t)
    verifie("helper : période entre parenthèses", "(1412-1431)" in t)
    verifie("helper : échappement XML (& → &amp;)", "&amp;" in t and " & " not in t)
    verifie("helper : suffixe ajouté",
            _titre_carte(ind, " — implexe, voir Sosa 4").endswith("voir Sosa 4"))
    verifie("helper : sans période → nom seul, pas de parenthèses vides",
            "(" not in _titre_carte({"prenoms": "X", "nom": "Y"}))
    verifie("helper : individu absent → « ? »", _titre_carte(None) == "?")


def test_ascendance_bh_et_implexe():
    """Les deux tracés d'ascendance (gauche-droite ET bas-haut) titrent leurs
    cartes, y compris avec l'option implexe active."""
    app = base_demo()
    d = app.base.donnees
    lucie = id_prenom(d, "Lucie")
    for sens in ("gd", "bh"):
        svg = arbre.rendre(d, lucie, "ascendance",
                           {"generations": 5, "sens": sens, "implexe": True})
        cartes = _cartes(svg)
        verifie("ascendance %s + implexe : titres présents partout" % sens,
                cartes and all(t for _pid, t in cartes))


if __name__ == "__main__":
    for fn in (test_titres_par_mode, test_titre_carte_helper,
               test_ascendance_bh_et_implexe):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
