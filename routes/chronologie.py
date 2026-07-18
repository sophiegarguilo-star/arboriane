# -*- coding: utf-8 -*-
"""Routes de la chronologie agrégée (L11) : frise multi-personnes et
contemporains d'une personne."""

from routes import route
from services import chronologie as ch


@route("GET", r"^/api/chronologie/frise$")
def frise(app, params, corps):
    if not app.base:
        return (400, {"erreur": "Aucun arbre ouvert."})
    ids = [x for x in (params.get("ids", "") or "").split(",") if x]
    return ch.frise(app.base.donnees, ids)


@route("GET", r"^/api/chronologie/contemporains$")
def contemporains(app, params, corps):
    if not app.base:
        return (400, {"erreur": "Aucun arbre ouvert."})
    c = ch.contemporains(app.base.donnees, params.get("id", ""))
    if c is None:
        return (404, {"erreur": "Personne inconnue ou sans date."})
    return c
