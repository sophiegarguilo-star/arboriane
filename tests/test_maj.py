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


def test_notes_completes():
    """Chaque version publiée doit avoir ses notes (leçon 1.9.6 → 1.9.10 :
    cinq versions publiées hors outil, sans « Quoi de neuf »)."""
    versions = [n["version"] for n in maj_svc.NOTES]
    verifie("NOTES[0] = version courante", versions and versions[0] == VERSION)
    for v in ("1.9.6", "1.9.7", "1.9.8", "1.9.9", "1.9.10"):
        verifie("notes présentes pour %s" % v, v in versions)
    # Ordre strictement décroissant (du plus récent au plus ancien).
    tuples = [maj_svc._tuple(v) for v in versions]
    verifie("NOTES triées décroissantes", tuples == sorted(tuples, reverse=True))
    # Chaque entrée est complète : date et au moins un point rédigé.
    completes = all(n.get("date") and n.get("points") for n in maj_svc.NOTES)
    verifie("chaque entrée a date + points", completes)


def test_changelog_coherence():
    """generer_changelog : la barrière refuse des NOTES en retard sur la
    version, et le rendu n'utilise plus de liens de tags supprimables."""
    sys.path.insert(0, os.path.join(RACINE, "outils"))
    import generer_changelog as gc

    verifie("coherence : OK sur l'état réel", gc.verifier_coherence() == "")
    err = gc.verifier_coherence(notes=[{"version": "0.0.1"}], version="9.9.9")
    verifie("coherence : NOTES[0] != VERSION refusé", "9.9.9" in err)
    verifie("coherence : NOTES vide refusé", gc.verifier_coherence(notes=[]) != "")

    texte = gc.rendu()
    verifie("rendu : ancres internes (pas de lien de tag)",
            "/releases/tag/" not in texte)
    verifie("rendu : la version courante est en tête",
            ("## %s — " % VERSION) in texte)

    # Et le fichier CHANGELOG.md committé est bien à jour (--verifier vert).
    import subprocess
    r = subprocess.run([sys.executable, "-X", "utf8",
                        os.path.join(RACINE, "outils", "generer_changelog.py"),
                        "--verifier"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    verifie("generer_changelog --verifier passe", r.returncode == 0)


def test_deployer_gardes():
    """deployer : publier() refuse sans contrôle d'arbre propre, refuse une
    release déjà en ligne (jamais --clobber), et build-info.txt s'écrit."""
    import importlib
    import tempfile as tf
    sys.path.insert(0, os.path.join(RACINE, "outils"))
    dep = importlib.import_module("deployer")

    # 1. Sans contrôle « arbre propre » (barrière contournée) : ARRÊT net,
    #    AVANT tout appel git/gh — le test n'exécute donc rien d'externe.
    dep._ARBRE_VERIFIE_PROPRE = False
    try:
        dep.publier()
        verifie("publier : refuse sans contrôle d'arbre propre", False)
    except SystemExit as e:
        verifie("publier : refuse sans contrôle d'arbre propre",
                "propre" in str(e))

    # 2. Release déjà publiée côté distant : ARRÊT clair, on monte la version.
    dep._ARBRE_VERIFIE_PROPRE = True
    vrai_existe = dep._release_distante_existe
    dep._release_distante_existe = lambda tag: True
    try:
        dep.publier()
        verifie("publier : refuse une release déjà en ligne", False)
    except SystemExit as e:
        msg = str(e)
        verifie("publier : refuse une release déjà en ligne", "DÉJÀ" in msg)
        verifie("publier : le message dit de monter la version",
                "montez VERSION" in msg)
    finally:
        dep._release_distante_existe = vrai_existe
        dep._ARBRE_VERIFIE_PROPRE = False

    # 3. Plus aucun --clobber dans le code (on ne remplace jamais un binaire).
    src = open(os.path.join(RACINE, "outils", "deployer.py"),
               encoding="utf-8").read()
    verifie("deployer : plus d'argument --clobber", '"--clobber"' not in src)
    verifie("deployer : plus de commit séparé « Page : version »",
            '"Page : version "' not in src)

    # 4. build-info.txt : écrit, avec la version et l'outillage.
    dossier = tf.mkdtemp(prefix="arbo_buildinfo_")
    chemin = dep.ecrire_build_info(dossier)
    contenu = open(chemin, encoding="utf-8").read()
    verifie("build-info : contient la version", VERSION in contenu)
    verifie("build-info : contient python + pyinstaller + inno",
            all(m in contenu for m in ("python", "pyinstaller", "inno setup")))


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
    test_notes_completes()
    test_changelog_coherence()
    test_deployer_gardes()
    test_notes_depuis()
    test_routes_etat_et_vu()
    test_optin_verif()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
