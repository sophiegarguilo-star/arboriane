# -*- coding: utf-8 -*-
"""
Événements standard ajoutés au recensement (v1.8.5) : baptême nourrisson (CHR),
ordination (ORDN), bar/bat mitzvah (BARM/BASM) côté personne, fiançailles (ENGA)
côté couple. Tous des tags GEDCOM 5.5.1 standard : export conforme + aller-retour.
Exécuter :  python -X utf8 tests/test_evenements_standards.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import modele                              # noqa: E402
from core.gedcom import ecriture, lecture            # noqa: E402


def _base():
    d = {"individus": {
            "I1": {"id": "I1", "nom": "A", "prenoms": "x", "sexe": "M", "fams": ["F1"],
                   "evenements": [{"type": "CHR", "date": "1910", "lieu": "Lyon", "valeur": ""},
                                  {"type": "ORDN", "date": "1935", "valeur": "Prêtre"},
                                  {"type": "BARM", "date": "1923", "valeur": ""}]},
            "I2": {"id": "I2", "nom": "B", "prenoms": "y", "sexe": "F", "fams": ["F1"],
                   "evenements": [{"type": "BASM", "date": "1925", "valeur": ""}]}},
         "familles": {"F1": {"id": "F1", "mari": "I1", "epouse": "I2",
                             "mariage": {"date": "12/06/1935", "lieu": "Paris"},
                             "evenements": [{"type": "ENGA", "date": "01/1935", "lieu": "Paris"}]}},
         "sources": {}, "depots": {}, "lieux": {}, "meta": {}}
    return modele.garantir_cles(d)


class TestEvenementsStandards(unittest.TestCase):
    def test_tags_exportes(self):
        texte = ecriture.exporter(_base())
        for tag in ("1 CHR", "1 ORDN", "1 BARM", "1 BASM", "1 ENGA"):
            self.assertIn("\n" + tag, "\n" + texte, "manque " + tag)

    def test_aller_retour(self):
        d2 = lecture.importer(ecriture.exporter(_base()))
        types_i1 = {e["type"] for e in d2["individus"]["I1"]["evenements"]}
        self.assertTrue({"CHR", "ORDN", "BARM"} <= types_i1)
        fam = list(d2["familles"].values())[0]
        self.assertIn("ENGA", {e["type"] for e in fam["evenements"]})

    def test_valeur_ordination_conservee(self):
        # la « valeur » d'un événement standard devient une NOTE (jamais perdue)
        d2 = lecture.importer(ecriture.exporter(_base()))
        ordn = next(e for e in d2["individus"]["I1"]["evenements"] if e["type"] == "ORDN")
        self.assertEqual(ordn.get("note"), "Prêtre")


if __name__ == "__main__":
    unittest.main(verbosity=2)
