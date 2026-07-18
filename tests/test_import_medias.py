# -*- coding: utf-8 -*-
"""Import LOCAL des scans référencés par un GEDCOM (retour utilisateur Michel).

Un GEDCOM Brother's Keeper rattache un scan par son chemin absolu
(« 4 FILE D:\\...\\X-00021.png »). Arboriane tournant en local, le fichier est
copié dans l'arbre s'il existe. On vérifie aussi le décodage ANSI (cp1252) sur le
VRAI fichier de Michel s'il est présent dans gitignore/.

Exécuter :  python -X utf8 tests/test_import_medias.py
"""

import base64
import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application          # noqa: E402
import routes                                      # noqa: E402
from services import gedcom_charset               # noqa: E402
from core import gedcom                            # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _app():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "S"})
    return app


# 1×1 PNG transparent (octets réels)
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9"
    "awAAAABJRU5ErkJggg==")


def _gedcom_avec_scan(chemin_scan):
    """GEDCOM minimal : un individu dont la naissance cite une source portant un
    OBJE/FILE = `chemin_scan` (chemin absolu, façon Brother's Keeper)."""
    return (
        "0 HEAD\n1 CHAR ANSI\n1 GEDC\n2 VERS 5.5.1\n"
        "0 @I1@ INDI\n1 NAME François /Castagne/\n1 SEX M\n"
        "1 BIRT\n2 DATE 1 MAR 1840\n2 PLAC Neufchâteau\n2 SOUR @S1@\n"
        "3 PAGE Acte 11\n3 OBJE\n4 FORM PNG\n4 FILE " + chemin_scan + "\n"
        "0 @S1@ SOUR\n1 TITL État civil\n0 TRLR\n")


def test_scan_present_copie():
    app = _app()
    d = tempfile.mkdtemp()
    chemin = os.path.join(d, "X-00021.png")
    with open(chemin, "wb") as f:
        f.write(_PNG)
    texte = _gedcom_avec_scan(chemin)
    octets = texte.encode("cp1252")
    rep = routes.dispatch(app, "POST", "/api/import/gedcom/appliquer", {},
                          {"octets_b64": base64.b64encode(octets).decode()})
    # le bilan d'import signale la copie
    verifie("bilan : 1 scan copié, 0 manquant",
            rep[1].get("scans") == {"copies": 1, "manquants": 0})
    # le fichier a été copié dans Sources/
    presents = app.lister_medias("Sources")
    verifie("scan copié dans Sources/", "X-00021.png" in presents)
    # la source référence le nom réellement enregistré
    src = list(app.base.donnees["sources"].values())[0]
    verifie("source pointe le fichier copié", "X-00021.png" in src.get("fichiers", []))
    verifie("aucun chemin transitoire résiduel", "_chemins_scans" not in src)


def test_scan_absent_reste_a_retrouver():
    app = _app()
    chemin = "D:\\Introuvable\\Michel\\X-99999.png"    # n'existe pas
    texte = _gedcom_avec_scan(chemin)
    octets = texte.encode("cp1252")
    rep = routes.dispatch(app, "POST", "/api/import/gedcom/appliquer", {},
                          {"octets_b64": base64.b64encode(octets).decode()})
    verifie("bilan : 0 copié, 1 manquant signalé",
            rep[1].get("scans") == {"copies": 0, "manquants": 1})
    presents = app.lister_medias("Sources")
    verifie("scan absent NON copié", "X-99999.png" not in presents)
    src = list(app.base.donnees["sources"].values())[0]
    # on garde le NOM (à retrouver), pas le chemin complet ni le champ transitoire
    verifie("nom du scan conservé (à retrouver)", "X-99999.png" in src.get("fichiers", []))
    verifie("pas de chemin transitoire persisté", "_chemins_scans" not in src)


def test_accents_ansi_fichier_reel():
    """Non-régression accents : le VRAI fichier ANSI de Michel (s'il est présent)
    doit s'importer sans un seul « � »."""
    chemin = os.path.join(RACINE, "gitignore", "Test-Arboriane.GED")
    if not os.path.isfile(chemin):
        print("  (skip) fichier réel de Michel absent — test synthétique seulement")
        octets = ("0 HEAD\n1 CHAR ANSI\n0 @I1@ INDI\n1 NAME François /Déçà/\n"
                  "1 BIRT\n2 PLAC Neufchâteau\n0 TRLR\n").encode("cp1252")
    else:
        octets = open(chemin, "rb").read()
    texte, cs, fi = gedcom_charset.decoder(octets)
    verifie("ANSI détecté = cp1252", cs == "cp1252")
    verifie("aucun caractère de remplacement �", texte.count("�") == 0)
    d = gedcom.importer(texte)
    accentues = [ind for ind in d["individus"].values()
                 if any(c in (ind.get("nom", "") + (ind.get("naissance") or {}).get("lieu", ""))
                        for c in "âéèàêçï")]
    verifie("des champs accentués bien importés", len(accentues) > 0)


if __name__ == "__main__":
    test_scan_present_copie()
    test_scan_absent_reste_a_retrouver()
    test_accents_ansi_fichier_reel()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
