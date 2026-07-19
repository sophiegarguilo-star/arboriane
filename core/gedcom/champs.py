# -*- coding: utf-8 -*-
"""GEDCOM — lecture des CHAMPS : notes, citations, coordonnées, dates
(calendrier républicain), événements/attributs, noms. Voir lecture.importer."""
import html
import os
import re

from core import modele
from core.gedcom.commun import *

__all__ = ["_lire_note", "_retirer_repli_source", "_citations", "_lire_coords", "_MOIS_REP_GED", "_MON_GREG", "_normaliser_date", "_evenement", "_lieu_depuis_addr", "_evenement_generique", "_nom"]

def _lire_note(noeud):
    """Lit un noeud NOTE en suivant un éventuel pointeur (1 NOTE @NT..@),
    puis nettoie le HTML/entités. Rend le texte final prêt à stocker."""
    v = (noeud.get("valeur") or "").strip()
    if v.startswith("@") and v.endswith("@") and " " not in v and len(v) > 2:
        rec = _NOTES.get(_pointeur(v))
        brut = rec if rec is not None else ""
    else:
        brut = _fusion_texte(noeud)
    # Pas de .strip() final : _nettoyer_texte retire déjà les espaces de fin et
    # les lignes vides, mais préserve l'indentation de tête, significative pour
    # la mise en forme d'une note (cf. norme 5.5.1, définition de CONT).
    return _nettoyer_texte(brut)

def _retirer_repli_source(src):
    """Retire de la note le repli lisible ajouté à l'export (« Source en ligne /
    Date de l'acte / Lieu de l'acte ») pour éviter les doublons en aller-retour,
    et RÉCUPÈRE ces valeurs si elles ne figurent pas déjà dans des tags dédiés."""
    note = src.get("note") or ""
    if not note:
        return note
    lignes = note.split("\n")

    def est_repli(l):
        s = l.strip()
        if not s:
            return True   # ligne vide adjacente au repli
        if s.startswith("Source en ligne : "):
            if not src.get("ark"):
                src["ark"] = s[len("Source en ligne : "):].strip()
            return True
        if s.startswith("Date de l'acte : "):
            if not src.get("date"):
                src["date"] = s[len("Date de l'acte : "):].strip()
            return True
        if s.startswith("Lieu de l'acte : "):
            if not src.get("lieu"):
                src["lieu"] = s[len("Lieu de l'acte : "):].strip()
            return True
        return False

    # on ne retire que la QUEUE de la note (le repli est toujours ajouté à la fin)
    i = len(lignes)
    while i > 0 and est_repli(lignes[i - 1]):
        i -= 1
    # garde-fou : ne retirer que si au moins une vraie ligne de repli a été vue
    queue = lignes[i:]
    if any(l.strip().startswith(("Source en ligne : ", "Date de l'acte : ",
                                 "Lieu de l'acte : ")) for l in queue):
        lignes = lignes[:i]
    return "\n".join(lignes).strip()

def _citations(noeud):
    """Lit les sous-noeuds SOUR d'un bloc et renvoie la liste des citations.

    Chaque citation : { source, page, quay, role }. Deux formes de SOUR :

    - « 1 SOUR @S1@ » : référence à un enregistrement source -> `source` = son id ;
    - « 1 SOUR <texte> » : source EN LIGNE, sans enregistrement (Geneanet et les
      sites GeneWeb aplatissent ainsi une source structurée en une phrase). On
      garde ce texte dans `source_texte` ; l'importateur en fera une vraie source
      (sinon on stockait le texte comme un identifiant, et la citation pointait
      vers une source inexistante).

    QUAY (fiabilité GEDCOM) : 3=acte, 2=déclaré, 1/0=estimé.
    """
    cites = []
    for enf in noeud["enfants"]:
        if enf["tag"] != "SOUR":
            continue
        brut = (enf.get("valeur") or "").strip()
        est_pointeur = bool(re.match(r"^@[^@\s]+@$", brut))
        src = _pointeur(brut) if est_pointeur else ""
        texte_inline = "" if est_pointeur else brut
        if not src and not texte_inline:
            continue                          # SOUR vide (ex. en-tête) : ignoré
        page = _premier(enf, "PAGE")
        quay = _premier(enf, "QUAY")
        cite = {"source": src,
                "page": _fusion_texte(page).strip() if page else "",
                "quay": None,
                "role": ""}
        if texte_inline:
            cite["source_texte"] = texte_inline
        if quay is not None:
            v = quay["valeur"].strip()
            cite["quay"] = int(v) if v.isdigit() else None
        # citation-extrait (verbatim) : DATA.TEXT (standard) ou TEXT direct
        data = _premier(enf, "DATA")
        txt_node = (_premier(data, "TEXT") if data else None) or _premier(enf, "TEXT")
        if txt_node:
            t = _fusion_texte(txt_node).strip()
            if t:
                cite["texte"] = t
        role = _premier(enf, "_ROLE") or _premier(enf, "ROLE")
        if role:
            r = _fusion_texte(role).strip()
            if r:
                cite["role"] = r
        # Scan attaché À LA CITATION (2 SOUR / 3 OBJE / 4 FILE) — fréquent chez
        # Brother's Keeper. On garde le NOM du fichier (le chemin est sur le disque
        # de l'export) ; l'importateur le rattachera à la source citée.
        obje = _premier(enf, "OBJE")
        fnode = _premier(obje, "FILE") if obje else None
        if fnode:
            chemin = _fusion_texte(fnode).strip()      # chemin d'origine (disque de l'export)
            f = chemin.replace("\\", "/")
            if f:
                cite["fichier_source"] = f.rsplit("/", 1)[-1]   # basename (affichage/stockage)
                cite["fichier_source_chemin"] = chemin          # chemin complet (import local)
        cites.append(cite)
    return cites

