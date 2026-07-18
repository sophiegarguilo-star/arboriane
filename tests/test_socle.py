# -*- coding: utf-8 -*-
"""
Tests du socle (Lot 1) — sans serveur HTTP : on pilote l'Application et le
routeur directement. Exécuter :  python -X utf8 tests/test_socle.py

Couvre : base vide, démo, création personne (+ garde-fou saisie), relations,
sauvegarde .zip, espace de travail, sécurité (Host/Origin/Content-Type).
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from core import securite                          # noqa: E402
from services import demo                          # noqa: E402
import routes                                      # noqa: E402

routes.charger_modules()

_ok = 0
_ko = 0


def verifie(nom, condition):
    global _ok, _ko
    if condition:
        _ok += 1
        print("  ok  ", nom)
    else:
        _ko += 1
        print("  FAIL", nom)


def app_neuve():
    return Application(tempfile.mkdtemp())


def call(app, methode, chemin, corps=None, params=None):
    return routes.dispatch(app, methode, chemin, params or {}, corps or {})


# ── Base vide ──────────────────────────────────────────────────────────
def test_base_vide():
    app = app_neuve()
    code, p = call(app, "GET", "/api/espace")
    verifie("base vide : aucun arbre ouvert", code == 200 and p["ouvert"] is False)
    code, p = call(app, "GET", "/api/individus")
    verifie("base vide : /individus refuse sans arbre", code == 400)


# ── Démo ───────────────────────────────────────────────────────────────
def test_demo():
    app = app_neuve()
    call(app, "POST", "/api/espaces/demo")
    code, p = call(app, "GET", "/api/espace")
    verifie("démo : arbre ouvert", p["ouvert"] and p["personnes"] >= 10)
    lst = call(app, "GET", "/api/individus")[1]
    verifie("démo : liste triée par nom de famille",
            lst == sorted(lst, key=lambda r: (r["nom_famille"].lower(),
                                              r["prenoms"].lower())))
    racine = app.manifeste["racine_id"]
    fiche = call(app, "GET", "/api/individus/" + racine)[1]
    verifie("démo : racine a deux parents",
            len(fiche["peres"]) == 1 and len(fiche["meres"]) == 1)
    verifie("démo : résumé de vie généré", "né" in fiche["resume_auto"].lower())
    # la démo n'utilise QUE des familles fictives (aucune donnée réelle).
    # On vérifie que les familles fictives attendues sont présentes ; le jeu de
    # démo est fictif par construction (voir services/demo.py).
    noms = {r["nom_famille"].upper() for r in lst if r["nom_famille"]}
    verifie("démo : familles fictives connues présentes", {"MARTIN", "WHITAKER"} <= noms)


# ── Création + garde-fou ───────────────────────────────────────────────
def test_creation():
    app = app_neuve()
    call(app, "POST", "/api/espaces/creer", {"nom": "Test"})
    n0 = len(call(app, "GET", "/api/individus")[1])
    code, p = call(app, "POST", "/api/individus", {})
    verifie("saisie vide refusée", code == 400)
    verifie("saisie vide n'a rien créé",
            len(call(app, "GET", "/api/individus")[1]) == n0)
    code, p = call(app, "POST", "/api/individus", {"non_identifiee": True})
    verifie("personne non identifiée créée sur choix explicite", code == 200)
    code, p = call(app, "POST", "/api/individus",
                   {"nom": "MARTIN", "prenoms": "Léon"})
    verifie("personne nommée créée", code == 200 and p["id"])


# ── Relations ──────────────────────────────────────────────────────────
def test_relations():
    app = app_neuve()
    call(app, "POST", "/api/espaces/creer", {"nom": "Rel"})
    enfant = call(app, "POST", "/api/individus",
                  {"nom": "MARTIN", "prenoms": "Enfant"})[1]["id"]
    call(app, "POST", "/api/individus/%s/parent" % enfant,
         {"role": "pere", "champs": {"nom": "MARTIN", "prenoms": "Papa", "sexe": "M"}})
    call(app, "POST", "/api/individus/%s/parent" % enfant,
         {"role": "mere", "champs": {"nom": "DUBOIS", "prenoms": "Maman", "sexe": "F"}})
    fiche = call(app, "GET", "/api/individus/" + enfant)[1]
    verifie("relations : père rattaché", len(fiche["peres"]) == 1)
    verifie("relations : mère rattachée", len(fiche["meres"]) == 1)
    conj = call(app, "POST", "/api/individus/%s/conjoint" % enfant,
                {"champs": {"nom": "PETIT", "prenoms": "Conjoint"}})[1]["id"]
    fiche = call(app, "GET", "/api/individus/" + enfant)[1]
    verifie("relations : conjoint rattaché",
            any(u["conjoint"] and u["conjoint"]["id"] == conj for u in fiche["unions"]))


def test_parents_multiples():
    """Une personne rattachée à deux familles-parents (adoption/remariage) doit
    voir TOUS ses parents sur sa fiche (régression : famc multiple)."""
    app = app_neuve()
    call(app, "POST", "/api/espaces/creer", {"nom": "Multi"})
    enfant = call(app, "POST", "/api/individus", {"nom": "X", "prenoms": "Enfant"})[1]["id"]
    p1 = call(app, "POST", "/api/individus", {"nom": "A", "prenoms": "Père1", "sexe": "M"})[1]["id"]
    p2 = call(app, "POST", "/api/individus", {"nom": "B", "prenoms": "Père2", "sexe": "M"})[1]["id"]
    call(app, "POST", "/api/individus/%s/parent" % enfant, {"role": "pere", "id": p1})
    # forcer une seconde famille-parent (cas rare mais légal)
    base = app.base
    fam2 = base._famille_pour_couple(p2, "")
    base._placer_parent(fam2, p2)
    fam2["enfants"].append(enfant)
    base.donnees["individus"][enfant]["famc"].append(fam2["id"])
    base.sauvegarder()
    fiche = call(app, "GET", "/api/individus/" + enfant)[1]
    verifie("parents multiples : les deux pères apparaissent", len(fiche["peres"]) == 2)


# ── Sauvegarde ─────────────────────────────────────────────────────────
def test_sauvegarde():
    app = app_neuve()
    call(app, "POST", "/api/espaces/demo")
    code, p = call(app, "POST", "/api/espaces/sauvegarde")
    verifie("sauvegarde .zip créée",
            code == 200 and p["fichier"].endswith(".zip") and os.path.exists(p["chemin"]))


# ── Espace de travail ──────────────────────────────────────────────────
def test_espaces():
    app = app_neuve()
    call(app, "POST", "/api/espaces/creer", {"nom": "Arbre A"})
    call(app, "POST", "/api/espaces/demo")
    espaces = call(app, "GET", "/api/espaces")[1]["espaces"]
    verifie("espaces : deux arbres listés", len(espaces) == 2)
    demo_carte = [e for e in espaces if e["demo"]]
    verifie("espaces : la démo est marquée", len(demo_carte) == 1)
    # renommer
    chemin_a = [e for e in espaces if e["nom"] == "Arbre A"][0]["chemin"]
    call(app, "POST", "/api/espaces/renommer", {"chemin": chemin_a, "nom": "Arbre B"})
    espaces = call(app, "GET", "/api/espaces")[1]["espaces"]
    verifie("espaces : renommage pris en compte",
            any(e["nom"] == "Arbre B" for e in espaces))
    # supprimer avec archive de sécurité
    code, p = call(app, "POST", "/api/espaces/supprimer", {"chemin": chemin_a})
    verifie("espaces : suppression + archive", code == 200 and p["archive"].endswith(".zip"))
    verifie("espaces : dossier bien supprimé", not os.path.isdir(chemin_a))


# ── Sécurité ───────────────────────────────────────────────────────────
def test_securite():
    verifie("sécurité : origine externe refusée",
            securite.verifier_mutation({"Host": "127.0.0.1", "Origin": "http://mal.com"})
            == (403, "Origine externe refusée."))
    verifie("sécurité : hôte non local refusé",
            securite.verifier_mutation({"Host": "mal.com"})[0] == 403)
    verifie("sécurité : content-type non JSON refusé",
            securite.verifier_mutation({"Host": "localhost",
                                        "Content-Type": "text/html"})[0] == 415)
    verifie("sécurité : corps trop gros refusé",
            securite.verifier_mutation({"Host": "localhost",
                                        "Content-Type": "application/json",
                                        "Content-Length": str(80 * 1024 * 1024)})[0] == 413)
    verifie("sécurité : requête locale valide acceptée",
            securite.verifier_mutation({"Host": "127.0.0.1:8770",
                                        "Content-Type": "application/json",
                                        "Content-Length": "12"}) is None)


if __name__ == "__main__":
    for fn in (test_base_vide, test_demo, test_creation, test_relations,
               test_parents_multiples, test_sauvegarde, test_espaces, test_securite):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
