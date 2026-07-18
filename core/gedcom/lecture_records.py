# -*- coding: utf-8 -*-
"""GEDCOM — construction des ENREGISTREMENTS à partir de leur noeud d'arbre :
`lire_indi` (INDI), `lire_fam` (FAM), `lire_sour` (SOUR).

Extrait de lecture.importer pour garder chaque fichier court. AUCUN changement de
comportement : ce sont les mêmes blocs, déplacés tels quels. Les post-traitements
(réconciliation de la parenté, sources en ligne, coordonnées) restent dans
lecture.py, car ils raisonnent sur l'ensemble des enregistrements, pas sur un seul.
"""
import os

from core.gedcom.commun import *
from core.gedcom.champs import *


def lire_indi(rec):
    """Construit l'individu (dict au schéma cible) depuis un noeud « 0 @I@ INDI »."""
    ident = _pointeur(rec["xref"])
    ind = {
        "id": ident,
        "sexe": "U",
        "prenoms": "",
        "nom": "",
        "prenom_principal": "",
        "prenoms_secondaires": "",
        "nom_particule": "",
        "nom_marital": "",
        "surnom": "",   # surnom / nom « dit » : NICK
        "noms_alternatifs": [],
        "naissance": {"date": "", "lieu": ""},
        "deces": {"date": "", "lieu": ""},
        "professions": [],   # [{valeur}] (schéma cible)
        "residences": [],    # domiciles datés : RESI (date/lieu/type)
        "associations": [],  # personnes liées hors filiation : ASSO/RELA
        "refn": "",   # numéro de référence utilisateur : REFN
        "resn": "",   # confidentialité : RESN (confidential/privacy/locked)
        "note": "",
        "tags": [],    # tags/statuts de recherche (façon Filae) : _TAG
        "pistes": [],  # pistes de recherche à chercher : _TODO (portable)
        "evenements": [],   # événements de vie (baptême, sépulture...)
        "medias": [],
        "citations": [],
        "famc": [],    # familles où l'individu est enfant
        "fams": [],    # familles où l'individu est parent
    }
    premier_nom = True
    for enf in rec["enfants"]:
        tag = enf["tag"]
        if tag == "NAME":
            prenoms, nom, suffixe = _nom(_fusion_texte(enf))
            if premier_nom:
                # sous-champs structurés (GIVN/SPFX/NPFX/NSFX/_RUFNAME/_MARNM)
                spfx = _premier(enf, "SPFX")
                part = _fusion_texte(spfx).strip() if spfx else ""
                # la particule est parfois collée en fin de prénoms -> la retirer
                if part and prenoms.lower().endswith(" " + part.lower()):
                    prenoms = prenoms[:-(len(part) + 1)].strip()
                givn = _premier(enf, "GIVN")
                if givn:
                    prenoms = _fusion_texte(givn).strip() or prenoms
                ruf = _premier(enf, "_RUFNAME")
                marn = _premier(enf, "_MARNM")
                npfx = _premier(enf, "NPFX")
                nsfx = _premier(enf, "NSFX")
                ind["prenoms"], ind["nom"] = prenoms, nom
                ind["nom_particule"] = part
                ind["nom_prefixe"] = _fusion_texte(npfx).strip() if npfx else ""
                # suffixe : tag NSFX prioritaire, sinon la fin de la ligne NAME
                ind["nom_suffixe"] = (_fusion_texte(nsfx).strip() if nsfx else suffixe)
                if ruf:
                    ind["prenom_principal"] = _fusion_texte(ruf).strip()
                if marn:
                    ind["nom_marital"] = _fusion_texte(marn).strip()
                nick = _premier(enf, "NICK")
                if nick:
                    ind["surnom"] = _fusion_texte(nick).strip()
                premier_nom = False
            else:
                alt = {"prenoms": prenoms, "nom": nom}
                typ = _premier(enf, "TYPE")
                if typ:
                    alt["type"] = _fusion_texte(typ).strip()
                ind["noms_alternatifs"].append(alt)
        elif tag == "SEX":
            v = enf["valeur"].strip().upper()
            ind["sexe"] = v if v in ("M", "F", "X", "N") else "U"
        elif tag == "_SOSA":
            v = _fusion_texte(enf).strip()
            if v.isdigit():
                ind["sosa"] = int(v)
        elif tag == "BIRT":
            ind["naissance"] = _evenement(enf)
        elif tag == "DEAT":
            ind["deces"] = _evenement(enf)
        elif tag == "OCCU":
            prof = _fusion_texte(enf).strip()
            if prof:
                ind["professions"].append({"valeur": prof})
        elif tag == "RESI":
            res = _evenement(enf)
            t = _premier(enf, "TYPE")
            res["type"] = _fusion_texte(t).strip() if t else ""
            ind["residences"].append(res)
        elif tag == "OBJE":
            fobj = _premier(enf, "FILE")
            fichier = _fusion_texte(fobj).strip() if fobj else ""
            if fichier:
                titl = _premier(enf, "TITL")
                prim = _premier(enf, "_PRIM")
                ind["medias"].append({
                    "fichier": fichier,
                    "titre": _fusion_texte(titl).strip() if titl else "",
                    "principale": bool(prim and _fusion_texte(prim)
                                       .strip().upper().startswith("Y")),
                })
        elif tag == "_TAG":
            v = _fusion_texte(enf).strip()
            if v:
                ind["tags"].append(v)
        elif tag == "_TODO":
            piste = _fusion_texte(enf).strip()
            if piste:
                stat = _premier(enf, "_STAT")
                faite = bool(stat and "done" in _fusion_texte(stat).strip().lower())
                ind["pistes"].append({"texte": piste, "faite": faite})
        elif tag == "ASSO":
            aid = _pointeur(enf.get("valeur"))
            if aid:
                rela = _premier(enf, "RELA")
                ind["associations"].append(
                    {"id": aid, "relation": _fusion_texte(rela).strip() if rela else ""})
        elif tag == "REFN":
            ind["refn"] = _fusion_texte(enf).strip()
        elif tag == "RESN":
            ind["resn"] = _fusion_texte(enf).strip().lower()
        elif tag == "NOTE":
            txt = _lire_note(enf)
            ind["note"] = (ind["note"] + "\n" + txt).strip() if ind["note"] else txt
        elif tag == "FAMC":
            fid = _pointeur(enf["valeur"])
            if fid:
                ind["famc"].append(fid)
        elif tag == "FAMS":
            fid = _pointeur(enf["valeur"])
            if fid:
                ind["fams"].append(fid)
        elif tag in TAGS_EVT_INDI:
            ind["evenements"].append(_evenement_generique(enf))
        elif tag.startswith("_"):
            # tag privé inconnu (_MILT, etc.) : conservé comme événement
            # générique plutôt que jeté → aller-retour sans perte.
            ind["evenements"].append(_evenement_generique(enf))
    # citations rattachées directement à la personne (non à un événement)
    cites = _citations(rec)
    if cites:
        ind["citations"] = cites
    return ind


