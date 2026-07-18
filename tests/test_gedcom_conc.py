# -*- coding: utf-8 -*-
"""Export GEDCOM : découpe des longues valeurs (CONC), sans perdre d'espace.

Norme 5.5.1, définition de CONC : « Values that are split for a CONC tag must
always be split at a non-space. If the value is split on a space the space will
be lost when concatenation takes place. »

Notre export coupait justement sur une espace, en la gardant en fin de morceau,
avec un commentaire affirmant qu'elle serait « préservée par CONC ». C'est le
contraire : tout lecteur conforme la perd. Une note de l'utilisateur revenait
amputée d'une espace à chaque coupure — chez les autres logiciels, pas chez nous,
donc nos tests d'aller-retour n'y voyaient rien.

Exécuter :  python -X utf8 tests/test_gedcom_conc.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import gedcom                              # noqa: E402
from core.gedcom.ecriture import _couper_255         # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


LONGUE = ("La grande famine de la pomme de terre, de 1845 à 1848, a frappé "
          "l'Irlande et poussé des centaines de milliers de personnes à "
          "traverser l'Atlantique vers Boston, New York et Philadelphie, où "
          "elles retrouvèrent la misère avant l'espoir. " * 4).rstrip()


def test_aucune_coupure_sur_une_espace():
    morceaux = _couper_255(LONGUE)
    verifie("le texte est bien découpé", len(morceaux) > 1)
    verifie("aucun morceau ne finit par une espace",
            not any(m.endswith(" ") for m in morceaux))
    verifie("aucun morceau ne commence par une espace",
            not any(m.startswith(" ") for m in morceaux))


def test_recollage_a_l_identique():
    verifie("recoller les morceaux rend le texte exact",
            "".join(_couper_255(LONGUE)) == LONGUE)
    # Espaces multiples À L'INTÉRIEUR du texte : elles doivent toutes survivre.
    bourre = (("mot" + " " * 7) * 60).rstrip()
    verifie("les espaces multiples internes survivent",
            "".join(_couper_255(bourre)) == bourre)


def test_espace_finale_retiree_a_l_export():
    """Aucun GEDCOM ne transporte une espace en fin de valeur : la norme constate
    elle-même que « many GEDCOM values are trimmed of trailing spaces ». On la
    retire à l'écriture, plutôt que d'émettre une ligne non conforme dont le
    logiciel d'en face fera ce qu'il veut. Les espaces de tête, elles, restent."""
    ind = {"id": "I1", "nom": "D", "prenoms": "J", "sexe": "M",
           "note": "   texte indenté   ", "naissance": {"date": "", "lieu": ""},
           "deces": {"date": "", "lieu": ""}}
    donnees = {"individus": {"I1": ind}, "familles": {}, "sources": {},
               "depots": {}, "lieux": {}, "meta": {}}
    relu = gedcom.importer(gedcom.exporter(donnees))
    verifie("l'espace finale est retirée, celle de tête est gardée",
            relu["individus"]["I1"]["note"] == "   texte indenté")


def test_chaque_ligne_tient_dans_255_octets():
    ind = {"id": "I1", "nom": "DUPONT", "prenoms": "Jean", "sexe": "M",
           "note": LONGUE, "naissance": {"date": "", "lieu": ""},
           "deces": {"date": "", "lieu": ""}}
    donnees = {"individus": {"I1": ind}, "familles": {}, "sources": {},
               "depots": {}, "lieux": {}, "meta": {}}
    texte = gedcom.exporter(donnees)
    trop = [l for l in texte.split("\n") if len(l.encode("utf-8")) + 2 > 255]
    verifie("aucune ligne ne dépasse 255 octets (terminateur compris)", not trop)
    finales = [l for l in texte.split("\n") if l != l.rstrip()]
    verifie("aucune ligne ne se termine par une espace", not finales)


def test_aller_retour_de_la_note():
    ind = {"id": "I1", "nom": "DUPONT", "prenoms": "Jean", "sexe": "M",
           "note": LONGUE, "naissance": {"date": "", "lieu": ""},
           "deces": {"date": "", "lieu": ""}}
    donnees = {"individus": {"I1": ind}, "familles": {}, "sources": {},
               "depots": {}, "lieux": {}, "meta": {}}
    relu = gedcom.importer(gedcom.exporter(donnees))
    verifie("la note revient exactement, espaces comprises",
            relu["individus"]["I1"]["note"] == LONGUE)


if __name__ == "__main__":
    for t in (test_aucune_coupure_sur_une_espace, test_recollage_a_l_identique,
              test_espace_finale_retiree_a_l_export,
              test_chaque_ligne_tient_dans_255_octets, test_aller_retour_de_la_note):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
