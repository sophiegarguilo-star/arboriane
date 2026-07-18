# -*- coding: utf-8 -*-
"""
Heure de naissance / décès — export GEDCOM (tag privé _TIME sous DATE) et
aller-retour fidèle (import). Exécuter : python -X utf8 tests/test_heure_gedcom.py
"""

import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import gedcom                 # noqa: E402
from core import modele                 # noqa: E402


def _base_une_personne():
    b = modele.base_vide()
    b["individus"]["I1"] = {
        "id": "I1", "sexe": "F", "nom": "DURAND", "prenoms": "Marie",
        "naissance": {"date": "12 MAR 1902", "lieu": "Paris", "heure": "14:30"},
        "deces": {"date": "3 JAN 1980", "lieu": "Lyon", "heure": "6:00"},
        "famc": [], "fams": [],
    }
    return b


class TestHeureGedcom(unittest.TestCase):
    def test_export_emet_time_sous_date(self):
        texte = gedcom.exporter(_base_une_personne())
        self.assertIn("_TIME 14:30", texte)
        self.assertIn("_TIME 6:00", texte)
        # le _TIME est bien un sous-niveau du DATE (niveau 3 sous BIRT niveau 1)
        self.assertIn("3 _TIME 14:30", texte)

    def test_aller_retour_conserve_heure(self):
        texte = gedcom.exporter(_base_une_personne())
        base2 = gedcom.importer(texte)
        ind = list(base2["individus"].values())[0]
        self.assertEqual(ind["naissance"].get("heure"), "14:30")
        self.assertEqual(ind["deces"].get("heure"), "6:00")
        # la date reste correcte
        self.assertIn("1902", ind["naissance"].get("date", ""))

    def test_sans_heure_pas_de_time(self):
        b = _base_une_personne()
        b["individus"]["I1"]["naissance"].pop("heure")
        b["individus"]["I1"]["deces"].pop("heure")
        texte = gedcom.exporter(b)
        self.assertNotIn("_TIME", texte)


if __name__ == "__main__":
    unittest.main(verbosity=2)
