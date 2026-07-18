# -*- coding: utf-8 -*-
"""
Test des mises à jour — « quoi de neuf » local + opt-in vérif en ligne.

Exécuter :  python -X utf8 tests/test_maj.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application            # noqa: E402
from core.version import VERSION                     # noqa: E402
from services import maj as maj_svc                  # noqa: E402
import routes                                        # noqa: E402

routes.charger_modules()

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_notes_depuis():
    # Premier lancement (aucune version vue) : rien à montrer.
    verifie("notes_depuis(None) vide", maj_svc.notes_depuis(None) == [])
    # Depuis une version ancienne : on remonte les entrées postérieures.
    r = maj_svc.notes_depuis("1.5.3")
    versions = [n["version"] for n in r]
    verifie("notes_depuis(1.5.3) exclut 1.5.3", "1.5.3" not in versions)
    verifie("notes_depuis(1.5.3) inclut 1.5.5", "1.5.5" in versions)
    # Déjà à jour : rien.
    verifie("notes_depuis(version courante) vide", maj_svc.notes_depuis(VERSION) == [])


def test_routes_etat_et_vu():
    app = Application(tempfile.mkdtemp())
    code, r = routes.dispatch(app, "GET", "/api/maj/etat", {}, {})
    verifie("etat : 200", code == 200)
    verifie("etat : version = source unique", r["version"] == VERSION)
    verifie("etat : premier_choix vrai au départ", r["premier_choix"] is True)
    verifie("etat : aucune nouveauté au 1er lancement", r["nouveautes"] == [])

    code, _ = routes.dispatch(app, "POST", "/api/maj/vu", {}, {})
    verifie("vu : 200", code == 200)
    code, r = routes.dispatch(app, "GET", "/api/maj/etat", {}, {})
    verifie("etat : dernière vue mémorisée", r["derniere_vue"] == VERSION)


def test_optin_verif():
    app = Application(tempfile.mkdtemp())
    # Non autorisé par défaut : /verifier ne fait AUCUN appel réseau.
    code, r = routes.dispatch(app, "GET", "/api/maj/verifier", {}, {})
    verifie("verifier : refusé sans opt-in", code == 200 and r["autorise"] is False)

    # L'utilisateur active la vérification.
    routes.dispatch(app, "POST", "/api/maj/preference", {}, {"actif": True})
    code, r = routes.dispatch(app, "GET", "/api/maj/etat", {}, {})
    verifie("etat : verif_active après opt-in", r["verif_active"] is True)
    verifie("etat : premier_choix faux après opt-in", r["premier_choix"] is False)

    # Vérif autorisée : on court-circuite le réseau (test hors ligne).
    maj_svc.verifier_en_ligne = lambda timeout=6: {
        "ok": True, "actuelle": VERSION, "derniere": "9.9.9",
        "disponible": True, "url": maj_svc.PAGE}
    code, r = routes.dispatch(app, "GET", "/api/maj/verifier", {}, {})
    verifie("verifier : autorisé renvoie disponible", r["autorise"] and r["disponible"])


if __name__ == "__main__":
    test_notes_depuis()
    test_routes_etat_et_vu()
    test_optin_verif()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
