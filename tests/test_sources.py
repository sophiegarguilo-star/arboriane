# -*- coding: utf-8 -*-
"""
Tests du Lot 3 (sources & diffusion) : sources CRUD, citations & niveaux de
preuve, upload média, publication (vivants masqués), GEDZIP, lieux.

Exécuter :  python -X utf8 tests/test_sources.py
"""

import base64
import os
import sys
import tempfile
import zipfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from core import modele                            # noqa: E402
from services import demo, sources, publication, lieux  # noqa: E402

_ok = _ko = 0
_PNG = ("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d4944415478da6360000002000154a24f6f0000000049454e44ae426082")


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


def id_prenom(d, p):
    return next(pid for pid, i in d["individus"].items() if p in i.get("prenoms", ""))


def test_sources_crud():
    app = base_demo()
    base = app.base
    n0 = len(base.donnees["sources"])
    src = base.creer_source({"titre": "Test acte", "type": "Acte", "fiabilite": "haute"})
    verifie("source créée", len(base.donnees["sources"]) == n0 + 1)
    base.modifier_source(src["id"], {"statut": "RETENU"})
    verifie("source modifiée",
            base.donnees["sources"][src["id"]]["statut"] == "RETENU")
    lst = sources.lister(base.donnees)
    verifie("source listée avec résumé", any(s["id"] == src["id"] for s in lst))
    base.supprimer_source(src["id"])
    verifie("source supprimée", src["id"] not in base.donnees["sources"])


def test_preuves():
    app = base_demo()
    d = app.base.donnees
    lucie = id_prenom(d, "Lucie")
    pv = sources.preuves_personne(d, lucie)
    naiss = next(f for f in pv["faits"] if f["fait"] == "naissance")
    verifie("preuve : naissance de Lucie prouvée par acte (QUAY3)",
            naiss["niveau"] == "acte")
    # ajouter une preuve déclarée sur le décès d'une personne
    src = app.base.creer_source({"titre": "Faire-part"})["id"]
    app.base.citer(lucie, "deces", {"source": src, "quay": 2})
    pv2 = sources.preuves_personne(d, lucie)
    dec = next(f for f in pv2["faits"] if f["fait"] == "deces")
    verifie("preuve : décès devient déclaré", dec["niveau"] == "declare")


def test_media():
    app = base_demo()
    nom = app.enregistrer_media("Sources", "acte.png", base64.b64encode(
        bytes.fromhex(_PNG)).decode())
    verifie("média enregistré et lisible", bool(app.chemin_media("Sources", nom)))
    # ne jamais écraser : un second fichier de même nom obtient un nom distinct
    nom2 = app.enregistrer_media("Sources", "acte.png", base64.b64encode(
        bytes.fromhex(_PNG)).decode())
    verifie("média : pas d'écrasement (nom unique)", nom != nom2)


def test_publication():
    app = base_demo()
    d = app.base.donnees
    avant = len(d["individus"])
    ap = publication.apercu_masques(d)
    verifie("publication : des vivants sont détectés", len(ap) > 0)
    # Lucie (2006) présumée vivante → masquée ; Thomas (1898-1969) → visible
    noms_masques = {m["nom"] for m in ap}
    verifie("publication : présumé vivant (Lucie) masqué",
            any("Lucie" in n for n in noms_masques))
    verifie("publication : ancêtre décédé (Thomas) non masqué",
            not any("Thomas" in n for n in noms_masques))
    publication.preparer(d, {})          # ne doit jamais toucher la base d'origine
    verifie("publication : base d'origine intacte", len(d["individus"]) == avant)


def test_gedzip():
    app = base_demo()
    chemin = publication.exporter_gedzip(app)
    verifie("gedzip : fichier .gdz créé", chemin.endswith(".gdz") and os.path.exists(chemin))
    with zipfile.ZipFile(chemin) as z:
        noms = z.namelist()
    verifie("gedzip : contient un GEDCOM", any(n.endswith(".ged") for n in noms))


def test_cadrage_photo_conserve():
    # Le cadrage carré (non destructif, « x% y% ») doit survivre à un enregistrement
    # de la galerie — sinon le portrait se recentre tout seul à chaque sauvegarde.
    app = base_demo()
    pid = next(iter(app.base.donnees["individus"]))
    app.base.definir_medias(pid, [{"fichier": "p.jpg", "principale": True, "cadrage": "30% 20%"}])
    m = app.base.donnees["individus"][pid]["medias"][0]
    verifie("cadrage conservé", m.get("cadrage") == "30% 20%")
    app.base.definir_medias(pid, [{"fichier": "q.jpg", "principale": True}])
    verifie("pas de clé cadrage si absent", "cadrage" not in app.base.donnees["individus"][pid]["medias"][0])


def test_apercu_saute_les_pdf():
    # La vignette d'une source (côté fiche) est une <img> : un PDF y resterait
    # blanc. L'aperçu doit donc pointer sur la 1re IMAGE, jamais sur un PDF.
    from services import sources as src_svc
    d = {"individus": {"I1": {"id": "I1", "citations": [
             {"source": "S1", "quay": 3}, {"source": "S2", "quay": 3}]}},
         "familles": {}, "lieux": {}, "sources": {
             "S1": {"id": "S1", "titre": "Livret", "fichiers": ["livret.pdf"]},
             "S2": {"id": "S2", "titre": "Acte", "fichiers": ["acte.jpg", "annexe.pdf"]}}}
    parid = {s["id"]: s for s in src_svc.sources_de_personne(d, "I1")}
    verifie("aperçu : PDF seul -> pas de vignette image", parid["S1"]["apercu"] == "")
    verifie("aperçu : image + PDF -> l'image", parid["S2"]["apercu"] == "acte.jpg")


def test_lieux():
    app = base_demo()
    r = lieux.lister(app.base.donnees)
    verifie("lieux : lieux distincts listés", r["nb"] >= 2)
    # La démo pré-géocode une partie des lieux (la carte s'affiche hors-ligne).
    verifie("lieux : la démo en pré-géocode certains",
            0 <= r["nb_a_geocoder"] < r["nb"])


if __name__ == "__main__":
    for fn in (test_sources_crud, test_preuves, test_media, test_publication,
               test_gedzip, test_cadrage_photo_conserve, test_apercu_saute_les_pdf, test_lieux):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
