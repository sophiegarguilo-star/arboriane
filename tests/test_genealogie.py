# -*- coding: utf-8 -*-
"""
Tests du Lot 2 (généalogie) : GEDCOM aller-retour, Sosa, parenté (sang +
alliance + vocabulaire), cohérence, statistiques, rendu d'arbre.

Exécuter :  python -X utf8 tests/test_genealogie.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from core import gedcom, modele                   # noqa: E402
from services import demo, sosa, parente, coherence, statistiques, arbre  # noqa: E402

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


def id_par_prenom(d, prenom):
    for pid, i in d["individus"].items():
        if prenom in i.get("prenoms", ""):
            return pid
    return None


def test_gedcom():
    app = base_demo()
    d = app.base.donnees
    txt = gedcom.exporter(d)
    verifie("gedcom : entête + TRLR",
            txt.startswith("0 HEAD") and txt.rstrip().endswith("0 TRLR"))
    verifie("gedcom : CHAR UTF-8", "1 CHAR UTF-8" in txt)
    d2 = gedcom.importer(txt)
    verifie("gedcom : nb individus conservé",
            len(d2["individus"]) == len(d["individus"]))
    verifie("gedcom : nb familles conservé",
            len(d2["familles"]) == len(d["familles"]))
    noms1 = sorted(modele.nom_complet(i) for i in d["individus"].values())
    noms2 = sorted(modele.nom_complet(i) for i in d2["individus"].values())
    verifie("gedcom : noms identiques après aller-retour", noms1 == noms2)


def test_sosa():
    app = base_demo()
    dc = app.manifeste["racine_id"]
    s = sosa.ascendance(app.base.donnees, dc, 5)
    verifie("sosa : génération 1 = 2 parents", s["generations"][1]["connus"] == 2)
    verifie("sosa : ruptures détectées", len(s["ruptures"]) > 0)


def test_parente():
    app = base_demo()
    d = app.base.donnees
    dc = app.manifeste["racine_id"]
    michel = id_par_prenom(d, "Michel")      # grand-père paternel (Sosa 4)
    tom = id_par_prenom(d, "Tom")            # frère (racine = Lucie)
    edith = id_par_prenom(d, "Edith")        # arrière-grand-mère (Sosa 9, anglaise)
    lp = parente.lien_complet(d, dc, michel)
    verifie("parenté : grand-père", lp and "grand-père" in lp["lien"])
    lm = parente.lien_complet(d, dc, tom)
    verifie("parenté : frère/sœur", lm and lm["lien"] in ("le frère", "la sœur"))
    lh = parente.lien_complet(d, dc, edith)
    verifie("parenté : arrière-grand-mère", lh and "arrière-grand-mère" in lh["lien"])


def test_coherence():
    app = base_demo()
    d = app.base.donnees
    c = coherence.analyser(d)
    # La démo porte des incohérences VOLONTAIRES, toutes confinées à la famille
    # « TESTUS » (cas de test clairement identifiés).
    testus = {pid for pid, i in d["individus"].items() if i.get("nom") == "TESTUS"}
    def _touche_testus(a):
        return a.get("personne") in testus or "TESTUS" in (a.get("personne_nom") or "")
    hautes = [a for a in c["alertes"] if a.get("gravite") == "haute"]
    verifie("cohérence : les incohérences volontaires sont détectées", len(hautes) >= 1)
    verifie("cohérence : anomalies confinées aux cas de test (TESTUS)",
            all(_touche_testus(a) for a in hautes))
    verifie("cohérence : décès avant naissance repéré (TESTUS)",
            any(a.get("type") == "deces_avant_naissance" for a in c["alertes"]))


def test_stats():
    app = base_demo()
    st = statistiques.calculer(app.base.donnees)
    verifie("stats : total cohérent",
            st["personnes"] == len(app.base.donnees["individus"]) and st["personnes"] >= 80)
    verifie("stats : complétude naissance 100 %",
            st["completude"]["date_naissance"] == 100)
    verifie("stats : siècles renseignés", len(st["par_siecle"]) >= 1)


def test_arbre():
    app = base_demo()
    dc = app.manifeste["racine_id"]
    for mode in ("eventail", "ascendance", "descendance"):
        svg = arbre.rendre(app.base.donnees, dc, mode)
        verifie("arbre : %s produit du SVG" % mode,
                svg.lstrip().startswith("<svg") and svg.rstrip().endswith("</svg>"))


if __name__ == "__main__":
    for fn in (test_gedcom, test_sosa, test_parente, test_coherence,
               test_stats, test_arbre):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
