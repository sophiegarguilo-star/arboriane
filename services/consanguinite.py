# -*- coding: utf-8 -*-
"""
Consanguinité — coefficient de consanguinité de l'enfant d'un couple.

Méthode des chemins : pour chaque ancêtre commun A aux deux conjoints, et pour
chaque paire de chemins (l1 depuis le conjoint 1, l2 depuis le conjoint 2) menant
à A, la contribution est (1/2)^(l1 + l2 + 1). Le coefficient F est la somme de
toutes ces contributions. (On néglige la consanguinité propre de A — usage courant.)

Ex. : enfant de deux vrais frère et sœur → F = 0,25.

Service pur ; garde anti-cycle sur chaque chemin.
"""

from core import modele
from core.modele import nom_complet, periode

MAXGEN = 20


def _chemins(donnees, pid, maxgen):
    """{ancetre_id: [longueurs de chemin]} depuis pid (inclus, longueur 0)."""
    resultat = {}

    def rec(cur, longueur, chemin):
        if not cur or longueur > maxgen or cur in chemin:
            return
        resultat.setdefault(cur, []).append(longueur)
        pere, mere = modele.parents(donnees, cur)
        chemin2 = chemin | {cur}
        rec(pere, longueur + 1, chemin2)
        rec(mere, longueur + 1, chemin2)

    rec(pid, 0, frozenset())
    return resultat


def coefficient(donnees, id_a, id_b, maxgen=MAXGEN):
    """Coefficient de consanguinité de l'enfant du couple (a, b). None si un
    identifiant est inconnu ou si a == b."""
    inds = donnees["individus"]
    if id_a == id_b or id_a not in inds or id_b not in inds:
        return None

    ca = _chemins(donnees, id_a, maxgen)
    cb = _chemins(donnees, id_b, maxgen)
    communs = set(ca) & set(cb)

    f = 0.0
    details = []
    for anc in communs:
        contrib = 0.0
        for l1 in ca[anc]:
            for l2 in cb[anc]:
                contrib += 0.5 ** (l1 + l2 + 1)
        f += contrib
        details.append({"id": anc, "nom": nom_complet(inds.get(anc, {})),
                        "periode": periode(inds.get(anc, {})),
                        "contribution": contrib})
    details.sort(key=lambda d: -d["contribution"])

    return {
        "a": id_a, "a_nom": nom_complet(inds.get(id_a, {})),
        "b": id_b, "b_nom": nom_complet(inds.get(id_b, {})),
        "coefficient": f,
        "pourcentage": round(f * 100, 4),
        "consanguin": f > 0,
        "nb_ancetres_communs": len(communs),
        "ancetres_communs": details,
    }
