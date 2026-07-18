# -*- coding: utf-8 -*-
"""
Implexe — mesure du recouvrement des ancêtres.

Il y a implexe quand une même personne occupe plusieurs positions Sosa dans une
ascendance (mariages entre parents, cousinages). On en donne le taux global, le
détail par génération, et la liste des ancêtres à Sosa multiples.

Service pur : réutilise modele.ascendance_sosa ; ne rend rien graphiquement (le
grisage des branches dans l'arbre est un chantier distinct, après refactor).
"""

import math

from core import modele
from core.modele import ascendance_sosa, nom_complet, periode


def _generation(num):
    """Génération d'un numéro Sosa (1 → 0, 2-3 → 1, 4-7 → 2…)."""
    return int(math.floor(math.log2(num))) if num >= 1 else 0


def analyser(donnees, racine_id, generations=10):
    """Taux d'implexe + détail par génération + ancêtres à Sosa multiples.
    Renvoie None si la racine est inconnue."""
    inds = donnees["individus"]
    if not racine_id or racine_id not in inds:
        return None

    table = ascendance_sosa(donnees, racine_id, generations)
    positions = {num: pid for num, pid in table.items() if _generation(num) < generations}

    par_gen = {}
    par_pid = {}
    for num, pid in positions.items():
        par_gen.setdefault(_generation(num), []).append(pid)
        par_pid.setdefault(pid, []).append(num)

    generations_liste = []
    for g in range(generations):
        pids = par_gen.get(g, [])
        distincts = len(set(pids))
        generations_liste.append({
            "generation": g, "positions": len(pids), "distincts": distincts,
            "implexe": len(pids) - distincts,
        })

    multiples = [{
        "id": pid, "nom": nom_complet(inds.get(pid, {})),
        "periode": periode(inds.get(pid, {})),
        "sosas": sorted(nums), "nb": len(nums),
    } for pid, nums in par_pid.items() if len(nums) > 1]
    multiples.sort(key=lambda m: (-m["nb"], m["sosas"][0]))

    total_positions = len(positions)
    distincts = len(set(positions.values()))
    taux = round((total_positions - distincts) * 100 / total_positions, 1) if total_positions else 0.0

    return {
        "racine": racine_id,
        "racine_nom": nom_complet(inds.get(racine_id, {})),
        "taux": taux,
        "total_positions": total_positions,
        "ancetres_distincts": distincts,
        "implexe_total": total_positions - distincts,
        "generations": generations_liste,
        "ancetres_multiples": multiples,
    }
