# -*- coding: utf-8 -*-
"""Import de tags privés Heredis (retour utilisateur Dominique) :
- _CREA / _UPD (date de création/màj d'une fiche) = métadonnée logicielle → ignorées
  (elles s'affichaient à tort comme des lignes dans « Vie & chronologie ») ;
- _FIL (nature de filiation : légitime, naturel, adopté…) = conservée dans un champ
  dédié « filiation » (affiché hors de la frise), et ré-exportée pour l'aller-retour."""

import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import gedcom, modele          # noqa: E402

GED = """0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Jean /Test/
1 SEX M
1 BIRT
2 DATE 1900
1 _CREA 12 JAN 2020
1 _UPD 3 FEB 2021
1 _FIL Naturel
1 _MILT quelque chose
0 TRLR
"""


class TestImportHeredis(unittest.TestCase):
    def setUp(self):
        self.d = gedcom.importer(GED)
        modele.garantir_cles(self.d)
        self.p = self.d["individus"]["I1"]

    def test_crea_upd_ignores(self):
        # aucune trace de _CREA / _UPD dans les événements
        libelles = " ".join(str(e) for e in self.p.get("evenements", []))
        self.assertNotIn("CREA", libelles)
        self.assertNotIn("UPD", libelles)

    def test_fil_dans_champ_filiation(self):
        self.assertEqual(self.p.get("filiation"), "Naturel")
        # et PAS dans la chronologie (evenements) : seul _MILT (vrai tag inconnu) y reste
        self.assertTrue(all("Naturel" not in str(e) for e in self.p.get("evenements", [])))

    def test_tag_inconnu_toujours_preserve(self):
        # un tag privé NON répertorié (_MILT) reste conservé en événement (aller-retour)
        self.assertTrue(any("MILT" in str(e).upper() for e in self.p.get("evenements", [])))

    def test_fil_reexporte(self):
        t = gedcom.exporter(self.d)
        self.assertIn("1 _FIL Naturel", t)
        self.assertNotIn("_CREA", t)
        self.assertNotIn("_UPD", t)


if __name__ == "__main__":
    unittest.main()
