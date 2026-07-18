# -*- coding: utf-8 -*-
"""
Routes des mises à jour (voir services/maj.py pour la philosophie).

  GET  /api/maj/etat        -> version, dernière vue, nouveautés, préférence
  POST /api/maj/vu          -> marque la version courante comme « vue »
  POST /api/maj/preference  -> {actif: bool} : autorise ou non la vérif en ligne
  GET  /api/maj/verifier    -> interroge GitHub (UNIQUEMENT si autorisé)

La préférence et la « dernière version vue » sont rangées dans les réglages
locaux (reglages.json), jamais dans un arbre.
"""

from routes import route
from services import maj as maj_svc
from core.version import VERSION


@route("GET", r"^/api/maj/etat$")
def etat(app, params, corps):
    r = app.lire_reglages()
    vue = r.get("derniere_version_vue")
    pref = r.get("verif_maj")                 # True / False / None (jamais choisi)
    return {
        "version": VERSION,
        "derniere_vue": vue,
        "premier_choix": pref is None,        # -> proposer l'opt-in au lancement
        "verif_active": bool(pref),
        "nouveautes": maj_svc.notes_depuis(vue),
    }


@route("POST", r"^/api/maj/vu$")
def marquer_vu(app, params, corps):
    app.ecrire_reglages({"derniere_version_vue": VERSION})
    return {"ok": True}


@route("POST", r"^/api/maj/preference$")
def preference(app, params, corps):
    actif = bool((corps or {}).get("actif"))
    app.ecrire_reglages({"verif_maj": actif})
    return {"ok": True, "verif_active": actif}


@route("GET", r"^/api/maj/verifier$")
def verifier(app, params, corps):
    if not app.lire_reglages().get("verif_maj"):
        return {"autorise": False}            # respecte l'opt-in : aucun appel réseau
    resultat = maj_svc.verifier_en_ligne()
    resultat["autorise"] = True
    return resultat
