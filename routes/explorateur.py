# -*- coding: utf-8 -*-
"""Explorateur de fichiers de l'ARBRE (retour Sophie) : parcourir, dans Arboriane,
les dossiers de l'arbre actif (Sources, Photos, Exports, Sauvegardes, GEDCOM,
journaux…), voir un aperçu des images, et ouvrir un dossier dans l'explorateur
Windows.

Sécurité : tout est CONFINÉ au dossier de l'arbre actif (aucune sortie possible,
même via « ..\\ » ou un chemin absolu). On ne parcourt jamais le reste du disque.
"""

import base64
import mimetypes
import os
import subprocess

from routes import route
from core.validation import ErreurValidation

_APERCU_MAX = 8 * 1024 * 1024        # 8 Mo : au-delà, pas d'aperçu inline
_NO_WINDOW = 0x08000000              # CREATE_NO_WINDOW (Windows)


def _cible(app, rel):
    """(racine, chemin absolu) confiné à l'arbre actif. Lève si hors périmètre."""
    if not app.espace_chemin:
        raise ErreurValidation("Aucun arbre ouvert.")
    racine = os.path.abspath(app.espace_chemin)
    cible = os.path.abspath(os.path.join(racine, (rel or "").replace("\\", "/")))
    if cible != racine and not cible.startswith(racine + os.sep):
        raise ErreurValidation("Accès hors de l'arbre refusé.")
    return racine, cible


@route("GET", r"^/api/explorateur$")
def lister(app, params, corps):
    racine, cible = _cible(app, params.get("chemin", ""))
    if not os.path.isdir(cible):
        raise ErreurValidation("Dossier introuvable.")
    dossiers, fichiers = [], []
    try:
        with os.scandir(cible) as it:
            for e in it:
                try:
                    st = e.stat()
                except OSError:
                    continue
                if e.is_dir():
                    dossiers.append({"nom": e.name, "modifie": int(st.st_mtime)})
                else:
                    fichiers.append({
                        "nom": e.name, "modifie": int(st.st_mtime),
                        "taille": st.st_size,
                        "ext": os.path.splitext(e.name)[1].lower().lstrip("."),
                    })
    except OSError:
        raise ErreurValidation("Dossier illisible.")
    dossiers.sort(key=lambda x: x["nom"].lower())
    fichiers.sort(key=lambda x: x["nom"].lower())
    rel = "" if cible == racine else os.path.relpath(cible, racine).replace(os.sep, "/")
    return {"racine_nom": os.path.basename(racine), "chemin": rel,
            "parties": [p for p in rel.split("/") if p],
            "dossiers": dossiers, "fichiers": fichiers}


@route("GET", r"^/api/explorateur/apercu$")
def apercu(app, params, corps):
    """Aperçu d'une image du dossier de l'arbre (data-URI). "" si non-image/trop gros."""
    racine, cible = _cible(app, params.get("chemin", ""))
    if not os.path.isfile(cible):
        raise ErreurValidation("Fichier introuvable.")
    mime = mimetypes.guess_type(cible)[0] or ""
    if not mime.startswith("image/") or os.path.getsize(cible) > _APERCU_MAX:
        return {"data": "", "mime": mime}
    try:
        with open(cible, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
    except OSError:
        raise ErreurValidation("Fichier illisible.")
    return {"data": "data:%s;base64,%s" % (mime, data), "mime": mime}


@route("POST", r"^/api/explorateur/ouvrir$")
def ouvrir(app, params, corps):
    """Ouvre un dossier (ou sélectionne un fichier) de l'arbre dans l'explorateur
    Windows. Confiné à l'arbre : impossible d'ouvrir un chemin extérieur."""
    racine, cible = _cible(app, (corps or {}).get("chemin", ""))
    try:
        if os.path.isfile(cible):
            subprocess.Popen(["explorer", "/select,", cible], creationflags=_NO_WINDOW)
        elif os.path.isdir(cible):
            subprocess.Popen(["explorer", cible], creationflags=_NO_WINDOW)
        else:
            raise ErreurValidation("Chemin introuvable.")
    except OSError as e:
        raise ErreurValidation("Impossible d'ouvrir l'explorateur : %s" % e)
    return {"ok": True}
