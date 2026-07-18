# -*- coding: utf-8 -*-
"""
Carnet de bord ↔ personnes ↔ plan de recherche.
- Une note peut tagger PLUSIEURS personnes (migration douce de l'ancien champ
  unique `personne`).
- Les pistes / à-faire du carnet, non terminés, remontent au plan de recherche
  sous chaque personne taguée.
- Les mentions d'une personne se retrouvent pour sa fiche.
Exécuter :  python -X utf8 tests/test_carnet.py
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services import carnet as cn          # noqa: E402
from services import recherche as rech      # noqa: E402


def _donnees():
    return {"individus": {
        "I1": {"id": "I1", "nom": "MARTIN", "prenoms": "Jean", "sexe": "M",
               "naissance": {"date": "1900", "lieu": "Lyon"}},
        "I2": {"id": "I2", "nom": "DURAND", "prenoms": "Marie", "sexe": "F"},
    }, "familles": {}, "sources": {}, "lieux": {}}


class TestCarnet(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_multi_personnes(self):
        e = cn.ajouter(self.dir, {"type": "piste", "titre": "chercher acte",
                                  "personnes": ["I1", "I2"]})
        self.assertEqual(e["personnes"], ["I1", "I2"])
        self.assertEqual(e["personne"], "I1")          # compat 1re personne
        lst = cn.lister(self.dir, _donnees())
        self.assertEqual({p["id"] for p in lst[0]["personnes_noms"]}, {"I1", "I2"})

    def test_migration_ancien_champ_unique(self):
        # une entrée écrite à l'ancienne (personne unique, sans `personnes`)
        chemin = os.path.join(self.dir, "Carnet", "carnet.json")
        os.makedirs(os.path.dirname(chemin))
        json.dump([{"id": "C1", "type": "piste", "titre": "vieux", "personne": "I1"}],
                  open(chemin, "w", encoding="utf-8"))
        lst = cn.lister(self.dir, _donnees())
        self.assertEqual(lst[0]["personnes"], ["I1"])

    def test_pistes_actives_filtre(self):
        cn.ajouter(self.dir, {"type": "piste", "titre": "à faire", "personnes": ["I1"]})
        cn.ajouter(self.dir, {"type": "trouvaille", "titre": "trouvé", "personnes": ["I1"]})  # pas une piste
        cn.ajouter(self.dir, {"type": "piste", "titre": "sans pers"})                          # pas de personne
        e = cn.ajouter(self.dir, {"type": "afaire", "titre": "close", "personnes": ["I2"]})
        cn.modifier(self.dir, e["id"], {"statut": "fait"})                                      # terminée
        actives = cn.pistes_actives(self.dir)
        self.assertEqual([a["titre"] for a in actives], ["à faire"])

    def test_mentions_de(self):
        cn.ajouter(self.dir, {"type": "reflexion", "titre": "note sur Jean", "personnes": ["I1"]})
        cn.ajouter(self.dir, {"type": "reflexion", "titre": "sur Marie", "personnes": ["I2"]})
        m = cn.mentions_de(self.dir, "I1", _donnees())
        self.assertEqual([x["titre"] for x in m], ["note sur Jean"])

    def test_carnet_remonte_au_plan(self):
        cn.ajouter(self.dir, {"type": "piste", "titre": "vérifier baptême",
                              "personnes": ["I1", "I2"]})
        p = rech.plan(_donnees(), pistes_carnet=cn.pistes_actives(self.dir))
        # la piste doit apparaître dans la catégorie dédiée, pour I1 ET I2
        plates = [pi for cat in p["categories"] for pi in cat["pistes"]] \
            if "categories" in p else p.get("pistes", [])
        carnet = [pi for pi in plates if pi["categorie"] == "Carnet — à explorer"]
        self.assertEqual({pi["personne"] for pi in carnet}, {"I1", "I2"})
        self.assertTrue(all(pi["quoi"] == "vérifier baptême" for pi in carnet))


if __name__ == "__main__":
    unittest.main(verbosity=2)
