# -*- coding: utf-8 -*-
"""Routes du Lot 4 : santé, carnet, plan de recherche, réglages, assistant."""

from routes import route
from services import sante as sante_svc
from services import recherche as recherche_svc
from services import carnet as carnet_svc
from services import assistant as assistant_svc
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


# ── Santé de l'arbre ──────────────────────────────────────────────────
@route("GET", r"^/api/sante$")
def sante(app, params, corps):
    return sante_svc.analyser(_base(app).donnees)


# ── Plan de recherche ─────────────────────────────────────────────────
@route("GET", r"^/api/plan$")
def plan(app, params, corps):
    d = _base(app).donnees
    racine = params.get("id") or app.manifeste.get("racine_id")
    try:
        gen = int(params.get("gen") or 12)
    except (TypeError, ValueError):
        gen = 12
    return recherche_svc.plan(d, racine, gen,
                              carnet_svc.pistes_actives(app.espace_chemin))


# ── Carnet de bord ────────────────────────────────────────────────────
@route("GET", r"^/api/carnet$")
def carnet_liste(app, params, corps):
    _base(app)
    return {"entrees": carnet_svc.lister(app.espace_chemin, app.base.donnees)}


@route("GET", r"^/api/carnet/personne/(?P<pid>[A-Za-z0-9]+)$")
def carnet_mentions(app, params, corps, pid):
    """Notes du carnet qui taguent cette personne — affichées sur sa fiche."""
    _base(app)
    return {"entrees": carnet_svc.mentions_de(app.espace_chemin, pid, app.base.donnees)}


@route("POST", r"^/api/carnet$")
def carnet_ajouter(app, params, corps):
    _base(app)
    e = carnet_svc.ajouter(app.espace_chemin, corps)
    return {"ok": True, "id": e["id"]}


@route("PUT", r"^/api/carnet/(?P<cid>[A-Za-z0-9]+)$")
def carnet_modifier(app, params, corps, cid):
    _base(app)
    e = carnet_svc.modifier(app.espace_chemin, cid, corps)
    if not e:
        return (404, {"erreur": "Entrée introuvable."})
    return {"ok": True}


@route("DELETE", r"^/api/carnet/(?P<cid>[A-Za-z0-9]+)$")
def carnet_supprimer(app, params, corps, cid):
    _base(app)
    if not carnet_svc.supprimer(app.espace_chemin, cid):
        return (404, {"erreur": "Entrée introuvable."})
    return {"ok": True}


# ── Réglages (clé API jamais renvoyée en clair) ───────────────────────
@route("GET", r"^/api/reglages$")
def reglages_lire(app, params, corps):
    return app.reglages_publics()


@route("PUT", r"^/api/reglages$")
def reglages_ecrire(app, params, corps):
    champs = {}
    for cle in ("ia_fournisseur", "ia_modele"):
        if cle in corps:
            champs[cle] = corps[cle]
    if corps.get("effacer_cle"):
        champs["ia_cle"] = ""
    elif (corps.get("ia_cle") or "").strip():
        champs["ia_cle"] = corps["ia_cle"].strip()
    if "geocodage_ok" in corps:
        champs["geocodage_ok"] = bool(corps["geocodage_ok"])
    if "pays_defaut" in corps:
        champs["pays_defaut"] = (corps.get("pays_defaut") or "").strip()[:80]
    if "navigateur" in corps:
        nav = (corps.get("navigateur") or "").strip().lower()
        champs["navigateur"] = nav if nav in ("edge", "chrome", "firefox", "defaut") else ""
    app.ecrire_reglages(champs)
    return {"ok": True, **app.reglages_publics()}


# ── Assistant IA (facultatif) ─────────────────────────────────────────
@route("POST", r"^/api/assistant/mission$")
def assistant_mission(app, params, corps):
    _base(app)
    if not app.reglages_publics()["cle_definie"]:
        raise ErreurValidation("Aucune clé API configurée.")
    try:
        return assistant_svc.mission(app, corps.get("type", ""), corps.get("cible"))
    except Exception as e:
        return (502, {"erreur": "L'assistant n'a pas pu répondre : %s" % e})


@route("POST", r"^/api/assistant/chat$")
def assistant_chat(app, params, corps):
    _base(app)
    if not app.reglages_publics()["cle_definie"]:
        raise ErreurValidation("Aucune clé API configurée.")
    try:
        return assistant_svc.chat(app, corps.get("message", ""))
    except Exception as e:
        return (502, {"erreur": "L'assistant n'a pas pu répondre : %s" % e})