def _lire_coords(plac_noeud):
    """Coordonnées (lat, lon) sous un noeud PLAC (MAP/LATI/LONG), ou None.
    Gère les préfixes N/S/E/W du format GEDCOM (ex. 'N43.296', 'W5.369')."""
    if not plac_noeud:
        return None
    m = _premier(plac_noeud, "MAP")
    if not m:
        return None
    la, lo = _premier(m, "LATI"), _premier(m, "LONG")
    if not (la and lo):
        return None

    def val(n):
        s = (n.get("valeur") or "").strip()
        signe = -1 if s[:1].upper() in ("S", "W") else 1
        try:
            return signe * float(s.lstrip("NSEWnsew"))
        except ValueError:
            return None
    lat, lon = val(la), val(lo)
    return (lat, lon) if (lat is not None and lon is not None) else None

_MOIS_REP_GED = {"VEND": 1, "BRUM": 2, "FRIM": 3, "NIVO": 4, "PLUV": 5, "VENT": 6,
                 "GERM": 7, "FLOR": 8, "PRAI": 9, "MESS": 10, "THER": 11, "FRUC": 12}

_MON_GREG = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
             "NOV", "DEC"]

def _normaliser_date(s):
    """Convertit une date GEDCOM républicaine (« @#DFRENCH R@ 12 GERM 3 ») en
    grégorien lisible (« 1 APR 1795 »), pour que l'année reste exploitable ; les
    autres calendriers voient juste leur tag retiré. Tolérant : renvoie l'original
    en cas d'échec. Les dates ordinaires sont inchangées."""
    if not s or "@#D" not in s.upper():
        return s
    m = re.match(r"^\s*(BEF|AFT|ABT|EST|CAL)?\s*@#DFRENCH\s*R?@\s*(.+)$", s.strip(), re.IGNORECASE)
    if not m:
        return re.sub(r"@#D\w+\s*\w*@", "", s).strip()
    dm = re.match(r"(\d{1,2})\s+([A-Za-z]{3,4})\s+(\d{1,4})", m.group(2).strip())
    mois = _MOIS_REP_GED.get(dm.group(2).upper()) if dm else None
    if not mois:
        return s
    from services import dates_rep          # utilitaire pur (aucun cycle)
    g = dates_rep.rep_vers_greg(int(dm.group(3)), mois, int(dm.group(1)))
    if not g:
        return s
    greg = "%d %s %d" % (g.day, _MON_GREG[g.month - 1], g.year)
    prefixe = (m.group(1) or "").upper()
    return (prefixe + " " + greg).strip() if prefixe else greg

