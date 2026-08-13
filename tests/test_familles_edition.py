# -*- coding: utf-8 -*-
"""Édition directe du bloc « Famille » de la fiche : remplacer / retirer un
parent d'une union, déplacer / détacher un enfant, corriger un parent d'un
enfant précis (cas des deux sœurs — même père, mère différente).

Couvre la nouvelle méthode Base.remplacer_conjoint, la route de déplacement
d'enfant (ajouter_enfant_famille / definir_parents) et la route /parent ancrée
sur l'enfant (conserve l'autre parent)."""

import os
import sys
import threading
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import stockage                    # noqa: E402
from routes import familles as r_familles    # noqa: E402


def _base():
    b = stockage.Base.__new__(stockage.Base)
    b._verrou = threading.RLock()
    b.donnees = {"individus": {}, "familles": {}, "sources": {}, "depots": {},
                 "lieux": {}, "meta": {}, "lieux_ref": {}, "favoris": {}, "ensembles": {}}
    b.sauvegarder = lambda *a, **k: None
    return b


def _ind(b, pid, sexe="U"):
    b.donnees["individus"][pid] = {"id": pid, "sexe": sexe, "prenoms": pid,
                                   "nom": pid, "fams": [], "famc": []}


def _fam(b, fid, mari="", epouse="", enfants=None, mariage=None):
    b.donnees["familles"][fid] = {
        "id": fid, "mari": mari, "epouse": epouse,
        "enfants": list(enfants or []),
        "mariage": mariage or {"date": "", "lieu": ""}, "note": ""}


class _App:
    def __init__(self, base):
        self.base = base


class TestRemplacerConjoint(unittest.TestCase):
    def _couple(self):
        b = _base()
        for pid, s in (("I1", "M"), ("I2", "F"), ("I3", "M"), ("I4", "F")):
            _ind(b, pid, s)
        _fam(b, "F1", "I1", "I2", enfants=["C1"],
             mariage={"date": "1900", "lieu": "Alger"})
        _ind(b, "C1")
        b.donnees["familles"]["F1"]["enfants"] = ["C1"]
        b._recalc_tous_liens()
        return b

    def test_remplace_mari_puis_epouse(self):
        b = self._couple()
        self.assertIsNotNone(b.remplacer_conjoint("F1", "mari", "I3"))
        self.assertEqual(b.donnees["familles"]["F1"]["mari"], "I3")
        self.assertNotIn("F1", b.donnees["individus"]["I1"]["fams"])
        self.assertIn("F1", b.donnees["individus"]["I3"]["fams"])
        self.assertIsNotNone(b.remplacer_conjoint("F1", "epouse", "I4"))
        self.assertEqual(b.donnees["familles"]["F1"]["epouse"], "I4")
        self.assertIn("F1", b.donnees["individus"]["I4"]["fams"])

    def test_retrait_vide_le_role_en_conservant_enfants_et_mariage(self):
        b = self._couple()
        b.remplacer_conjoint("F1", "epouse", "")
        fam = b.donnees["familles"]["F1"]
        self.assertEqual(fam["epouse"], "")
        self.assertEqual(fam["enfants"], ["C1"])          # enfants conservés
        self.assertEqual(fam["mariage"]["date"], "1900")  # mariage conservé
        # l'ancienne épouse existe toujours mais n'est plus rattachée à F1
        self.assertIn("I2", b.donnees["individus"])
        self.assertNotIn("F1", b.donnees["individus"]["I2"]["fams"])

    def test_couple_avec_soi_meme_refuse(self):
        b = self._couple()
        # mettre I2 (déjà épouse) comme mari de la même famille → interdit
        self.assertIsNone(b.remplacer_conjoint("F1", "mari", "I2"))
        self.assertEqual(b.donnees["familles"]["F1"]["mari"], "I1")

    def test_famille_ou_role_inconnu(self):
        b = self._couple()
        self.assertIsNone(b.remplacer_conjoint("FX", "mari", "I3"))
        self.assertIsNone(b.remplacer_conjoint("F1", "bidon", "I3"))
        self.assertIsNone(b.remplacer_conjoint("F1", "mari", "IX"))  # id inexistant


