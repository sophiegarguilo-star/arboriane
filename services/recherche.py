# -*- coding: utf-8 -*-
"""
Plan de recherche — transforme l'arbre en actions concrètes. Chaque proposition
dit QUOI chercher, POURQUOI, et OÙ regarder si possible.
"""

from core import modele
from core.modele import nom_complet, periode, annee_naissance
from services import sources as src_svc
from services import sosa as sosa_svc
from services import coherence as coherence_svc


def _piste(categorie, priorite, pid, nom, quoi, pourquoi, ou=""):
    return {"categorie": categorie, "priorite": priorite, "personne": pid,
            "personne_nom": nom, "quoi": quoi, "pourquoi": pourquoi, "ou": ou}


def plan(donnees, racine_id=None, gen=12, pistes_carnet=None):
    inds = donnees["individus"]
    pistes = []

    # Preuves calculées UNE SEULE FOIS par personne, puis réutilisées ci-dessous
    # (évite le double calcul entre « actes à trouver » et « personnes à
    # documenter » — coûteux sur un grand arbre).
    preuves = {pid: src_svc.preuves_personne(donnees, pid) for pid in inds}

    # 1) Actes manquants : faits vitaux présents mais non prouvés par acte
    pistes.extend(_actes_a_trouver(donnees, preuves))

    # 2) Personnes peu documentées (aucune source du tout)
    for pid, ind in inds.items():
        pv = preuves[pid]
        if not any(f["nb_sources"] for f in pv["faits"]) and not (ind.get("citations")):
            pistes.append(_piste(
                "Personnes à documenter", 2, pid, nom_complet(ind),
                "Trouver une première source",
                "Rien ne prouve encore ce qu'on affirme sur cette personne.",
                _ou_chercher(ind, "naissance")))

    # 3) Branches faibles : ruptures Sosa (un parent manque)
    if racine_id and racine_id in inds:
        s = sosa_svc.ascendance(donnees, racine_id, gen)
        for r in s["ruptures"]:
            pistes.append(_piste(
                "Branches à remonter", 3, r["id"], r["nom"],
                "Trouver le %s (Sosa %d)" % (r["manque"], r["sosa_manquant"]),
                "C'est le bout d'une branche : le %s permettrait de remonter." % r["manque"],
                ""))

    # 4) Pistes personnelles notées sur les fiches
    for pid, ind in inds.items():
        for p in ind.get("pistes", []):
            texte = p.get("texte") if isinstance(p, dict) else str(p)
            if texte and not (isinstance(p, dict) and p.get("faite")):
                pistes.append(_piste(
                    "Vos pistes", 2, pid, nom_complet(ind), texte,
                    "Note personnelle à explorer.", ""))

    # 4 bis) Pistes et à-faire notés dans le CARNET et taggant des personnes.
    # Le carnet cesse d'être un cul-de-sac : ce qu'on y note « à explorer »
    # remonte au plan, sous chaque personne concernée.
    for e in (pistes_carnet or []):
        quoi = (e.get("titre") or "").strip() or (e.get("texte") or "").strip()[:80]
        if not quoi:
            continue
        for pid in e.get("personnes", []):
            ind = inds.get(pid)
            if ind:
                pistes.append(_piste(
                    "Carnet — à explorer", 2, pid, nom_complet(ind), quoi,
                    "Note du carnet de bord à explorer.", ""))

    # 5) Incohérences hautes à résoudre
    coh = coherence_svc.analyser(donnees)
    for a in coh["alertes"]:
        if a["gravite"] == "haute":
            pistes.append(_piste(
                "Incohérences à résoudre", 3, a["personne"], a["personne_nom"],
                a["message"], "Anomalie qui fragilise l'arbre.", ""))

    pistes.sort(key=lambda p: -p["priorite"])
    par_cat = {}
    for p in pistes:
        par_cat.setdefault(p["categorie"], []).append(p)
    return {"total": len(pistes),
            "categories": [{"nom": c, "pistes": ps} for c, ps in par_cat.items()]}


