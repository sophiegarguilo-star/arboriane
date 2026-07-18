# -*- coding: utf-8 -*-
"""
Décès présumés — personnes présumées vivantes mais trop âgées (souvent sans date
de naissance, mais un enfant/une union situe leur époque).
Exécuter :  python -X utf8 tests/test_deces_presumes.py
"""

import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import modele                                  # noqa: E402
from services import deductions as ded                   # noqa: E402
from services import coherence as coh                     # noqa: E402

ANNEE = 2026


def _base():
    b = modele.base_vide()
    # I1 : aïeul SANS date de naissance ni décès, mais enfant né en 1850.
    b["individus"]["I1"] = {"id": "I1", "nom": "AIEUL", "prenoms": "Jean", "fams": ["F1"]}
    # I2 : l'enfant, né 1850.
    b["individus"]["I2"] = {"id": "I2", "nom": "AIEUL", "prenoms": "Fils",
                            "naissance": {"date": "1850"}, "famc": ["F1"]}
    # I3 : personne vivante plausible (enfant né en 2015).
    b["individus"]["I3"] = {"id": "I3", "nom": "MODERNE", "prenoms": "Léa", "fams": ["F2"]}
    b["individus"]["I4"] = {"id": "I4", "nom": "MODERNE", "prenoms": "Bébé",
                            "naissance": {"date": "2015"}, "famc": ["F2"]}
    # I5 : décès déjà renseigné → ne doit jamais être touché.
    b["individus"]["I5"] = {"id": "I5", "nom": "DEFUNT", "prenoms": "Paul",
                            "deces": {"date": "1900"}}
    b["familles"]["F1"] = {"id": "F1", "mari": "I1", "epouse": "", "enfants": ["I2"]}
    b["familles"]["F2"] = {"id": "F2", "mari": "", "epouse": "I3", "enfants": ["I4"]}
    return b


class TestDecesPresumes(unittest.TestCase):
    def test_age_minimal_deduit_de_enfant(self):
        b = _base()
        am = modele.age_minimal(b, "I1", annee_courante=ANNEE)
        # né au plus tard 1850-12 = 1838 → au moins 188 ans
        self.assertEqual(am, ANNEE - 1838)

    def test_detecte_aieul_sans_naissance(self):
        b = _base()
        res = ded.deces_presumes(b, annee_courante=ANNEE)
        ids = [p["id"] for p in res["personnes"]]
        self.assertIn("I1", ids)
        self.assertNotIn("I3", ids)      # personne moderne plausible
        self.assertNotIn("I5", ids)      # déjà décédée (pas présumée vivante)
        p = next(p for p in res["personnes"] if p["id"] == "I1")
        self.assertTrue(p["sans_naissance"])
        self.assertIn("enfant", p["indice"])

    def test_appliquer_pose_vivant_false(self):
        b = _base()
        ded.appliquer_deces(b, "I1")
        self.assertIs(b["individus"]["I1"]["vivant"], False)
        self.assertFalse(modele.est_vivant_presume(b["individus"]["I1"]))
        # après correction, I1 n'est plus détecté
        res = ded.deces_presumes(b, annee_courante=ANNEE)
        self.assertNotIn("I1", [p["id"] for p in res["personnes"]])

    def test_appliquer_ne_touche_pas_un_deces_connu(self):
        b = _base()
        ded.appliquer_deces(b, "I5")     # a déjà un décès
        self.assertNotIn("vivant", b["individus"]["I5"])   # inchangé

    def test_appliquer_tous(self):
        b = _base()
        res = ded.appliquer_deces_tous(b, annee_courante=ANNEE)
        self.assertIn("I1", res["corriges"])
        self.assertIs(b["individus"]["I1"]["vivant"], False)

    def test_coherence_signale_anomalie(self):
        b = _base()
        rapport = coh.analyser(b)
        types = [a["type"] for a in rapport["alertes"]]
        self.assertIn("vivant_improbable", types)


if __name__ == "__main__":
    unittest.main(verbosity=2)
