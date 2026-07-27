# -*- coding: utf-8 -*-
"""« Ranger les pièces » : renommer les scans selon la nomenclature triable, en
gardant les citations intactes. Deux niveaux :
  1) le PLAN (nommage) — la date employée est celle de l'ÉVÉNEMENT (naissance),
     pas la date de l'acte ;
  2) l'APPLICATION — le fichier est bien renommé sur le disque ET la source qui
     le cite pointe vers le nouveau nom (le lien source ↔ scan ne casse pas).

Exécuter :  python -X utf8 tests/test_rangement.py
"""
import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from services import nomenclature as nm, demo          # noqa: E402
from core.application import Application               # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_plan_utilise_la_date_de_l_evenement():
    donnees = {
        "individus": {"I1": {"id": "I1", "nom": "GARGUILO", "prenoms": "Sophie",
                             "naissance": {"date": "20/07/1984"}}},
        "familles": {},
        "sources": {"S1": {"id": "S1", "type": "Acte de naissance",
                           "date": "21/07/1984",     # l'acte a été DRESSÉ le 21
                           "lieu": "Marseille, Bouches-du-Rhône, France",
                           "fichiers": ["Acte de naissance Sophie GARGUILO.jpg"],
                           "personnes": [{"id": "I1", "role": "sujet"}]}},
    }
    # la date de l'événement (naissance) prime sur la date de l'acte
    verifie("date événement = naissance (20/07), pas l'acte (21/07)",
            nm._date_evenement(donnees, donnees["sources"]["S1"]) == "20/07/1984")
    items = nm.plan(donnees)
    verifie("plan : 1 pièce à ranger", len(items) == 1)
    if items:
        verifie("nom proposé = 1984-07-20_N_GARGUILO-Sophie_Marseille.jpg",
                items[0]["vers"] == "1984-07-20_N_GARGUILO-Sophie_Marseille.jpg")
    # un fichier déjà conforme n'est pas reproposé
    donnees["sources"]["S1"]["fichiers"] = ["1984-07-20_N_GARGUILO-Sophie_Marseille.jpg"]
    verifie("un fichier déjà bien nommé n'est pas listé", nm.plan(donnees) == [])


def test_nom_ignore_les_personnes_citees():
    # Sur l'acte de naissance de Sophie, un ex-conjoint est cité en marge
    # (rôle « cité ») : il ne doit PAS entrer dans le nom du fichier.
    donnees = {
        "individus": {
            "I1": {"id": "I1", "nom": "GARGUILO", "prenoms": "Sophie",
                   "naissance": {"date": "20/07/1984"}},
            "I4": {"id": "I4", "nom": "CHETNIK", "prenoms": "Marcin"}},
        "familles": {},
        "sources": {"S1": {"id": "S1", "type": "Acte de naissance",
                           "date": "20/07/1984", "lieu": "Marseille",
                           "fichiers": ["scan.jpg"],
                           "personnes": [{"id": "I1", "role": "sujet"},
                                         {"id": "I4", "role": "cité"}]}},
    }
    items = nm.plan(donnees)
    verifie("le nom n'utilise que le sujet (pas le cité)",
            items and items[0]["vers"] == "1984-07-20_N_GARGUILO-Sophie_Marseille.jpg")
    # Repli sans rôle : deux personnes sans rôle -> les deux (comportement d'avant)
    for p in donnees["sources"]["S1"]["personnes"]:
        p["role"] = ""
    donnees["sources"]["S1"]["fichiers"] = ["scan.jpg"]
    v = nm.plan(donnees)[0]["vers"]
    verifie("sans rôle renseigné : repli sur toutes les personnes (%s)" % v,
            "GARGUILO-Sophie" in v and "CHETNIK-Marcin" in v)


def test_application_renomme_et_garde_la_citation():
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    base = app.base
    pid = base.creer_individu({"nom": "GARGUILO", "prenoms": "Sophie",
                               "naissance": {"date": "20/07/1984",
                                             "lieu": "Marseille, Bouches-du-Rhône, France"}})["id"]
    # un vrai fichier dans Sources/
    srcdir = os.path.join(app.espace_chemin, "Sources")
    os.makedirs(srcdir, exist_ok=True)
    with open(os.path.join(srcdir, "vieux nom.jpg"), "wb") as f:
        f.write(b"fake-scan")
    sid = base.creer_source({"type": "Acte de naissance", "date": "21/07/1984",
                             "lieu": "Marseille, Bouches-du-Rhône, France",
                             "fichiers": ["vieux nom.jpg"],
                             "personnes": [{"id": pid, "role": "sujet"}]})["id"]

    # on ne range QUE notre pièce (l'arbre de démo a ses propres scans)
    items = [it for it in nm.plan(base.donnees) if it["de"] == "vieux nom.jpg"]
    rapport = app.ranger_pieces(items)

    nouveau = "1984-07-20_N_GARGUILO-Sophie_Marseille.jpg"
    verifie("rapport : 1 renommé, 0 ignoré",
            len(rapport["renommes"]) == 1 and not rapport["ignores"])
    verifie("fichier renommé sur le disque",
            os.path.isfile(os.path.join(srcdir, nouveau))
            and not os.path.exists(os.path.join(srcdir, "vieux nom.jpg")))
    verifie("la citation pointe vers le NOUVEAU nom (lien intact)",
            base.donnees["sources"][sid]["fichiers"] == [nouveau])
    verifie("plus aucune référence à l'ancien nom",
            "vieux nom.jpg" not in base.donnees["sources"][sid]["fichiers"])


if __name__ == "__main__":
    for fn in (test_plan_utilise_la_date_de_l_evenement,
               test_nom_ignore_les_personnes_citees,
               test_application_renomme_et_garde_la_citation):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
