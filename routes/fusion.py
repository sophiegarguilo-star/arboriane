# -*- coding: utf-8 -*-
"""Routes de la fusion assistée (L14) : doublons scorés, comparaison, fusion
guidée de personnes, et fusion des orthographes de lieux."""

from routes import route
from services import fusion_assistee as fa


def _besoin_arbre(app):
    return None if app.base else (400, {"erreur": "Aucun arbre ouvert."})


@route("GET", r"^/api/fusion/doublons$")
def doublons(app, params, corps):
    err = _besoin_arbre(app)
    if err:
        return err
    return {"paires": fa.paires_scorees(app.base.donnees)}


@route("GET", r"^/api/fusion/comparer$")
def comparer(app, params, corps):
    err = _besoin_arbre(app)
    if err:
        return err
    c = fa.comparer(app.base.donnees, params.get("a", ""), params.get("b", ""))
    if not c:
        return (404, {"erreur": "Personne introuvable."})
    return c


@route("POST", r"^/api/fusion/personnes$")
def fusionner_personnes(app, params, corps):
    err = _besoin_arbre(app)
    if err:
        return err
    c = corps or {}
    resume = fa.fusionner_assiste(app.base, c.get("garde", ""), c.get("absorbe", ""),
                                  c.get("choix") or {}, bool(c.get("forcer_sexe")))
    return {"ok": True, "resume": resume}


@route("POST", r"^/api/fusion/ecarter$")
def ecarter(app, params, corps):
    """Marque une paire « pas un doublon » pour ne plus la reproposer."""
    err = _besoin_arbre(app)
    if err:
        return err
    c = corps or {}
    try:
        res = fa.ecarter_paire(app.base, c.get("a", ""), c.get("b", ""))
    except ValueError as e:
        return (400, {"erreur": str(e)})
    return {"ok": True, **res}


@route("GET", r"^/api/fusion/lieux$")
def lieux(app, params, corps):
    err = _besoin_arbre(app)
    if err:
        return err
    return {"groupes": fa.lieux_doublons(app.base.donnees)}


@route("POST", r"^/api/fusion/lieux$")
def fusionner_lieux(app, params, corps):
    err = _besoin_arbre(app)
    if err:
        return err
    c = corps or {}
    return {"ok": True, **fa.fusionner_lieux(app.base, c.get("canonique", ""),
                                             c.get("absorbes") or [])}
