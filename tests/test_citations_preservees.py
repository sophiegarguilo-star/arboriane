# -*- coding: utf-8 -*-
"""Non-régression : ré-enregistrer une personne ne doit PLUS effacer les preuves
(citations) attachées à ses métiers, résidences et événements — bug signalé par
un utilisateur (« si je les rentre par Sources & preuves ils disparaissent »).

Cause d'origine : modifier_individu ne préservait les citations que pour les
faits vitaux (naissance/décès, champs dict). Les faits en LISTE (professions,
residences, evenements) étaient écrasés en bloc par un formulaire qui renvoie
{date, lieu} sans le sous-champ « citations »."""

import os
import sys
import threading
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import stockage          # noqa: E402


def _base():
    b = stockage.Base.__new__(stockage.Base)
    b._verrou = threading.RLock()
    b.donnees = {"individus": {}, "familles": {}, "sources": {}, "depots": {},
                 "lieux": {}, "meta": {}, "lieux_ref": {}, "favoris": {}, "ensembles": {}}
    b.sauvegarder = lambda: None
    return b


class TestCitationsPreservees(unittest.TestCase):
    def _personne_sourcee(self):
        return {"id": "I1", "sexe": "F", "prenoms": "Test", "nom": "X",
                "professions": [{"valeur": "Couturière", "date": "1883",
                                 "citations": [{"source": "S1", "quay": 3}]}],
                "residences": [{"date": "1901", "lieu": "Chellala",
                                "citations": [{"source": "S2", "quay": 2}]}],
                "evenements": [{"type": "EVEN", "precision": "PACS", "date": "2007",
                                "citations": [{"source": "S3"}]}]}

    def test_formulaire_sans_citations_ne_les_efface_pas(self):
        b = _base()
        b.donnees["individus"]["I1"] = self._personne_sourcee()
        # le formulaire renvoie les listes SANS le sous-champ citations
        b.modifier_individu("I1", {
            "professions": [{"valeur": "Couturière", "date": "1883"}],
            "residences": [{"date": "1901", "lieu": "Chellala"}],
            "evenements": [{"type": "EVEN", "precision": "PACS", "date": "2007"}]})
        p = b.donnees["individus"]["I1"]
        self.assertEqual(p["professions"][0]["citations"], [{"source": "S1", "quay": 3}])
        self.assertEqual(p["residences"][0]["citations"], [{"source": "S2", "quay": 2}])
        self.assertEqual(p["evenements"][0]["citations"], [{"source": "S3"}])

    def test_citations_explicites_vides_sont_respectees(self):
        # envoyer citations:[] = effacement volontaire, on ne restaure pas
        b = _base()
        b.donnees["individus"]["I1"] = self._personne_sourcee()
        b.modifier_individu("I1", {
            "professions": [{"valeur": "Couturière", "date": "1883", "citations": []}]})
        self.assertEqual(b.donnees["individus"]["I1"]["professions"][0]["citations"], [])

    def test_fait_modifie_ne_recupere_pas_les_citations_d_un_autre(self):
        # si le fait change de valeur (nouvelle résidence), pas de report abusif
        b = _base()
        b.donnees["individus"]["I1"] = self._personne_sourcee()
        b.modifier_individu("I1", {
            "residences": [{"date": "1912", "lieu": "Marseille"}]})  # autre résidence
        self.assertFalse(b.donnees["individus"]["I1"]["residences"][0].get("citations"))

    def test_reordonnancement_preserve_les_bonnes_citations(self):
        b = _base()
        ind = self._personne_sourcee()
        ind["professions"] = [
            {"valeur": "Couturière", "date": "1883", "citations": [{"source": "S1"}]},
            {"valeur": "Modiste", "date": "1901", "citations": [{"source": "S9"}]}]
        b.donnees["individus"]["I1"] = ind
        # le client renvoie les deux métiers dans l'ordre inverse, sans citations
        b.modifier_individu("I1", {"professions": [
            {"valeur": "Modiste", "date": "1901"},
            {"valeur": "Couturière", "date": "1883"}]})
        profs = b.donnees["individus"]["I1"]["professions"]
        self.assertEqual(profs[0]["citations"], [{"source": "S9"}])   # Modiste
        self.assertEqual(profs[1]["citations"], [{"source": "S1"}])   # Couturière


if __name__ == "__main__":
    unittest.main()
