# -*- coding: utf-8 -*-
"""Nomenclature des sources : titre suggéré et nom de scan triable.

Le titre DÉCRIT (il se lit), le nom de fichier NOMME (il se trie). Les deux se
déduisent de ce que l'utilisateur a déjà saisi, pour qu'il n'ait pas à inventer
« acte naissance 2 ».

Exécuter :  python -X utf8 tests/test_nomenclature.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from services import nomenclature as nm           # noqa: E402
import routes                                     # noqa: E402

routes.charger_modules()
_ok = _ko = 0

JEAN = {"nom": "DUPONT", "prenoms": "Jean Baptiste"}
MARIE = {"nom": "Lefèvre", "prenoms": "Marie"}


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def egal(nom, obtenu, attendu):
    verifie("%s  (%r)" % (nom, obtenu), obtenu == attendu)


def call(app, m, c, corps=None, params=None):
    return routes.dispatch(app, m, c, params or {}, corps or {})


# ── Dates ────────────────────────────────────────────────────────────────
def test_date_iso():
    egal("jour GEDCOM", nm.date_iso("12 MAR 1902"), "1902-03-12")
    egal("jour slash", nm.date_iso("12/03/1902"), "1902-03-12")
    egal("déjà ISO", nm.date_iso("1902-03-12"), "1902-03-12")
    egal("mois seul", nm.date_iso("MAR 1902"), "1902-03")
    egal("année seule", nm.date_iso("1902"), "1902")
    egal("approximative : on garde l'année", nm.date_iso("ABT 1902"), "1902")
    egal("vide", nm.date_iso(""), "")
    egal("incompréhensible", nm.date_iso("un jour de pluie"), "")


# ── Titre ────────────────────────────────────────────────────────────────
def test_titre_complet():
    egal("titre complet",
         nm.titre_suggere("Acte de naissance", [JEAN], "12/03/1902", "Lyon, Rhône"),
         "Acte de naissance — Jean Baptiste DUPONT — 12/03/1902 — Lyon, Rhône")


def test_titre_deux_personnes_et_plus():
    egal("un mariage : deux noms",
         nm.titre_suggere("Acte de mariage", [JEAN, MARIE], "1925", "Lyon"),
         "Acte de mariage — Jean Baptiste DUPONT & Marie LEFÈVRE — 1925 — Lyon")
    t = nm.titre_suggere("Recensement", [JEAN, MARIE, JEAN, MARIE], "1926", "Lyon")
    verifie("au-delà de deux, on résume (le titre reste lisible)",
            "et 2 autres" in t and t.count("&") == 0)


def test_titre_partiel_pas_de_tirets_orphelins():
    egal("type seul", nm.titre_suggere("Acte de décès"), "Acte de décès")
    egal("sans type : « Source »", nm.titre_suggere("", [], "1902", ""), "Source — 1902")
    egal("sans personne", nm.titre_suggere("Recensement", [], "1926", "Lyon"),
         "Recensement — 1926 — Lyon")
    egal("rien du tout", nm.titre_suggere(), "Source")


# ── Nom de fichier ───────────────────────────────────────────────────────
def test_nom_fichier():
    egal("nom triable",
         nm.nom_fichier("IMG_4521.JPG", "Acte de naissance", [JEAN],
                        "12 MAR 1902", "Lyon, Rhône"),
         "1902-03-12_N_DUPONT-Jean_Lyon.jpg")
    egal("accents et espaces gommés",
         nm.nom_fichier("s.jpg", "Acte de décès", [MARIE], "1930", "Saint-Étienne, Loire"),
         "1930_D_LEFEVRE-Marie_Saint-Etienne.jpg")
    egal("mariage : les deux époux",
         nm.nom_fichier("s.pdf", "Acte de mariage", [JEAN, MARIE], "1925", "Lyon"),
         "1925_M_DUPONT-Jean-et-LEFEVRE-Marie_Lyon.pdf")


def test_nom_fichier_extension_et_vide():
    egal("l'extension d'origine est conservée (minuscule)",
         nm.nom_fichier("Scan.TIFF", "Recensement", [], "1926", "Lyon"),
         "1926_REC_Lyon.tiff")
    egal("rien de connu : on garde le nom d'origine",
         nm.nom_fichier("IMG_4521.jpg"), "IMG_4521.jpg")


def test_nom_fichier_collisions():
    egal("un fichier du même nom existe déjà : suffixe",
         nm.nom_fichier("a.jpg", "Acte de naissance", [JEAN], "1902", "Lyon",
                        existants=["1902_N_DUPONT-Jean_Lyon.jpg"]),
         "1902_N_DUPONT-Jean_Lyon-2.jpg")
    a = nm.apercu("Acte de naissance", [JEAN], "1902", "Lyon",
                  fichiers=["recto.jpg", "verso.jpg"])
    noms = [f["propose"] for f in a["fichiers"]]
    egal("deux vues du même acte : _1 et _2",
         noms, ["1902_N_DUPONT-Jean_Lyon_1.jpg", "1902_N_DUPONT-Jean_Lyon_2.jpg"])
    verifie("l'aperçu rappelle le nom d'origine",
            a["fichiers"][0]["origine"] == "recto.jpg")


def test_nom_fichier_sans_caractere_interdit():
    n = nm.nom_fichier("a.jpg", "Presse / article", [], "1902", "Lyon")
    verifie("aucun caractère interdit par Windows dans %r" % n,
            not any(c in n for c in '\\/:*?"<>|'))


# ── Route ────────────────────────────────────────────────────────────────
def test_route_nomenclature():
    app = Application(tempfile.mkdtemp())
    call(app, "POST", "/api/espaces/creer", {"nom": "P"})
    pid = call(app, "POST", "/api/individus",
               {"nom": "DUPONT", "prenoms": "Jean Baptiste", "sexe": "M"})[1]["id"]
    code, r = call(app, "POST", "/api/nomenclature",
                   {"type": "Acte de naissance", "personnes": [pid],
                    "date": "12 MAR 1902", "lieu": "Lyon, Rhône",
                    "fichiers": ["IMG_4521.JPG"]})
    verifie("/api/nomenclature : 200", code == 200)
    # Le titre reprend la date TELLE QUE SAISIE ; seul le fichier la normalise.
    egal("titre proposé", r["titre"],
         "Acte de naissance — Jean Baptiste DUPONT — 12 MAR 1902 — Lyon, Rhône")
    egal("fichier proposé", r["fichiers"][0]["propose"],
         "1902-03-12_N_DUPONT-Jean_Lyon.jpg")


def test_route_personne_inconnue_ne_casse_rien():
    app = Application(tempfile.mkdtemp())
    call(app, "POST", "/api/espaces/creer", {"nom": "P"})
    code, r = call(app, "POST", "/api/nomenclature",
                   {"type": "Recensement", "personnes": ["IZZZ"],
                    "date": "1926", "lieu": "Lyon", "fichiers": []})
    verifie("une personne inconnue est ignorée, pas une erreur", code == 200)
    egal("titre sans personne", r["titre"], "Recensement — 1926 — Lyon")


if __name__ == "__main__":
    for t in (test_date_iso, test_titre_complet, test_titre_deux_personnes_et_plus,
              test_titre_partiel_pas_de_tirets_orphelins, test_nom_fichier,
              test_nom_fichier_extension_et_vide, test_nom_fichier_collisions,
              test_nom_fichier_sans_caractere_interdit,
              test_route_nomenclature, test_route_personne_inconnue_ne_casse_rien):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
