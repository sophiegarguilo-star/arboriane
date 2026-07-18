# -*- coding: utf-8 -*-
"""
Numérotation d'Aboville — numérote la descendance d'une personne.

La souche porte « 1 » ; ses enfants « 1.1 », « 1.2 »… ; les enfants de « 1.2 »
deviennent « 1.2.1 », « 1.2.2 »… La profondeur du point donne la génération.

Service pur ; garde anti-cycle ; enfants ordonnés par année de naissance.
"""

from core import modele
from core.modele import nom_complet, periode, annee_naissance


def descendance(donnees, racine_id, max_prof=12):
    """Liste { id, nom, numero, generation } de la descendance, souche incluse.
    None si la racine est inconnue."""
    inds = donnees["individus"]
    if not racine_id or racine_id not in inds:
        return None

    out = []

    def rec(pid, numero, prof, chemin):
        if not pid or pid in chemin or prof > max_prof:
            return
        ind = inds.get(pid, {})
        out.append({"id": pid, "nom": nom_complet(ind), "periode": periode(ind),
                    "numero": numero, "generation": prof})
        enfants = sorted(modele.enfants(donnees, pid),
                         key=lambda e: (annee_naissance(inds.get(e, {})) or 9999))
        chemin2 = chemin | {pid}
        for i, e in enumerate(enfants, start=1):
            rec(e, "%s.%d" % (numero, i), prof + 1, chemin2)

    rec(racine_id, "1", 0, frozenset())
    return {"racine": racine_id, "racine_nom": nom_complet(inds.get(racine_id, {})),
            "total": len(out), "personnes": out}
