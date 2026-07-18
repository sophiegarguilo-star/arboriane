# -*- coding: utf-8 -*-
"""
Test de la restauration d'une sauvegarde .zip côté serveur (sélecteur natif).

Vérifie notamment le cas d'une archive dont le contenu est niché dans un
sous-dossier unique (ex. « Ma généalogie/… »), comme une vraie sauvegarde.

Exécuter :  python -X utf8 tests/test_restaurer.py
"""

import os
import sys
import tempfile
import zipfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application            # noqa: E402
from core import espace as espace_mod               # noqa: E402
from services import selecteur_dossier              # noqa: E402
import routes                                        # noqa: E402

routes.charger_modules()

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _zip_sauvegarde(dossier_zip):
    """Fabrique un .zip contenant un arbre valide NICHÉ dans « Mon arbre/ »."""
    src = tempfile.mkdtemp()
    espace_mod.creer(src, "Mon arbre sauvegardé")
    chemin_zip = os.path.join(dossier_zip, "sauvegarde.zip")
    with zipfile.ZipFile(chemin_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, fichiers in os.walk(src):
            for f in fichiers:
                plein = os.path.join(base, f)
                arc = os.path.join("Mon arbre", os.path.relpath(plein, src))
                z.write(plein, arc)
    return chemin_zip


def test_restaurer_zip_niche():
    app = Application(tempfile.mkdtemp())
    zchemin = _zip_sauvegarde(tempfile.mkdtemp())

    # Simule le choix de fichier natif -> renvoie notre zip.
    selecteur_dossier.choisir_fichier = lambda *a, **k: zchemin
    code, r = routes.dispatch(app, "POST", "/api/espaces/restaurer", {}, {})
    verifie("restaurer : 200", code == 200)
    verifie("restaurer : pas annulé", r.get("annule") is False)
    verifie("restaurer : arbre ouvert et valide",
            r.get("chemin") and espace_mod.est_espace(r["chemin"]))
    verifie("restaurer : dossier sous « Mes arbres »",
            os.path.normpath(app.dossier_arbres) in os.path.normpath(r["chemin"]))


def test_restaurer_annule():
    app = Application(tempfile.mkdtemp())
    selecteur_dossier.choisir_fichier = lambda *a, **k: ""      # l'utilisateur annule
    code, r = routes.dispatch(app, "POST", "/api/espaces/restaurer", {}, {})
    verifie("annulation : 200 + annule=True", code == 200 and r.get("annule") is True)


if __name__ == "__main__":
    test_restaurer_zip_niche()
    test_restaurer_annule()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
