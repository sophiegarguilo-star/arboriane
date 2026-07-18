# -*- coding: utf-8 -*-
"""
Chronologie agrégée (L11) — frise multi-personnes et « contemporains ».

Service pur : calcule des INTERVALLES DE VIE (naissance → décès, décès estimé si
inconnu) et leurs CHEVAUCHEMENTS. Deux usages :
  • `frise(ids)` : données pour une frise horizontale de plusieurs personnes.
  • `contemporains(pid)` : qui vivait à la même époque qu'une personne, avec un
    drapeau « lié » (dans sa parenté proche : ancêtres, descendants, conjoints,
    fratrie) ou « sans lien ».

GEDCOM-first : rien n'est persisté ; tout se recalcule depuis les dates saisies.
"""

from core import modele

ESPERANCE = 85          # espérance de vie par défaut pour estimer une borne absente


def _intervalle(ind):
    """(debut, fin, estime) en années, ou None si aucune année connue.
    Si une seule borne est connue, l'autre est estimée (± ESPERANCE)."""
    nb, nd = modele.annee_naissance(ind), modele.annee_deces(ind)
    if nb is not None and nd is not None:
        return (nb, max(nd, nb), False)
    if nb is not None:
        return (nb, nb + ESPERANCE, True)
    if nd is not None:
        return (nd - ESPERANCE, nd, True)
    return None


def _ligne(pid, ind):
    iv = _intervalle(ind)
    if not iv:
        return None
    deb, fin, estime = iv
    return {"id": pid, "nom": modele.nom_complet(ind), "sexe": ind.get("sexe", "U"),
            "debut": deb, "fin": fin, "estime": estime,
            "naissance": modele.annee_naissance(ind),
            "deces": modele.annee_deces(ind)}


def frise(donnees, ids):
    """Données d'une frise multi-personnes : une barre [debut, fin] par personne,
    triées par début, plus l'amplitude globale (min/max)."""
    inds = donnees["individus"]
    lignes = [l for l in (_ligne(pid, inds[pid]) for pid in ids if pid in inds) if l]
    lignes.sort(key=lambda x: (x["debut"], x["fin"]))
    if not lignes:
        return {"personnes": [], "min": None, "max": None}
    return {"personnes": lignes,
            "min": min(l["debut"] for l in lignes),
            "max": max(l["fin"] for l in lignes)}


def _parente_proche(donnees, pid, generations=6):
    """Ensemble des ids « liés » à pid : ancêtres, descendants, conjoints,
    fratrie (sert à distinguer contemporains apparentés vs sans lien)."""
    liee = set(modele.ascendance_sosa(donnees, pid, generations).values())
    for c, _ in modele.conjoints(donnees, pid):
        if c:
            liee.add(c)
    liee.update(modele.freres_soeurs(donnees, pid))
    pile, vus = [pid], set()          # descendance
    while pile:
        x = pile.pop()
        if x in vus:
            continue
        vus.add(x)
        for e in modele.enfants(donnees, x):
            liee.add(e)
            pile.append(e)
    liee.discard(pid)
    return liee


def contemporains(donnees, pid):
    """Personnes dont la vie chevauche celle de pid. Chaque contemporain :
    {id, nom, sexe, chevauchement:[a,b], annees, lie, naissance, deces}.
    None si pid inconnu ou sans aucune date."""
    inds = donnees["individus"]
    base = inds.get(pid)
    iv = _intervalle(base) if base else None
    if not iv:
        return None
    d0, f0, _ = iv
    liee = _parente_proche(donnees, pid)
    out = []
    for oid, ind in inds.items():
        if oid == pid:
            continue
        ov = _intervalle(ind)
        if not ov:
            continue
        a, b = max(d0, ov[0]), min(f0, ov[1])
        if a > b:                     # pas de chevauchement
            continue
        out.append({"id": oid, "nom": modele.nom_complet(ind),
                    "sexe": ind.get("sexe", "U"), "chevauchement": [a, b],
                    "annees": b - a, "lie": oid in liee,
                    "naissance": modele.annee_naissance(ind),
                    "deces": modele.annee_deces(ind)})
    out.sort(key=lambda x: (-x["annees"], x["chevauchement"][0]))
    return {"id": pid, "nom": modele.nom_complet(base), "intervalle": [d0, f0],
            "nb_lies": sum(1 for x in out if x["lie"]),
            "nb_sans_lien": sum(1 for x in out if not x["lie"]),
            "contemporains": out}
