# -*- coding: utf-8 -*-
"""Non-régression sur deux retours utilisateur (Michel) :

Point 3 — une source posée DIRECTEMENT sur la famille (« 1 SOUR » sous le FAM,
pas sous MARR, cas fréquent quand un conjoint est inconnu) doit être rattachée à
l'union et créditer la personne (sinon elle apparaît « sans source »).

Point 4 — un fait qui a une source SANS niveau de fiabilité (QUAY absent, cas
courant après import GEDCOM) ne doit PLUS être compté comme une tâche du plan de
recherche : un fait sourcé n'est pas à re-attester."""

import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import gedcom, modele            # noqa: E402
from services import sources as SR, recherche as RE   # noqa: E402


GED_SOURCE_FAM = """0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Bernard /Roz/
1 SEX M
1 FAMS @F1@
0 @F1@ FAM
1 HUSB @I1@
1 MARR
1 SOUR @S1@
2 PAGE RC page 189
0 @S1@ SOUR
1 TITL Registre paroissial
0 TRLR
"""


class TestRetoursMichel(unittest.TestCase):
    def test_source_niveau_famille_credite_la_personne(self):
        d = gedcom.importer(GED_SOURCE_FAM)
        modele.garantir_cles(d)
        # la source « 1 SOUR » du FAM doit finir dans mariage.citations
        cits = (d["familles"]["F1"].get("mariage") or {}).get("citations") or []
        self.assertTrue(any(c.get("source") == "S1" for c in cits))
        # et la personne n'est plus « sans aucune source »
        pv = SR.preuves_personne(d, "I1")
        self.assertTrue(any(f["nb_sources"] for f in pv["faits"]))

    def test_source_sous_marr_toujours_lue(self):
        # non-régression : une source sous MARR (niveau 2) reste bien lue
        ged = GED_SOURCE_FAM.replace("1 MARR\n1 SOUR @S1@\n2 PAGE RC page 189",
                                     "1 MARR\n2 SOUR @S1@\n3 PAGE RC page 189")
        d = gedcom.importer(ged)
        modele.garantir_cles(d)
        cits = (d["familles"]["F1"].get("mariage") or {}).get("citations") or []
        self.assertTrue(any(c.get("source") == "S1" for c in cits))

    def test_fait_source_sans_fiabilite_pas_une_tache(self):
        # une naissance citée mais sans QUAY ne doit pas apparaître au plan
        d = {"individus": {"I1": {"id": "I1", "sexe": "M", "prenoms": "Test", "nom": "X",
              "naissance": {"date": "1700", "lieu": "Nives",
                            "citations": [{"source": "S1", "quay": None}]},
              "deces": {}, "fams": [], "famc": []}},
             "familles": {}, "sources": {"S1": {"id": "S1", "titre": "acte"}}}
        modele.garantir_cles(d)
        pv = SR.preuves_personne(d, "I1")
        nais = next(f for f in pv["faits"] if f["fait"] == "naissance")
        self.assertEqual(nais["niveau"], "non_qualifie")   # sourcé, sans fiabilité
        res = RE.plan(d)
        # aucune tâche « acte à trouver » pour ce fait sourcé
        titres = " ".join(str(c) for c in res.get("categories", []))
        self.assertNotIn("Naissance", titres)
        # un fait SANS aucune source reste, lui, une tâche légitime
        d["individus"]["I1"]["naissance"]["citations"] = []
        modele.garantir_cles(d)
        pv2 = SR.preuves_personne(d, "I1")
        nais2 = next(f for f in pv2["faits"] if f["fait"] == "naissance")
        self.assertEqual(nais2["niveau"], "manquant")


if __name__ == "__main__":
    unittest.main()
