# -*- coding: utf-8 -*-
"""
Dépôts d'archives — le 3ᵉ niveau du sourçage : Dépôt → Source → Citation.

Un dépôt (Archives départementales, mairie, site, bibliothèque…) devient une
ENTITÉ réutilisable et éditable, référencée par les sources via ``depot_id``.
Le nom du dépôt reste aussi porté par la source (``depot``) pour rester
GEDCOM-first (balise REPO) ; l'entité ajoute type, lieu, site web et note.

Suppression et perte : jamais destructif — retirer un dépôt laisse le nom en
clair sur les sources (``depot``), donc rien n'est perdu.
"""

from core import modele

TYPES = ("Archives départementales", "Archives municipales", "Archives nationales",
         "Mairie", "Site en ligne", "Bibliothèque", "Archives privées", "Autre")


def _depots(donnees):
    return donnees.setdefault("depots", {})


def nom(donnees, src):
    """Nom du dépôt d'une source : via l'entité (depot_id) sinon le texte libre."""
    d = _depots(donnees).get(src.get("depot_id"))
    return d.get("nom", "") if d else (src.get("depot") or "").strip()


def lister(donnees):
    """Dépôts + nombre de sources rattachées, triés par nom."""
    dep = _depots(donnees)
    compte = {}
    for src in donnees.get("sources", {}).values():
        did = src.get("depot_id")
        if did in dep:
            compte[did] = compte.get(did, 0) + 1
    out = [dict(d, nb_sources=compte.get(did, 0)) for did, d in dep.items()]
    out.sort(key=lambda x: (x.get("nom") or "").lower())
    return {"total": len(out), "depots": out}


def creer(donnees, champs):
    dep = _depots(donnees)
    did = modele.nouvel_id(dep, "D")
    d = {"id": did}
    for cle in ("nom", "type", "lieu", "www", "note"):
        d[cle] = (champs.get(cle) or "").strip()
    dep[did] = d
    return d


def modifier(donnees, did, champs):
    d = _depots(donnees).get(did)
    if not d:
        return None
    for cle in ("nom", "type", "lieu", "www", "note"):
        if cle in champs:
            d[cle] = (champs[cle] or "").strip()
    # cohérence GEDCOM : propager le nom aux sources liées
    for src in donnees.get("sources", {}).values():
        if src.get("depot_id") == did:
            src["depot"] = d.get("nom", "")
    return d


def supprimer(donnees, did):
    """Retire un dépôt. Les sources qui le citaient gardent leur nom en clair
    (``depot``) mais perdent le lien (``depot_id``) — aucune perte de donnée."""
    dep = _depots(donnees)
    if did not in dep:
        return False
    for src in donnees.get("sources", {}).values():
        if src.get("depot_id") == did:
            src.pop("depot_id", None)
    del dep[did]
    return True


def assigner_source(donnees, sid, did):
    """Rattache (ou détache si did vide) une source à un dépôt. Met le nom en
    clair à jour. Lève ValueError si le dépôt est inconnu."""
    src = donnees.get("sources", {}).get(sid)
    if not src:
        return None
    if did:
        d = _depots(donnees).get(did)
        if not d:
            raise ValueError("Dépôt inconnu : %s" % did)
        src["depot_id"] = did
        src["depot"] = d.get("nom", "")
    else:
        src.pop("depot_id", None)
    return src


def promouvoir(donnees):
    """Crée une entité dépôt pour chaque nom distinct présent en texte libre sur
    les sources, et lie les sources (depot_id). Idempotent (n'invente pas de
    doublon). Renvoie {crees, lies}."""
    dep = _depots(donnees)
    par_nom = {(d.get("nom") or "").strip().lower(): did
               for did, d in dep.items() if (d.get("nom") or "").strip()}
    crees = lies = 0
    for src in donnees.get("sources", {}).values():
        if src.get("depot_id") in dep:
            continue
        nom_dep = (src.get("depot") or "").strip()
        if not nom_dep:
            continue
        cle = nom_dep.lower()
        did = par_nom.get(cle)
        if not did:
            did = creer(donnees, {"nom": nom_dep})["id"]
            par_nom[cle] = did
            crees += 1
        src["depot_id"] = did
        lies += 1
    return {"crees": crees, "lies": lies}