def _lieu_du_fait(ind, fait):
    """Lieu associé à un fait (naissance/décès), '' sinon."""
    if fait == "naissance":
        return (ind.get("naissance") or {}).get("lieu", "")
    if fait == "deces":
        return (ind.get("deces") or {}).get("lieu", "")
    return ""


def _departement(lieu):
    """Département/dépôt approximatif : la dernière partie après une virgule
    (heuristique douce), sinon le lieu entier. '' si vide."""
    parts = [p.strip() for p in (lieu or "").split(",") if p.strip()]
    if not parts:
        return ""
    return parts[-1] if len(parts) > 1 else parts[0]


def _ou_chercher(ind, fait):
    """Suggère un dépôt d'archives à partir du lieu de l'événement."""
    dept = _departement(_lieu_du_fait(ind, fait))
    if not dept:
        return ""
    return "État civil / registres paroissiaux de %s (archives départementales)." % dept


# Un fait vital se prouve par un ACTE nommé ; une profession ou une résidence,
# non (« trouver l'acte de profession — archiviste » n'a aucun sens). On adapte
# donc la formulation au fait, et on n'écrase pas la casse des lieux.
_ACTE_DU_FAIT = {"naissance": "l'acte de naissance",
                 "deces": "l'acte de décès",
                 "union": "l'acte de mariage"}


def _quoi_chercher(fait, libelle):
    acte = _ACTE_DU_FAIT.get(fait)
    if acte:
        return "Trouver %s" % acte
    return "Prouver : %s" % libelle          # résidence, profession, événement…


def _actes_a_trouver(donnees, preuves=None):
    """Pistes « Actes à trouver » (faits présents mais non prouvés), chacune
    dotée d'un champ « depot » pour le regroupement géographique. `preuves`
    (dict pid → preuves_personne) permet de réutiliser un calcul déjà fait ;
    sinon il est calculé à la volée (appel isolé, ex. par_depot)."""
    pistes = []
    for pid, ind in donnees["individus"].items():
        pv = preuves[pid] if preuves is not None else src_svc.preuves_personne(donnees, pid)
        for f in pv["faits"]:
            # « non_qualifie » = le fait A une source, juste sans niveau de
            # fiabilité (fréquent après import GEDCOM : la plupart des logiciels
            # n'exportent pas QUAY). Un fait sourcé n'est PAS une tâche à faire —
            # on ne nage plus l'utilisateur pour ré-attester ce qui est déjà cité.
            if f["present"] and f["niveau"] in ("manquant", "estime"):
                p = _piste(
                    "Actes à trouver", 2 if f["niveau"] == "estime" else 3, pid,
                    nom_complet(ind),
                    _quoi_chercher(f["fait"], f["libelle"]),
                    "Le fait est renseigné mais pas prouvé par un acte.",
                    _ou_chercher(ind, f["fait"]))
                p["depot"] = _departement(_lieu_du_fait(ind, f["fait"]))
                pistes.append(p)
    return pistes


def par_depot(donnees):
    """Regroupe les actes à rechercher par dépôt/département, pour préparer une
    visite aux archives (tous les actes d'un même lieu d'un bloc).
    Renvoie {total, groupes:[{depot, nb, pistes}]}, les dépôts les plus fournis
    d'abord, « Lieu non précisé » en dernier."""
    groupes = {}
    for p in _actes_a_trouver(donnees):
        cle = p.get("depot") or "Lieu non précisé"
        groupes.setdefault(cle, []).append(p)
    liste = [{"depot": d, "nb": len(ps), "pistes": ps} for d, ps in groupes.items()]
    liste.sort(key=lambda g: (g["depot"] == "Lieu non précisé", -g["nb"], g["depot"].lower()))
    return {"total": sum(g["nb"] for g in liste), "groupes": liste}
