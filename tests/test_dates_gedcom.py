# -*- coding: utf-8 -*-
"""
Traduction des dates à la frontière GEDCOM : interne FRANÇAIS ⇄ GEDCOM 5.5.1.
L'app affiche « 20/07/1984 » ; le GEDCOM doit sortir « 20 JUL 1984 ». Les deux
fonctions sont idempotentes (indispensable pour migrer un arbre sans double
conversion) et forment un aller-retour fidèle.
Exécuter :  python -X utf8 tests/test_dates_gedcom.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.dates_rep import gedcom_vers_fr, fr_vers_gedcom   # noqa: E402


class TestDatesFrontiere(unittest.TestCase):
    # (français interne, gedcom)
    PAIRES = [
        ("20/07/1984", "20 JUL 1984"),
        ("07/1984", "JUL 1984"),
        ("1984", "1984"),
        ("vers 1850", "ABT 1850"),
        ("avant 1900", "BEF 1900"),
        ("après 1900", "AFT 1900"),
        ("estimé 1800", "EST 1800"),
        ("entre 1850 et 1860", "BET 1850 AND 1860"),
        ("entre 01/1850 et 12/1860", "BET JAN 1850 AND DEC 1860"),
        ("de 1914 à 1918", "FROM 1914 TO 1918"),
        ("depuis 1920", "FROM 1920"),
        ("jusqu'à 1925", "TO 1925"),
        ("vers 05/06/1799", "ABT 5 JUN 1799"),
    ]

    def test_gedcom_vers_francais(self):
        for fr, ged in self.PAIRES:
            self.assertEqual(gedcom_vers_fr(ged), fr, "GED→FR sur %r" % ged)

    def test_francais_vers_gedcom(self):
        for fr, ged in self.PAIRES:
            self.assertEqual(fr_vers_gedcom(fr), ged, "FR→GED sur %r" % fr)

    def test_idempotence(self):
        # une date déjà dans la bonne langue ne doit PAS être re-traduite
        for fr, ged in self.PAIRES:
            self.assertEqual(gedcom_vers_fr(fr), fr, "GED→FR ré-appliqué à du FR: %r" % fr)
            self.assertEqual(fr_vers_gedcom(ged), ged, "FR→GED ré-appliqué à du GED: %r" % ged)

    def test_aller_retour(self):
        for fr, ged in self.PAIRES:
            self.assertEqual(fr_vers_gedcom(gedcom_vers_fr(ged)), ged)
            self.assertEqual(gedcom_vers_fr(fr_vers_gedcom(fr)), fr)

    def test_vide_et_inconnu(self):
        # sans préfixe reconnu ni date parseable : on ne touche à rien
        for x in ("", None, "Pâques", "un jour", "?"):
            self.assertEqual(gedcom_vers_fr(x), x or "")
            self.assertEqual(fr_vers_gedcom(x), x or "")

    def test_prefixe_seul_traduit_meme_si_atome_libre(self):
        # le qualificatif est traduit ; le mot libre reste tel quel
        self.assertEqual(fr_vers_gedcom("vers Pâques"), "ABT Pâques")
        self.assertEqual(gedcom_vers_fr("ABT Pâques"), "vers Pâques")

    def test_mois_anglais_reste_stable_en_export(self):
        # sécurité : une date déjà GEDCOM anglaise n'est pas cassée à l'export
        self.assertEqual(fr_vers_gedcom("5 JAN 1900"), "5 JAN 1900")


if __name__ == "__main__":
    unittest.main(verbosity=2)
