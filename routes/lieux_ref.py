# -*- coding: utf-8 -*-
"""Routes du Lot L15 — référentiel de lieux hiérarchique (noms datés)."""

from routes import route
from services import lieux_ref as lr
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


@route("GET", r"^/api/lieux-ref$")
def lister(app, params, corps):
    return lr.lister(_base(app).donnees)


@route("POST", r"^/api/lieux-ref$")
def creer(app, params, corps):
    base = _base(app)
    if not (corps or {}).get("nom", "").strip():
        raise ErreurValidation("Le nom du lieu est requis.")
    e = lr.creer(base.donnees, corps)
    base.sauvegarder()
    return {"ok": True, "lieu": e}


@route("POST", r"^/api/lieux-ref/construire$")
def construire(app, params, corps):
    base = _base(app)
    r = lr.construire_depuis_evenements(base.donnees)
    base.sauvegarder()
    return {"ok": True, **r}


@route("GET", r"^/api/lieux-ref/resoudre$")
def resoudre(app, params, corps):
    d = _base(app).donnees
    try:
        annee = int(params.get("annee")) if params.get("annee") else None
    except (TypeError, ValueError):
        annee = None
    r = lr.resoudre(d, params.get("lieu", ""), annee)
    return r or {"id": "", "nom_resolu": "", "chemin": ""}


@route("PUT", r"^/api/lieux-ref/(?P<lid>[^/]+)$")
def modifier(app, params, corps, lid):
    base = _base(app)
    e = lr.modifier(base.donnees, lid, corps or {})
    if not e:
        return (404, {"erreur": "Lieu inconnu."})
    base.sauvegarder()
    return {"ok": True, "lieu": e}


@route("DELETE", r"^/api/lieux-ref/(?P<lid>[^/]+)$")
def supprimer(app, params, corps, lid):
    base = _base(app)
    if not lr.supprimer(base.donnees, lid):
        return (404, {"erreur": "Lieu inconnu."})
    base.sauvegarder()
    return {"ok": True}
