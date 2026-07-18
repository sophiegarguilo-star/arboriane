# -*- coding: utf-8 -*-
"""Routes des favoris & ensembles de personnes (L13)."""

from routes import route
from services import favoris as fav


def _b(app):
    return app.base


def _garde(app):
    return None if app.base else (400, {"erreur": "Aucun arbre ouvert."})


@route("GET", r"^/api/favoris$")
def etat(app, params, corps):
    err = _garde(app)
    if err:
        return err
    d = _b(app).donnees
    return {"favoris": fav.lister_favoris(d), "ensembles": fav.lister_ensembles(d)}


@route("POST", r"^/api/favoris/basculer$")
def basculer(app, params, corps):
    err = _garde(app)
    if err:
        return err
    return {"ok": True, "favori": fav.basculer(_b(app), (corps or {}).get("id", ""))}


@route("POST", r"^/api/ensembles$")
def creer(app, params, corps):
    err = _garde(app)
    if err:
        return err
    c = corps or {}
    return {"ok": True, "ensemble": fav.creer_ensemble(_b(app), c.get("nom", ""), c.get("ids") or [])}


@route("GET", r"^/api/ensembles/(?P<eid>[A-Za-z0-9]+)$")
def membres(app, params, corps, eid):
    err = _garde(app)
    if err:
        return err
    m = fav.membres(_b(app).donnees, eid)
    if m is None:
        return (404, {"erreur": "Ensemble inconnu."})
    return m


@route("PUT", r"^/api/ensembles/(?P<eid>[A-Za-z0-9]+)$")
def renommer(app, params, corps, eid):
    err = _garde(app)
    if err:
        return err
    e = fav.renommer_ensemble(_b(app), eid, (corps or {}).get("nom", ""))
    if e is None:
        return (404, {"erreur": "Ensemble inconnu."})
    return {"ok": True, "nom": e["nom"]}


@route("DELETE", r"^/api/ensembles/(?P<eid>[A-Za-z0-9]+)$")
def supprimer(app, params, corps, eid):
    err = _garde(app)
    if err:
        return err
    return {"ok": fav.supprimer_ensemble(_b(app), eid)}


@route("POST", r"^/api/ensembles/(?P<eid>[A-Za-z0-9]+)/membre$")
def membre(app, params, corps, eid):
    err = _garde(app)
    if err:
        return err
    return {"ok": True, "membre": fav.basculer_membre(_b(app), eid, (corps or {}).get("id", ""))}
