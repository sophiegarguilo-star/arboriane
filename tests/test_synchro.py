# -*- coding: utf-8 -*-
"""
Tests de la synchro multi-ordinateurs (services/synchro) + intégration verrou
dans l'Application. Exécuter :  python -X utf8 tests/test_synchro.py

Couvre : détection de dossier cloud (OneDrive env + marqueurs Dropbox/Drive),
pose/lecture/péremption/verrou étranger/libération, et pose automatique du
verrou à l'activation d'un arbre situé dans un dossier synchronisé.
"""

import os
import sys
import tempfile
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from services import synchro                       # noqa: E402
from core.application import Application            # noqa: E402


class TestDetectionCloud(unittest.TestCase):
    def test_local_non_detecte(self):
        self.assertIsNone(synchro.detecter_cloud(r"C:\Users\x\Documents\Arbres\Famille"))

    def test_dropbox(self):
        c = synchro.detecter_cloud(r"C:\Users\x\Dropbox\Arbres\Famille")
        self.assertEqual(c and c["fournisseur"], "Dropbox")

    def test_google_drive(self):
        c = synchro.detecter_cloud(r"C:\Users\x\Google Drive\Genea\Arbre")
        self.assertEqual(c and c["fournisseur"], "Google Drive")

    def test_onedrive_par_variable(self):
        d = tempfile.mkdtemp()
        try:
            os.environ["OneDrive"] = d
            sous = os.path.join(d, "Arbres", "Famille")
            c = synchro.detecter_cloud(sous)
            self.assertEqual(c and c["fournisseur"], "OneDrive")
        finally:
            os.environ.pop("OneDrive", None)

    def test_chemin_vide(self):
        self.assertIsNone(synchro.detecter_cloud(""))
        self.assertIsNone(synchro.detecter_cloud(None))


class TestVerrou(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()

    def test_poser_lire(self):
        synchro.poser_verrou(self.dossier, machine="PC-A", maintenant=1000)
        v = synchro.lire_verrou(self.dossier)
        self.assertEqual(v["machine"], "PC-A")

    def test_absent(self):
        self.assertIsNone(synchro.lire_verrou(self.dossier))
        self.assertIsNone(synchro.verrou_etranger(self.dossier, machine="PC-A"))

    def test_etranger_recent(self):
        synchro.poser_verrou(self.dossier, machine="PC-A", maintenant=1000)
        v = synchro.verrou_etranger(self.dossier, machine="PC-B", maintenant=1120)  # +2 min
        self.assertIsNotNone(v)
        self.assertEqual(v["machine"], "PC-A")
        self.assertEqual(v["age_min"], 2)

    def test_notre_propre_verrou_pas_etranger(self):
        synchro.poser_verrou(self.dossier, machine="PC-A", maintenant=1000)
        self.assertIsNone(synchro.verrou_etranger(self.dossier, machine="PC-A", maintenant=1100))

    def test_verrou_perime_ignore(self):
        synchro.poser_verrou(self.dossier, machine="PC-A", maintenant=1000)
        loin = 1000 + synchro.PEREMPTION + 60
        self.assertIsNone(synchro.verrou_etranger(self.dossier, machine="PC-B", maintenant=loin))

    def test_liberer_seulement_le_notre(self):
        synchro.poser_verrou(self.dossier, machine="PC-A", maintenant=1000)
        self.assertFalse(synchro.liberer_verrou(self.dossier, machine="PC-B"))  # pas à nous
        self.assertIsNotNone(synchro.lire_verrou(self.dossier))                 # toujours là
        self.assertTrue(synchro.liberer_verrou(self.dossier, machine="PC-A"))   # à nous
        self.assertIsNone(synchro.lire_verrou(self.dossier))                    # retiré


class TestIntegrationApplication(unittest.TestCase):
    def test_verrou_pose_pour_arbre_cloud_pas_pour_local(self):
        app_dir = tempfile.mkdtemp()
        app = Application(app_dir)

        # Arbre LOCAL (dans « Mes arbres/ ») : aucun fichier-verrou ajouté.
        app.creer("Local")
        self.assertIsNone(app.cloud_actif())
        self.assertFalse(os.path.exists(os.path.join(app.espace_chemin, synchro.NOM_VERROU)))

        # Arbre dans un dossier au chemin « Dropbox » : verrou posé automatiquement.
        parent_cloud = os.path.join(tempfile.mkdtemp(), "Dropbox")
        os.makedirs(parent_cloud)
        app.creer("Sur le cloud", parent_cloud)
        self.assertEqual((app.cloud_actif() or {}).get("fournisseur"), "Dropbox")
        self.assertTrue(os.path.exists(os.path.join(app.espace_chemin, synchro.NOM_VERROU)))

    def test_verrou_pas_dans_la_sauvegarde_zip(self):
        import zipfile
        app_dir = tempfile.mkdtemp()
        app = Application(app_dir)
        parent_cloud = os.path.join(tempfile.mkdtemp(), "Dropbox")
        os.makedirs(parent_cloud)
        app.creer("Cloud", parent_cloud)
        cible = app.sauvegarde_complete()
        with zipfile.ZipFile(cible) as z:
            noms = [os.path.basename(n) for n in z.namelist()]
        self.assertNotIn(synchro.NOM_VERROU, noms)


if __name__ == "__main__":
    unittest.main(verbosity=2)
