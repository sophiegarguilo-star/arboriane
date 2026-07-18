# -*- coding: utf-8 -*-
"""
Ouverture d'un navigateur MODERNE (core/navigateur.py) — jamais Internet Explorer.
Arboriane a besoin de modules ES : ouvrir dans le navigateur PAR DÉFAUT (IE sur
certaines machines) casse l'app ET bloque le téléchargement des mises à jour.
Exécuter :  python -X utf8 tests/test_navigateur.py
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import navigateur                       # noqa: E402


class TestNavigateur(unittest.TestCase):
    def test_prefere_edge_chrome(self):
        # un candidat (Edge/Chrome) existe -> on le lance, PAS webbrowser (IE possible)
        with mock.patch.object(navigateur.os.path, "exists", return_value=True), \
             mock.patch.object(navigateur.shutil, "which", side_effect=lambda c: None), \
             mock.patch.object(navigateur.subprocess, "Popen") as popen, \
             mock.patch.object(navigateur.webbrowser, "open") as wopen:
            ok = navigateur.ouvrir("http://127.0.0.1:8770/")
        self.assertTrue(ok)
        self.assertTrue(popen.called)          # Edge/Chrome lancé
        self.assertFalse(wopen.called)         # jamais le navigateur par défaut

    def test_repli_navigateur_defaut(self):
        # aucun Edge/Chrome trouvé -> repli sur webbrowser.open (sans planter)
        with mock.patch.object(navigateur.os.path, "exists", return_value=False), \
             mock.patch.object(navigateur.shutil, "which", return_value=None), \
             mock.patch.object(navigateur.webbrowser, "open", return_value=True) as wopen:
            ok = navigateur.ouvrir("http://127.0.0.1:8770/")
        self.assertTrue(ok)
        self.assertTrue(wopen.called)

    def test_ne_leve_jamais(self):
        with mock.patch.object(navigateur.os.path, "exists", return_value=False), \
             mock.patch.object(navigateur.shutil, "which", return_value=None), \
             mock.patch.object(navigateur.webbrowser, "open", side_effect=Exception("boom")):
            self.assertFalse(navigateur.ouvrir("http://x/"))   # renvoie False, ne lève pas


if __name__ == "__main__":
    unittest.main(verbosity=2)
