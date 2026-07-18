# -*- coding: utf-8 -*-
"""Tests de torture — données volontairement tordues / hostiles, pour vérifier
qu'Arboriane ne plante pas et reste cohérent : filiations cycliques, champs
vides/None, unicode extrême, PACS bancals, suppressions en cascade, GEDCOM
aller-retour de cas pénibles.

Exécuter :  python -X utf8 tests/test_torture.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import modele                              # noqa: E402
from core.gedcom import ecriture, lecture            # noqa: E402
from core.application import Application             # noqa: E402
from services import demo, sources                   # noqa: E402
from services.personnes import _categories, lister   # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def sans_planter(nom, fn):
    """Le test réussit si l'appel NE lève PAS (robustesse), et renvoie le résultat."""
    try:
        r = fn(); verifie(nom + " (ne plante pas)", True); return r
    except Exception as e:  # noqa: BLE001
        verifie(nom + " (ne plante pas) — " + type(e).__name__ + ": " + str(e), False)
        return None


# ── 1. Filiation cyclique : une personne est son propre ancêtre ───────────
def test_filiation_cyclique():
    # A enfant de B, B enfant de A (cycle). sosa et catégories doivent terminer.
    donnees = {
        "individus": {
            "A": {"id": "A", "famc": ["FB"], "fams": ["FA"]},
            "B": {"id": "B", "famc": ["FA"], "fams": ["FB"]},
        },
        "familles": {
            "FA": {"id": "FA", "mari": "B", "epouse": None, "enfants": ["A"]},
            "FB": {"id": "FB", "mari": "A", "epouse": None, "enfants": ["B"]},
        },
    }
    sosa = sans_planter("sosa sur filiation cyclique",
                        lambda: modele.sosa_par_individu(donnees, "A"))
    verifie("cycle : sosa borné (pas d'explosion)", sosa is not None and len(sosa) < 100)
    cats = sans_planter("catégories sur filiation cyclique",
                        lambda: _categories(donnees, sosa or {"A": 1}))
    verifie("cycle : A et B classés directe/élargie (pas 'hors')",
            cats and cats.get("A") in ("directe", "elargie") and cats.get("B") in ("directe", "elargie"))


# ── 2. Champs vides / None / structures dégénérées ────────────────────────
def test_champs_vides():
    sans_planter("resume() sur individu quasi vide", lambda: modele.resume({"id": "X"}))
    sans_planter("sosa sur base vide", lambda: modele.sosa_par_individu({"individus": {}, "familles": {}}, "Z"))
    # union où les deux conjoints sont la MÊME personne
    donnees = {"individus": {"I1": {"id": "I1", "fams": ["F"]}},
               "familles": {"F": {"id": "F", "mari": "I1", "epouse": "I1", "enfants": ["I1"]}}}
    sans_planter("auto-mariage + auto-enfant", lambda: _categories(donnees, {"I1": 1}))
    # famille pointant vers des ids inexistants
    d2 = {"individus": {"I1": {"id": "I1", "fams": ["F"]}},
          "familles": {"F": {"id": "F", "mari": "I1", "epouse": "FANTOME", "enfants": ["INEXISTANT"]}}}
    sans_planter("famille vers ids fantômes", lambda: _categories(d2, {"I1": 1}))


# ── 3. Catégories : cas limites de rattachement ───────────────────────────
def test_categories_limites():
    # couple pacsé AVEC enfant commun -> l'enfant relie tout le monde (élargie)
    donnees = {
        "individus": {k: {"id": k} for k in ["R", "P", "X", "K"]},
        "familles": {
            "F1": {"mari": "P", "enfants": ["R"]},
            # R + X pacsés (pas de mariage) MAIS enfant commun K
            "F2": {"mari": "R", "epouse": "X", "enfants": ["K"],
                   "evenements": [{"type": "EVEN", "precision": "PACS", "date": "01/01/2020"}]},
        },
    }
    cats = _categories(donnees, {"R": 1, "P": 2})
    verifie("PACS AVEC enfant commun : partenaire devient élargie (via l'enfant)",
            cats["X"] == "elargie" and cats["K"] == "elargie")
    # composants disjoints : une 2e famille sans lien avec la racine = hors
    d2 = {
        "individus": {k: {"id": k} for k in ["R", "P", "Z", "W"]},
        "familles": {"F1": {"mari": "P", "enfants": ["R"]},
                     "F2": {"mari": "Z", "epouse": "W", "mariage": {"date": "01/01/1900"}, "enfants": []}},
    }
    c2 = _categories(d2, {"R": 1, "P": 2})
    verifie("composant disjoint : Z et W = hors", c2["Z"] == "hors" and c2["W"] == "hors")


