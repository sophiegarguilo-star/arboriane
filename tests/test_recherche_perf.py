# -*- coding: utf-8 -*-
"""
Plan de recherche — le calcul des preuves ne doit être fait qu'UNE fois par
personne (pas deux, comme le signalait une revue externe).
Exécuter :  python -X utf8 tests/test_recherche_perf.py
"""

import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import modele                       # noqa: E402
from services import recherche                # noqa: E402
from services import sources as src_svc        # noqa: E402


def _base(n=6):
    b = modele.base_vide()
    for i in range(1, n + 1):
        b["individus"]["I%d" % i] = {
            "id": "I%d" % i, "nom": "TEST", "prenoms": "P%d" % i,
            "naissance": {"date": "190%d" % (i % 10), "lieu": "Paris, Seine"},
        }
    return b


class TestPlanPerf(unittest.TestCase):
    def test_preuves_calculees_une_seule_fois_par_personne(self):
        b = _base(6)
        compteur = {}
        original = src_svc.preuves_personne

        def espion(donnees, pid):
            compteur[pid] = compteur.get(pid, 0) + 1
            return original(donnees, pid)

        src_svc.preuves_personne = espion
        try:
            res = recherche.plan(b)
        finally:
            src_svc.preuves_personne = original

        # chaque personne : preuves calculées EXACTEMENT une fois (avant : deux)
        self.assertEqual(set(compteur), set(b["individus"]))
        self.assertTrue(all(v == 1 for v in compteur.values()),
                        "double calcul détecté : %r" % compteur)
        # et le plan reste fonctionnel
        self.assertGreater(res["total"], 0)

    def test_par_depot_fonctionne_sans_preuves_precalculees(self):
        # _actes_a_trouver doit rester utilisable seul (appel de par_depot).
        b = _base(3)
        res = recherche.par_depot(b)
        self.assertIn("groupes", res)


if __name__ == "__main__":
    unittest.main(verbosity=2)
