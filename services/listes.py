# -*- coding: utf-8 -*-
"""
Listes textuelles — unions, ascendance et descendance en listes exportables.

Réutilise les briques existantes (sosa.ascendance, aboville.descendance) : ces
fonctions ne recalculent rien, elles mettent en forme une sortie tabulaire que
la vue exporte en CSV/HTML côté client.
"""

from core import modele
from core.modele import nom_complet
from services import sosa as sosa_svc
from services import aboville as aboville_svc


def _date_union(fam):
    """Date/lieu/type représentatifs d'une union : le mariage s'il existe,
    sinon le PACS / les fiançailles (pour les couples non mariés, la colonne
    « date » restait vide alors que l'union EST datée)."""
    mar = fam.get("mariage") or {}
    if mar.get("date") or mar.get("lieu"):
        return mar.get("date", ""), mar.get("lieu", ""), "Mariage"
    for ev in fam.get("evenements") or []:
        if not isinstance(ev, dict):
            continue
        prec = (ev.get("precision") or "").strip()
        if ev.get("type") == "EVEN" and prec == "PACS":
            return ev.get("date", ""), ev.get("lieu", ""), "PACS"
        if ev.get("type") == "ENGA":
            return ev.get("date", ""), ev.get("lieu", ""), "Fiançailles"
    return "", "", ""


def unions(donnees):
    """Liste des unions : couple, date/lieu (mariage ou, à défaut, PACS), triée."""
    inds = donnees["individus"]
    out = []
    for fid, fam in donnees["familles"].items():
        mari = inds.get(fam.get("mari"))
        epouse = inds.get(fam.get("epouse"))
        if not mari and not epouse:
            continue
        date, lieu, type_union = _date_union(fam)
        out.append({
            "id": fid,
            "mari": nom_complet(mari) if mari else "?", "mari_id": fam.get("mari", ""),
            "epouse": nom_complet(epouse) if epouse else "?", "epouse_id": fam.get("epouse", ""),
            "date": date, "lieu": lieu, "type": type_union,
            "annee": modele.annee(date),
        })
    out.sort(key=lambda u: (u["annee"] or 9999, u["mari"].lower()))
    return {"total": len(out), "unions": out}


def ascendance_texte(donnees, racine, generations=12):
    """Ascendance en liste plate par génération (numéro Sosa). None si racine KO."""
    a = sosa_svc.ascendance(donnees, racine, generations)
    if not a:
        return None
    lignes = []
    for g in a["generations"]:
        for p in g["personnes"]:
            lignes.append({"sosa": p["sosa"], "generation": g["generation"],
                           "id": p["id"], "nom": p["nom"], "periode": p["periode"]})
    lignes.sort(key=lambda x: x["sosa"])
    return {"racine": racine, "racine_nom": a["de_cujus_nom"],
            "total": len(lignes), "lignes": lignes}


def descendance_texte(donnees, racine):
    """Descendance en liste (numérotation d'Aboville). None si racine KO."""
    a = aboville_svc.descendance(donnees, racine)
    if not a:
        return None
    return {"racine": racine, "racine_nom": a["racine_nom"], "total": a["total"],
            "lignes": [{"numero": p["numero"], "generation": p["generation"],
                        "id": p["id"], "nom": p["nom"], "periode": p["periode"]}
                       for p in a["personnes"]]}