def lire_fam(rec):
    """Construit la famille (dict au schéma cible) depuis un noeud « 0 @F@ FAM »."""
    ident = _pointeur(rec["xref"])
    fam = {
        "id": ident,
        "mari": "",
        "epouse": "",
        "enfants": [],
        "mariage": {"date": "", "lieu": ""},
        "evenements": [],   # événements du couple (divorce, fiançailles...)
        "note": "",
    }
    for enf in rec["enfants"]:
        tag = enf["tag"]
        if tag == "HUSB":
            fam["mari"] = _pointeur(enf["valeur"])
        elif tag == "WIFE":
            fam["epouse"] = _pointeur(enf["valeur"])
        elif tag == "CHIL":
            cid = _pointeur(enf["valeur"])
            if cid:
                fam["enfants"].append(cid)
        elif tag == "MARR":
            # Un couple = un mariage principal. Un 2e MARR (ex. saisi par
            # erreur/test sur un site) est gardé comme événement, sans
            # écraser le mariage déjà lu.
            if fam["mariage"].get("date") or fam["mariage"].get("lieu"):
                fam["evenements"].append(_evenement_generique(enf))
            else:
                fam["mariage"] = _evenement(enf)
        elif tag == "NOTE":
            fam["note"] = _lire_note(enf)
        elif tag in TAGS_EVT_FAM:
            fam["evenements"].append(_evenement_generique(enf))
    return fam


