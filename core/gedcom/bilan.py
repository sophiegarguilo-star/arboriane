# -*- coding: utf-8 -*-
"""GEDCOM — bilan des balises NON RECONNUES à la lecture (PARC-11).

Un import peut « réussir » en jetant sans un mot des balises que le lecteur ne
connaît pas (rites LDS, FONE/ROMN, citations au niveau famille…). On compte ici,
aux niveaux 1 et 2 des enregistrements INDI/FAM/SOUR/REPO, les balises qui ne
sont ni lues ni volontairement ignorées (administratif trivial), par tag. Le
résultat remonte dans le bilan d'import : l'utilisateur sait CE QUI n'a pas été
repris, et qu'il doit garder son fichier d'origine.

Comptage seulement — aucune influence sur la lecture elle-même.
"""
from core.gedcom.commun import (_lire_lignes, _arborescence,
                                TAGS_EVT_INDI, TAGS_EVT_FAM)

# Administratif sans valeur généalogique : ignoré en silence, jamais compté.
_TRIVIAUX = {"CONC", "CONT", "CHAN", "RIN", "AFN", "RFN", "SUBM", "ANCI",
             "DESI", "_UID", "_UPD", "_FIL"}

# Balises de niveau 1 comprises, par type d'enregistrement (cf. lecture_records).
_N1_INDI = ({"NAME", "SEX", "BIRT", "DEAT", "OCCU", "RESI", "OBJE", "ASSO",
             "REFN", "RESN", "NOTE", "FAMC", "FAMS", "SOUR", "_SOSA", "_TAG",
             "_TODO"} | TAGS_EVT_INDI)
_N1_FAM = {"HUSB", "WIFE", "CHIL", "MARR", "NOTE"} | TAGS_EVT_FAM
_N1_SOUR = {"TITL", "AUTH", "REPO", "DATA", "TEXT", "ABBR", "PUBL", "NOTE",
            "OBJE", "WWW", "_TYPE", "_DATE", "_PLAC", "_ARK", "_LINK",
            "_FIAB", "_STATUT", "_PAGE", "_VILLE", "_PAYS"}
_N1_REPO = {"NAME", "_TYPE", "ADDR", "WWW", "NOTE"}

# Sous-balises (niveau 2) comprises sous un événement (BIRT/DEAT/MARR/RESI et
# événements génériques) : cf. champs._evenement / _evenement_generique.
_SOUS_EVT = {"DATE", "PLAC", "TYPE", "CAUS", "NOTE", "SOUR", "ADDR"}

# Sous-balises comprises sous les autres structures de niveau 1. Une balise de
# niveau 1 absente de cette table est traitée comme « sans sous-champ lu » :
# tout niveau 2 non trivial dessous est compté (ex. 2 DATE sous 1 OCCU, perdu).
_SOUS = {
    "NAME": {"GIVN", "SURN", "SPFX", "NPFX", "NSFX", "NICK", "TYPE",
             "_RUFNAME", "_MARNM"},
    "OBJE": {"FILE", "FORM", "TITL", "_PRIM"},
    "SOUR": {"PAGE", "QUAY", "DATA", "TEXT", "OBJE", "ROLE", "_ROLE"},  # citation
    "FAMC": {"PEDI", "STAT"},
    "CHIL": {"_FREL", "_MREL"},
    "ASSO": {"RELA"},
    "_TODO": {"_STAT"},
    "REPO": {"CALN"},                     # SOUR.REPO -> cote
    "DATA": {"EVEN", "TEXT"},             # SOUR.DATA
}


def compter_arbre(arbre):
    """Compte {tag: n} des balises niveau 1-2 non reconnues, sur l'arborescence
    déjà lue (celle de importer). HEAD et les enregistrements inconnus de
    niveau 0 ne sont pas parcourus : on ne juge que ce que le lecteur visite."""
    comptes = {}

    def compter(tag):
        comptes[tag] = comptes.get(tag, 0) + 1

    for rec in arbre:
        t0 = rec["tag"]
        if t0 == "INDI":
            n1, prive_ok = _N1_INDI, True    # tag privé N1 gardé en événement
        elif t0 == "FAM":
            n1, prive_ok = _N1_FAM, False
        elif t0 == "SOUR" and rec.get("xref"):
            n1, prive_ok = _N1_SOUR, False
        elif t0 == "REPO":
            n1, prive_ok = _N1_REPO, False
        else:
            continue                         # HEAD, NOTE, TRLR, records inconnus
        evts = TAGS_EVT_INDI if t0 == "INDI" else TAGS_EVT_FAM
        for enf in rec["enfants"]:
            tag = enf["tag"]
            if not tag or tag in _TRIVIAUX:
                continue
            if tag not in n1 and not (prive_ok and tag.startswith("_")):
                compter(tag)                 # balise N1 inconnue : perdue entière
                continue
            # N1 comprise : contrôler ses sous-balises de niveau 2.
            if tag in ("BIRT", "DEAT", "MARR", "RESI") or tag in evts or (
                    prive_ok and tag.startswith("_") and tag not in _SOUS):
                sous = _SOUS_EVT
            else:
                sous = _SOUS.get(tag, set())
            for pt in enf["enfants"]:
                t2 = pt["tag"]
                if t2 and t2 not in sous and t2 not in _TRIVIAUX:
                    compter(t2)
    return comptes


def compter_non_reconnues(texte):
    """Comme compter_arbre, mais depuis le TEXTE GEDCOM brut (pour les routes
    qui n'ont pas l'arborescence sous la main : comparer, fusionner)."""
    return compter_arbre(_arborescence(_lire_lignes(texte)))
