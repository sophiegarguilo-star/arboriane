# -*- coding: utf-8 -*-
"""
Index des professions — regroupe les personnes par métier.

(Les index lieux / patronymes / prénoms sont déjà produits par statistiques.py ;
seul l'index des métiers manquait.)
"""

from core.modele import nom_complet, periode


def index(donnees, exclure=None):
    """{ metiers: [{metier, nb, personnes}], total_metiers } trié par fréquence.
    `exclure` : ensemble d'id à ignorer (ex. personnes hors famille)."""
    exclure = exclure or set()
    par_metier = {}
    for pid, ind in donnees["individus"].items():
        if pid in exclure:
            continue
        vus = set()
        for prof in ind.get("professions", []):
            val = (prof.get("valeur") if isinstance(prof, dict) else str(prof)).strip()
            cle = val.lower()
            if val and cle not in vus:
                vus.add(cle)
                par_metier.setdefault(val, []).append(
                    {"id": pid, "nom": nom_complet(ind), "periode": periode(ind)})
    metiers = [{"metier": m, "nb": len(ps),
                "personnes": sorted(ps, key=lambda x: x["nom"].lower())}
               for m, ps in par_metier.items()]
    metiers.sort(key=lambda x: (-x["nb"], x["metier"].lower()))
    return {"total_metiers": len(metiers),
            "total_personnes": sum(m["nb"] for m in metiers),
            "metiers": metiers}
