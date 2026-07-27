# -*- coding: utf-8 -*-
"""Taxonomie des documents (10 familles / ~100 types), codes et légende.

Exécuter :  python -X utf8 tests/test_taxonomie.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from services import taxonomie_actes as tax       # noqa: E402
from services import nomenclature as nm            # noqa: E402
import routes                                      # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def call(app, m, c, corps=None):
    return routes.dispatch(app, m, c, {}, corps or {})


def test_structure():
    fams = tax.selecteur()
    verifie("10 familles", len(fams) == 10)
    types = list(tax._iter_types())
    verifie("~100 types (au moins 90)", len(types) >= 90)
    verifie("chaque type a un code non vide",
            all(code and code.isupper() for *_, code in types))


def test_codes_communs_stables():
    # Codes de la taxonomie (libellés de la taxonomie).
    for lib, code in [("Acte de naissance", "N"), ("Acte de mariage", "M"),
                      ("Acte de décès", "D"), ("Livret de famille", "LF"),
                      ("Recensement de population", "REC"),
                      ("Fiche matricule militaire", "MIL")]:
        verifie("code taxonomie %s=%s" % (lib, code), tax.code_de(lib) == code)
    # Compat ascendante : les libellés HISTORIQUES restent mappés au même code
    # dans la nomenclature (sinon on renommerait des fichiers déjà rangés).
    for lib, code in [("Recensement", "REC"), ("Matricule militaire", "MIL"),
                      ("Acte de notoriété", "NOTO")]:
        verifie("libellé historique préservé %s=%s" % (lib, code),
                nm.CODES_TYPE.get(lib) == code)


def test_code_partage_pour_forme():
    verifie("naissance et sa transcription partagent le code N",
            tax.code_de("Acte de naissance") == "N"
            and tax.code_de("Transcription de naissance") == "N")


def test_fusion_nomenclature_sans_ecraser():
    # Les nouveaux codes sont dispo pour nommer les fichiers…
    verifie("un type nouveau a son code dans la nomenclature",
            nm.CODES_TYPE.get("Testament") == "TEST")
    # …et les codes historiques restent intacts.
    verifie("le code historique 'Acte de notoriété'=NOTO est préservé",
            nm.CODES_TYPE.get("Acte de notoriété") == "NOTO")
    n = nm.nom_fichier("s.jpg", "Testament", [{"nom": "DUPONT", "prenoms": "Jean"}],
                       "1902", "Lyon")
    verifie("nom de fichier d'un Testament  (%r)" % n, n == "1902_TEST_DUPONT-Jean_Lyon.jpg")


def test_legende_texte():
    t = tax.legende_texte()
    verifie("la légende cite N et MIL", "\nN " in t and "MIL" in t)
    verifie("la légende rappelle le format", "Format :" in t)


def test_routes():
    app = Application(tempfile.mkdtemp())
    call(app, "POST", "/api/espaces/creer", {"nom": "P"})
    code, r = call(app, "GET", "/api/nomenclature/taxonomie")
    verifie("GET taxonomie : 200 + 10 familles",
            code == 200 and len(r["selecteur"]) == 10 and "Original" in r["formes"])
    code, r = call(app, "GET", "/api/nomenclature/legende")
    verifie("GET legende : 200 + texte", code == 200 and "LÉGENDE" in r["texte"])
    code, r = call(app, "POST", "/api/nomenclature/legende")
    verifie("POST legende : écrit le fichier", code == 200 and r["fichier"] == "_LEGENDE-codes.txt")
    verifie("le fichier est bien dans Sources/",
            "_LEGENDE-codes.txt" in app.lister_medias("Sources"))


if __name__ == "__main__":
    for t in (test_structure, test_codes_communs_stables, test_code_partage_pour_forme,
              test_fusion_nomenclature_sans_ecraser, test_legende_texte, test_routes):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
