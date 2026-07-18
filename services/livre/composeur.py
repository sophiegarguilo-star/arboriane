# -*- coding: utf-8 -*-
"""
Composeur — modèle d'un livre et persistance (D1).

Un livre = un fichier JSON dans « Mes arbres/<arbre>/Livres/<id>.json », comme le
carnet : il fait partie de l'espace, donc sauvegardé et exporté avec lui.
Plusieurs livres par arbre (un par branche, un par couple…).
"""

import json
import os
import threading
import time

from core import modele

_verrou = threading.RLock()          # sérialise création / écriture / suppression

DOSSIER = "Livres"

# Sections disponibles au J1 (le catalogue complet arrive aux jalons suivants).
# `mode` : "auto" (régénérée à l'ouverture) ; le mode « personnalisé » vient au J2.
SECTIONS_J1 = ("couverture", "comment_lire", "preface", "biographie", "chronologie",
               "filiation", "unions", "ascendance", "descendance", "album", "index")
_GENERATIONS = {"ascendance": 4, "descendance": 3}
_INACTIVES = ("preface",)              # présentes mais décochées par défaut


# Sections de TEXTE LIBRE ajoutables par l'utilisateur (Palier A). Titre fixe par
# type sauf « chapitre » (titre saisi). Chacune reçoit une clé unique -> on peut
# en ajouter plusieurs et les réordonner sans collision d'ancre.
TYPES_TEXTE = ("dedicace", "remerciements", "introduction", "chapitre")
SECTIONS_AJOUTABLES = {
    "dedicace": "Dédicace", "remerciements": "Remerciements",
    "introduction": "Introduction", "chapitre": "Chapitre personnel",
}


def _section_neuve(t):
    s = {"type": t, "actif": t not in _INACTIVES, "mode": "auto"}
    if t in _GENERATIONS:
        s["generations"] = _GENERATIONS[t]
    if t == "preface":
        s["texte"] = ""
    return s


def nouvelle_section(type_, titre=""):
    """Crée une section de texte libre (dédicace, remerciements, introduction,
    chapitre) avec une CLÉ UNIQUE. Utilisé pour ajouter du contenu personnel."""
    if type_ not in TYPES_TEXTE:
        raise ValueError("Type de section non ajoutable : %s" % type_)
    s = {"type": type_, "cle": "%s-%d" % (type_, int(time.time() * 1000)),
         "actif": True, "mode": "manuel", "texte": ""}
    if type_ == "chapitre":
        s["titre"] = (titre or "").strip()
    return s

MISE_EN_PAGE_DEFAUT = {
    "theme": "heritage",       # heritage | epure | sepia (voir rendu_html.THEMES)
    "format": "a4",            # a4 | a5
    "taille": 100,             # 85..130 (%)
    "couverture": "classique", # classique (médaillon) | sobre
}


def _dossier(espace_chemin):
    return os.path.join(espace_chemin, DOSSIER)


import re
_ID_OK = re.compile(r"^[A-Za-z0-9_-]+$")


def _chemin(espace_chemin, lid):
    # Confinement : un identifiant de livre ne contient que [A-Za-z0-9_-] — bloque
    # toute traversée de répertoire (« ..\\ », chemins absolus…).
    if not lid or not _ID_OK.match(str(lid)):
        raise ValueError("Identifiant de livre invalide.")
    return os.path.join(_dossier(espace_chemin), "%s.json" % lid)


def _lire_fichier(chemin):
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _ecrire_fichier(chemin, livre):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(livre, f, ensure_ascii=False, indent=2)
    os.replace(tmp, chemin)


# Types de livre (Palier D). « monographie » = une personne (défaut historique) ;
# « ascendance » = livret complet, un chapitre par couple, de la personne aux aïeux.
TYPES_LIVRE = ("monographie", "ascendance")


def _titre_defaut(type_livre, nom):
    if type_livre == "ascendance":
        return "Les ancêtres de %s" % nom
    return "Le livre de %s" % nom


def livre_neuf(donnees, referent_id, titre="", type_livre="monographie"):
    """Structure d'un livre neuf pour un référent."""
    ind = donnees["individus"].get(referent_id) or {}
    nom = modele.nom_complet(ind) or "cette personne"
    type_livre = type_livre if type_livre in TYPES_LIVRE else "monographie"
    lid = "L%d" % int(time.time() * 1000)
    return {
        "id": lid,
        "type": type_livre,
        "titre": (titre or "").strip() or _titre_defaut(type_livre, nom),
        "sous_titre": "",
        "auteur": "",
        "referent": referent_id,
        "generations": 5,                 # profondeur du livret d'ascendance (Palier D)
        "masquer_vivants": True,          # un livre est fait pour circuler (D3)
        "mise_en_page": dict(MISE_EN_PAGE_DEFAUT),
        "sections": [_section_neuve(t) for t in SECTIONS_J1],
        "cree": int(time.time()),
        "modifie": int(time.time()),
    }


def creer(espace_chemin, donnees, referent_id, titre="", type_livre="monographie"):
    if referent_id not in donnees["individus"]:
        raise ValueError("Personne de référence inconnue.")
    with _verrou:
        livre = livre_neuf(donnees, referent_id, titre, type_livre)
        base = livre["id"]                    # garantit un id unique : jamais d'écrasement
        n = 1
        while os.path.exists(_chemin(espace_chemin, livre["id"])):
            n += 1
            livre["id"] = "%s-%d" % (base, n)
        _ecrire_fichier(_chemin(espace_chemin, livre["id"]), livre)
    return livre


def lister(espace_chemin, donnees=None):
    """Résumés des livres (id, titre, référent, dates), plus récents d'abord."""
    dossier = _dossier(espace_chemin)
    resumes = []
    try:
        noms = os.listdir(dossier)
    except OSError:
        return []
    for n in noms:
        if not n.endswith(".json"):
            continue
        livre = _lire_fichier(os.path.join(dossier, n))
        if not livre:
            continue
        ref = livre.get("referent")
        ref_nom = ""
        if donnees and ref:
            ref_nom = modele.nom_complet(donnees["individus"].get(ref) or {})
        resumes.append({"id": livre.get("id"), "titre": livre.get("titre", ""),
                        "referent": ref, "referent_nom": ref_nom,
                        "modifie": livre.get("modifie", 0)})
    resumes.sort(key=lambda r: r.get("modifie", 0), reverse=True)
    return resumes


def lire(espace_chemin, lid):
    return _lire_fichier(_chemin(espace_chemin, lid))


def enregistrer(espace_chemin, livre):
    """Fusionne et écrit un livre existant (ne recrée pas l'id ni la date de
    création). Renvoie le livre enregistré."""
    lid = livre.get("id")
    if not lid:
        raise ValueError("Livre sans identifiant.")
    with _verrou:
        ancien = lire(espace_chemin, lid) or {}
        ancien.update(livre)
        ancien["id"] = lid
        ancien["modifie"] = int(time.time())
        _ecrire_fichier(_chemin(espace_chemin, lid), ancien)
    return ancien


def supprimer(espace_chemin, lid):
    with _verrou:
        try:
            os.remove(_chemin(espace_chemin, lid))
            return True
        except OSError:
            return False
