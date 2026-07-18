# -*- coding: utf-8 -*-
"""
Chapitre « Les aïeux » — ascendance narrée sur N générations (numérotation Sosa).

S'appuie sur services.sosa (déjà éprouvé). Chaque ancêtre reçoit une courte
notice descriptive (naissance, métier, décès), jamais inventée. Un ancêtre qui
réapparaît par implexe (mêmes aïeux des deux côtés) n'est présenté qu'une fois ;
les occurrences suivantes renvoient à son numéro Sosa.
"""

from core import modele
from services import sosa as sosa_svc

MASQUE = "———"
_LABELS = {1: "Les parents", 2: "Les grands-parents", 3: "Les arrière-grands-parents",
           4: "Les trisaïeuls", 5: "Les quadrisaïeuls", 6: "Les quintaïeuls",
           7: "Les sextaïeuls"}


def _label_gen(g):
    return _LABELS.get(g, "%dᵉ génération" % g)


def _evt(verbe, an, lieu):
    bout = verbe
    if an:
        bout += " en %d" % an
    if lieu:
        bout += " à %s" % lieu
    return bout if (an or lieu) else ""


def _notice(ind):
    """Courte notice descriptive d'un ancêtre (sans son nom, porté par l'entrée)."""
    sexe = ind.get("sexe", "U")
    naiss, dec = ind.get("naissance") or {}, ind.get("deces") or {}
    bits = []
    b = _evt(modele.genre(sexe, "né", "née"), modele.annee_naissance(ind),
             (naiss.get("lieu") or "").strip())
    if b:
        bits.append(b)
    profs = [p.get("valeur") for p in ind.get("professions", []) if p.get("valeur")]
    if profs:
        bits.append("de profession %s" % ", ".join(profs))
    d = _evt(modele.genre(sexe, "décédé", "décédée"), modele.annee_deces(ind),
             (dec.get("lieu") or "").strip())
    if d:
        bits.append(d)
    if not bits:
        return ""
    texte = ", ".join(bits)
    return texte[0].upper() + texte[1:] + "."


def chapitre(base, referent, generations=4, masquer=True):
    """Renvoie une liste de générations :
    [{ generation, titre, ancetres: [{sosa, nom, notice, repet}] }]
    `repet` = numéro Sosa de la première occurrence si l'ancêtre est déjà cité."""
    donnees = base.donnees
    generations = max(1, min(8, int(generations)))
    asc = sosa_svc.ascendance(donnees, referent, generations + 1)
    if not asc:
        return []
    vus = {}                                    # id -> premier Sosa (anti-implexe)
    blocs = []
    for gen in asc["generations"]:
        g = gen["generation"]
        if g < 1 or g > generations:
            continue
        ancetres = []
        for p in gen["personnes"]:
            ind = donnees["individus"].get(p["id"], {})
            masque = masquer and modele.est_vivant_presume(ind)
            nom = MASQUE if masque else p["nom"]
            repet = vus.get(p["id"])
            if repet is None:
                vus[p["id"]] = p["sosa"]
            ancetres.append({
                "sosa": p["sosa"], "nom": nom,
                "periode": "" if masque else p.get("periode", ""),
                "notice": "" if (masque or repet) else _notice(ind),
                "repet": repet,
            })
        if ancetres:
            blocs.append({"generation": g, "titre": _label_gen(g), "ancetres": ancetres})
    return blocs
