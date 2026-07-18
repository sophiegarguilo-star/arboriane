# -*- coding: utf-8 -*-
"""
Test du Lot 5 — vérifications médias/sources (fichiers manquants, à transcrire).

Exécuter :  python -X utf8 tests/test_verif_medias.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from core import espace                            # noqa: E402
from services import demo, verif_medias            # noqa: E402
import routes                                       # noqa: E402

routes.charger_modules()

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _app_demo():
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    return app


def test_fichiers_manquants():
    app = _app_demo()
    c = espace.chemins(app.espace_chemin)
    os.makedirs(c["sources"], exist_ok=True)
    with open(os.path.join(c["sources"], "present.jpg"), "wb") as f:
        f.write(b"scan")
    d = app.base.donnees
    d["sources"]["Stest1"] = {"id": "Stest1", "titre": "Acte présent",
                              "fichiers": ["present.jpg"], "transcription": "relevé"}
    d["sources"]["Stest2"] = {"id": "Stest2", "titre": "Acte manquant",
                              "fichiers": ["absent.jpg"], "transcription": ""}
    rep = verif_medias.fichiers_manquants(app)
    noms = [m["fichier"] for m in rep["manquants"]]
    verifie("médias : fichier introuvable détecté", "absent.jpg" in noms)
    verifie("médias : fichier présent non signalé", "present.jpg" not in noms)
    verifie("médias : contexte porté sur le manquant",
            any(m["contexte"] == "Acte manquant" for m in rep["manquants"]))
    verifie("médias : compteur cohérent",
            rep["presents"] == rep["total"] - rep["nb_manquants"])


def test_a_transcrire():
    app = _app_demo()
    d = app.base.donnees
    d["sources"]["Str1"] = {"id": "Str1", "titre": "Déjà transcrit",
                            "fichiers": ["a.jpg"], "transcription": "le texte"}
    d["sources"]["Str2"] = {"id": "Str2", "titre": "Scan sans relevé",
                            "fichiers": ["b.jpg"]}
    d["sources"]["Str3"] = {"id": "Str3", "titre": "Sans scan", "transcription": ""}
    trans = verif_medias.a_transcrire(d)
    ids = [s["id"] for s in trans["sources"]]
    verifie("à transcrire : scan sans relevé listé", "Str2" in ids)
    verifie("à transcrire : source transcrite exclue", "Str1" not in ids)
    verifie("à transcrire : source sans scan exclue", "Str3" not in ids)


def test_route_verif():
    app = _app_demo()
    code, r = routes.dispatch(app, "GET", "/api/verif", {}, {})
    verifie("route /api/verif : 200", code == 200)
    for cle in ("fichiers_manquants", "a_transcrire", "sexes_absents",
                "noms_absents", "plan_depots", "coherence"):
        verifie("route /api/verif : contient %s" % cle, cle in r)


def test_route_appliquer_sexe():
    app = _app_demo()
    d = app.base.donnees
    d["individus"]["Ix"] = {"id": "Ix", "prenoms": "Test", "nom": "SANS", "sexe": "U"}
    code, r = routes.dispatch(app, "POST", "/api/verif/sexe", {}, {"id": "Ix", "sexe": "F"})
    verifie("route sexe : 200", code == 200)
    verifie("route sexe : appliqué et persisté", d["individus"]["Ix"]["sexe"] == "F")
    code2, _ = routes.dispatch(app, "POST", "/api/verif/sexe", {}, {"id": "Ix", "sexe": "Z"})
    verifie("route sexe : valeur invalide → 400", code2 == 400)


if __name__ == "__main__":
    test_fichiers_manquants()
    test_a_transcrire()
    test_route_verif()
    test_route_appliquer_sexe()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
