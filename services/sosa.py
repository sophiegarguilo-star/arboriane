# -*- coding: utf-8 -*-
"""
Sosa-Stradonitz — ascendance numérotée d'un de cujus.

Numérotation : 1 = de cujus, 2 = père, 3 = mère, 2n = père de n, 2n+1 = mère.
Fournit l'ascendance par génération, le taux de complétude par génération, et
les « ruptures » (une personne connue dont un parent manque : c'est là qu'il
faut chercher).
"""

import math

from core import modele
from core.modele import ascendance_sosa, parents, nom_complet, periode


def _generation(num):
    """Génération d'un numéro Sosa (1 → 0, 2-3 → 1, 4-7 → 2…)."""
    return int(math.floor(math.log2(num))) if num >= 1 else 0


def numero_sosa(donnees, racine_id, pid, generations=40):
    """Numéro Sosa de `pid` dans l'ascendance de la personne racine, ou None
    si elle n'est pas un ancêtre direct. 1 = la racine elle-même."""
    if not racine_id or racine_id not in donnees["individus"]:
        return None
    table = ascendance_sosa(donnees, racine_id, generations)
    for num, x in table.items():
        if x == pid:
            return num
    return None


def libelle_lien_racine(sosa):
    """Petit libellé du lien à la racine à partir du numéro Sosa."""
    if sosa is None:
        return None
    if sosa == 1:
        return "Personne de référence (racine)"
    g = _generation(sosa)
    noms = {1: "Parent", 2: "Grand-parent", 3: "Arrière-grand-parent",
            4: "Trisaïeul", 5: "Quadrisaïeul", 6: "Quintaïeul"}
    base = noms.get(g, "Ancêtre (%dᵉ génération)" % g)
    return "Ancêtre direct — %s (Sosa %d)" % (base.lower(), sosa)


def ascendance(donnees, de_cujus, generations=10):
    """Ascendance Sosa structurée par génération + complétude + ruptures."""
    inds = donnees["individus"]
    if de_cujus not in inds:
        return None
    table = ascendance_sosa(donnees, de_cujus, generations)

    par_gen = {}
    for num, pid in table.items():
        g = _generation(num)
        if g >= generations:
            continue
        ind = inds.get(pid, {})
        par_gen.setdefault(g, []).append({
            "sosa": num, "id": pid, "nom": nom_complet(ind),
            "sexe": ind.get("sexe", "U"), "periode": periode(ind),
        })
    for g in par_gen:
        par_gen[g].sort(key=lambda x: x["sosa"])

    generations_liste = []
    for g in range(generations):
        connus = len(par_gen.get(g, []))
        attendus = 2 ** g
        generations_liste.append({
            "generation": g, "connus": connus, "attendus": attendus,
            "taux": round(connus * 100 / attendus) if attendus else 0,
            "personnes": par_gen.get(g, []),
        })

    # ruptures : personne connue dont au moins un parent manque (dans la portée)
    ruptures = []
    for num, pid in table.items():
        if _generation(num) >= generations - 1:
            continue
        pere, mere = parents(donnees, pid)
        manquants = []
        if not pere:
            manquants.append(("père", num * 2))
        if not mere:
            manquants.append(("mère", num * 2 + 1))
        for role, sosa_manquant in manquants:
            ruptures.append({
                "sosa": num, "id": pid, "nom": nom_complet(inds.get(pid, {})),
                "manque": role, "sosa_manquant": sosa_manquant,
            })
    ruptures.sort(key=lambda r: r["sosa"])

    total_connus = len({pid for pid in table.values()})
    return {
        "de_cujus": de_cujus,
        "de_cujus_nom": nom_complet(inds.get(de_cujus, {})),
        "generations": generations_liste,
        "total_connus": total_connus,
        "ruptures": ruptures,
    }
