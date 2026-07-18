# -*- coding: utf-8 -*-
"""
Tests du Lot 4 (qualité & diffusion) : santé, carnet, plan de recherche,
réglages (clé masquée), garde-fous de l'assistant.

Exécuter :  python -X utf8 tests/test_qualite.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from services import demo, sante, recherche, carnet  # noqa: E402
import routes                                      # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def base_demo():
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    return app


def test_sante():
    app = base_demo()
    s = sante.analyser(app.base.donnees)
    verifie("santé : % prouvés calculé", 0 <= s["pct_prouves"] <= 100)
    verifie("santé : Louis (naissance acte) compté",
            s["faits_actes"] >= 1)
    verifie("santé : personnes sans source détectées",
            s["nb_personnes_sans_source"] > 0)
    verifie("santé : message encourageant présent", bool(s["humeur"]))


def test_plan():
    app = base_demo()
    p = recherche.plan(app.base.donnees, app.manifeste["racine_id"])
    verifie("plan : des pistes proposées", p["total"] > 0)
    cats = {c["nom"] for c in p["categories"]}
    verifie("plan : catégorie « Branches à remonter »",
            "Branches à remonter" in cats)
    # chaque piste dit quoi + pourquoi
    exemple = p["categories"][0]["pistes"][0]
    verifie("plan : piste avec quoi + pourquoi",
            bool(exemple["quoi"]) and bool(exemple["pourquoi"]))


def test_carnet():
    app = base_demo()
    e = carnet.ajouter(app.espace_chemin, {"type": "piste", "titre": "Chercher acte",
                                           "texte": "AD35"})
    verifie("carnet : entrée créée", e["id"].startswith("C"))
    lst = carnet.lister(app.espace_chemin, app.base.donnees)
    verifie("carnet : entrée listée", any(x["id"] == e["id"] for x in lst))
    carnet.modifier(app.espace_chemin, e["id"], {"titre": "Modifié"})
    lst = carnet.lister(app.espace_chemin)
    verifie("carnet : entrée modifiée",
            any(x["id"] == e["id"] and x["titre"] == "Modifié" for x in lst))
    carnet.supprimer(app.espace_chemin, e["id"])
    verifie("carnet : entrée supprimée",
            not any(x["id"] == e["id"] for x in carnet.lister(app.espace_chemin)))


def test_reglages_cle_masquee():
    app = base_demo()
    app.ecrire_reglages({"ia_cle": "sk-secret-abcd1234", "ia_fournisseur": "anthropic"})
    pub = app.reglages_publics()
    verifie("réglages : clé jamais renvoyée en clair", "ia_cle" not in pub)
    verifie("réglages : présence de la clé signalée", pub["cle_definie"] is True)
    verifie("réglages : aperçu = 4 derniers caractères", pub["cle_apercu"] == "…1234")
    # au repos : rien en clair sur le disque, seulement le champ chiffré
    brut = open(app._fichier_reglages, encoding="utf-8").read()
    verifie("réglages : clé absente du fichier en clair", "sk-secret-abcd1234" not in brut)
    verifie("réglages : champ chiffré présent sur disque", "ia_cle_chiffree" in brut)
    verifie("réglages : clé déchiffrable à la volée", app.cle_ia() == "sk-secret-abcd1234")
    # effacement
    app.ecrire_reglages({"ia_cle": ""})
    verifie("réglages : clé effacée", app.reglages_publics()["cle_definie"] is False)
    verifie("réglages : champ chiffré retiré après effacement",
            "ia_cle_chiffree" not in open(app._fichier_reglages, encoding="utf-8").read())


def test_reglages_migration_cle_claire():
    """Une ancienne clé en clair dans reglages.json est chiffrée à la lecture."""
    app = base_demo()
    app._sauver_reglages({"ia_cle": "sk-vieux-en-clair-9999", "ia_fournisseur": "openai"})
    r = app.lire_reglages()                          # déclenche la migration
    verifie("migration : clé en clair retirée du dict", "ia_cle" not in r)
    verifie("migration : clé désormais chiffrée", bool(r.get("ia_cle_chiffree")))
    verifie("migration : disparue du fichier en clair",
            "sk-vieux-en-clair-9999" not in open(app._fichier_reglages, encoding="utf-8").read())
    verifie("migration : clé toujours utilisable", app.cle_ia() == "sk-vieux-en-clair-9999")
    verifie("migration : autres réglages préservés", r.get("ia_fournisseur") == "openai")


def test_plan_par_depot():
    from core import modele
    d = modele.base_vide()
    d["individus"] = {
        "I1": {"id": "I1", "prenoms": "A", "nom": "X",
               "naissance": {"date": "1850", "lieu": "Marseille, Bouches-du-Rhône"}},
        "I2": {"id": "I2", "prenoms": "B", "nom": "Y",
               "naissance": {"date": "1852", "lieu": "Aix, Bouches-du-Rhône"}},
        "I3": {"id": "I3", "prenoms": "C", "nom": "Z",
               "deces": {"date": "1900", "lieu": "Napoli"}},
        "I4": {"id": "I4", "prenoms": "D", "nom": "W", "naissance": {"date": "1860"}},
    }
    r = recherche.par_depot(d)
    depots = {g["depot"]: g["nb"] for g in r["groupes"]}
    verifie("plan/dépôt : total des actes", r["total"] == 4)
    verifie("plan/dépôt : regroupement par département", depots.get("Bouches-du-Rhône") == 2)
    verifie("plan/dépôt : dépôt distinct séparé", depots.get("Napoli") == 1)
    verifie("plan/dépôt : sans lieu en dernier",
            r["groupes"][-1]["depot"] == "Lieu non précisé")


def test_assistant_garde_fou():
    app = base_demo()

    def call(m, c, corps=None):
        return routes.dispatch(app, m, c, {}, corps or {})
    code, p = call("POST", "/api/assistant/mission", {"type": "biographie"})
    verifie("assistant : refuse sans clé (400)", code == 400)


if __name__ == "__main__":
    for fn in (test_sante, test_plan, test_plan_par_depot, test_carnet,
               test_reglages_cle_masquee, test_reglages_migration_cle_claire,
               test_assistant_garde_fou):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
