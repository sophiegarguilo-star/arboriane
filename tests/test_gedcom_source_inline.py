# -*- coding: utf-8 -*-
"""Import : une source EN LIGNE devient une vraie source.

Découvert par un test d'interopérabilité réel : un arbre exporté d'Arboriane,
importé dans Geneanet puis réexporté. Geneanet (comme les sites GeneWeb) aplatit
une source structurée en une phrase collée sur la personne — « 1 SOUR <texte> »
au lieu d'un enregistrement « 0 @S1@ SOUR » référencé par « 1 SOUR @S1@ ».

Arboriane stockait alors ce texte comme s'il était l'IDENTIFIANT d'une source :
la citation pointait vers une source inexistante, et l'information n'était nulle
part consultable. On matérialise désormais ce texte en une vraie source.

Exécuter :  python -X utf8 tests/test_gedcom_source_inline.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                          # noqa: E402

_ok = _ko = 0

INLINE = """0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME Anne /NOËL/
1 BIRT
2 DATE 1980
2 SOUR Acte de naissance — Lyon, Rhône — état civil
0 @I2@ INDI
1 NAME Marc /NOËL/
1 SOUR Acte de naissance — Lyon, Rhône — état civil
0 TRLR
"""


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _sources(d):
    return d.get("sources") or {}


def _citations(ind):
    c = list(ind.get("citations") or [])
    for ev in ("naissance", "deces"):
        e = ind.get(ev)
        if isinstance(e, dict):
            c += e.get("citations") or []
    return c


def test_source_inline_materialisee():
    d = gedcom.importer(INLINE)
    srcs = _sources(d)
    verifie("une source en ligne devient une vraie source", len(srcs) == 1)
    titre = next(iter(srcs.values()))["titre"] if srcs else ""
    verifie("le titre reprend le texte de la source",
            "Acte de naissance — Lyon, Rhône" in titre)


def test_meme_texte_dedupe():
    """Deux personnes citant LE MÊME texte partagent une seule source."""
    d = gedcom.importer(INLINE)
    verifie("le texte identique n'est pas dupliqué", len(_sources(d)) == 1)


def test_citation_pointe_vers_une_source_existante():
    d = gedcom.importer(INLINE)
    srcs = _sources(d)
    for ind in d["individus"].values():
        for c in _citations(ind):
            verifie("la citation de %s pointe vers une source réelle"
                    % ind["prenoms"], c.get("source") in srcs)
            verifie("aucun source_texte résiduel", "source_texte" not in c)


def test_pointeur_normal_inchange():
    """Un « 1 SOUR @S1@ » vers un vrai enregistrement reste tel quel : la
    matérialisation ne concerne que les sources SANS enregistrement."""
    texte = """0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @I1@ INDI
1 NAME X /Y/
1 BIRT
2 SOUR @S1@
3 QUAY 3
0 @S1@ SOUR
1 TITL Registre paroissial
0 TRLR
"""
    d = gedcom.importer(texte)
    verifie("un seul enregistrement source", len(_sources(d)) == 1)
    sid = next(iter(_sources(d)))
    verifie("l'id de source est bien celui du fichier (S1)", sid == "S1")
    cits = _citations(next(iter(d["individus"].values())))
    verifie("la citation garde le pointeur et son QUAY",
            cits and cits[0]["source"] == "S1" and cits[0].get("quay") == 3)


if __name__ == "__main__":
    for t in (test_source_inline_materialisee, test_meme_texte_dedupe,
              test_citation_pointe_vers_une_source_existante,
              test_pointeur_normal_inchange):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
