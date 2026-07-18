# -*- coding: utf-8 -*-
"""
Annexes du livre : chronologie de vie (frise) et index (noms & lieux).

Comme le reste, purement descriptif : uniquement des événements datés réels.
"""

from core import modele
from services import aboville as aboville_svc


def _annee(datestr):
    return modele.annee_naissance({"naissance": {"date": datestr or ""}})


def frise(base, f, masquer=True):
    """Événements datés de la vie du référent, triés par année :
    [{annee, texte}]. Les événements sans année ne figurent pas dans une frise."""
    ind = base.donnees["individus"].get(f["id"]) or {}
    ev = []

    def add(an, txt):
        if an:
            ev.append((an, txt))

    naiss = ind.get("naissance") or {}
    add(modele.annee_naissance(ind),
        "Naissance" + (" à %s" % naiss["lieu"] if naiss.get("lieu") else ""))
    for p in ind.get("professions", []):
        if p.get("valeur"):
            add(_annee(p.get("date")), "Profession : %s" % p["valeur"])
    for r in ind.get("residences", []):
        if r.get("lieu"):
            add(_annee(r.get("date")), "Installation à %s" % r["lieu"])
    for u in f.get("unions", []):
        mar = u.get("mariage") or {}
        conj = u.get("conjoint") or {}
        nom = conj.get("nom", "")
        if masquer and conj.get("id"):
            ci = base.donnees["individus"].get(conj["id"])
            if ci and modele.est_vivant_presume(ci):
                nom = "———"
        txt = "Mariage" + (" avec %s" % nom if nom else "")
        if mar.get("lieu"):
            txt += " à %s" % mar["lieu"]
        add(_annee(mar.get("date")), txt)
    dec = ind.get("deces") or {}
    add(modele.annee_deces(ind),
        "Décès" + (" à %s" % dec["lieu"] if dec.get("lieu") else ""))

    ev.sort(key=lambda x: x[0])
    return [{"annee": a, "texte": t} for a, t in ev]


def _cle_nom(nom):
    parts = nom.rsplit(" ", 1)
    return (parts[-1].lower(), parts[0].lower()) if len(parts) == 2 else (nom.lower(), "")


def index(base, f, masquer=True, generations=8):
    """Index alphabétique des personnes citées (aïeux + descendance + proches)
    et des lieux, en excluant les personnes présumées vivantes si demandé."""
    donnees = base.donnees
    inds = donnees["individus"]
    ids = {f["id"]}
    for pid in modele.ascendance_sosa(donnees, f["id"], generations).values():
        ids.add(pid)
    d = aboville_svc.descendance(donnees, f["id"], generations) or {"personnes": []}
    for p in d["personnes"]:
        ids.add(p["id"])

    noms, lieux = set(), set()
    for pid in ids:
        ind = inds.get(pid) or {}
        if masquer and modele.est_vivant_presume(ind):
            continue
        nom = modele.nom_complet(ind)
        if nom:
            noms.add(nom)
        for ev in (ind.get("naissance"), ind.get("deces")):
            lieu = (ev or {}).get("lieu", "").strip()
            if lieu:
                lieux.add(lieu)
    return {"noms": sorted(noms, key=_cle_nom),
            "lieux": sorted(lieux, key=str.lower)}
