# -*- coding: utf-8 -*-
"""
Export d'un RAMEAU — l'ascendance OU la descendance d'une personne seulement.

Construit une sous-base (copie profonde filtrée) ne contenant que la personne
choisie et ses ancêtres (via parents récursifs) OU ses descendants (via
enfants), plus les familles qui les relient et les sources citées, puis exporte
en GEDCOM 5.5.1. Le fichier .ged est écrit dans le dossier Exports/ de l'espace
actif. Bibliothèque standard uniquement (deepcopy).
"""

import copy

from core import gedcom, modele
from core.espace import chemins
from core.fichiers import dans, horodatage, nom_sur


def _ascendants(donnees, pid, generations):
    """Ensemble des ids : pid + ses ancêtres. Anti-cycle par le chemin."""
    vus = set()

    def remonter(ident, niveau):
        if not ident or ident in vus or ident not in donnees["individus"]:
            return
        if generations is not None and niveau > generations:
            return
        vus.add(ident)
        pere, mere = modele.parents(donnees, ident)
        remonter(pere, niveau + 1)
        remonter(mere, niveau + 1)

    remonter(pid, 0)
    return vus


def _descendants(donnees, pid, generations):
    """Ensemble des ids : pid + sa descendance. Anti-cycle par l'ensemble vu."""
    vus = set()

    def descendre(ident, niveau):
        if not ident or ident in vus or ident not in donnees["individus"]:
            return
        if generations is not None and niveau > generations:
            return
        vus.add(ident)
        for enfant in modele.enfants(donnees, ident):
            descendre(enfant, niveau + 1)

    descendre(pid, 0)
    return vus


def _sous_base(donnees, ids):
    """Fabrique une base autonome limitée aux individus de `ids`, avec les
    familles qui les relient (au moins deux membres retenus, ou un parent
    retenu) et les sources citées par ce sous-ensemble."""
    inds = {i: copy.deepcopy(donnees["individus"][i])
            for i in ids if i in donnees["individus"]}

    # Familles : on ne garde une famille que si un membre RETENU y figure ;
    # on filtre ses rôles/enfants aux seuls individus retenus (pas d'orphelins).
    familles = {}
    for fid, fam in donnees["familles"].items():
        mari = fam.get("mari") if fam.get("mari") in inds else ""
        epouse = fam.get("epouse") if fam.get("epouse") in inds else ""
        enfants = [e for e in fam.get("enfants", []) if e in inds]
        if not mari and not epouse and not enfants:
            continue
        f = copy.deepcopy(fam)
        f["mari"], f["epouse"], f["enfants"] = mari, epouse, enfants
        familles[fid] = f

    # Sources citées par les individus/familles retenus (citations + personnes).
    sids = set()

    def _rec_cites(cites):
        for c in cites or []:
            s = c.get("source")
            if s:
                sids.add(s)

    for ind in inds.values():
        _rec_cites(ind.get("citations"))
        for evt in ("naissance", "deces"):
            e = ind.get(evt)
            if isinstance(e, dict):
                _rec_cites(e.get("citations"))
        for e in ind.get("evenements", []):
            _rec_cites(e.get("citations"))
        for r in ind.get("residences", []):
            _rec_cites(r.get("citations"))
    for fam in familles.values():
        m = fam.get("mariage")
        if isinstance(m, dict):
            _rec_cites(m.get("citations"))
        for e in fam.get("evenements", []):
            _rec_cites(e.get("citations"))

    sources = {}
    for sid, src in donnees.get("sources", {}).items():
        tague = any(p.get("id") in inds for p in src.get("personnes", []))
        if sid in sids or tague:
            s = copy.deepcopy(src)
            s["personnes"] = [p for p in s.get("personnes", []) if p.get("id") in inds]
            sources[sid] = s

    sous = {
        "individus": inds,
        "familles": familles,
        "sources": sources,
        "lieux": copy.deepcopy(donnees.get("lieux", {})),
        "meta": {"source": "export rameau"},
    }
    modele.garantir_cles(sous)
    return sous


def exporter_rameau(app, personne_id, sens="ascendance", generations=None):
    """Construit la sous-base (ascendance ou descendance de personne_id), l'exporte
    en GEDCOM et l'écrit dans Exports/. Renvoie (chemin, texte).

    sens ∈ {"ascendance", "descendance"}. generations=None : sans limite."""
    if not app.base:
        raise ValueError("Aucun arbre ouvert.")
    if not app.espace_chemin:
        raise ValueError("Aucun arbre ouvert.")
    donnees = app.base.donnees
    if personne_id not in donnees["individus"]:
        raise ValueError("Personne introuvable : %s" % personne_id)
    if sens not in ("ascendance", "descendance"):
        raise ValueError("Sens inconnu : %s" % sens)
    if generations is not None:
        try:
            generations = int(generations)
        except (TypeError, ValueError):
            generations = None

    if sens == "ascendance":
        ids = _ascendants(donnees, personne_id, generations)
    else:
        ids = _descendants(donnees, personne_id, generations)

    sous = _sous_base(donnees, ids)
    texte = gedcom.exporter(sous)

    ind = donnees["individus"][personne_id]
    nom = nom_sur(modele.nom_complet(ind), "personne")
    c = chemins(app.espace_chemin)
    cible = dans(c["exports"], "%s_%s_%s.ged" % (nom, sens, horodatage()))
    with open(cible, "w", encoding="utf-8") as f:
        f.write(texte)
    return cible, texte
