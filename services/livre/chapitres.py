# -*- coding: utf-8 -*-
"""
Chapitres structurés d'un livre (filiation, unions & enfants).

Renvoient des données prêtes à mettre en page (pas de HTML ici) — le masquage
des personnes vivantes est appliqué au niveau des noms.
"""

from core import modele

MASQUE = "———"


def _nom(base, mini, masquer):
    if not mini:
        return ""
    if masquer:
        ind = base.donnees["individus"].get(mini.get("id"))
        if ind and modele.est_vivant_presume(ind):
            return MASQUE
    return mini.get("nom", "")


def _entree(base, mini, masquer):
    """{ nom, periode } pour une personne liée. Si elle est masquée (vivante),
    on efface AUSSI la période : sinon l'année de naissance fuiterait."""
    if not mini:
        return None
    nom = _nom(base, mini, masquer)
    periode = "" if nom == MASQUE else mini.get("periode", "")
    return {"nom": nom, "periode": periode}


def filiation(base, f, masquer=True):
    """{ parents: [{nom, role}], fratrie: [{nom, periode}] }."""
    parents = []
    for p in f.get("peres", []):
        parents.append({"nom": _nom(base, p, masquer), "role": "Père"})
    for m in f.get("meres", []):
        parents.append({"nom": _nom(base, m, masquer), "role": "Mère"})
    fratrie = [e for e in (_entree(base, s, masquer) for s in f.get("fratrie", [])) if e]
    return {"parents": [p for p in parents if p["nom"]], "fratrie": fratrie}


def unions(base, f, masquer=True):
    """Liste d'unions : [{ conjoint, quand, lieu, enfants: [{nom, periode}] }]."""
    res = []
    for u in f.get("unions", []):
        mar = u.get("mariage") or {}
        an = modele.annee_naissance({"naissance": mar}) if mar.get("date") else None
        res.append({
            "conjoint": _nom(base, u.get("conjoint"), masquer),
            "quand": ("en %d" % an) if an else "",
            "lieu": mar.get("lieu", ""),
            "enfants": [e for e in (_entree(base, e, masquer)
                                    for e in u.get("enfants", [])) if e],
        })
    return res