def _evenement(noeud):
    """Extrait { date, lieu, cause?, citations } d'un bloc événement
    (BIRT, DEAT, MARR...)."""
    ev = {"date": "", "lieu": ""}
    d = _premier(noeud, "DATE")
    if d:
        brut = _fusion_texte(d).strip()
        ev["date"] = _normaliser_date(brut)
        # Conserve la date républicaine d'origine (sinon perdue) : réémise à
        # l'export pour un aller-retour fidèle.
        if ev["date"] != brut and "@#DFRENCH" in brut.upper():
            ev["date_rep"] = brut
        heure_node = _premier(d, "_TIME")   # heure du fait (extension Arboriane)
        if heure_node:
            h = (heure_node.get("valeur") or "").strip()
            if h:
                ev["heure"] = h
    p = _premier(noeud, "PLAC")
    if p:
        ev["lieu"] = _fusion_texte(p).strip()
        c = _lire_coords(p)
        if c:
            ev["_coords"] = c
    if not ev["lieu"]:
        ev["lieu"] = _lieu_depuis_addr(noeud)
    caus = _premier(noeud, "CAUS")   # cause de l'événement (ex. cause du décès)
    if caus:
        cause = _fusion_texte(caus).strip()
        if cause:
            ev["cause"] = cause
    # note de l'événement (2 NOTE sous BIRT/DEAT/MARR/RESI) : elle était perdue
    # à l'import alors que _evenement_generique la lisait déjà (GED-01).
    n = _premier(noeud, "NOTE")
    if n:
        txt = _lire_note(n)
        if txt:
            ev["note"] = txt
    cites = _citations(noeud)
    if cites:
        ev["citations"] = cites
    return ev

def _lieu_depuis_addr(noeud):
    """Récupère un lieu depuis ADDR/ADR1 quand PLAC est absent
    (MyHeritage exporte les résidences en ADDR au lieu de PLAC)."""
    a = _premier(noeud, "ADDR")
    if not a:
        return ""
    adr1 = _premier(a, "ADR1")
    return (_fusion_texte(adr1).strip() if adr1 else _fusion_texte(a).strip())


# Événements GEDCOM gérés EN PLUS de BIRT/DEAT (personne) et MARR (famille).
# Ils sont importés dans ind/fam["evenements"] et ré-exportés tels quels
# (avec leur tag) -> aller-retour sans perte pour ces événements de vie.
# Attributs individuels (GEDCOM INDIVIDUAL_ATTRIBUTE_STRUCTURE) : contrairement
# aux événements, leur VALEUR est portée par la ligne du tag (ex. « 1 TITL Baron »).
# OCCU/RESI sont gérés à part (professions / résidences).

def _evenement_generique(noeud):
    """Événement complet : {type, date, lieu, valeur, note?, citations?}.
    Sert aux événements de vie (baptême, sépulture, divorce...) que l'on
    conserve tels quels pour l'aller-retour GEDCOM. Le tag GEDCOM est stocké
    dans le champ `type` (schéma cible : evenements[{type,date,lieu,valeur,…}])."""
    ev = {"type": noeud["tag"], "date": "", "lieu": "", "valeur": ""}
    # valeur portée par la ligne du tag (attributs : « 1 TITL Baron », descripteur EVEN…)
    val = (noeud.get("valeur") or "").strip()
    if val:
        ev["valeur"] = val
    d = _premier(noeud, "DATE")
    if d:
        brut = _fusion_texte(d).strip()
        ev["date"] = _normaliser_date(brut)
        # Conserve la date républicaine d'origine (sinon perdue) : réémise à
        # l'export pour un aller-retour fidèle.
        if ev["date"] != brut and "@#DFRENCH" in brut.upper():
            ev["date_rep"] = brut
        heure_node = _premier(d, "_TIME")   # heure du fait (extension Arboriane)
        if heure_node:
            h = (heure_node.get("valeur") or "").strip()
            if h:
                ev["heure"] = h
    p = _premier(noeud, "PLAC")
    if p:
        ev["lieu"] = _fusion_texte(p).strip()
        c = _lire_coords(p)
        if c:
            ev["_coords"] = c
    if not ev["lieu"]:
        ev["lieu"] = _lieu_depuis_addr(noeud)
    # précision libre du GEDCOM (TYPE) : conservée dans la note pour ne rien perdre
    t = _premier(noeud, "TYPE")
    if t:
        precision = _fusion_texte(t).strip()
        if precision:
            ev["precision"] = precision
    caus = _premier(noeud, "CAUS")
    if caus:
        cause = _fusion_texte(caus).strip()
        if cause:
            ev["cause"] = cause
    n = _premier(noeud, "NOTE")
    if n:
        ev["note"] = _lire_note(n)
    cites = _citations(noeud)
    if cites:
        ev["citations"] = cites
    return ev

def _nom(valeur):
    """'Jean Pierre /DUPONT/ Jr' -> ('Jean Pierre', 'DUPONT', 'Jr').
    Le 3e élément est le suffixe (NSFX) placé après le nom dans la ligne NAME."""
    m = re.match(r"^(.*?)/([^/]*)/(.*)$", valeur)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return valeur.strip(), "", ""