def lire_sour(rec, repo_rx, depots_imp):
    """Construit la source (dict au schéma cible) depuis un noeud « 0 @S@ SOUR ».

    `repo_rx` (xref REPO -> depot_id) et `depots_imp` (depot_id -> entité) servent
    à résoudre SOUR.REPO vers un dépôt déjà lu. La note de repli n'est PAS retirée
    ici (elle l'est dans importer, via _retirer_repli_source, après matérialisation).
    """
    sid = _pointeur(rec["xref"])
    src = {"id": sid, "titre": "", "type": "", "date": "", "lieu": "",
           "ville": "", "pays": "", "auteur": "", "depot": "", "cote": "",
           "abbr": "", "publ": "", "ark": "", "note": "", "fichier": "",
           "fichiers": [], "transcription": "", "personnes": []}
    for enf in rec["enfants"]:
        if enf["tag"] == "TITL":
            src["titre"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "AUTH":
            src["auteur"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "REPO":
            rx = _pointeur(enf.get("valeur"))
            did = repo_rx.get(rx)
            if did:
                src["depot"] = depots_imp[did].get("nom", "")
                src["depot_id"] = did
            caln = _premier(enf, "CALN")
            if caln:
                src["cote"] = _fusion_texte(caln).strip()
        elif enf["tag"] == "DATA":
            # place standard : DATA.EVEN(.DATE/.PLAC) ; DATA.TEXT = transcription
            ev = _premier(enf, "EVEN")
            if ev:
                if not src["type"]:
                    src["type"] = _fusion_texte(ev).strip()
                d, p = _premier(ev, "DATE"), _premier(ev, "PLAC")
                if d and not src["date"]:
                    src["date"] = _fusion_texte(d).strip()
                if p and not src["lieu"]:
                    src["lieu"] = _fusion_texte(p).strip()
            tx = _premier(enf, "TEXT")
            if tx and not src["transcription"]:
                src["transcription"] = _fusion_texte(tx).strip()
        elif enf["tag"] == "TEXT":
            if not src["transcription"]:
                src["transcription"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "_TYPE":      # legacy Arboriane
            src["type"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "_DATE":      # legacy Arboriane
            src["date"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "_PLAC":      # legacy Arboriane
            src["lieu"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "ABBR":
            src["abbr"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "PUBL":
            src["publ"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "_FIAB":
            src["fiabilite"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "_STATUT":
            src["statut"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "_PAGE":
            src["page"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "_VILLE":
            src["ville"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "_PAYS":
            src["pays"] = _fusion_texte(enf).strip()
        elif enf["tag"] in ("WWW", "_ARK", "_LINK"):
            if not src["ark"]:
                src["ark"] = _fusion_texte(enf).strip()
        elif enf["tag"] == "NOTE":
            src["note"] = _lire_note(enf)
        elif enf["tag"] == "OBJE":
            f = _premier(enf, "FILE")
            if f:
                chemin = _fusion_texte(f).strip()
                # On stocke le NOM du fichier (cohérent avec le reste) ; le chemin
                # complet éventuel sert à l'import local du scan (import_medias).
                src["fichiers"].append(os.path.basename(chemin.replace("\\", "/")))
                if "\\" in chemin or "/" in chemin:
                    src.setdefault("_chemins_scans", []).append(chemin)
    if src["fichiers"]:
        src["fichier"] = src["fichiers"][0]   # image primaire (compat)
    return src
