# -*- coding: utf-8 -*-
"""GED-02 — Revenir en arrière : lister et RESTAURER les copies automatiques.

Avant : les copies Sauvegardes/arboriane_*.json existaient mais rien dans
l'application ne permettait de les voir ni d'y revenir. Désormais :

  - GET /api/archives liste les copies de l'arbre actif (nom, date lisible,
    nombre de personnes lu dans le JSON — les archives sont un dump direct
    des données), la plus récente d'abord ;
  - POST /api/archives/restaurer {nom} remplace la base par la copie choisie,
    APRÈS avoir archivé l'état courant (revenir en arrière n'efface rien) ;
  - garde-fous : nom contrôlé (pas de traversée de chemin), JSON validé.

Exécuter :  python -X utf8 tests/test_restaurer_archives.py
"""

import os
import sys
import tempfile
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

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


def test_lister_puis_restaurer():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "Archives"})

    # État A : 1 personne (la 1re sauvegarde crée toujours une archive).
    routes.dispatch(app, "POST", "/api/individus", {},
                    {"nom": "PREMIER", "prenoms": "Paul"})
    time.sleep(1.1)                    # noms d'archives à la seconde près
    # État B : 2 personnes, archivé de force (l'archivage auto est espacé).
    routes.dispatch(app, "POST", "/api/individus", {},
                    {"nom": "SECONDE", "prenoms": "Zoé"})
    app.base.sauvegarder(forcer_horodatage=True)

    code, r = routes.dispatch(app, "GET", "/api/archives", {}, {})
    verifie("GET /api/archives : 200", code == 200)
    archives = r.get("archives") or []
    verifie("au moins 2 copies listées", len(archives) >= 2)
    verifie("chaque copie a nom + date + personnes",
            all(a.get("nom") and a.get("date") and a.get("personnes") is not None
                for a in archives))
    verifie("la plus récente d'abord (2 personnes)",
            archives[0]["personnes"] == 2)
    ancienne = next((a for a in archives if a["personnes"] == 1), None)
    verifie("la copie « état A » (1 personne) est listée", ancienne is not None)

    # Restaurer l'état A — l'état courant (2 personnes) doit être archivé avant.
    time.sleep(1.1)
    nb_avant = len(archives)
    code, r = routes.dispatch(app, "POST", "/api/archives/restaurer", {},
                              {"nom": ancienne["nom"]})
    verifie("restaurer : 200 + ok", code == 200 and r.get("ok"))
    verifie("la base est revenue à 1 personne",
            r.get("personnes") == 1 and len(app.base.donnees["individus"]) == 1)
    verifie("le fichier principal aussi (rechargement disque)",
            (app.base.charger() or len(app.base.donnees["individus"]) == 1))
    code, r = routes.dispatch(app, "GET", "/api/archives", {}, {})
    apres = r.get("archives") or []
    verifie("l'état courant a été archivé AVANT la restauration",
            len(apres) > nb_avant and any(a["personnes"] == 2 for a in apres))

    # Revenir en avant : restaurer la copie « 2 personnes » la plus récente.
    time.sleep(1.1)
    recente = next(a for a in apres if a["personnes"] == 2)
    code, r = routes.dispatch(app, "POST", "/api/archives/restaurer", {},
                              {"nom": recente["nom"]})
    verifie("re-revenir en avant fonctionne aussi",
            code == 200 and len(app.base.donnees["individus"]) == 2)


def test_garde_fous():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "Gardes"})
    routes.dispatch(app, "POST", "/api/individus", {},
                    {"nom": "SEUL", "prenoms": "Jean"})

    code, _ = routes.dispatch(app, "POST", "/api/archives/restaurer", {},
                              {"nom": "../espace.json"})
    verifie("traversée de chemin refusée (400)", code == 400)
    code, _ = routes.dispatch(app, "POST", "/api/archives/restaurer", {},
                              {"nom": "espace.json"})
    verifie("nom hors motif arboriane_*.json refusé (400)", code == 400)
    code, _ = routes.dispatch(app, "POST", "/api/archives/restaurer", {},
                              {"nom": "arboriane_9999-01-01_000000.json"})
    verifie("copie inexistante -> 404", code == 404)

    # archive illisible : listée quand même, mais refusée à la restauration
    cassee = os.path.join(app.base.dossier_sauvegardes,
                          "arboriane_2020-01-01_000000.json")
    with open(cassee, "w", encoding="utf-8") as f:
        f.write("{ pas du json")
    code, r = routes.dispatch(app, "GET", "/api/archives", {}, {})
    verifie("copie illisible listée (personnes = None)",
            any(a["nom"] == os.path.basename(cassee)
                and a["personnes"] is None for a in r["archives"]))
    code, _ = routes.dispatch(app, "POST", "/api/archives/restaurer", {},
                              {"nom": os.path.basename(cassee)})
    verifie("copie illisible refusée à la restauration (400)", code == 400)
    verifie("la base actuelle n'a pas bougé",
            len(app.base.donnees["individus"]) == 1)

    # un JSON valide mais qui n'est pas un arbre
    pas_arbre = os.path.join(app.base.dossier_sauvegardes,
                             "arboriane_2020-01-02_000000.json")
    with open(pas_arbre, "w", encoding="utf-8") as f:
        f.write('{"bonjour": true}')
    code, _ = routes.dispatch(app, "POST", "/api/archives/restaurer", {},
                              {"nom": os.path.basename(pas_arbre)})
    verifie("JSON non-arbre refusé (400)", code == 400)


def test_corrompu_puis_restaurer_efface_avertissement():
    """DAT-03 : après quarantaine (avertissement « corrompu »), restaurer une
    copie répare la base ET éteint le bandeau."""
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "Quarantaine"})
    routes.dispatch(app, "POST", "/api/individus", {},
                    {"nom": "SAINE", "prenoms": "Base"})
    # corrompre le fichier principal puis recharger : quarantaine
    with open(app.base.chemin, "w", encoding="utf-8") as f:
        f.write("{ceci n'est pas du json")
    app.base.charger()
    verifie("le JSON corrompu déclenche l'avertissement",
            app.base.avertissement == "corrompu")
    code, r = routes.dispatch(app, "GET", "/api/espace", {}, {})
    verifie("/api/espace expose l'avertissement",
            r.get("avertissement") == "corrompu")
    code, r = routes.dispatch(app, "GET", "/api/archives", {}, {})
    archive = (r.get("archives") or [{}])[0]
    verifie("une copie saine est disponible", archive.get("personnes") == 1)
    code, r = routes.dispatch(app, "POST", "/api/archives/restaurer", {},
                              {"nom": archive["nom"]})
    verifie("restauration après quarantaine : 200", code == 200)
    verifie("la base est réparée", len(app.base.donnees["individus"]) == 1)
    verifie("l'avertissement est éteint après restauration",
            app.base.avertissement == "")


def test_sans_arbre_ouvert():
    app = Application(tempfile.mkdtemp())
    code, r = routes.dispatch(app, "GET", "/api/archives", {}, {})
    verifie("sans arbre : liste vide, pas d'erreur",
            code == 200 and r.get("archives") == [])
    code, _ = routes.dispatch(app, "POST", "/api/archives/restaurer", {},
                              {"nom": "arboriane_x.json"})
    verifie("sans arbre : restaurer refusé (400)", code == 400)


if __name__ == "__main__":
    for t in (test_lister_puis_restaurer, test_garde_fous,
              test_corrompu_puis_restaurer_efface_avertissement,
              test_sans_arbre_ouvert):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
