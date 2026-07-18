# -*- coding: utf-8 -*-
"""GEDCOM — primitives partagées : verrou de sérialisation, lecture bas niveau
(lignes → arborescence), fusion de texte, et dictionnaires de balises."""
import html
import os
import re
import threading

from core import modele

__all__ = ["_GEDCOM_LOCK", "_serialise", "_NOTES", "_LIGNE", "_lire_lignes", "_arborescence", "_fusion_texte", "_premier", "_pointeur", "_nettoyer_texte", "ATTRIBUTS_INDI", "TAGS_EVT_INDI", "TAGS_EVT_FAM"]

_GEDCOM_LOCK = threading.RLock()

def _serialise(fonction):
    def enveloppe(*a, **k):
        with _GEDCOM_LOCK:
            return fonction(*a, **k)
    enveloppe.__name__ = fonction.__name__
    enveloppe.__doc__ = fonction.__doc__
    return enveloppe


# Rempli au début de importer() : { id_sans_@ : texte } pour les NOTE records
# (0 @NT..@ NOTE) que certains logiciels (Filae) référencent par pointeur.

_NOTES = {}


# ---------------------------------------------------------------------------
# LECTURE (parsing)
# ---------------------------------------------------------------------------

_LIGNE = re.compile(r"^\s*(\d+)\s+(@[^@]+@)?\s*([A-Za-z0-9_]+)?\s?(.*)$")

def _lire_lignes(texte):
    """Transforme le texte GEDCOM en liste de noeuds (niveau, xref, tag, valeur)."""
    noeuds = []
    for brute in texte.splitlines():
        if not brute.strip():
            continue
        m = _LIGNE.match(brute)
        if not m:
            continue
        niveau = int(m.group(1))
        xref = (m.group(2) or "").strip()
        tag = (m.group(3) or "").strip()
        valeur = m.group(4) or ""
        noeuds.append({"niveau": niveau, "xref": xref, "tag": tag,
                       "valeur": valeur, "enfants": []})
    return noeuds

def _arborescence(noeuds):
    """Reconstruit la hiérarchie GEDCOM par niveaux d'indentation."""
    racine = {"niveau": -1, "enfants": []}
    pile = [racine]
    for n in noeuds:
        while pile and pile[-1]["niveau"] >= n["niveau"]:
            pile.pop()
        if not pile:
            pile = [racine]
        pile[-1]["enfants"].append(n)
        pile.append(n)
    return racine["enfants"]

def _fusion_texte(noeud):
    """Reconstitue une valeur multi-lignes (CONC = colle, CONT = saut de ligne)."""
    valeur = noeud.get("valeur", "")
    for enf in noeud["enfants"]:
        if enf["tag"] == "CONC":
            valeur += enf["valeur"]
        elif enf["tag"] == "CONT":
            valeur += "\n" + enf["valeur"]
    return valeur

def _premier(noeud, tag):
    for enf in noeud["enfants"]:
        if enf["tag"] == tag:
            return enf
    return None

def _pointeur(valeur):
    """Identifiant désigné par un pointeur GEDCOM : « @I12@ » -> « I12 ».

    On enlève les espaces AVANT les arobases : plusieurs logiciels (dont Heredis)
    laissent une espace ou une tabulation en fin de ligne, et « @I12@ ».strip("@")
    rend alors « I12@ » — un identifiant qui ne correspond à personne. Toute la
    parenté disparaissait ainsi en silence, sans la moindre erreur.
    Renvoie "" si le pointeur est vide ou absent.
    """
    return (valeur or "").strip().strip("@").strip()

def _nettoyer_texte(txt):
    """Nettoie un texte de note issu d'un autre logiciel :
    - retire les blocs <pre>...</pre> (GeneWeb y recrache du GEDCOM brut) ;
    - convertit <br> en saut de ligne, retire <p>/</p> ;
    - décode les entités HTML (&apos; -> ', &amp; -> & ...) écrites par Ancestry.
    """
    if not txt:
        return txt
    txt = re.sub(r"(?is)<pre>.*?</pre>", "", txt)
    txt = re.sub(r"(?i)<br\s*/?>", "\n", txt)
    txt = re.sub(r"(?i)</p>", "\n", txt)
    txt = re.sub(r"(?i)<p>", "", txt)
    txt = html.unescape(txt)
    # espaces / lignes vides superflus laissés par le nettoyage
    txt = re.sub(r"[ \t]+\n", "\n", txt)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    # On retire les lignes vides et les espaces de FIN, jamais l'indentation de
    # tête : la norme rappelle que « leading spaces could be important to the
    # formatting of the resultant text ». Un strip() global écrasait la mise en
    # forme des notes à chaque aller-retour.
    return txt.strip("\n").rstrip()

ATTRIBUTS_INDI = {"TITL", "RELI", "DSCR", "EDUC", "NATI",
                  "CAST", "PROP", "IDNO", "NMR", "NCHI", "SSN", "FACT"}

TAGS_EVT_INDI = {"BAPM", "CHR", "CHRA", "CONF", "FCOM", "COMU", "ORDN",
                 "BARM", "BASM", "BLES", "BURI", "CREM", "CENS", "EMIG",
                 "IMMI", "NATU", "GRAD", "RETI", "ADOP", "WILL", "PROB",
                 "EVEN"} | ATTRIBUTS_INDI

TAGS_EVT_FAM = {"ENGA", "MARB", "MARC", "MARL", "MARS", "DIV", "DIVF",
                "ANUL", "SEPR", "CENS", "EVEN"}
