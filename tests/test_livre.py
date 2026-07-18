# -*- coding: utf-8 -*-
"""
Test du Lot L10 — Jalon 1 (livres biographiques).

Exécuter :  python -X utf8 tests/test_livre.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core.application import Application            # noqa: E402
from services import demo                           # noqa: E402
from services.livre import composeur, recit, rendu_html   # noqa: E402
from services import personnes                       # noqa: E402
import routes                                        # noqa: E402

routes.charger_modules()

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _app():
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer, version=demo.VERSION)
    return app


def test_composeur_crud():
    app = _app()
    ref = app.manifeste.get("racine_id")
    verifie("démo : référent (racine) présent", bool(ref))
    livre = composeur.creer(app.espace_chemin, app.base.donnees, ref)
    verifie("créer : id + titre auto", livre["id"] and livre["titre"])
    verifie("créer : 11 sections", len(livre["sections"]) == 11)
    asc = next((s for s in livre["sections"] if s["type"] == "ascendance"), None)
    verifie("créer : section aïeux avec profondeur", asc and asc.get("generations") == 4)
    verifie("créer : mise en page par défaut A4",
            livre["mise_en_page"]["format"] == "a4")
    liste = composeur.lister(app.espace_chemin, app.base.donnees)
    verifie("lister : le livre apparaît", any(l["id"] == livre["id"] for l in liste))
    # modification persistée
    livre["mise_en_page"]["format"] = "a5"
    composeur.enregistrer(app.espace_chemin, livre)
    relu = composeur.lire(app.espace_chemin, livre["id"])
    verifie("enregistrer : format A5 persisté", relu["mise_en_page"]["format"] == "a5")
    composeur.supprimer(app.espace_chemin, livre["id"])
    verifie("supprimer : plus dans la liste",
            not composeur.lister(app.espace_chemin))


def test_recit_et_rendu():
    app = _app()
    inds = app.base.donnees["individus"]
    # une personne DÉCÉDÉE de la démo (pour un récit complet naissance→décès)
    ref = next((pid for pid, i in inds.items()
                if (i.get("deces") or {}).get("date")), app.manifeste.get("racine_id"))
    f = personnes.fiche(app.base, ref)
    paras = recit.biographie(app.base, f, masquer=True)
    verifie("récit : au moins un paragraphe", len(paras) >= 1)
    verifie("récit : commence par le nom", paras[0].startswith(f["nom_complet"][:4]))

    livre = composeur.creer(app.espace_chemin, app.base.donnees, ref)
    html = rendu_html.rendre(app.base, livre)
    verifie("rendu : document HTML complet", html.lstrip().startswith("<!doctype html"))
    verifie("rendu : titre du livre présent", livre["titre"] in html)
    verifie("rendu : chapitre Biographie", 'id="biographie"' in html)
    verifie("rendu : sommaire cliquable", 'href="#biographie"' in html)
    verifie("rendu : format A4 dans @page", "size:A4" in html)

    # A5 change la taille de page
    livre["mise_en_page"]["format"] = "a5"
    html5 = rendu_html.rendre(app.base, livre)
    verifie("rendu : format A5 pris en compte", "size:A5" in html5)

    # — Palier A : sections de texte libre & chapitres personnels —
    ded = composeur.nouvelle_section("dedicace"); ded["texte"] = "À ma famille."
    chap = composeur.nouvelle_section("chapitre", "Le hameau")
    chap["texte"] = "Un lieu de mémoire.\nOn y vivait simplement."
    vide = composeur.nouvelle_section("introduction")     # sans texte -> ignorée
    livre["sections"] = [livre["sections"][0], ded, chap, vide] + livre["sections"][1:]
    hA = rendu_html.rendre(app.base, livre)
    verifie("Palier A : clé unique par chapitre", ded["cle"] != chap["cle"])
    verifie("Palier A : dédicace rendue & stylée", 'class="page dedicace"' in hA and "À ma famille." in hA)
    verifie("Palier A : chapitre titre + texte", "Le hameau" in hA and "Un lieu de mémoire." in hA)
    verifie("Palier A : chapitre au sommaire", "Le hameau</a>" in hA)
    verifie("Palier A : section de texte vide ignorée", "Introduction" not in hA)
    # persistance de l'ordre & des sections ajoutées
    composeur.enregistrer(app.espace_chemin, livre)
    relu = composeur.lire(app.espace_chemin, livre["id"])
    verifie("Palier A : sections perso persistées",
            any(s.get("cle") == chap["cle"] for s in relu["sections"]))

    # écrit un aperçu visible pour Sophie
    dest = os.path.join(tempfile.gettempdir(), "apercu_livre_arboriane.html")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("     → aperçu écrit : %s" % dest)


def test_livret_ascendance():
    """Palier D : livret d'ascendance complète, un chapitre par couple."""
    from core import gedcom
    from services.livre import livret_ascendance
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "Asc"})
    src = ("0 HEAD\n1 CHAR UTF-8\n"
           "0 @I1@ INDI\n1 NAME Enfant /Test/\n1 SEX M\n1 BIRT\n2 DATE 1900\n1 FAMC @F1@\n"
           "0 @I2@ INDI\n1 NAME Pierre /Test/\n1 SEX M\n1 BIRT\n2 DATE 1870\n1 FAMS @F1@\n"
           "0 @I3@ INDI\n1 NAME Marie /Durand/\n1 SEX F\n1 BIRT\n2 DATE 1872\n1 FAMS @F1@\n"
           "0 @F1@ FAM\n1 HUSB @I2@\n1 WIFE @I3@\n1 CHIL @I1@\n1 MARR\n2 DATE 1895\n0 TRLR\n")
    app.base.remplacer(gedcom.importer(src))
    parties = livret_ascendance.chapitres(app.base, "I1", 3, masquer=False)
    verifie("ascendance : 2 parties (référent + parents)", len(parties) == 2)
    verifie("ascendance : génération 0 = référent", parties[0]["generation"] == 0)
    couple = parties[1]["chapitres"][0]
    verifie("ascendance : chapitre-couple des parents",
            "Pierre Test" in couple["titre"] and "Marie Durand" in couple["titre"])
    verifie("ascendance : renvoi vers l'enfant", "Enfant Test" in (couple["renvoi"] or ""))
    livre = composeur.creer(app.espace_chemin, app.base.donnees, "I1", "", "ascendance")
    verifie("ascendance : type stocké", livre.get("type") == "ascendance")
    html = rendu_html.rendre(app.base, livre)
    verifie("ascendance : rendu avec chapitres-couples", 'class="page chap"' in html)
    verifie("ascendance : partie par génération", 'class="page partie"' in html)


if __name__ == "__main__":
    test_composeur_crud()
    test_recit_et_rendu()
    test_livret_ascendance()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
