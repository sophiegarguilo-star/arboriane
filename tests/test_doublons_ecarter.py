# -*- coding: utf-8 -*-
"""Fusion assistée — « ce n'est pas un doublon » : écarter une paire la retire
définitivement des doublons proposés (retour utilisateur Michel)."""

import os
import sys
import threading
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import stockage, modele                 # noqa: E402
from services import fusion_assistee as FA         # noqa: E402


def _base():
    b = stockage.Base.__new__(stockage.Base)
    b._verrou = threading.RLock()
    b.donnees = {"individus": {}, "familles": {}, "sources": {}, "depots": {},
                 "lieux": {}, "meta": {}, "lieux_ref": {}, "favoris": {}, "ensembles": {}}
    b.sauvegarder = lambda: None
    b.donnees["individus"] = {
        "I1": {"id": "I1", "sexe": "M", "prenoms": "Jean", "nom": "DURAND",
               "naissance": {"date": "1850"}, "fams": [], "famc": []},
        "I2": {"id": "I2", "sexe": "M", "prenoms": "Jean", "nom": "DURAND",
               "naissance": {"date": "1851"}, "fams": [], "famc": []}}
    modele.garantir_cles(b.donnees)
    return b


class TestDoublonsEcarter(unittest.TestCase):
    def test_ecarter_retire_la_paire(self):
        b = _base()
        self.assertEqual(len(FA.paires_scorees(b.donnees)), 1)
        FA.ecarter_paire(b, "I1", "I2")
        self.assertEqual(FA.paires_scorees(b.donnees), [])
        self.assertIn("I1|I2", b.donnees["meta"]["doublons_ecartes"])

    def test_ecart_independant_de_l_ordre_et_idempotent(self):
        b = _base()
        FA.ecarter_paire(b, "I2", "I1")            # ordre inversé
        FA.ecarter_paire(b, "I1", "I2")            # doublon d'appel
        self.assertEqual(b.donnees["meta"]["doublons_ecartes"], ["I1|I2"])
        self.assertEqual(FA.paires_scorees(b.donnees), [])

    def test_paire_invalide_refusee(self):
        b = _base()
        with self.assertRaises(ValueError):
            FA.ecarter_paire(b, "I1", "I1")        # même personne
        with self.assertRaises(ValueError):
            FA.ecarter_paire(b, "I1", "IX")        # inexistante


if __name__ == "__main__":
    unittest.main()
