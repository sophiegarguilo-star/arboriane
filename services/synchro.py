# -*- coding: utf-8 -*-
"""
Synchro multi-ordinateurs — SANS compte, SANS serveur, SANS réseau.

Principe : « un arbre = un dossier ». Si l'utilisateur range un arbre dans un
dossier synchronisé par SON cloud (OneDrive, Google Drive, Dropbox, iCloud), le
dossier se réplique tout seul entre ses ordinateurs. Arboriane ne synchronise
rien : il se contente

  1. de DÉTECTER qu'un arbre vit dans un dossier synchronisé (pour avertir), et
  2. de poser un VERROU SOUPLE — un petit fichier `.arboriane-ouvert.json`
     déposé dans le dossier de l'arbre (donc lui-même synchronisé). À
     l'ouverture sur un 2e poste, si ce verrou est récent et vient d'une AUTRE
     machine, on prévient « ouvert sur X ? ».

Le verrou est SOUPLE (advisory) : la latence de synchro le rend faillible, il
n'empêche donc jamais d'ouvrir — il avertit. La règle d'or reste : un seul
ordinateur à la fois. Le verrou n'est posé QUE pour les arbres en dossier
synchronisé : les arbres purement locaux restent vierges de tout fichier ajouté.
"""

import json
import os
import socket
import time

# Fichier-verrou déposé dans le dossier de l'arbre.
NOM_VERROU = ".arboriane-ouvert.json"

# Au-delà de ce délai sans rafraîchissement, un verrou est considéré périmé
# (machine éteinte/plantée) donc l'arbre est réputé libre.
PEREMPTION = 900          # 15 minutes


# ── Détection d'un dossier synchronisé ────────────────────────────────────
# Marqueurs de dossier (composant de chemin) → fournisseur affiché.
_MARQUEURS = {
    "dropbox": "Dropbox",
    "google drive": "Google Drive",
    "googledrive": "Google Drive",
    "my drive": "Google Drive",
    "icloud drive": "iCloud",
    "iclouddrive": "iCloud",
    "pcloud": "pCloud",
    "mega": "MEGA",
    "sync": "Sync.com",
}


def detecter_cloud(chemin):
    """Renvoie {'fournisseur': 'OneDrive'|…} si `chemin` est (sous) un dossier
    synchronisé connu, sinon None. Heuristique par nom de dossier + variables
    d'environnement OneDrive — volontairement prudente (aucun réseau)."""
    if not chemin:
        return None
    p = os.path.normpath(os.path.abspath(chemin)).lower()

    # 1) OneDrive : variables d'environnement (le plus fiable sous Windows).
    for var in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        racine = os.environ.get(var)
        if racine:
            racine = os.path.normpath(os.path.abspath(racine)).lower()
            if p == racine or p.startswith(racine + os.sep):
                return {"fournisseur": "OneDrive"}

    # 2) Marqueurs par composant de chemin.
    for comp in p.split(os.sep):
        if comp.startswith("onedrive"):        # « OneDrive - Contoso », etc.
            return {"fournisseur": "OneDrive"}
        f = _MARQUEURS.get(comp)
        if f:
            return {"fournisseur": f}
    return None


# ── Verrou souple ─────────────────────────────────────────────────────────
def nom_machine():
    """Nom lisible de cet ordinateur (pour le message « ouvert sur X »)."""
    try:
        return socket.gethostname() or "cet ordinateur"
    except OSError:
        return "cet ordinateur"


def _fichier(dossier):
    return os.path.join(dossier, NOM_VERROU)


def poser_verrou(dossier, machine=None, maintenant=None):
    """Écrit (atomiquement) le verrou de CETTE machine dans le dossier de
    l'arbre. Renvoie le contenu écrit. Peut lever OSError (dossier non
    inscriptible) — l'appelant l'ignore (le verrou est un confort)."""
    data = {
        "machine": machine or nom_machine(),
        "pid": os.getpid(),
        "horodatage": float(maintenant if maintenant is not None else time.time()),
    }
    cible = _fichier(dossier)
    tmp = cible + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, cible)
    return data


def lire_verrou(dossier):
    """Contenu du verrou présent, ou None (absent/illisible)."""
    try:
        with open(_fichier(dossier), "r", encoding="utf-8") as f:
            v = json.load(f)
        if isinstance(v, dict) and v.get("machine"):
            return v
    except (OSError, ValueError):
        pass
    return None


def verrou_etranger(dossier, machine=None, peremption=PEREMPTION, maintenant=None):
    """Renvoie le verrou s'il est RÉCENT et posé par une AUTRE machine — sinon
    None (absent, périmé, ou c'est nous). Le dict renvoyé porte en plus
    `age_min` (minutes écoulées) pour le message d'avertissement."""
    v = lire_verrou(dossier)
    if not v:
        return None
    machine = machine or nom_machine()
    maintenant = float(maintenant if maintenant is not None else time.time())
    age = maintenant - float(v.get("horodatage", 0) or 0)
    if age > peremption:                       # périmé → arbre réputé libre
        return None
    if v.get("machine") == machine:            # c'est notre propre verrou
        return None
    v["age_min"] = max(0, int(age // 60))
    return v


def liberer_verrou(dossier, machine=None):
    """Retire le verrou s'il est le NÔTRE (ne supprime jamais celui d'un autre
    poste). Sans effet si absent. Renvoie True si un verrou nôtre a été retiré."""
    v = lire_verrou(dossier)
    if not v:
        return False
    machine = machine or nom_machine()
    if v.get("machine") != machine:
        return False
    try:
        os.remove(_fichier(dossier))
        return True
    except OSError:
        return False
