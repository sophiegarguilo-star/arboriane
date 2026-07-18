# -*- coding: utf-8 -*-
"""Routes des sources, citations, médias (scans & photos)."""

import os

from routes import route
from services import sources as src_svc
from core.validation import ErreurValidation

_PLAFOND_MEDIA = 12 * 1024 * 1024   # 12 Mo


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


# ── Sources ───────────────────────────────────────────────────────────
@route("GET", r"^/api/sources$")
def lister(app, params, corps):
    d = _base(app).donnees
    return {"sources": src_svc.lister(d), "types": src_svc.types(d)}


@route("GET", r"^/api/sources/(?P<sid>[A-Za-z0-9]+)$")
def fiche(app, params, corps, sid):
    f = src_svc.fiche_source(_base(app).donnees, sid)
    if not f:
        return (404, {"erreur": "Source introuvable."})
    return f


@route("POST", r"^/api/sources$")
def creer(app, params, corps):
    src = _base(app).creer_source(corps)
    return {"ok": True, "id": src["id"]}


@route("PUT", r"^/api/sources/(?P<sid>[A-Za-z0-9]+)$")
def modifier(app, params, corps, sid):
    src = _base(app).modifier_source(sid, corps)
    if not src:
        return (404, {"erreur": "Source introuvable."})
    return {"ok": True}


@route("DELETE", r"^/api/sources/(?P<sid>[A-Za-z0-9]+)$")
def supprimer(app, params, corps, sid):
    if not _base(app).supprimer_source(sid):
        return (404, {"erreur": "Source introuvable."})
    return {"ok": True}


@route("POST", r"^/api/sources/(?P<sid>[A-Za-z0-9]+)/personne$")
def taguer(app, params, corps, sid):
    src = _base(app).taguer_personne_source(sid, corps.get("id"), corps.get("role", ""))
    if not src:
        return (404, {"erreur": "Source introuvable."})
    return {"ok": True}


# ── Citations (preuves attachées à un fait) ───────────────────────────
@route("POST", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)/citer$")
def citer(app, params, corps, pid):
    citation = {"source": corps.get("source"), "page": corps.get("page", ""),
                "quay": corps.get("quay"), "role": corps.get("role", "")}
    ind = _base(app).citer(pid, corps.get("fait", "personne"), citation,
                           famille=corps.get("famille"))
    if not ind:
        return (404, {"erreur": "Personne ou fait introuvable."})
    return {"ok": True}


@route("GET", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)/preuves$")
def preuves(app, params, corps, pid):
    p = src_svc.preuves_personne(_base(app).donnees, pid)
    if p is None:
        return (404, {"erreur": "Personne introuvable."})
    return p


# ── Médias (upload base64) ────────────────────────────────────────────
@route("POST", r"^/api/media/(?P<categorie>Sources|Photos|Fonds)$")
def televerser(app, params, corps, categorie):
    nom = app.enregistrer_media(categorie, corps.get("nom", "image"),
                                corps.get("data", ""))
    return {"ok": True, "fichier": nom}


@route("POST", r"^/api/media/(?P<categorie>Sources|Photos|Fonds)/renommer$")
def renommer_media(app, params, corps, categorie):
    """Renomme un scan tout juste déposé, selon la nomenclature. Refusé si le
    fichier est déjà référencé par une source : on ne casse pas une citation."""
    de = (corps.get("de") or "").strip()
    vers = (corps.get("vers") or "").strip()
    if not de or not vers:
        raise ErreurValidation("Noms de fichier manquants.")
    if app._media_reference(de):
        raise ErreurValidation("Ce fichier est déjà cité par une source : "
                               "il ne peut plus être renommé.")
    try:
        final = app.renommer_media(categorie, de, vers)
    except ValueError as e:
        raise ErreurValidation(str(e))
    return {"ok": True, "fichier": final}


@route("POST", r"^/api/media/(?P<categorie>Sources|Photos|Fonds)/url$")
def televerser_url(app, params, corps, categorie):
    """Télécharge une image depuis une URL http(s) et l'enregistre dans l'arbre."""
    import base64
    import urllib.request
    from urllib.parse import urlparse
    url = (corps.get("url") or "").strip()
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.netloc:
        raise ErreurValidation("URL invalide (http:// ou https:// attendu).")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Arboriane/1.0"})
        with urllib.request.urlopen(req, timeout=15) as rep:
            ctype = (rep.headers.get("Content-Type") or "").lower()
            if "image" not in ctype:
                raise ErreurValidation("Ce lien ne pointe pas vers une image.")
            data = rep.read(_PLAFOND_MEDIA + 1)
    except ErreurValidation:
        raise
    except Exception:
        raise ErreurValidation("Téléchargement impossible depuis cette adresse.")
    if len(data) > _PLAFOND_MEDIA:
        raise ErreurValidation("Image trop volumineuse (max 12 Mo).")
    nom = os.path.basename(p.path) or "image"
    fichier = app.enregistrer_media(categorie, nom,
                                    base64.b64encode(data).decode("ascii"))
    return {"ok": True, "fichier": fichier}


@route("DELETE", r"^/api/media/(?P<categorie>Sources|Photos|Fonds)/(?P<nom>.+)$")
def supprimer_media(app, params, corps, categorie, nom):
    """Supprime un média UNIQUEMENT s'il n'est référencé nulle part (nettoyage
    d'un import abandonné). Un fichier utilisé n'est jamais supprimé."""
    from urllib.parse import unquote
    supprime = app.supprimer_media_si_inutilise(categorie, unquote(nom))
    return {"ok": True, "supprime": supprime}
