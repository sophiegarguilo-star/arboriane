# -*- coding: utf-8 -*-
"""
Sourçage complet — chaque fait NOMMÉ (résidence, profession, événement) peut
recevoir une source, pas seulement les 3 faits vitaux.
Exécuter :  python -X utf8 tests/test_sourcage.py
"""

import os
import sys
import tempfile
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import stockage                    # noqa: E402
from services import sources as src_svc       # noqa: E402


def _base():
    d = tempfile.mkdtemp()
    b = stockage.Base(os.path.join(d, "a.json"), os.path.join(d, "Sauvegardes"))
    pid = b.creer_individu({
        "nom": "GRANDPERE",
        "residences": [{"date": "1872", "lieu": "Alger"}],
        "professions": [{"valeur": "instituteur", "date": "1880"}],
        "evenements": [{"type": "DECORATION", "valeur": "Légion d'honneur"}],
    })["id"]
    return b, pid


class TestSourcage(unittest.TestCase):
    def test_citer_residence(self):
        b, pid = _base()
        r = b.citer(pid, "residence:0", {"source": "S1", "quay": 3})
        self.assertIsNotNone(r)
        cit = b.donnees["individus"][pid]["residences"][0].get("citations")
        self.assertEqual(cit[0]["source"], "S1")

    def test_citer_evenement_par_cle(self):
        b, pid = _base()
        b.citer(pid, "evenement:0", {"source": "S2", "quay": 2})
        cit = b.donnees["individus"][pid]["evenements"][0].get("citations")
        self.assertEqual(cit[0]["source"], "S2")

    def test_citer_profession(self):
        b, pid = _base()
        b.citer(pid, "profession:0", {"source": "S3", "quay": 1})
        cit = b.donnees["individus"][pid]["professions"][0].get("citations")
        self.assertEqual(cit[0]["source"], "S3")

    def test_cible_invalide_renvoie_none(self):
        b, pid = _base()
        self.assertIsNone(b.citer(pid, "residence:9", {"source": "S9"}))
        self.assertIsNone(b.citer(pid, "inconnu:0", {"source": "S9"}))

    def test_compat_evenement_par_int(self):
        b, pid = _base()
        b.citer(pid, 0, {"source": "S4", "quay": 3})   # ancien format (int)
        cit = b.donnees["individus"][pid]["evenements"][0].get("citations")
        self.assertEqual(cit[-1]["source"], "S4")

    def test_suppression_personne_nettoie_les_citations(self):
        # Supprimer une personne citée par une source doit la retirer de cette
        # source (sinon lien fantôme : la source cite quelqu'un qui n'existe plus).
        b, _ = _base()
        temoin = b.creer_individu({"nom": "TEMOIN", "prenoms": "Paul"})["id"]
        b.donnees["sources"]["S1"] = {"id": "S1", "titre": "Acte", "personnes": [
            {"id": temoin, "role": "témoin"}]}
        b.supprimer_individu(temoin)
        self.assertEqual(b.donnees["sources"]["S1"]["personnes"], [])

    def test_union_affiche_sa_date(self):
        # La colonne « Date » de l'union doit montrer la date du mariage (comme
        # naissance/décès) — sinon elle restait vide.
        b = stockage.Base(*[os.path.join(tempfile.mkdtemp(), x) for x in ("a.json", "Sv")])
        a = b.creer_individu({"nom": "MARI", "prenoms": "Paul", "sexe": "M"})["id"]
        c = b.creer_individu({"nom": "FEMME", "prenoms": "Marie", "sexe": "F"})["id"]
        b.ajouter_conjoint(a, c, {"date": "12/06/1935", "lieu": "Paris"})
        pv = src_svc.preuves_personne(b.donnees, a)
        union = next(f for f in pv["faits"] if f["fait"] == "union")
        self.assertEqual(union["date"], "12/06/1935")

    def test_divorce_est_prouvable(self):
        # Un divorce est un fait du COUPLE (fam.evenements/DIV). Il doit être
        # listé dans les preuves ET pouvoir recevoir une citation. C'est le trou
        # qui faisait qu'aucun bouton « Prouver » n'apparaissait sur un divorce.
        b, _ = _base()
        a = b.creer_individu({"nom": "MARI", "prenoms": "Paul", "sexe": "M"})["id"]
        c = b.creer_individu({"nom": "FEMME", "prenoms": "Marie", "sexe": "F"})["id"]
        b.ajouter_conjoint(a, c, {"date": "2000", "lieu": "Paris"})
        fid = b.donnees["individus"][a]["fams"][0]
        b.modifier_famille(fid, {"evenements": [{"type": "DIV", "date": "2010", "lieu": "Lyon"}]})

        pv = src_svc.preuves_personne(b.donnees, a)
        div = next((f for f in pv["faits"] if f["fait"] == "union_evenement:0"), None)
        self.assertIsNotNone(div, "le divorce doit figurer dans les preuves")
        self.assertEqual(div["libelle"], "Divorce")           # type seul
        self.assertEqual(div["date"], "2010")                 # date en colonne
        self.assertEqual(div["famille"], fid)                 # famille transmise

        # citation partagée par les DEUX ex-conjoints
        self.assertIsNotNone(b.citer(a, "union_evenement:0", {"source": "S1", "quay": 3}, famille=fid))
        cit = b.donnees["familles"][fid]["evenements"][0].get("citations")
        self.assertEqual(cit[0]["source"], "S1")
        pv_c = src_svc.preuves_personne(b.donnees, c)
        div_c = next(f for f in pv_c["faits"] if f["fait"] == "union_evenement:0")
        self.assertEqual(div_c["niveau"], "acte")

    def test_libelle_evenement_reste_court(self):
        # L'étiquette d'un événement individuel = type + date, jamais tout le texte.
        b = stockage.Base(*[os.path.join(tempfile.mkdtemp(), x) for x in ("a.json", "Sv")])
        pid = b.creer_individu({"nom": "X", "evenements": [
            {"type": "EVEN", "precision": "PACS", "date": "2007",
             "valeur": "PACS avec un très long texte " * 20}]})["id"]
        pv = src_svc.preuves_personne(b.donnees, pid)
        ev = next(f for f in pv["faits"] if f["fait"] == "evenement:0")
        # la précision (« PACS ») prime sur le tag générique « EVEN » ; date à part
        self.assertEqual(ev["libelle"], "PACS")
        self.assertEqual(ev["date"], "2007")

    def test_preuves_liste_tous_les_faits(self):
        b, pid = _base()
        pv = src_svc.preuves_personne(b.donnees, pid)
        faits = {f["fait"] for f in pv["faits"]}
        self.assertIn("naissance", faits)
        self.assertIn("residence:0", faits)
        self.assertIn("profession:0", faits)
        self.assertIn("evenement:0", faits)
        # niveau reflète les citations
        b.citer(pid, "residence:0", {"source": "S1", "quay": 3})
        pv2 = src_svc.preuves_personne(b.donnees, pid)
        res = next(f for f in pv2["faits"] if f["fait"] == "residence:0")
        self.assertEqual(res["nb_sources"], 1)
        self.assertEqual(res["niveau"], "acte")


if __name__ == "__main__":
    unittest.main(verbosity=2)