# ── 4. Unicode extrême + très longues chaînes en GEDCOM ───────────────────
def test_unicode_et_longueur():
    nom_fou = "Æ𝕏Ø-Łœ ᛗᚱ 中文 émoji😀 " + "a" * 300   # accents, CJK, emoji, très long
    lieu_fou = "Sɑɔ Paȵlo, Brãsíl — " + "z" * 400
    donnees = {
        "individus": {
            "I1": {"id": "I1", "prenoms": nom_fou, "nom": "TEST", "sexe": "F", "fams": ["F1"],
                   "naissance": {"lieu": lieu_fou}},
            "I2": {"id": "I2", "prenoms": "Zoé", "nom": "PARTNER", "sexe": "F", "fams": ["F1"]},
        },
        "familles": {"F1": {"id": "F1", "mari": "I2", "epouse": "I1", "enfants": [],
            "evenements": [{"type": "EVEN", "precision": "PACS", "date": "29/08/2022",
                            "lieu": lieu_fou, "valeur": nom_fou}]}},
        "sources": {}, "lieux": {}, "depots": {},
    }
    txt = sans_planter("export GEDCOM unicode/long", lambda: ecriture.exporter(donnees))
    if txt:
        d2 = sans_planter("réimport GEDCOM unicode/long", lambda: lecture.importer(txt))
        if d2:
            i1 = d2["individus"].get("I1", {})
            verifie("unicode : prénom conservé", nom_fou.strip() in (i1.get("prenoms") or ""))
            # PACS même-sexe conservé
            evs = (d2["familles"].get("F1") or {}).get("evenements") or []
            verifie("PACS même-sexe conservé à l'aller-retour",
                    any((e.get("precision") or "") == "PACS" for e in evs))
            # aucune ligne GEDCOM ne dépasse la limite de 255 octets (CONC)
            trop = [l for l in txt.splitlines() if len(l.encode("utf-8")) > 255]
            verifie("aucune ligne > 255 octets (découpe CONC)", not trop)


# ── 5. PACS bancals ───────────────────────────────────────────────────────
def test_pacs_bancals():
    # dissolution SANS début, PACS sans date (lieu seul)
    donnees = {
        "individus": {"I1": {"id": "I1", "fams": ["F1"]}, "I2": {"id": "I2", "fams": ["F1"]}},
        "familles": {"F1": {"id": "F1", "mari": "I2", "epouse": "I1", "enfants": [],
            "evenements": [
                {"type": "EVEN", "precision": "Dissolution de PACS", "date": "", "lieu": "Lyon"},
                {"type": "EVEN", "precision": "PACS", "date": "", "lieu": ""}]}},
        "sources": {}, "lieux": {}, "depots": {},
    }
    txt = sans_planter("export PACS sans date", lambda: ecriture.exporter(donnees))
    if txt:
        sans_planter("réimport PACS sans date", lambda: lecture.importer(txt))


