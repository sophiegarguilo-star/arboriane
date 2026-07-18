# -*- coding: utf-8 -*-
"""
Chapitre « La descendance » — descendance narrée sur N générations (d'Aboville).

Pendant du chapitre « Les aïeux ». S'appuie sur services.aboville. Chaque
descendant reçoit son numéro d'Aboville (1, 1.1, 1.2.3…) et une courte notice
descriptive, jamais inventée. Les personnes présumées vivantes sont masquées
(une descendance récente en compte souvent beaucoup).
"""

from core import modele
from services import aboville as aboville_svc
from services.livre.ascendance import _notice, MASQUE

_LABELS = {1: "Les enfants", 2: "Les petits-enfants",
           3: "Les arrière-petits-enfants", 4: "Les arrière-arrière-petits-enfants"}


def _label_gen(g):
    return _LABELS.get(g, "%dᵉ génération de descendants" % g)


def chapitre(base, referent, generations=3, masquer=True):
    """Renvoie une liste de générations :
    [{ generation, titre, personnes: [{numero, nom, periode, notice}] }]."""
    generations = max(1, min(6, int(generations)))
    d = aboville_svc.descendance(base.donnees, referent, generations)
    if not d:
        return []
    par_gen = {}
    for p in d["personnes"]:
        g = p["generation"]
        if g < 1 or g > generations:          # g == 0 = la souche (déjà le référent)
            continue
        par_gen.setdefault(g, []).append(p)
    blocs = []
    for g in sorted(par_gen):
        personnes = []
        for p in par_gen[g]:
            ind = base.donnees["individus"].get(p["id"], {})
            masque = masquer and modele.est_vivant_presume(ind)
            personnes.append({
                "numero": p["numero"],
                "nom": MASQUE if masque else p["nom"],
                "periode": "" if masque else p.get("periode", ""),
                "notice": "" if masque else _notice(ind),
            })
        if personnes:
            blocs.append({"generation": g, "titre": _label_gen(g), "personnes": personnes})
    return blocs
