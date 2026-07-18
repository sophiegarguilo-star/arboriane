# -*- coding: utf-8 -*-
"""
Routes du Lot 7 — parenté avancée : implexe, consanguinité, Aboville, Sosa permanent.

Les calculs vivent dans les services ; ici on route et on persiste (Sosa figé).
"""

from routes import route
from services import implexe as implexe_svc
from services import consanguinite as cons_svc
from services import aboville as aboville_svc
from services import sosa_permanent as sp_svc
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


def _gen(params, defaut=12, maxi=20):
    try:
        g = int(params.get("gen") or params.get("generations") or defaut)
    except (TypeError, ValueError):
        g = defaut
    return max(1, min(g, maxi))


@route("GET", r"^/api/implexe$")
def implexe(app, params, corps):
    d = _base(app).donnees
    racine = params.get("id") or app.manifeste.get("racine_id")
    r = implexe_svc.analyser(d, racine, _gen(params))
    return r if r is not None else (404, {"erreur": "Personne racine introuvable."})


@route("GET", r"^/api/consanguinite$")
def consanguinite(app, params, corps):
    d = _base(app).donnees
    a, b = params.get("a"), params.get("b")
    if not a or not b:
        raise ErreurValidation("Deux personnes sont attendues.")
    r = cons_svc.coefficient(d, a, b)
    if r is None:
        raise ErreurValidation("Choisissez deux personnes distinctes et existantes.")
    return r


@route("GET", r"^/api/aboville$")
def aboville(app, params, corps):
    d = _base(app).donnees
    racine = params.get("id") or app.manifeste.get("racine_id")
    r = aboville_svc.descendance(d, racine)
    return r if r is not None else (404, {"erreur": "Personne introuvable."})


@route("GET", r"^/api/sosa-permanent$")
def sosa_perm_lister(app, params, corps):
    return sp_svc.lister(_base(app).donnees)


@route("POST", r"^/api/sosa-permanent/figer$")
def sosa_perm_figer(app, params, corps):
    base = _base(app)
    racine = (corps or {}).get("id") or app.manifeste.get("racine_id")
    n = sp_svc.figer(base.donnees, racine, 40)
    if not n:
        raise ErreurValidation("Personne racine introuvable.")
    base.sauvegarder()
    return {"ok": True, "numerotees": n}


@route("POST", r"^/api/sosa-permanent/effacer$")
def sosa_perm_effacer(app, params, corps):
    base = _base(app)
    n = sp_svc.effacer(base.donnees)
    base.sauvegarder()
    return {"ok": True, "effacees": n}
