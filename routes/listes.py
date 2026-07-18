# -*- coding: utf-8 -*-
"""Routes du Lot 8 — listes & index exportables."""

from routes import route
from services import index_pro
from services import listes as listes_svc
from services import anniversaires
from services import personnes as personnes_svc
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


def _hors_famille(app):
    """Id des personnes hors famille (à exclure des index/stats), d'après la racine."""
    return personnes_svc.ids_hors_famille(_base(app).donnees,
                                          app.manifeste.get("racine_id"))


@route("GET", r"^/api/index-metiers$")
def index_metiers(app, params, corps):
    return index_pro.index(_base(app).donnees, exclure=_hors_famille(app))


@route("GET", r"^/api/unions$")
def unions(app, params, corps):
    return listes_svc.unions(_base(app).donnees)


@route("GET", r"^/api/ascendance-texte$")
def ascendance_texte(app, params, corps):
    d = _base(app).donnees
    racine = params.get("id") or app.manifeste.get("racine_id")
    r = listes_svc.ascendance_texte(d, racine)
    return r if r is not None else (404, {"erreur": "Personne racine introuvable."})


@route("GET", r"^/api/descendance-texte$")
def descendance_texte(app, params, corps):
    d = _base(app).donnees
    racine = params.get("id") or app.manifeste.get("racine_id")
    r = listes_svc.descendance_texte(d, racine)
    return r if r is not None else (404, {"erreur": "Personne introuvable."})


@route("GET", r"^/api/ephemeride$")
def ephemeride(app, params, corps):
    return anniversaires.ephemeride(_base(app).donnees)
