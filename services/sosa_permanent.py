# -*- coding: utf-8 -*-
"""
Sosa permanent — fige les numéros Sosa dans la base, relatifs à une personne
racine (le « de-cujus » du dossier).

Le Sosa reste par défaut recalculé à la volée ; ici on le MÉMORISE dans le champ
`sosa` de chaque ancêtre, pour l'afficher/l'exporter (balise GEDCOM `_SOSA`) sans
recalcul et de façon stable. En cas d'implexe, on garde le plus petit numéro.

C'est un simple cache marqué : `effacer` le retire ; la vérité reste la structure
familiale.
"""

from core import modele
from core.modele import nom_complet, periode


def figer(donnees, racine_id, generations=40):
    """Pose `sosa` sur chaque ancêtre de la racine (efface les précédents).
    Renvoie le nombre de personnes numérotées ; 0 si racine inconnue."""
    inds = donnees["individus"]
    if not racine_id or racine_id not in inds:
        return 0
    for ind in inds.values():
        ind.pop("sosa", None)
    table = modele.sosa_par_individu(donnees, racine_id, generations)
    for pid, num in table.items():
        if pid in inds:
            inds[pid]["sosa"] = num
    return len(table)


def effacer(donnees):
    """Retire tous les Sosa figés. Renvoie le nombre de retraits."""
    n = 0
    for ind in donnees["individus"].values():
        if "sosa" in ind:
            del ind["sosa"]
            n += 1
    return n


def lister(donnees):
    """Personnes portant un Sosa figé, triées par numéro."""
    out = [{"id": pid, "nom": nom_complet(ind), "periode": periode(ind),
            "sosa": ind["sosa"]}
           for pid, ind in donnees["individus"].items() if ind.get("sosa")]
    out.sort(key=lambda x: x["sosa"])
    return {"total": len(out), "personnes": out}