# ── 6. Suppression en cascade (personne = conjoint + parent + source) ─────
def test_suppression_cascade():
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    base = app.base
    d = base.donnees
    # prendre une personne qui a une famille (conjoint/enfants) et la citer
    pid = next((p for p, i in d["individus"].items() if i.get("fams") or i.get("famc")), None)
    verifie("cascade : une personne liée existe", pid is not None)
    if pid:
        src = base.creer_source({"titre": "Torture"})["id"]
        base.citer(pid, "naissance", {"source": src, "quay": 2})
        base.supprimer_individu(pid)
        verifie("cascade : individu supprimé", pid not in d["individus"])
        # aucune famille ne référence encore le pid
        ref_fam = any(pid in (f.get("mari"), f.get("epouse")) or pid in (f.get("enfants") or [])
                      for f in d["familles"].values())
        verifie("cascade : plus aucune référence dans les familles", not ref_fam)
        # la source ne liste plus le pid dans ses personnes
        s = d["sources"].get(src, {})
        verifie("cascade : source nettoyée du pid", pid not in (s.get("personnes") or []))
        # les vues ne plantent pas après coup
        sans_planter("cascade : lister() après suppression", lambda: lister(base))
        sans_planter("cascade : preuves d'une autre personne",
                     lambda: sources.preuves_personne(d, next(iter(d["individus"]))))


# ── 6b. Écriture hostile : types invalides ne doivent PAS corrompre la base ─
def test_ecriture_types_invalides():
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    base = app.base
    pid = next(iter(base.donnees["individus"]))
    # evenements en TEXTE, sexe absurde, naissance en texte → doivent être neutralisés
    base.modifier_individu(pid, {"evenements": "pas-un-tableau", "sexe": "Z" * 1000,
                                 "naissance": "pas-un-dict", "medias": 42, "note": None})
    ind = base.donnees["individus"][pid]
    verifie("evenements forcé en liste", isinstance(ind["evenements"], list))
    verifie("medias forcé en liste", isinstance(ind["medias"], list))
    verifie("naissance forcée en dict", isinstance(ind["naissance"], dict))
    verifie("sexe invalide -> U", ind["sexe"] == "U")
    verifie("note None -> chaîne", isinstance(ind["note"], str))
    # la fiche se construit toujours (le vrai risque : .forEach sur une chaîne)
    sans_planter("fiche après écriture hostile",
                 lambda: __import__("services.personnes", fromlist=["fiche"]).fiche(base, pid))
    # famille : mariage/evenements en type invalide ne plantent pas (dict(str) crashait)
    fid = next((f for f in base.donnees["familles"]), None)
    if fid:
        sans_planter("modifier_famille mariage=texte",
                     lambda: base.modifier_famille(fid, {"mariage": "pas-un-dict", "evenements": "x"}))
        verifie("famille evenements forcé en liste",
                isinstance(base.donnees["familles"][fid]["evenements"], list))
    # les citations d'un fait vital ne doivent pas sauter si l'écran renvoie
    # naissance sans « citations » (un simple changement de date, p. ex.)
    pid2 = next(iter(base.donnees["individus"]))
    base.modifier_individu(pid2, {"naissance": {"date": "01/01/1900",
                                                 "citations": [{"source": "S_X", "quay": 3}]}})
    base.modifier_individu(pid2, {"naissance": {"date": "02/02/1900"}})   # sans citations
    verifie("citations de naissance préservées si non renvoyées",
            (base.donnees["individus"][pid2]["naissance"].get("citations") or []) != []
            and base.donnees["individus"][pid2]["naissance"]["date"] == "02/02/1900")


# ── 6c. Pas de « Décès — À prouver » pour un présumé vivant ───────────────
def test_deces_pas_a_prouver_si_vivant():
    donnees = {
        "individus": {
            "V": {"id": "V", "naissance": {"date": "20/07/1984"}, "deces": {}},   # présumé vivant
            "D": {"id": "D", "naissance": {"date": "10/01/1900"},
                  "deces": {"date": "05/05/1970"}},                               # décédé
            "X": {"id": "X", "naissance": {"date": "01/01/1850"}, "deces": {}},   # trop vieux -> non vivant
        },
        "familles": {},
    }
    fv = sources.preuves_personne(donnees, "V")
    verifie("présumé vivant : pas de fait 'deces'",
            not any(f["fait"] == "deces" for f in fv["faits"]))
    fd = sources.preuves_personne(donnees, "D")
    verifie("décédé avec date : fait 'deces' présent",
            any(f["fait"] == "deces" for f in fd["faits"]))
    fx = sources.preuves_personne(donnees, "X")
    verifie("né en 1850 sans décès : décès à prouver (plus présumé vivant)",
            any(f["fait"] == "deces" for f in fx["faits"]))


