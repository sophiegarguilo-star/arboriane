# -*- coding: utf-8 -*-
"""Import : reconnaître la VERSION du fichier, et le dire.

Arboriane lit le GEDCOM 5.5.1. Un fichier 7.0 s'importe quand même — la grammaire
des lignes n'a pas changé, les personnes et les familles non plus — mais les
structures nouvelles (notes partagées, rôles d'association, phrases explicatives)
sont perdues sans un mot.

Vérifié sur les fichiers d'exemple officiels de gedcom.io : maximal70.ged ressort
avec 4 personnes et 5 pointeurs abandonnés, notes-1.ged avec zéro personne. Aucun
plantage, aucun avertissement — le pire des deux mondes. On lit donc HEAD.GEDC.VERS
pour pouvoir prévenir l'utilisateur.

Exécuter :  python -X utf8 tests/test_gedcom_version.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                          # noqa: E402
from core.application import Application         # noqa: E402
import routes                                    # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _entete(vers=None, gedc=True):
    lignes = ["0 HEAD"]
    if gedc:
        lignes.append("1 GEDC")
        if vers:
            lignes.append("2 VERS " + vers)
    lignes += ["1 CHAR UTF-8",
               "0 @I1@ INDI", "1 NAME Jean /DUPONT/", "1 SEX M",
               "0 TRLR"]
    return "\n".join(lignes) + "\n"


def test_version_lue_dans_l_entete():
    for v in ("5.5.1", "5.5.5", "7.0", "7.0.14"):
        d = gedcom.importer(_entete(v))
        verifie("VERS %s reconnue" % v, d["meta"]["version_fichier"] == v)


def test_entete_sans_version():
    d = gedcom.importer(_entete(None))
    verifie("GEDC sans VERS : chaîne vide, pas d'erreur",
            d["meta"]["version_fichier"] == "")
    d = gedcom.importer(_entete(None, gedc=False))
    verifie("aucun GEDC : chaîne vide, pas d'erreur",
            d["meta"]["version_fichier"] == "")


def test_l_import_reste_possible_en_7():
    """On avertit, on ne refuse pas : un arbre à moitié lu vaut mieux que rien,
    à condition de le dire."""
    d = gedcom.importer(_entete("7.0"))
    verifie("un fichier 7.0 s'importe quand même", len(d["individus"]) == 1)


def test_la_version_remonte_dans_les_deux_modes():
    for url in ("/api/import/gedcom/appliquer", "/api/import/gedcom/fusionner"):
        app = Application(tempfile.mkdtemp())
        routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "P"})
        code, r = routes.dispatch(app, "POST", url, {}, {"texte": _entete("7.0")})
        verifie("%s renvoie la version du fichier" % url.rsplit("/", 1)[-1],
                code == 200 and r.get("version_fichier") == "7.0")


def test_un_fichier_551_ne_declenche_aucune_alerte():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "P"})
    _, r = routes.dispatch(app, "POST", "/api/import/gedcom/appliquer", {},
                           {"texte": _entete("5.5.1")})
    verifie("5.5.1 : la version est rapportée sans être une alerte",
            r["version_fichier"] == "5.5.1")


if __name__ == "__main__":
    for t in (test_version_lue_dans_l_entete, test_entete_sans_version,
              test_l_import_reste_possible_en_7,
              test_la_version_remonte_dans_les_deux_modes,
              test_un_fichier_551_ne_declenche_aucune_alerte):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