class TestDeplacerEnfant(unittest.TestCase):
    def test_ajouter_enfant_famille_rattache_et_detache(self):
        b = _base()
        _ind(b, "I1", "M"); _ind(b, "I2", "F")
        _ind(b, "I3", "M"); _ind(b, "I4", "F"); _ind(b, "C1")
        _fam(b, "F1", "I1", "I2", enfants=["C1"], mariage={"date": "1900", "lieu": ""})
        _fam(b, "F2", "I3", "I4", mariage={"date": "1920", "lieu": ""})
        b._recalc_tous_liens()
        b.ajouter_enfant_famille("F2", "C1")
        self.assertNotIn("C1", b.donnees["familles"]["F1"]["enfants"])
        self.assertIn("C1", b.donnees["familles"]["F2"]["enfants"])
        self.assertEqual(b.donnees["individus"]["C1"]["famc"], ["F2"])

    def test_detachement_vide_la_famc(self):
        b = _base()
        _ind(b, "I1", "M"); _ind(b, "I2", "F"); _ind(b, "C1")
        _fam(b, "F1", "I1", "I2", enfants=["C1"], mariage={"date": "1900", "lieu": ""})
        b._recalc_tous_liens()
        b.definir_parents("C1", "", "")
        self.assertEqual(b.donnees["individus"]["C1"]["famc"], [])


class TestRouteParentDeuxSoeurs(unittest.TestCase):
    def test_changer_la_mere_conserve_le_pere(self):
        """Deux sœurs, mêmes parents. On corrige la mère de la cadette : le père
        reste, l'aînée n'est pas touchée."""
        b = _base()
        _ind(b, "PERE", "M"); _ind(b, "MERE", "F"); _ind(b, "AUTRE", "F")
        _ind(b, "S1", "F"); _ind(b, "S2", "F")
        _fam(b, "F1", "PERE", "MERE", enfants=["S1", "S2"],
             mariage={"date": "1900", "lieu": ""})
        b._recalc_tous_liens()
        app = _App(b)
        res = r_familles.ajouter_parent(app, None,
                                        {"role": "mere", "id": "AUTRE"}, "S2")
        self.assertTrue(res.get("ok"))
        # S2 a désormais AUTRE comme mère mais PERE reste son père
        fam_s2 = b.donnees["familles"][b.donnees["individus"]["S2"]["famc"][0]]
        self.assertEqual(fam_s2["mari"], "PERE")
        self.assertEqual(fam_s2["epouse"], "AUTRE")
        # S1 conserve ses parents d'origine
        fam_s1 = b.donnees["familles"][b.donnees["individus"]["S1"]["famc"][0]]
        self.assertEqual(fam_s1["mari"], "PERE")
        self.assertEqual(fam_s1["epouse"], "MERE")


class TestRoutesConjointDeplacer(unittest.TestCase):
    def _app(self):
        b = _base()
        _ind(b, "I1", "M"); _ind(b, "I2", "F"); _ind(b, "I3", "M"); _ind(b, "C1")
        _fam(b, "F1", "I1", "I2", enfants=["C1"], mariage={"date": "1900", "lieu": ""})
        b._recalc_tous_liens()
        return _App(b), b

    def test_route_conjoint_ok_et_erreurs(self):
        app, b = self._app()
        self.assertEqual(
            r_familles.remplacer_conjoint(app, None, {"role": "mari", "id": "I3"}, "F1"),
            {"ok": True})
        self.assertEqual(b.donnees["familles"]["F1"]["mari"], "I3")
        self.assertEqual(
            r_familles.remplacer_conjoint(app, None, {"role": "mari", "id": "I3"}, "FX")[0], 404)
        self.assertEqual(
            r_familles.remplacer_conjoint(app, None, {"role": "x", "id": "I3"}, "F1")[0], 400)

    def test_route_deplacer(self):
        app, b = self._app()
        self.assertEqual(
            r_familles.deplacer_enfant(app, None, {"famille": ""}, "C1"), {"ok": True})
        self.assertEqual(b.donnees["individus"]["C1"]["famc"], [])
        self.assertEqual(
            r_familles.deplacer_enfant(app, None, {"famille": "FX"}, "C1")[0], 404)


if __name__ == "__main__":
    unittest.main()
