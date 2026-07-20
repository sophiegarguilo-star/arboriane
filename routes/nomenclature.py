# -*- coding: utf-8 -*-
"""Route de nomenclature : le formulaire de source demande au serveur le titre
et les noms de fichiers qu'il propose, pendant la saisie. La règle de nommage
vit dans services/nomenclature.py — un seul endroit, testable."""

from routes import route
from services import nomenclature as nm
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


def _personnes(app, ids):
    """Identifiants → {nom, prenoms}, dans l'ordre demandé. Les inconnus sont
    ignorés plutôt que de faire échouer une suggestion de confort."""
    inds = app.base.donnees["individus"]
    gens = []
    for pid in ids or []:
        ind = inds.get(pid)
        if ind:
            gens.append({"nom": ind.get("nom", ""), "prenoms": ind.get("prenoms", "")})
    return gens


@route("POST", r"^/api/nomenclature$")
def proposer(app, params, corps):
    """{type, personnes:[pid], date, lieu, fichiers:[nom]} → {titre, fichiers}."""
    return nm.apercu(
        type_acte=corps.get("type", ""),
        personnes=_personnes(app, corps.get("personnes")),
        date=corps.get("date", ""),
        lieu=corps.get("lieu", ""),
        fichiers=corps.get("fichiers") or [],
        existants=app.lister_medias("Sources"))


@route("GET", r"^/api/nomenclature/rangement$")
def rangement_apercu(app, params, corps):
    """Aperçu (lecture seule) : les scans à renommer selon la nomenclature."""
    return {"items": nm.plan(_base(app).donnees)}


@route("POST", r"^/api/nomenclature/rangement$")
def rangement_appliquer(app, params, corps):
    """Applique le rangement : renomme les scans + met à jour les citations.
    `items` (facultatif) restreint aux entrées choisies ; sinon tout le plan."""
    _base(app)
    items = corps.get("items")
    if items is None:
        items = nm.plan(app.base.donnees)
    return app.ranger_pieces(items)
