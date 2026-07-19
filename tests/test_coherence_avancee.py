# -*- coding: utf-8 -*-
"""
Tests audit MET-02 / MET-03 — garde anti-cycle à la fusion + cohérence avancée
(enfant posthume, dates aberrantes en chaîne brute, cycle de filiation).

Exécuter :  python -X utf8 tests/test_coherence_avancee.py
"""

import datetime
import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import modele                              # noqa: E402
from core.application import Application            # noqa: E402
from core.validation import ErreurValidation        # noqa: E402
from services import coherence, fusion              # noqa: E402
from services import fusion_assistee as fa          # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _ind(i, prenoms, nom, sexe="M", naiss="", dec="", **extra):
    d = {"id": i, "prenoms": prenoms, "nom": nom, "sexe": sexe,
         "naissance": {"date": naiss, "lieu": ""},
         "deces": {"date": dec, "lieu": ""}}
    d.update(extra)
    return d


def _donnees(individus, familles):
    """Mini-arbre en dicts purs (pour coherence.analyser)."""
    d = modele.base_vide()
    d["individus"] = {i["id"]: i for i in individus}
    d["familles"] = {f["id"]: f for f in familles}
    return d


def _base(individus, familles):
    """Mini-arbre dans une vraie Base (pour la fusion, qui sauvegarde)."""
    app = Application(tempfile.mkdtemp())
    app.creer("T")
    b = app.base
    b.donnees["individus"] = {i["id"]: i for i in individus}
    b.donnees["familles"] = {f["id"]: f for f in familles}
    b._recalc_tous_liens()
    b.sauvegarder()
    return b


# ── MET-02 : garde anti-cycle à la fusion ───────────────────────────────────
def test_fusion_anti_cycle():
    # I1 (grand-père) → I2 (père) → I3 (fils), homonymes ; I4 frère de I3.
    def arbre():
        return _base(
            [_ind("I1", "Jean", "MARTIN", "M", "1800"),
             _ind("I2", "Jean", "MARTIN", "M", "1830"),
             _ind("I3", "Jean", "MARTIN", "M", "1860"),
             _ind("I4", "Paul", "MARTIN", "M", "1862")],
            [{"id": "F1", "mari": "I1", "epouse": "", "enfants": ["I2"]},
             {"id": "F2", "mari": "I2", "epouse": "", "enfants": ["I3", "I4"]}])

    b = arbre()
    d = b.donnees
    verifie("en_ligne_directe : père/fils", fusion.en_ligne_directe(d, "I2", "I3"))
    verifie("en_ligne_directe : petit-fils/grand-père (descendance)",
            fusion.en_ligne_directe(d, "I1", "I3"))
    verifie("en_ligne_directe : sens inverse (ascendance)",
            fusion.en_ligne_directe(d, "I3", "I1"))
    verifie("en_ligne_directe : frères = PAS ligne directe",
            not fusion.en_ligne_directe(d, "I3", "I4"))

    try:
        fusion.fusionner(b, "I2", "I3")
        verifie("fusionner : refus père/fils (ErreurValidation)", False)
    except ErreurValidation as e:
        verifie("fusionner : refus père/fils (ErreurValidation)", True)
        verifie("fusionner : message parle de ligne directe / cycle",
                "ligne directe" in str(e) and "cycle" in str(e))
    verifie("fusionner : rien n'a été fusionné (I3 toujours là)",
            "I3" in b.donnees["individus"])

    # score_paire : fort malus + indice pour une paire en ligne directe
    s_direct, ind_direct = fa.score_paire(d, "I2", "I3")
    _s_freres, ind_freres = fa.score_paire(d, "I3", "I4")
    verifie("score_paire : indice « ⚠ en ligne directe »",
            "⚠ en ligne directe" in ind_direct)
    verifie("score_paire : score faible en ligne directe",
            s_direct < 45 and fa._niveau(s_direct) == "faible")
    verifie("score_paire : pas d'indice pour des frères",
            all("ligne directe" not in i for i in ind_freres))

    # fusion assistée : refus AVANT d'appliquer les choix (garde intacte)
    b2 = arbre()
    try:
        fa.fusionner_assiste(b2, "I2", "I3", choix={"naissance.date": "b"})
        verifie("fusionner_assiste : refus ligne directe", False)
    except ErreurValidation:
        verifie("fusionner_assiste : refus ligne directe", True)
    verifie("fusionner_assiste : la gardée n'a pas été modifiée",
            b2.donnees["individus"]["I2"]["naissance"]["date"] == "1830")

    # une fusion légitime (deux frères homonymes) passe toujours
    b3 = _base(
        [_ind("I1", "Jean", "MARTIN", "M", "1830"),
         _ind("I2", "Jean", "MARTIN", "M", "1830"),
         _ind("I3", "Pierre", "MARTIN", "M", "1800")],
        [{"id": "F1", "mari": "I3", "epouse": "", "enfants": ["I1", "I2"]}])
    r = fusion.fusionner(b3, "I1", "I2")
    verifie("fusionner : doublon légitime (frères) accepté",
            r and r.get("garde") == "I1" and "I2" not in b3.donnees["individus"])


