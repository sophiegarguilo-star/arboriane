# -*- coding: utf-8 -*-
"""Routes d'analyse : Sosa, Parenté, Cohérence, Statistiques."""

from routes import route
from services import sosa as sosa_svc
from services import parente as parente_svc
from services import coherence as coherence_svc
from services import statistiques as stats_svc
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


@route("GET", r"^/api/sosa$")
def sosa(app, params, corps):
    d = _base(app).donnees
    de_cujus = params.get("de_cujus") or app.manifeste.get("racine_id")
    try:
        gen = int(params.get("generations") or 10)
    except (TypeError, ValueError):
        gen = 10
    gen = max(1, min(gen, 20))          # bornée : évite un message d'erreur brut et un abus
    res = sosa_svc.ascendance(d, de_cujus, gen)
    if not res:
        return (404, {"erreur": "Personne racine introuvable."})
    return res


@route("GET", r"^/api/parente$")
def parente(app, params, corps):
    d = _base(app).donnees
    a, b = params.get("a"), params.get("b")
    if not a or not b:
        raise ErreurValidation("Deux personnes sont attendues.")
    lien = parente_svc.lien_complet(d, a, b)
    return {"lien": lien}


@route("GET", r"^/api/coherence$")
def coherence(app, params, corps):
    return coherence_svc.analyser(_base(app).donnees, app.manifeste.get("racine_id"))


@route("GET", r"^/api/statistiques$")
def statistiques(app, params, corps):
    from services import personnes as personnes_svc
    d = _base(app).donnees
    exclure = personnes_svc.ids_hors_famille(d, app.manifeste.get("racine_id"))
    return stats_svc.calculer(d, exclure=exclure)
