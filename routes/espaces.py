# -*- coding: utf-8 -*-
"""Routes de l'espace de travail (un arbre = un dossier)."""

import os
import sys
import subprocess

from routes import route
from services import demo


@route("GET", r"^/api/espace$")
def etat(app, params, corps):
    """État courant : quel arbre est ouvert, son nom, ses compteurs."""
    if not app.espace_chemin:
        return {"ouvert": False}
    app.rafraichir_verrou()        # « je suis toujours là » (throttlé, arbres cloud)
    return {
        "ouvert": True,
        "chemin": app.espace_chemin,
        "nom": app.manifeste.get("nom", ""),
        "racine_id": app.manifeste.get("racine_id", ""),
        "personnes": len(app.base.donnees["individus"]),
        "familles": len(app.base.donnees["familles"]),
        "sources": len(app.base.donnees.get("sources", {})),
        "arbre_fond": app.manifeste.get("arbre_fond", {}),
        "cloud": app.cloud_actif(),      # {'fournisseur': …} si dossier synchronisé, sinon None
    }


@route("GET", r"^/api/espaces$")
def lister(app, params, corps):
    return {"espaces": app.lister()}


@route("GET", r"^/api/demo/histoire$")
def demo_histoire(app, params, corps):
    """Résumé de la saga familiale fictive de l'arbre de démonstration."""
    return {"texte": getattr(demo, "HISTOIRE", "")}


@route("POST", r"^/api/espaces/ouvrir$")
def ouvrir(app, params, corps):
    chemin = corps.get("chemin", "")
    # Verrou souple : si l'arbre (dossier synchronisé) semble ouvert sur une
    # AUTRE machine, on ne l'ouvre pas d'emblée — on renvoie l'info pour que le
    # navigateur demande « ouvrir quand même ? ». `forcer` passe outre.
    if not (corps or {}).get("forcer"):
        v = app.verrou_etranger(chemin)
        if v:
            return {"ok": False, "verrou": v}
    m = app.ouvrir(chemin)
    return {"ok": True, "nom": m.get("nom", "")}


@route("POST", r"^/api/espaces/creer$")
def creer(app, params, corps):
    # `emplacement` (optionnel) = dossier où ranger l'arbre (ex. sur le disque D:).
    # Absent → « Mes arbres/ ». app.creer lève ValueError si le dossier est
    # invalide → dispatch renvoie 400 avec le message.
    m = app.creer(corps.get("nom", ""), (corps or {}).get("emplacement") or None)
    return {"ok": True, "nom": m.get("nom", ""), "chemin": app.espace_chemin}


@route("POST", r"^/api/espaces/choisir-dossier$")
def choisir_dossier(app, params, corps):
    """Ouvre le dialogue natif « Parcourir… » et renvoie le dossier choisi.
    Rien n'est créé : le chemin repart au navigateur, qui le renvoie à
    /api/espaces/creer. Renvoie {chemin: ""} si l'utilisateur annule."""
    from services import selecteur_dossier
    depart = (corps or {}).get("depart") or app.dossier_arbres
    return {"chemin": selecteur_dossier.choisir("Où ranger ce nouvel arbre ?", depart)}


@route("POST", r"^/api/espaces/demo$")
def ouvrir_demo(app, params, corps):
    m = app.ouvrir_demo(demo.generer, version=demo.VERSION)
    return {"ok": True, "nom": m.get("nom", ""), "chemin": app.espace_chemin}


@route("POST", r"^/api/espaces/renommer$")
def renommer(app, params, corps):
    m = app.renommer(corps.get("chemin", ""), corps.get("nom", ""))
    return {"ok": True, "nom": m.get("nom", "")}


@route("POST", r"^/api/espaces/fond-arbre$")
def fond_arbre(app, params, corps):
    """Mémorise (ou efface) l'arrière-plan de l'arbre dans le manifeste."""
    if not app.espace_chemin:
        return (400, {"erreur": "Aucun arbre ouvert."})
    c = corps or {}
    fond = app.enregistrer_fond_arbre(c.get("fond", ""), c.get("fond_opacite", 60))
    return {"ok": True, "arbre_fond": fond}


@route("POST", r"^/api/espaces/racine$")
def definir_racine(app, params, corps):
    pid = (corps or {}).get("id", "")
    if not app.base or pid not in app.base.donnees["individus"]:
        return (400, {"erreur": "Personne introuvable."})
    m = app.definir_racine(pid)
    return {"ok": True, "racine_id": m.get("racine_id", "")}


@route("POST", r"^/api/espaces/ouvrir-dossier$")
def ouvrir_dossier(app, params, corps):
    """Ouvre le dossier de l'arbre actif dans l'explorateur de fichiers du système.
    N'ouvre QUE le dossier de l'espace courant — jamais un chemin fourni par le client."""
    chemin = app.espace_chemin
    if not chemin or not os.path.isdir(chemin):
        return (400, {"erreur": "Aucun arbre ouvert."})
    try:
        if os.name == "nt":
            os.startfile(chemin)                       # Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", chemin])         # macOS
        else:
            subprocess.Popen(["xdg-open", chemin])     # Linux
    except OSError as e:
        return (500, {"erreur": "Ouverture impossible : %s" % e})
    return {"ok": True, "chemin": chemin}


@route("POST", r"^/api/espaces/oublier$")
def oublier(app, params, corps):
    app.oublier(corps.get("chemin", ""))
    return {"ok": True}


@route("POST", r"^/api/espaces/supprimer$")
def supprimer(app, params, corps):
    """Supprime un espace — archive de sécurité déposée AVANT effacement."""
    res = app.supprimer(corps.get("chemin", ""))
    return {"ok": True, "archive": os.path.basename(res["archive"])}


@route("POST", r"^/api/espaces/sauvegarde$")
def sauvegarde(app, params, corps):
    """Sauvegarde complète (.zip) de l'arbre actif, dans son Exports/."""
    cible = app.sauvegarde_complete()
    return {"ok": True, "fichier": os.path.basename(cible), "chemin": cible}
