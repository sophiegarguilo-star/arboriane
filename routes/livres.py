# -*- coding: utf-8 -*-
"""
Routes des livres biographiques (L10 — Jalon 1).

  GET    /api/livres            → liste des livres de l'arbre
  POST   /api/livres            → crée un livre { referent, titre? }
  GET    /api/livres/<id>       → un livre (JSON)
  PUT    /api/livres/<id>       → enregistre un livre (titre, sections, mise en page…)
  DELETE /api/livres/<id>       → supprime un livre
  GET    /api/livres/<id>/html  → rend le livre en HTML autonome { html }
"""

import base64
import mimetypes
import os

from routes import route
from services.livre import composeur, rendu_html
from core.validation import ErreurValidation

_MAX_IMG = 8 * 1024 * 1024          # par fichier : au-delà, non intégré
_BUDGET_TOTAL = 48 * 1024 * 1024    # budget cumulé : borne le poids total du HTML


def _lecteur_media(app):
    """Renvoie un callable(fichier) -> data-URI d'IMAGE, pour intégrer les photos
    dans le HTML autonome. Cherche dans Photos/ puis Sources/. "" si absent, trop
    lourd, non-image (pas de PDF/txt encapsulé en <img>), ou budget global atteint."""
    etat = {"total": 0}

    def lire(fichier):
        if not fichier:
            return ""
        for cat in ("Photos", "Sources"):
            chemin = app.chemin_media(cat, fichier)
            if not chemin:
                continue
            mime = mimetypes.guess_type(chemin)[0] or ""
            if not mime.startswith("image/"):
                return ""
            try:
                taille = os.path.getsize(chemin)
                if taille > _MAX_IMG or etat["total"] + taille > _BUDGET_TOTAL:
                    return ""
                with open(chemin, "rb") as f:
                    data = f.read()
            except OSError:
                return ""
            etat["total"] += taille
            return "data:%s;base64,%s" % (mime, base64.b64encode(data).decode("ascii"))
        return ""
    return lire


def _ctx(app):
    if not app.base or not app.espace_chemin:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base, app.espace_chemin


@route("GET", r"^/api/livres$")
def lister(app, params, corps):
    base, ec = _ctx(app)
    return {"livres": composeur.lister(ec, base.donnees)}


@route("POST", r"^/api/livres$")
def creer(app, params, corps):
    base, ec = _ctx(app)
    c = corps or {}
    livre = composeur.creer(ec, base.donnees, (c.get("referent") or "").strip(),
                            c.get("titre", ""), (c.get("type") or "monographie"))
    return {"ok": True, "livre": livre}


@route("GET", r"^/api/livres/(?P<lid>[^/]+)$")
def lire(app, params, corps, lid):
    base, ec = _ctx(app)
    livre = composeur.lire(ec, lid)
    if not livre:
        raise ErreurValidation("Livre introuvable.")
    return {"livre": livre}


@route("PUT", r"^/api/livres/(?P<lid>[^/]+)$")
def enregistrer(app, params, corps, lid):
    base, ec = _ctx(app)
    if not composeur.lire(ec, lid):
        raise ErreurValidation("Livre introuvable.")
    c = dict(corps or {})
    c["id"] = lid                       # l'id vient de l'URL, pas du corps
    return {"ok": True, "livre": composeur.enregistrer(ec, c)}


@route("DELETE", r"^/api/livres/(?P<lid>[^/]+)$")
def supprimer(app, params, corps, lid):
    base, ec = _ctx(app)
    return {"ok": composeur.supprimer(ec, lid)}


@route("GET", r"^/api/livres/(?P<lid>[^/]+)/html$")
def rendu(app, params, corps, lid):
    base, ec = _ctx(app)
    livre = composeur.lire(ec, lid)
    if not livre:
        raise ErreurValidation("Livre introuvable.")
    return {"html": rendu_html.rendre(base, livre, _lecteur_media(app))}
