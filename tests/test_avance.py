# -*- coding: utf-8 -*-
"""
Tests du lot « généalogie avancée » : fusion de doublons, détection de doublons
probables, export d'un rameau (GEDCOM d'un sous-ensemble), import fusionnant
(complète sans écraser, ajoute le reste), et import d'un .zip d'arbre.

Exécuter :  python -X utf8 tests/test_avance.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application               # noqa: E402
from core import gedcom                                 # noqa: E402
from services import demo, fusion, rameau, import_avance  # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1
        print("  ok  ", nom)
    else:
        _ko += 1
        print("  FAIL", nom)


def base_demo():
    app = Application(tempfile.mkdtemp())
    app.ouvrir_demo(demo.generer)
    return app


def id_prenom(d, p):
    return next(pid for pid, i in d["individus"].items() if p in i.get("prenoms", ""))


# ── Fusion ─────────────────────────────────────────────────────────────────
def test_fusion():
    app = base_demo()
    base = app.base
    d = base.donnees
    louis = id_prenom(d, "Thomas")           # Thomas WHITAKER (marié, avec parents)

    # Créer un doublon PARTIEL : mêmes nom/prénoms, mais champs vides
    # complétables (surnom + décès) — sans écraser ce que le gardé a déjà.
    absorbe = base.creer_individu({
        "prenoms": "Thomas", "nom": "WHITAKER", "sexe": "U",
        "surnom": "le charpentier",
        "deces": {"date": "1969", "lieu": "Tours, Indre-et-Loire"},
        "professions": [{"valeur": "ébéniste"}],
    })["id"]
    # tag source sur l'absorbé, pour vérifier le repointage
    s = base.creer_source({"titre": "Fiche doublon"})["id"]
    base.taguer_personne_source(s, absorbe, "sujet")

    n_avant = len(d["individus"])
    naiss_avant = dict(d["individus"][louis].get("naissance") or {})

    res = fusion.fusionner(base, louis, absorbe)
    verifie("fusion : résumé renvoyé", isinstance(res, dict) and res.get("garde") == louis)
    verifie("fusion : absorbé supprimé", absorbe not in d["individus"])
    verifie("fusion : effectif -1", len(d["individus"]) == n_avant - 1)

    g = d["individus"][louis]
    verifie("fusion : surnom (vide) complété", g.get("surnom") == "le charpentier")
    verifie("fusion : sexe conservé (non écrasé)", g.get("sexe") == "M")
    verifie("fusion : naissance de garde intacte (non écrasée)",
            (g.get("naissance") or {}).get("date") == naiss_avant.get("date"))
    verifie("fusion : profession fusionnée (append)",
            any((p.get("valeur") == "ébéniste") for p in g.get("professions", [])))

    # source repointée sur le gardé
    src = d["sources"][s]
    verifie("fusion : source repointée vers garde",
            any(p.get("id") == louis for p in src.get("personnes", []))
            and not any(p.get("id") == absorbe for p in src.get("personnes", [])))

    # liens recalculés : Louis reste marié (fams) et enfant (famc) cohérents
    verifie("fusion : liens fams recalculés cohérents",
            all(louis in (d["familles"][f].get("mari"), d["familles"][f].get("epouse"))
                for f in g.get("fams", [])))
    verifie("fusion : liens famc recalculés cohérents",
            all(louis in d["familles"][f].get("enfants", []) for f in g.get("famc", [])))

    # id identiques / invalides -> None
    verifie("fusion : ids identiques rejetés", fusion.fusionner(base, louis, louis) is None)
    verifie("fusion : id inexistant rejeté", fusion.fusionner(base, louis, "ZZ") is None)


def test_doublons():
    app = base_demo()
    base = app.base
    d = base.donnees
    louis = id_prenom(d, "Thomas")
    louis_ind = d["individus"][louis]
    # doublon : même nom, année de naissance manquante
    base.creer_individu({"prenoms": louis_ind["prenoms"], "nom": louis_ind["nom"],
                         "sexe": "M"})
    paires = fusion.doublons_probables(d)
    noms = {p["nom"] for p in paires}
    verifie("doublons : la paire Thomas WHITAKER est détectée",
            any("Thomas" in n for n in noms))
    verifie("doublons : chaque paire a a/b/nom/raison",
            all({"a", "b", "nom", "raison"} <= set(p) for p in paires))


# ── Rameau ──────────────────────────────────────────────────────────────────
def test_rameau_ascendance():
    app = base_demo()
    d = app.base.donnees
    lucie = id_prenom(d, "Lucie")
    chemin, texte = rameau.exporter_rameau(app, lucie, "ascendance")
    verifie("rameau : fichier .ged créé", chemin.endswith(".ged") and os.path.exists(chemin))
    verifie("rameau : dans Exports/", "Exports" in chemin)

    sous = gedcom.importer(texte)
    noms = {i.get("prenoms", "") for i in sous["individus"].values()}
    # ascendance de Lucie : Nicolas (père), Michel, Thomas (ancêtres)…
    verifie("rameau : contient la personne racine (Lucie)",
            any("Lucie" in n for n in noms))
    verifie("rameau : contient un ancêtre (Thomas)",
            any("Thomas" in n for n in noms))
    # …mais PAS Tom (frère, hors ascendance)
    verifie("rameau : exclut la fratrie hors branche (Tom)",
            not any(n == "Tom" for n in noms))
    verifie("rameau : sous-ensemble strict",
            len(sous["individus"]) < len(d["individus"]))


def test_rameau_descendance():
    app = base_demo()
    d = app.base.donnees
    thomas = id_prenom(d, "Thomas")          # Thomas WHITAKER, ancêtre de Lucie
    _chemin, texte = rameau.exporter_rameau(app, thomas, "descendance")
    sous = gedcom.importer(texte)
    noms = {i.get("prenoms", "") for i in sous["individus"].values()}
    verifie("rameau desc : contient la racine (Thomas)",
            any("Thomas" in n for n in noms))
    verifie("rameau desc : contient un descendant (Lucie)",
            any("Lucie" in n for n in noms))
    # Gérard (branche maternelle FONTAINE, pas descendant de Thomas) exclu
    verifie("rameau desc : exclut une autre branche (Gérard)",
            not any(n == "Gérard" for n in noms))


# ── Import fusionnant ────────────────────────────────────────────────────────
def test_import_fusionner():
    app = base_demo()
    d = app.base.donnees
    n_avant = len(d["individus"])
    louis = id_prenom(d, "Thomas")
    # naissance existante (réelle) pour apparier ET vérifier le non-écrasement
    naiss_louis = (d["individus"][louis].get("naissance") or {}).get("date")
    lieu_louis = (d["individus"][louis].get("naissance") or {}).get("lieu")

    # GEDCOM entrant : Thomas (apparié via nom + naissance, profession NOUVELLE)
    # + une personne totalement nouvelle.
    ged = (
        "0 HEAD\n1 SOUR Test\n1 GEDC\n2 VERS 5.5.1\n2 FORM LINEAGE-LINKED\n1 CHAR UTF-8\n"
        "0 @I1@ INDI\n1 NAME Thomas /WHITAKER/\n1 SEX M\n"
        "1 BIRT\n2 DATE %s\n2 PLAC %s\n"
        "1 OCCU horloger\n"
        "0 @I2@ INDI\n1 NAME Aldric /DURAND/\n1 SEX M\n1 BIRT\n2 DATE 1910\n"
        "0 TRLR\n" % (naiss_louis, lieu_louis)
    )
    res = import_avance.fusionner_import(app, ged)
    verifie("import fusion : 1 personne ajoutée", res["ajoutees"] == 1)
    verifie("import fusion : effectif +1", len(d["individus"]) == n_avant + 1)
    verifie("import fusion : nouvelle personne présente (Aldric)",
            any("Aldric" in i.get("prenoms", "") for i in d["individus"].values()))
    # Thomas conservé (pas de doublon), naissance NON écrasée
    louis2 = [pid for pid, i in d["individus"].items()
              if "Thomas" in i.get("prenoms", "") and i.get("nom") == "WHITAKER"]
    verifie("import fusion : pas de doublon de Thomas", len(louis2) == 1)
    verifie("import fusion : naissance existante non écrasée",
            (d["individus"][louis2[0]].get("naissance") or {}).get("date") == naiss_louis)
    verifie("import fusion : profession nouvelle ajoutée à Louis",
            any(p.get("valeur") == "horloger"
                for p in d["individus"][louis2[0]].get("professions", [])))
    verifie("import fusion : ne supprime jamais d'existant",
            len(d["individus"]) >= n_avant)


def test_comparer_detaille():
    app = base_demo()
    d = app.base.donnees
    thomas = id_prenom(d, "Thomas")
    nt = (d["individus"][thomas].get("naissance") or {})
    ged = (
        "0 HEAD\n1 SOUR Test\n1 GEDC\n2 VERS 5.5.1\n2 FORM LINEAGE-LINKED\n1 CHAR UTF-8\n"
        "0 @I1@ INDI\n1 NAME Thomas /WHITAKER/\n1 SEX M\n"
        "1 BIRT\n2 DATE %s\n2 PLAC %s\n"
        "1 OCCU horloger\n"
        "0 @I2@ INDI\n1 NAME Aldric /DURAND/\n1 SEX M\n1 BIRT\n2 DATE 1910\n"
        "0 TRLR\n" % (nt.get("date"), nt.get("lieu"))
    )
    r = import_avance.comparer_detaille(app, ged)
    verifie("comparer : Aldric listé comme ajouté",
            any("Aldric" in n for n in r["ajoutees"]))
    verifie("comparer : Thomas apparié (pas ajouté)",
            not any("Thomas" in n for n in r["ajoutees"]))
    verifie("comparer : Thomas marqué modifié (professions)",
            any("Thomas" in m["nom"] and "professions" in m["champs"]
                for m in r["modifiees"]))
    verifie("comparer : des personnes actuelles disparaissent de l'entrant",
            len(r["disparues"]) > 0)


# ── Import ZIP ───────────────────────────────────────────────────────────────
def test_importer_zip():
    app = base_demo()
    # produire un .zip complet de l'espace actif, puis le relire
    cible = app.sauvegarde_complete()
    verifie("zip : archive créée", cible.endswith(".zip") and os.path.exists(cible))
    apercu = import_avance.importer_zip(app, cible)
    verifie("zip : aperçu compte les personnes",
            apercu["personnes"] == len(app.base.donnees["individus"]))
    verifie("zip : aperçu compte les sources",
            apercu["sources"] == len(app.base.donnees.get("sources", {})))
    verifie("zip : base extraite (non appliquée) fournie",
            isinstance(apercu.get("donnees"), dict))

    # même chose via des octets en mémoire
    with open(cible, "rb") as f:
        octets = f.read()
    apercu2 = import_avance.importer_zip(app, octets)
    verifie("zip : lecture depuis des octets",
            apercu2["personnes"] == apercu["personnes"])


if __name__ == "__main__":
    for fn in (test_fusion, test_doublons, test_rameau_ascendance,
               test_rameau_descendance, test_import_fusionner,
               test_comparer_detaille, test_importer_zip):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
