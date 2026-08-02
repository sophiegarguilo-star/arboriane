# -*- coding: utf-8 -*-
"""Éditeur enrichi des transcriptions : à l'EXPORT GEDCOM, la transcription doit
rester du TEXTE SIMPLE — aucune balise HTML ne doit atteindre un fichier exporté
(« il ne faut pas qu'à l'export ça mette la panique »).

Couvre : le helper html_vers_texte (balises, sauts de ligne, puces, entités,
texte simple inchangé) ; l'export d'un record source (DATA/TEXT) ; le repliage
par les profils d'export (note de source / TEXT de citation / note de personne).
"""

import copy
import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                                   # noqa: E402
from core.gedcom.champs import html_vers_texte            # noqa: E402
from services import profils_export                       # noqa: E402

HTML = "<b>L'an mil huit cent</b><br>Fils de Pierre &amp; Marie.<ul><li>un</li><li>deux</li></ul>"


class TestHtmlVersTexte(unittest.TestCase):
    def test_texte_simple_inchange(self):
        s = "Ligne une\nLigne deux"
        self.assertEqual(html_vers_texte(s), s)

    def test_balises_retirees(self):
        r = html_vers_texte("<b>gras</b> et <i>ital</i>")
        self.assertNotIn("<", r)
        self.assertIn("gras", r)
        self.assertIn("ital", r)

    def test_sauts_de_ligne(self):
        r = html_vers_texte("un<br>deux<p>trois</p>quatre")
        lignes = [l for l in r.split("\n") if l]
        self.assertEqual(lignes, ["un", "deux", "trois", "quatre"])

    def test_puces(self):
        r = html_vers_texte("<ul><li>un</li><li>deux</li></ul>")
        self.assertIn("- un", r)
        self.assertIn("- deux", r)

    def test_entites_decodees(self):
        # Décodage seulement quand l'entrée est du HTML (présence d'une balise).
        r = html_vers_texte("<b>Pierre &amp; Marie &lt;x&gt;&nbsp;fin</b>")
        self.assertIn("Pierre & Marie", r)
        self.assertIn("<x>", r)
        self.assertNotIn("&amp;", r)
        self.assertNotIn("&nbsp;", r)

    def test_texte_simple_avec_entites_inchange(self):
        # Sans balise : renvoyé tel quel (aller-retour d'un texte simple existant).
        s = "Pierre &amp; Marie"
        self.assertEqual(html_vers_texte(s), s)

    def test_script_retire(self):
        r = html_vers_texte("avant<script>alert(1)</script>apres")
        self.assertNotIn("<", r)
        self.assertIn("avant", r)
        self.assertIn("apres", r)


def _base():
    """Mini-arbre : I1, naissance citant S1 dont la transcription est du HTML."""
    return {
        "individus": {
            "I1": {"id": "I1", "prenoms": "Jean", "nom": "MARTIN", "sexe": "M",
                   "naissance": {"date": "3 janvier 1850", "lieu": "Marseille",
                                 "citations": [{"source": "S1", "quay": 3}]},
                   "deces": {}, "citations": []},
        },
        "familles": {},
        "sources": {
            "S1": {"id": "S1", "titre": "Acte de naissance", "type": "naissance",
                   "date": "", "lieu": "", "transcription": HTML,
                   "ark": "https://example.org/acte/1", "note": "", "depot": "",
                   "cote": "", "personnes": [], "fichiers": []},
        },
    }


class TestExportSansBalises(unittest.TestCase):
    def _assert_pas_de_balise(self, ged, contexte):
        for balise in ("<b>", "</b>", "<br>", "<ul>", "<li>"):
            self.assertNotIn(balise, ged, contexte + " : balise " + balise + " présente")

    def test_record_source_texte_simple(self):
        ged = gedcom.exporter(_base())
        self._assert_pas_de_balise(ged, "export générique record")
        self.assertIn("L'an mil huit cent", ged)   # le texte, lui, est là
        self.assertIn("- un", ged)                  # la puce est bien un « - »
        self.assertNotIn("&amp;", ged)              # entité décodée

    def test_profils_replient_sans_balise(self):
        for profil in ("myheritage", "ancestry", "filae", "geneanet", "generique"):
            donnees = _base()
            copie = profils_export.appliquer_profil(donnees, profil)
            ged = profils_export.nettoyer_texte(gedcom.exporter(copie), profil)
            self._assert_pas_de_balise(ged, "profil " + profil)
            self.assertIn("L'an mil huit cent", ged, "profil " + profil + " : texte perdu")

    def test_entree_non_modifiee(self):
        donnees = _base()
        avant = copy.deepcopy(donnees["sources"]["S1"]["transcription"])
        gedcom.exporter(donnees)
        self.assertEqual(donnees["sources"]["S1"]["transcription"], avant)


if __name__ == "__main__":
    unittest.main()
