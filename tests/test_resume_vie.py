# -*- coding: utf-8 -*-
"""Résumé de vie auto-généré : il ne doit JAMAIS appeler « marié·e » une union
qui n'est qu'un PACS (bug relevé en usage réel : un PACS s'affichait « mariée
avec … »). On distingue mariage / PACS / union libre.

Exécuter :  python -X utf8 tests/test_resume_vie.py
"""
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from services.personnes import resume_de_vie          # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


class BaseFactice:
    """resume_de_vie ne lit que base.donnees (+ des fonctions pures de modele)."""
    def __init__(self, donnees):
        self.donnees = donnees


def _base_sophie():
    inds = {
        "I1": {"id": "I1", "sexe": "F", "prenoms": "Sophie", "nom": "GARGUILO",
               "naissance": {"date": "20/07/1984", "lieu": "Marseille 8e"},
               "deces": {}, "fams": ["F2", "F3", "F4"]},
        "M": {"id": "M", "sexe": "M", "prenoms": "Marcin", "nom": "CHETNIK"},
        "D": {"id": "D", "sexe": "M", "prenoms": "Damien", "nom": "JACKY"},
        "S": {"id": "S", "sexe": "M", "prenoms": "Sébastien", "nom": "MIETTE"},
    }
    fams = {
        "F2": {"id": "F2", "epouse": "I1", "mari": "M", "enfants": [],
               "mariage": {"date": "", "lieu": ""},
               "evenements": [{"type": "EVEN", "precision": "PACS", "date": "04/06/2007"},
                              {"type": "EVEN", "precision": "Dissolution de PACS", "date": "15/04/2010"}]},
        "F3": {"id": "F3", "epouse": "I1", "mari": "D", "enfants": [],
               "mariage": {"date": "19/12/2016", "lieu": "Belcodène"},
               "evenements": [{"type": "EVEN", "precision": "PACS", "date": "02/07/2012"},
                              {"type": "DIV", "date": "20/04/2022"}]},
        "F4": {"id": "F4", "epouse": "I1", "mari": "S", "enfants": [],
               "mariage": {"date": "", "lieu": ""},
               "evenements": [{"type": "EVEN", "precision": "PACS", "date": "29/08/2022"}]},
    }
    return BaseFactice({"individus": inds, "familles": fams})


def test_pacs_pas_confondu_avec_mariage():
    base = _base_sophie()
    r = resume_de_vie(base, base.donnees["individus"]["I1"])
    print("    résumé =", r)
    # PACS (Marcin, Sébastien) -> « pacsée », JAMAIS « mariée »
    verifie("PACS Marcin -> pacsée", "pacsée en 2007 avec Marcin" in r)
    verifie("PACS Sébastien -> pacsée", "pacsée en 2022 avec Sébastien" in r)
    verifie("un PACS n'est jamais dit « mariée »", "mariée avec Marcin" not in r
            and "mariée en 2007" not in r and "mariée en 2022" not in r)
    # Mariage (Damien) -> « mariée », avec lieu et divorce
    verifie("mariage Damien -> mariée en 2016 à Belcodène",
            "mariée en 2016 à Belcodène avec Damien" in r)
    verifie("divorce -> divorcée en 2022", "divorcée en 2022" in r)


def test_accord_masculin():
    """Un homme pacsé -> « pacsé » (sans e)."""
    inds = {"H": {"id": "H", "sexe": "M", "prenoms": "Léo", "nom": "T",
                  "naissance": {}, "deces": {}, "fams": ["F"]},
            "A": {"id": "A", "sexe": "F", "prenoms": "Ana", "nom": "B"}}
    fams = {"F": {"id": "F", "mari": "H", "epouse": "A", "enfants": [],
                  "mariage": {"date": "", "lieu": ""},
                  "evenements": [{"type": "EVEN", "precision": "PACS", "date": "2010"}]}}
    r = resume_de_vie(BaseFactice({"individus": inds, "familles": fams}), inds["H"])
    print("    résumé =", r)
    verifie("homme pacsé -> « pacsé … avec Ana »", "pacsé en 2010 avec Ana" in r)
    verifie("pas de « pacsée » pour un homme", "pacsée" not in r)


if __name__ == "__main__":
    for fn in (test_pacs_pas_confondu_avec_mariage, test_accord_masculin):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
