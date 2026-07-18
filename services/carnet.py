# -*- coding: utf-8 -*-
"""
Carnet de bord — journal de recherche personnel, stocké en fichier lisible
dans l'espace (Carnet/carnet.json). Types d'entrée : séance, piste, trouvaille,
réflexion, à faire, IA. Règle : une piste va au carnet ; une preuve va aux
sources.
"""

import json
import os
import time

from core import modele

TYPES = ("seance", "piste", "trouvaille", "reflexion", "afaire", "ia")
FICHIER = "Carnet"          # sous-dossier ; le json s'appelle carnet.json


def _chemin(espace_chemin):
    return os.path.join(espace_chemin, FICHIER, "carnet.json")


def _normaliser(e):
    """Migration douce : `personne` (unique) → `personnes` (liste). Garantit
    aussi `statut` (« » ouvert / « fait ») pour les pistes et à-faire."""
    if "personnes" not in e:
        p = e.get("personne")
        e["personnes"] = [p] if p else []
    e.setdefault("statut", "")
    return e


def _pids(champs):
    """Liste de personnes depuis les champs entrants (accepte `personnes` liste
    OU l'ancien `personne` unique)."""
    ps = champs.get("personnes")
    if isinstance(ps, list):
        return [p for p in ps if p]
    p = champs.get("personne")
    return [p] if p else []


def _lire(espace_chemin):
    try:
        with open(_chemin(espace_chemin), "r", encoding="utf-8") as f:
            data = json.load(f)
            return [_normaliser(e) for e in data] if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _ecrire(espace_chemin, entrees):
    chemin = _chemin(espace_chemin)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entrees, f, ensure_ascii=False, indent=2)
    os.replace(tmp, chemin)


def _resoudre_noms(entrees, donnees):
    """Ajoute `personnes_noms` = [{id, nom}] (et `personne_nom` = le 1er, pour
    la compatibilité) à chaque entrée."""
    inds = donnees["individus"]
    for e in entrees:
        noms = []
        for pid in e.get("personnes", []):
            ind = inds.get(pid)
            noms.append({"id": pid, "nom": modele.nom_complet(ind) if ind else ""})
        e["personnes_noms"] = noms
        e["personne_nom"] = noms[0]["nom"] if noms else ""
    return entrees


def lister(espace_chemin, donnees=None):
    """Entrées, plus récentes d'abord, avec noms des personnes liées résolus."""
    entrees = _lire(espace_chemin)
    if donnees:
        _resoudre_noms(entrees, donnees)
    entrees.sort(key=lambda e: e.get("date", ""), reverse=True)
    return entrees


def pistes_actives(espace_chemin):
    """Pistes et à-faire du carnet NON terminés et rattachés à au moins une
    personne — pour alimenter le plan de recherche."""
    return [e for e in _lire(espace_chemin)
            if e.get("type") in ("piste", "afaire")
            and e.get("statut") != "fait" and e.get("personnes")]


def mentions_de(espace_chemin, pid, donnees=None):
    """Entrées du carnet qui taguent la personne `pid` (pour sa fiche)."""
    out = [e for e in _lire(espace_chemin) if pid in e.get("personnes", [])]
    if donnees:
        _resoudre_noms(out, donnees)
    out.sort(key=lambda e: e.get("date", ""), reverse=True)
    return out


def ajouter(espace_chemin, champs):
    entrees = _lire(espace_chemin)
    nums = [int(e["id"][1:]) for e in entrees if e.get("id", "").startswith("C")
            and e["id"][1:].isdigit()]
    ident = "C%d" % ((max(nums) + 1) if nums else 1)
    pids = _pids(champs)
    entree = {
        "id": ident,
        "date": champs.get("date") or time.strftime("%Y-%m-%d"),
        "type": champs.get("type") if champs.get("type") in TYPES else "seance",
        "titre": (champs.get("titre") or "").strip(),
        "texte": (champs.get("texte") or "").strip(),
        "personnes": pids,
        "personne": pids[0] if pids else "",         # compat lecture ancienne
        "statut": champs.get("statut") if champs.get("statut") in ("", "fait") else "",
        "source": champs.get("source") or "",
    }
    entrees.append(entree)
    _ecrire(espace_chemin, entrees)
    return entree


def modifier(espace_chemin, ident, champs):
    entrees = _lire(espace_chemin)
    for e in entrees:
        if e.get("id") == ident:
            for cle in ("date", "type", "titre", "texte", "source"):
                if cle in champs:
                    e[cle] = champs[cle]
            if "personnes" in champs or "personne" in champs:
                pids = _pids(champs)
                e["personnes"] = pids
                e["personne"] = pids[0] if pids else ""
            if "statut" in champs:
                e["statut"] = champs["statut"] if champs["statut"] in ("", "fait") else ""
            _ecrire(espace_chemin, entrees)
            return e
    return None


def supprimer(espace_chemin, ident):
    entrees = _lire(espace_chemin)
    reste = [e for e in entrees if e.get("id") != ident]
    if len(reste) == len(entrees):
        return False
    _ecrire(espace_chemin, reste)
    return True
