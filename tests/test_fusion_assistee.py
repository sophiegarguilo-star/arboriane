# -*- coding: utf-8 -*-
"""
Test L14 — fusion assistée (personnes : score/comparaison/garde-fou ; lieux).

Exécuter :  python -X utf8 tests/test_fusion_assistee.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application       # noqa: E402
from services import fusion_assistee as fa     # noqa: E402

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
    def ind(i, prenoms, nom, sexe, an, **extra):
        d = {"id": i, "prenoms": prenoms, "nom": nom, "sexe": sexe,
             "naissance": {"date": str(an) if an else "", "lieu": ""}, "deces": {}}
        d.update(extra); return d
    b.donnees["individus"] = {
        "I3": ind("I3", "Pierre", "MARTIN", "M", 1820),
        "I4": ind("I4", "Anne", "DUR", "F", 1825),
        "I1": ind("I1", "Jean", "MARTIN", "M", 1850, famc=["F0"], prenom_principal="Jean"),
        "I2": ind("I2", "Jean", "MARTIN", "M", 1850, famc=["F0"], prenom_principal="Jeannot"),
        "I5": ind("I5", "Alex", "DURAND", "M", 1900),
        "I6": ind("I6", "Alex", "DURAND", "F", 1900),
    }
    b.donnees["familles"] = {
        "F0": {"id": "F0", "mari": "I3", "epouse": "I4", "enfants": ["I1", "I2"]},
    }
    b._recalc_tous_liens(); b.sauvegarder()
    return app, b


def test_score():
    app, b = _base()
    d = b.donnees
    s1, ind1 = fa.score_paire(d, "I1", "I2")   # même nom, année, sexe, parents
    verifie("doublon fort (I1/I2) score élevé", s1 >= 70 and fa._niveau(s1) == "eleve")
    verifie("indices incluent « parent commun »", "parent commun" in ind1)
    s2, ind2 = fa.score_paire(d, "I5", "I6")   # sexes différents
    verifie("sexes différents -> score abaissé", s2 < 45)
    verifie("indice ⚠ sexes différents", any("sexes" in i for i in ind2))
    paires = fa.paires_scorees(d)
    verifie("paires triées par score décroissant",
            len(paires) >= 1 and paires == sorted(paires, key=lambda x: -x["score"]))


def test_comparer():
    app, b = _base()
    cmp = fa.comparer(b.donnees, "I1", "I2")
    ligne = next((l for l in cmp["lignes"] if l["cle"] == "prenom_principal"), None)
    verifie("comparaison : prénom usuel présent", ligne is not None)
    verifie("comparaison : conflit détecté (Jean vs Jeannot)", ligne and ligne["conflit"] is True)


def test_garde_fou_et_choix():
    app, b = _base()
    # garde-fou sexe : I5(M) vs I6(F) refusé
    try:
        fa.fusionner_assiste(b, "I5", "I6")
        verifie("garde-fou sexe : refus sans forçage", False)
    except ValueError:
        verifie("garde-fou sexe : refus sans forçage", True)
    # choix "b" : imposer le prénom usuel de l'absorbée
    r = fa.fusionner_assiste(b, "I1", "I2", choix={"prenom_principal": "b"})
    verifie("fusion assistée réussie", r and r.get("garde") == "I1")
    verifie("choix « b » appliqué (Jeannot)",
            b.donnees["individus"]["I1"].get("prenom_principal") == "Jeannot")
    verifie("absorbée supprimée", "I2" not in b.donnees["individus"])


def test_lieux():
    app, b = _base()
    inds = b.donnees["individus"]
    inds["I1"]["naissance"]["lieu"] = "Paris"
    inds["I2"]["naissance"]["lieu"] = "paris"
    inds["I3"]["naissance"]["lieu"] = "PARIS "
    inds["I4"]["deces"]["lieu"] = "Lyon"
    b.sauvegarder()
    groupes = fa.lieux_doublons(b.donnees)
    g = next((x for x in groupes if fa._cle_lieu(x["canonique"]) == "paris"), None)
    verifie("groupe de variantes « Paris » détecté", g is not None)
    verifie("canonique = variante la plus fréquente", g and g["canonique"] in ("Paris", "paris", "PARIS"))
    verifie("Lyon (unique) non regroupé", all(fa._cle_lieu(x["canonique"]) != "lyon" for x in groupes))
    res = fa.fusionner_lieux(b, "Paris", ["paris", "PARIS"])
    verifie("fusion de lieux : au moins 2 réécritures", res["modifies"] >= 2)
    lieux_apres = {(inds[i].get("naissance") or {}).get("lieu") for i in ("I1", "I2", "I3")}
    verifie("toutes les variantes -> « Paris »", lieux_apres == {"Paris"})


if __name__ == "__main__":
    test_score()
    test_comparer()
    test_garde_fou_et_choix()
    test_lieux()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
