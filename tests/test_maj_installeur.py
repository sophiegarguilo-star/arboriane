# -*- coding: utf-8 -*-
"""Le bouton « Télécharger la mise à jour » doit pointer sur l'installeur .exe,
pas sur la page ni sur le fichier .sha256 (retour utilisateur : « télécharge un
fichier non exécutable »).

Exécuter :  python -X utf8 tests/test_maj_installeur.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from services.maj import _url_installeur   # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_url_installeur():
    assets = [
        {"name": "Installer-Arboriane.exe.sha256",
         "browser_download_url": "https://x/Installer-Arboriane.exe.sha256"},
        {"name": "Installer-Arboriane.exe",
         "browser_download_url": "https://x/Installer-Arboriane.exe"},
    ]
    url = _url_installeur(assets)
    verifie("choisit le .exe", url == "https://x/Installer-Arboriane.exe")
    verifie("jamais le .sha256", not url.endswith(".sha256"))
    verifie("aucun asset -> ''", _url_installeur([]) == "")
    verifie("None -> ''", _url_installeur(None) == "")
    # ordre inverse (le .exe en premier) : toujours bon
    verifie("ordre indifférent",
            _url_installeur([assets[1], assets[0]]) == "https://x/Installer-Arboriane.exe")


if __name__ == "__main__":
    test_url_installeur()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
