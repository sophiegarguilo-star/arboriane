# -*- coding: utf-8 -*-
"""
Favoris & ensembles de personnes (L13).

Deux repères persistants, stockés dans l'arbre (tables `favoris` / `ensembles`,
migration transparente via garantir_cles) :
  • FAVORIS : un jeu de personnes « épinglées » pour y accéder vite (étoile).
  • ENSEMBLES : des listes NOMMÉES et réutilisables de personnes (« ma branche
    paternelle », « à présenter au cousin X »…).

Non destructif : ce sont des repères, jamais des données généalogiques ;
supprimer un favori/ensemble ne touche pas aux personnes.
"""

from core import modele


def _fav(donnees):
    return donnees.setdefault("favoris", {})


def _ens(donnees):
    return donnees.setdefault("ensembles", {})


def _carte(inds, pid):
    ind = inds[pid]
    return {"id": pid, "nom": modele.nom_complet(ind),
            "periode": modele.periode(ind), "sexe": ind.get("sexe", "U")}


# ── Favoris ─────────────────────────────────────────────────────────────────
def est_favori(donnees, pid):
    return pid in _fav(donnees)


def basculer(base, pid):
    """Épingle / désépingle une personne. Renvoie l'état (True = favori)."""
    with base._verrou:
        fav = _fav(base.donnees)
        if pid in fav:
            del fav[pid]; etat = False
        elif pid in base.donnees["individus"]:
            fav[pid] = 1; etat = True
        else:
            raise ValueError("Personne inconnue.")
        base.sauvegarder()
    return etat


def lister_favoris(donnees):
    inds = donnees["individus"]
    out = [_carte(inds, pid) for pid in _fav(donnees) if pid in inds]
    out.sort(key=lambda x: x["nom"].lower())
    return out


# ── Ensembles ───────────────────────────────────────────────────────────────
def lister_ensembles(donnees):
    inds = donnees["individus"]
    out = [{"id": eid, "nom": e.get("nom", ""),
            "nb": sum(1 for m in e.get("membres", []) if m in inds)}
           for eid, e in _ens(donnees).items()]
    out.sort(key=lambda x: x["nom"].lower())
    return out


def membres(donnees, eid):
    inds = donnees["individus"]
    e = _ens(donnees).get(eid)
    if not e:
        return None
    return {"id": eid, "nom": e.get("nom", ""),
            "membres": [_carte(inds, m) for m in e.get("membres", []) if m in inds]}


def creer_ensemble(base, nom, ids=None):
    with base._verrou:
        ens = _ens(base.donnees)          # garantit la table
        # id monotone persisté (meta.compteurs) : jamais réutilisé après suppression
        eid = modele.nouvel_id_monotone(base.donnees, "ensembles", "E")
        ens[eid] = {"id": eid, "nom": (nom or "").strip() or "Nouvel ensemble",
                    "membres": [i for i in (ids or []) if i in base.donnees["individus"]]}
        base.sauvegarder()
    return ens[eid]


def renommer_ensemble(base, eid, nom):
    with base._verrou:
        e = _ens(base.donnees).get(eid)
        if not e:
            return None
        e["nom"] = (nom or "").strip() or e["nom"]
        base.sauvegarder()
    return e


def supprimer_ensemble(base, eid):
    with base._verrou:
        ens = _ens(base.donnees)
        if eid not in ens:
            return False
        del ens[eid]
        base.sauvegarder()
    return True


def basculer_membre(base, eid, pid):
    """Ajoute / retire une personne d'un ensemble. Renvoie l'état (True = membre)."""
    with base._verrou:
        e = _ens(base.donnees).get(eid)
        if not e:
            raise ValueError("Ensemble inconnu.")
        mem = e.setdefault("membres", [])
        if pid in mem:
            mem.remove(pid); etat = False
        elif pid in base.donnees["individus"]:
            mem.append(pid); etat = True
        else:
            raise ValueError("Personne inconnue.")
        base.sauvegarder()
    return etat
