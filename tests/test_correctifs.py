# -*- coding: utf-8 -*-
"""Tests de non-régression des correctifs issus de l'audit complet (2026-07).
Chaque test verrouille un défaut trouvé par les agents d'audit."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import espace as em, gedcom
from core.application import Application
from services import demo, parente, sosa
import routes

routes.charger_modules()

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1
    else:
        _ko += 1
        print("  FAIL", nom)


def _demo():
    d = tempfile.mkdtemp()
    em.creer(d, "T")
    base = demo.generer(d)
    return d, base


# ── GEDCOM : champs source (fiabilité/statut/page/ville/pays) ──────────────
def test_gedcom_champs_source():
    _, base = _demo()
    sid = base.creer_source({"titre": "Acte test", "fiabilite": "haute",
                             "statut": "RETENU", "page": "acte 42",
                             "ville": "Tours", "pays": "France"})["id"]
    d2 = gedcom.importer(gedcom.exporter(base.donnees))
    s = d2["sources"].get(sid, {})
    verifie("gedcom : fiabilité conservée", s.get("fiabilite") == "haute")
    verifie("gedcom : statut conservé", s.get("statut") == "RETENU")
    verifie("gedcom : page conservée", s.get("page") == "acte 42")
    verifie("gedcom : ville conservée", s.get("ville") == "Tours")
    verifie("gedcom : pays conservé", s.get("pays") == "France")


# ── GEDCOM : événement privé _XXXX préservé (ex. _MILT) ────────────────────
def test_gedcom_evenement_prive():
    _, base = _demo()
    pid = next(iter(base.donnees["individus"]))
    base.modifier_individu(pid, {"evenements": [
        {"type": "_MILT", "date": "1915", "lieu": "Verdun", "valeur": "127e RI"}]})
    d2 = gedcom.importer(gedcom.exporter(base.donnees))
    evs = d2["individus"][pid].get("evenements", [])
    milt = [e for e in evs if e.get("type") == "_MILT"]
    verifie("gedcom : événement privé _MILT conservé", len(milt) == 1)
    verifie("gedcom : valeur de l'événement privé conservée",
            milt and milt[0].get("valeur") == "127e RI")


# ── stockage : suppression source nettoie AUSSI les résidences ─────────────
def test_suppr_source_residence():
    _, base = _demo()
    pid = next(iter(base.donnees["individus"]))
    sid = base.creer_source({"titre": "src résidence"})["id"]
    base.modifier_individu(pid, {"residences": [
        {"date": "1900", "lieu": "Tours", "citations": [{"source": sid, "quay": 2}]}]})
    base.supprimer_source(sid)
    res = base.donnees["individus"][pid]["residences"][0]
    orphelines = [c for c in (res.get("citations") or []) if c.get("source") == sid]
    verifie("suppr source : 0 citation orpheline sur la résidence", not orphelines)


# ── parenté : vocabulaire des aïeux correct et cohérent avec Sosa ──────────
def test_parente_aieux():
    d, base = _demo()
    don = base.donnees
    racine = em.charger(d)["racine_id"]
    # Sosa 8 = arrière-grand-père (gen 3), Sosa 16 = trisaïeul (gen 4)
    par_sosa = sosa.ascendance_sosa(don, racine)   # {numéro Sosa: pid}
    ggp = par_sosa.get(8)
    tgp = par_sosa.get(16)
    l_ggp = parente.lien_complet(don, racine, ggp).get("lien") if ggp else ""
    l_tgp = parente.lien_complet(don, racine, tgp).get("lien") if tgp else ""
    verifie("parenté : Sosa 8 = arrière-grand-père", "arrière-grand-père" in l_ggp)
    verifie("parenté : Sosa 16 = trisaïeul (pas bisaïeul)",
            "trisaïeul" in l_tgp and "bisaïeul" not in l_tgp)


# ── géocodage : la route respecte l'opt-in (pas d'appel sans consentement) ──
def test_geocodage_optin():
    d, base = _demo()
    app = Application(d)
    app.ouvrir_demo(demo.generer, version=demo.VERSION)
    # reglages sans geocodage_ok
    c, r = routes.dispatch(app, "POST", "/api/lieux/geocoder", {}, {})
    verifie("géocodage : route refuse sans opt-in", r.get("geocodage_ok") is False)
    verifie("géocodage : aucun lieu géocodé sans opt-in", r.get("geocodes") == 0)


# ── familles : lien sur une personne inexistante = erreur, pas d'orphelin ───
def test_familles_pid_inexistant():
    d = tempfile.mkdtemp()
    app = Application(d)
    app.ouvrir_demo(demo.generer, version=demo.VERSION)
    n0 = len(app.base.donnees["individus"])
    c, r = routes.dispatch(app, "POST", "/api/individus/ZZINEXISTANT/parent",
                           {}, {"champs": {"prenoms": "Fantôme", "nom": "X"}})
    verifie("familles : pid inconnu → 400", c == 400)
    verifie("familles : aucune personne orpheline créée",
            len(app.base.donnees["individus"]) == n0)


# ── arbre : injection SVG neutralisée (trait_couleur + fond_image_data) ─────
def test_arbre_anti_injection():
    d = tempfile.mkdtemp()
    app = Application(d)
    app.ouvrir_demo(demo.generer, version=demo.VERSION)
    racine = app.manifeste["racine_id"]
    mal = 'red"/><script>alert(1)</script><rect x="0'
    c, r = routes.dispatch(app, "GET", "/api/arbre",
                           {"racine": racine, "mode": "ascendance", "generations": "3",
                            "trait_couleur": mal}, {})
    verifie("arbre : trait_couleur malveillant neutralisé", "<script>" not in r["svg"])
    c, r = routes.dispatch(app, "GET", "/api/arbre",
                           {"racine": racine, "mode": "eventail",
                            "fond_image_data": 'x"/><script>alert(2)</script>'}, {})
    verifie("arbre : fond_image_data de la requête neutralisé", "<script>" not in r["svg"])


# ── arbre : la descendance respecte le bouton « légende » ──────────────────
def test_arbre_legende_descendance():
    from services import arbre
    d, base = _demo()
    don = base.donnees
    racine = em.charger(d)["racine_id"]
    avec = arbre.rendre(don, racine, "descendance", {"generations": 3, "preuves": True, "legende": True})
    sans = arbre.rendre(don, racine, "descendance", {"generations": 3, "preuves": True, "legende": False})
    verifie("arbre : légende affichée en descendance quand demandée", "legende-preuve" in avec)
    verifie("arbre : légende masquée en descendance quand désactivée", "legende-preuve" not in sans)


if __name__ == "__main__":
    for fn in (test_gedcom_champs_source, test_gedcom_evenement_prive,
               test_suppr_source_residence, test_parente_aieux, test_geocodage_optin,
               test_familles_pid_inexistant, test_arbre_anti_injection,
               test_arbre_legende_descendance):
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
