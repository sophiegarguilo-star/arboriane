# -*- coding: utf-8 -*-
"""Routes de l'espace de travail (un arbre = un dossier)."""

import json
import os
import sys
import subprocess
import time

from routes import route
from services import demo
from core.validation import ErreurValidation


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
        # "corrompu" si le JSON a été mis en quarantaine au chargement (repart
        # à vide) — un bandeau UI pourra l'afficher. "" sinon.
        "avertissement": getattr(app.base, "avertissement", ""),
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


# ── « Revenir en arrière » : les copies automatiques de Sauvegardes/ ──
@route("GET", r"^/api/archives$")
def archives(app, params, corps):
    """Copies automatiques (Sauvegardes/arboriane_*.json) de l'arbre actif :
    nom de fichier, date lisible et nombre de personnes. Les archives sont un
    dump direct des données — le nombre de personnes se lit dans le JSON."""
    if not app.base:
        return {"archives": []}
    dossier = app.base.dossier_sauvegardes
    try:
        noms = [n for n in os.listdir(dossier)
                if n.startswith("arboriane_") and n.endswith(".json")]
    except OSError:
        noms = []
    lignes = []
    for n in noms:
        plein = os.path.join(dossier, n)
        try:
            mtime = os.path.getmtime(plein)
        except OSError:
            continue
        personnes = None
        try:
            with open(plein, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                personnes = len(d.get("individus") or {})
        except (OSError, ValueError):
            pass                    # archive illisible : listée quand même
        lignes.append({"nom": n, "mtime": mtime, "personnes": personnes,
                       "date": time.strftime("%d/%m/%Y à %H:%M",
                                             time.localtime(mtime))})
    lignes.sort(key=lambda l: l["mtime"], reverse=True)     # la plus récente d'abord
    for l in lignes:
        del l["mtime"]
    return {"archives": lignes}


@route("POST", r"^/api/archives/restaurer$")
def archives_restaurer(app, params, corps):
    """Remplace la base de l'arbre actif par une copie automatique. L'état
    COURANT est archivé D'ABORD : revenir en arrière n'efface jamais rien —
    on peut toujours re-revenir en avant."""
    if not app.base:
        return (400, {"erreur": "Aucun arbre ouvert."})
    nom = os.path.basename((corps or {}).get("nom") or "")
    if not (nom.startswith("arboriane_") and nom.endswith(".json")):
        raise ErreurValidation("Nom d'archive invalide.")
    plein = os.path.join(app.base.dossier_sauvegardes, nom)
    if not os.path.isfile(plein):
        return (404, {"erreur": "Cette copie est introuvable."})
    try:
        with open(plein, "r", encoding="utf-8") as f:
            donnees = json.load(f)
    except ValueError:
        raise ErreurValidation("Cette copie est illisible (JSON invalide) — "
                               "choisissez-en une autre.")
    if not isinstance(donnees, dict) or not isinstance(
            donnees.get("individus"), dict):
        raise ErreurValidation("Ce fichier n'est pas une copie d'arbre valide.")
    # 1) filet : archiver l'état courant ; 2) remplacer par la copie choisie
    # (garantir_cles + réalignement des liens sont faits par remplacer()).
    app.base.sauvegarder(forcer_horodatage=True)
    app.base.remplacer(donnees)
    return {"ok": True, "personnes": len(app.base.donnees["individus"])}
