# -*- coding: utf-8 -*-
"""MET-01 — Type de filiation enfant→famille (FAMC.PEDI).

Avant : le modèle n'avait AUCUN type de lien enfant→famille — une adoption
importée d'un autre logiciel s'affichait comme une filiation biologique, sans
que rien ne le dise. Désormais :

  - la famille porte un dict optionnel fam["pedi"] = {enfant_id: type} avec les
    types FRANÇAIS « adoption », « accueil », « probable » (absence = naissance) ;
  - l'import lit FAMC.PEDI (adopted/foster) + STAT challenged (→ probable) sur
    l'INDI, et les tags privés _FREL/_MREL (FTM/PAF) sous le CHIL du FAM ;
  - l'export réécrit PEDI sous la ligne FAMC (probable → birth + STAT challenged) ;
  - la route POST /api/familles/<fid>/filiation pose/retire le type.

Exécuter :  python -X utf8 tests/test_filiation_pedi.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                          # noqa: E402
from core.application import Application         # noqa: E402
import routes                                    # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _ged(*lignes):
    return "\n".join(("0 HEAD", "1 GEDC", "2 VERS 5.5.1", "1 CHAR UTF-8")
                     + lignes + ("0 TRLR",)) + "\n"


_FICHIER_PEDI = _ged(
    "0 @I1@ INDI", "1 NAME Pierre /DUPONT/", "1 SEX M", "1 FAMS @F1@",
    "0 @I2@ INDI", "1 NAME Marie /MARTIN/", "1 SEX F", "1 FAMS @F1@",
    "0 @I3@ INDI", "1 NAME Adopte /DUPONT/", "1 SEX M",
    "1 FAMC @F1@", "2 PEDI adopted",
    "0 @I4@ INDI", "1 NAME Accueilli /DUPONT/", "1 SEX M",
    "1 FAMC @F1@", "2 PEDI foster",
    "0 @I5@ INDI", "1 NAME Probable /DUPONT/", "1 SEX F",
    "1 FAMC @F1@", "2 PEDI birth", "2 STAT challenged",
    "0 @I6@ INDI", "1 NAME Naturel /DUPONT/", "1 SEX M",
    "1 FAMC @F1@", "2 PEDI birth",
    "0 @F1@ FAM", "1 HUSB @I1@", "1 WIFE @I2@",
    "1 CHIL @I3@", "1 CHIL @I4@", "1 CHIL @I5@", "1 CHIL @I6@",
)


def test_import_pedi():
    d = gedcom.importer(_FICHIER_PEDI)
    pedi = d["familles"]["F1"].get("pedi") or {}
    verifie("PEDI adopted -> « adoption »", pedi.get("I3") == "adoption")
    verifie("PEDI foster -> « accueil »", pedi.get("I4") == "accueil")
    verifie("STAT challenged -> « probable »", pedi.get("I5") == "probable")
    verifie("PEDI birth = naissance : PAS d'entrée", "I6" not in pedi)
    verifie("le champ temporaire _pedi ne fuit pas dans les individus",
            all("_pedi" not in ind for ind in d["individus"].values()))


def test_import_frel_mrel():
    """Tags privés FTM/PAF portés par le CHIL du FAM (pas par l'INDI)."""
    d = gedcom.importer(_ged(
        "0 @I1@ INDI", "1 NAME Pere /X/", "1 SEX M", "1 FAMS @F1@",
        "0 @I3@ INDI", "1 NAME Fils /X/", "1 FAMC @F1@",
        "0 @I4@ INDI", "1 NAME Pupille /X/", "1 FAMC @F1@",
        "0 @F1@ FAM", "1 HUSB @I1@",
        "1 CHIL @I3@", "2 _FREL Adopted", "2 _MREL Natural",
        "1 CHIL @I4@", "2 _FREL Guardian",
    ))
    pedi = d["familles"]["F1"].get("pedi") or {}
    verifie("_FREL Adopted -> « adoption »", pedi.get("I3") == "adoption")
    verifie("_FREL Guardian -> « accueil »", pedi.get("I4") == "accueil")


def test_pedi_indi_prioritaire_sur_frel():
    """Le PEDI standard de l'INDI a le dernier mot sur _FREL/_MREL."""
    d = gedcom.importer(_ged(
        "0 @I1@ INDI", "1 NAME Pere /X/", "1 SEX M", "1 FAMS @F1@",
        "0 @I3@ INDI", "1 NAME Fils /X/", "1 FAMC @F1@", "2 PEDI foster",
        "0 @F1@ FAM", "1 HUSB @I1@", "1 CHIL @I3@", "2 _FREL Adopted",
    ))
    verifie("PEDI (INDI) écrase _FREL (FAM)",
            (d["familles"]["F1"].get("pedi") or {}).get("I3") == "accueil")


def test_export_pedi():
    d = gedcom.importer(_FICHIER_PEDI)
    texte = gedcom.exporter(d)
    lignes = texte.splitlines()
    verifie("export : 2 PEDI adopted présent", "2 PEDI adopted" in lignes)
    verifie("export : 2 PEDI foster présent", "2 PEDI foster" in lignes)
    verifie("export : probable -> 2 PEDI birth + 2 STAT challenged",
            "2 PEDI birth" in lignes and "2 STAT challenged" in lignes)
    # I6 (naissance) : sa ligne FAMC ne doit être suivie d'aucun PEDI
    verifie("export : un seul PEDI birth (I5), pas pour la naissance ordinaire",
            lignes.count("2 PEDI birth") == 1)


def test_round_trip():
    """Import → export → réimport : les trois types survivent tels quels."""
    d1 = gedcom.importer(_FICHIER_PEDI)
    d2 = gedcom.importer(gedcom.exporter(d1))
    p1 = d1["familles"]["F1"].get("pedi") or {}
    p2 = d2["familles"]["F1"].get("pedi") or {}
    verifie("round-trip : types de filiation conservés à l'identique", p1 == p2)
    verifie("round-trip : les trois types sont bien là",
            sorted(p2.values()) == ["accueil", "adoption", "probable"])


def test_route_filiation():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "P"})
    routes.dispatch(app, "POST", "/api/import/gedcom/appliquer", {},
                    {"texte": _FICHIER_PEDI})

    # poser un type sur l'enfant « naissance »
    code, r = routes.dispatch(app, "POST", "/api/familles/F1/filiation", {},
                              {"enfant": "I6", "type": "adoption"})
    verifie("route : pose « adoption » (200)", code == 200 and r.get("ok"))
    verifie("route : le type est stocké côté famille",
            app.base.donnees["familles"]["F1"]["pedi"].get("I6") == "adoption")

    # le type posé part bien à l'export
    code, r = routes.dispatch(app, "GET", "/api/export/gedcom", {}, {})
    verifie("route : l'export compte 2 lignes PEDI adopted (I3 + I6)",
            code == 200 and r["texte"].splitlines().count("2 PEDI adopted") == 2)

    # retirer le type (retour au défaut naissance)
    code, r = routes.dispatch(app, "POST", "/api/familles/F1/filiation", {},
                              {"enfant": "I6", "type": ""})
    verifie("route : type vide = retrait (200)", code == 200)
    verifie("route : l'entrée a disparu du dict",
            "I6" not in (app.base.donnees["familles"]["F1"].get("pedi") or {}))

    # le dict survit à une relecture du fichier JSON (garantir_cles ne l'écrase pas)
    app.base.charger()
    verifie("relecture du JSON : fam[pedi] toujours là",
            app.base.donnees["familles"]["F1"]["pedi"].get("I3") == "adoption")

    # garde-fous
    code, _ = routes.dispatch(app, "POST", "/api/familles/F1/filiation", {},
                              {"enfant": "I1", "type": "adoption"})
    verifie("route : parent (non enfant de l'union) refusé (400)", code == 400)
    code, _ = routes.dispatch(app, "POST", "/api/familles/F1/filiation", {},
                              {"enfant": "I3", "type": "martienne"})
    verifie("route : type inconnu refusé (400)", code == 400)
    code, _ = routes.dispatch(app, "POST", "/api/familles/F999/filiation", {},
                              {"enfant": "I3", "type": "adoption"})
    verifie("route : famille inconnue -> 404", code == 404)


if __name__ == "__main__":
    for t in (test_import_pedi, test_import_frel_mrel,
              test_pedi_indi_prioritaire_sur_frel, test_export_pedi,
              test_round_trip, test_route_filiation):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