# ── MET-03a : enfant né après le décès du parent ────────────────────────────
def test_enfant_posthume():
    d = _donnees(
        [_ind("M1", "Marie", "DUPONT", "F", "1820", "1850", fams=["F1"]),
         _ind("P1", "Paul", "DUPONT", "M", "1815", "1850", fams=["F1"]),
         _ind("E1", "Luc", "DUPONT", "M", "1852", "", famc=["F1"]),
         # enfant posthume TOLÉRÉ pour le père (né moins d'un an après)
         _ind("P2", "Jacques", "ROY", "M", "1810", "1840", fams=["F2"]),
         _ind("E2", "Anne", "ROY", "F", "1841", "", famc=["F2"])],
        [{"id": "F1", "mari": "P1", "epouse": "M1", "enfants": ["E1"]},
         {"id": "F2", "mari": "P2", "epouse": "", "enfants": ["E2"]}])
    types = [(a["type"], a["personne"]) for a in coherence.analyser(d)["alertes"]]
    verifie("mère décédée avant la naissance -> alerte",
            ("enfant_apres_deces_mere", "M1") in types)
    verifie("père décédé > 1 an avant la naissance -> alerte",
            ("enfant_apres_deces_pere", "P1") in types)
    verifie("enfant posthume (père, < 1 an) -> PAS d'alerte",
            ("enfant_apres_deces_pere", "P2") not in types)


# ── MET-03b : date aberrante lue dans la chaîne brute ───────────────────────
def test_date_impossible_brute():
    an_max = datetime.date.today().year + 1
    d = _donnees(
        [_ind("I1", "Ava", "TEST", "F", "987"),                 # < 1000
         _ind("I2", "Bob", "TEST", "M", "", str(an_max + 100)),  # futur lointain
         _ind("I3", "Céline", "TEST", "F", "15 mars 1850"),      # normale
         _ind("I4", "Dan", "TEST", "M", "acte 234 du 5 mai 1850")],  # n° d'acte
        [])
    alertes = coherence.analyser(d)["alertes"]
    imp = {a["personne"] for a in alertes if a["type"] == "date_impossible"}
    verifie("année 987 (brute) détectée", "I1" in imp)
    verifie("année future aberrante détectée", "I2" in imp)
    verifie("date normale : pas d'alerte", "I3" not in imp)
    verifie("numéro d'acte en tête : pas d'alerte", "I4" not in imp)


# ── MET-03c : cycle de filiation ─────────────────────────────────────────────
def test_cycle_filiation():
    # A parent de B, B parent de C… et C parent de A : cycle A→B→C→A.
    d = _donnees(
        [_ind("A", "Aline", "BOUCLE", "F", famc=["F3"], fams=["F1"]),
         _ind("B", "Boris", "BOUCLE", "M", famc=["F1"], fams=["F2"]),
         _ind("C", "Cora", "BOUCLE", "F", famc=["F2"], fams=["F3"]),
         _ind("Z", "Zoé", "SAINE", "F", famc=["F2"])],
        [{"id": "F1", "mari": "", "epouse": "A", "enfants": ["B"]},
         {"id": "F2", "mari": "B", "epouse": "", "enfants": ["C", "Z"]},
         {"id": "F3", "mari": "", "epouse": "C", "enfants": ["A"]}])
    alertes = coherence.analyser(d)["alertes"]
    cycles = [a for a in alertes if a["type"] == "cycle_filiation"]
    verifie("un cycle détecté (et un seul)", len(cycles) == 1)
    verifie("gravité haute", cycles and cycles[0]["gravite"] == "haute")
    verifie("liste des personnes du cycle = {A, B, C}",
            cycles and set(cycles[0].get("personnes", [])) == {"A", "B", "C"})
    verifie("Zoé (hors cycle) pas dans la liste",
            cycles and "Z" not in cycles[0].get("personnes", []))

    # arbre sain : aucun cycle signalé
    d2 = _donnees(
        [_ind("P", "Pierre", "SAIN", "M", "1800", fams=["F1"]),
         _ind("F", "Fils", "SAIN", "M", "1830", famc=["F1"])],
        [{"id": "F1", "mari": "P", "epouse": "", "enfants": ["F"]}])
    verifie("arbre sain : aucun cycle_filiation",
            all(a["type"] != "cycle_filiation"
                for a in coherence.analyser(d2)["alertes"]))


if __name__ == "__main__":
    for fn in (test_fusion_anti_cycle, test_enfant_posthume,
               test_date_impossible_brute, test_cycle_filiation):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
