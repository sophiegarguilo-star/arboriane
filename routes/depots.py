# -*- coding: utf-8 -*-
"""Routes du Lot L5+ — dépôts d'archives (3ᵉ niveau du sourçage)."""

from routes import route
from services import depots as depots_svc
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


@route("GET", r"^/api/depots$")
def lister(app, params, corps):
    return depots_svc.lister(_base(app).donnees)


@route("POST", r"^/api/depots$")
def creer(app, params, corps):
    base = _base(app)
    if not (corps or {}).get("nom", "").strip():
        raise ErreurValidation("Le nom du dépôt est requis.")
    d = depots_svc.creer(base.donnees, corps)
    base.sauvegarder()
    return {"ok": True, "depot": d}


@route("POST", r"^/api/depots/promouvoir$")
def promouvoir(app, params, corps):
    base = _base(app)
    r = depots_svc.promouvoir(base.donnees)
    base.sauvegarder()
    return {"ok": True, **r}


@route("POST", r"^/api/depots/assigner$")
def assigner(app, params, corps):
    base = _base(app)
    corps = corps or {}
    src = depots_svc.assigner_source(base.donnees, corps.get("source"),
                                     corps.get("depot_id") or "")
    if src is None:
        return (404, {"erreur": "Source inconnue."})
    base.sauvegarder()
    return {"ok": True}


@route("PUT", r"^/api/depots/(?P<did>[^/]+)$")
def modifier(app, params, corps, did):
    base = _base(app)
    d = depots_svc.modifier(base.donnees, did, corps or {})
    if not d:
        return (404, {"erreur": "Dépôt inconnu."})
    base.sauvegarder()
    return {"ok": True, "depot": d}


@route("DELETE", r"^/api/depots/(?P<did>[^/]+)$")
def supprimer(app, params, corps, did):
    base = _base(app)
    if not depots_svc.supprimer(base.donnees, did):
        return (404, {"erreur": "Dépôt inconnu."})
    base.sauvegarder()
    return {"ok": True}
