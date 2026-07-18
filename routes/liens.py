# -*- coding: utf-8 -*-
"""
Routes du Lot 6 — liens de recherche web.

GET /api/liens?id=<pid> renvoie des URL de recherche construites LOCALEMENT pour
la personne. L'ouverture se fait côté client : rien n'est transmis d'ici.
"""

from routes import route
from services import liens_web as lw_svc
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


@route("GET", r"^/api/liens$")
def liens(app, params, corps):
    base = _base(app)
    pid = params.get("id")
    ind = base.donnees["individus"].get(pid) if pid else None
    if not ind:
        raise ErreurValidation("Personne inconnue.")
    return {"liens": lw_svc.liens_pour(ind, app.lire_reglages())}
