# -*- coding: utf-8 -*-
"""Routes du Lot L16 — conversion de dates (calendrier républicain, dates complexes)."""

from routes import route
from services import dates_rep as dr


@route("GET", r"^/api/date/convertir$")
def convertir(app, params, corps):
    texte = params.get("texte", "")
    r = dr.convertir(texte)
    return r or {"entree": texte, "republicain": "", "gregorien": ""}


@route("GET", r"^/api/date/decrire$")
def decrire(app, params, corps):
    return {"texte": dr.decrire(params.get("texte", ""))}