# ── 6d. Hors famille exclus des index/stats ; date d'union non mariée ─────
def test_hors_famille_exclus_des_stats():
    from services import index_pro, statistiques, listes
    from services.personnes import ids_hors_famille
    donnees = {
        "individus": {
            "R": {"id": "R", "professions": [{"valeur": "boulanger"}]},
            "P": {"id": "P", "professions": [{"valeur": "boulanger"}]},
            "O": {"id": "O", "professions": [{"valeur": "officier de l'état civil"}]},  # hors
        },
        "familles": {
            "F1": {"mari": "P", "enfants": ["R"]},
            # R pacsé avec O (union libre, pas de mariage, pas d'enfant) -> O reste hors
            "F2": {"mari": "R", "epouse": "O",
                   "evenements": [{"type": "EVEN", "precision": "PACS", "date": "01/01/2020",
                                   "lieu": "Lyon"}]},
        },
    }
    hors = ids_hors_famille(donnees, "R")
    verifie("officier détecté comme hors famille", hors == {"O"})
    idx = index_pro.index(donnees, exclure=hors)
    metiers = {m["metier"] for m in idx["metiers"]}
    verifie("index métiers : « officier » exclu",
            "officier de l'état civil" not in metiers and "boulanger" in metiers)
    st = statistiques.calculer(donnees, exclure=hors)
    verifie("stats : l'officier n'est pas compté", st["personnes"] == 2)
    # union non mariée : la date vient du PACS (repli)
    u = listes.unions(donnees)
    fam2 = next(x for x in u["unions"] if x["id"] == "F2")
    verifie("union non mariée : date = date du PACS", fam2["date"] == "01/01/2020")
    verifie("union non mariée : type = PACS", fam2["type"] == "PACS")


# ── 6d. Cohérence : un « hors famille » isolé n'est pas signalé « isolé » ──
def test_coherence_hors_famille():
    from services import coherence
    # R racine (Sosa 1), P son parent ; O = officier isolé (cité, hors famille) ;
    # Q = orphelin isolé SANS racine connue reliée.
    donnees = {
        "individus": {"R": {"id": "R", "famc": ["F1"]}, "P": {"id": "P", "fams": ["F1"]},
                      "O": {"id": "O"}, "Q": {"id": "Q"}},
        "familles": {"F1": {"mari": "P", "epouse": "", "enfants": ["R"]}},
    }
    # avec racine : O et Q sont hors famille -> pas d'alerte « isolée »
    al = coherence.analyser(donnees, "R")["alertes"]
    isolees = {a["personne"] for a in al if a["type"] == "isolee"}
    verifie("hors famille (racine connue) : aucune alerte « isolée »", not isolees)
    # sans racine : comportement d'avant conservé (les isolés sont signalés)
    al2 = coherence.analyser(donnees)["alertes"]
    isolees2 = {a["personne"] for a in al2 if a["type"] == "isolee"}
    verifie("sans racine : les isolés restent signalés (rétrocompat)",
            {"O", "Q"} <= isolees2)


# ── 7. Racine incohérente ────────────────────────────────────────────────
def test_racine_incoherente():
    donnees = {"individus": {"I1": {"id": "I1"}}, "familles": {}}
    # sosa avec une racine qui n'existe pas
    sans_planter("sosa racine inexistante", lambda: modele.sosa_par_individu(donnees, "NOPE"))
    verifie("catégories sans racine -> vide", _categories(donnees, {}) == {})


if __name__ == "__main__":
    for fn in (test_filiation_cyclique, test_champs_vides, test_categories_limites,
               test_unicode_et_longueur, test_pacs_bancals, test_suppression_cascade,
               test_ecriture_types_invalides, test_deces_pas_a_prouver_si_vivant,
               test_hors_famille_exclus_des_stats, test_coherence_hors_famille,
               test_racine_incoherente):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
