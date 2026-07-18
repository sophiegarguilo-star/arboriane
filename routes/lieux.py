# -*- coding: utf-8 -*-
"""Routes Lieux / Carte : agrégation des lieux, carte des migrations et
géocodage OpenStreetMap (opt-in, jamais automatique)."""

from routes import route
from services import lieux as lieux_svc
from services import lieux_ref
from services import fusion_assistee as fusion_svc
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


@route("GET", r"^/api/lieux$")
def lister(app, params, corps):
    return lieux_svc.lister(_base(app).donnees)


@route("POST", r"^/api/lieux/ajouter-pays$")
def ajouter_pays(app, params, corps):
    """Ajoute le « pays par défaut » (Réglages) aux lieux sans pays — soit la
    liste fournie {lieux:[...]}, soit tous. Réécrit chaque « Ville » en
    « Ville, Pays » partout (via la fusion de lieux). Persiste si modifié."""
    base = _base(app)
    pays = (app.lire_reglages().get("pays_defaut") or "").strip()
    if not pays:
        raise ErreurValidation("Renseignez d'abord un « Pays par défaut » "
                               "dans les Réglages (section Géocodage).")
    noms = (corps or {}).get("lieux")
    if not noms:
        noms = [x["nom"] for x in lieux_svc.sans_pays(base.donnees)]
    modifies = 0
    for nom in noms:
        parts = [p.strip() for p in (nom or "").split(",") if p.strip()]
        if not parts or parts[-1].lower() in lieux_ref._PAYS:
            continue                       # déjà un pays : on n'y touche pas
        r = fusion_svc.fusionner_lieux(base, nom + ", " + pays, [nom])
        modifies += r.get("modifies", 0)
    if modifies:
        base.sauvegarder()
    return {"ok": True, "modifies": modifies}


@route("GET", r"^/api/carte$")
def carte(app, params, corps):
    d = _base(app).donnees
    pid = params.get("id") or None
    mode = params.get("mode") or "personne"
    return lieux_svc.carte(d, pid, mode)


@route("GET", r"^/api/lieux/suggest$")
def suggest(app, params, corps):
    """Autocomplétion de lieux géolocalisés (Nominatim). Strictement opt-in :
    ne renvoie rien tant que le géocodage n'est pas autorisé dans les Réglages."""
    if not app.lire_reglages().get("geocodage_ok"):
        return {"suggestions": [], "geocodage_ok": False}
    q = (params.get("q") or "").strip()
    return {"suggestions": lieux_svc.suggerer(q), "geocodage_ok": True}


@route("POST", r"^/api/lieux/coords$")
def coords(app, params, corps):
    """Mémorise les coordonnées d'un lieu choisi dans l'autocomplétion (déjà
    connues), pour qu'il apparaisse aussitôt sur la carte."""
    base = _base(app)
    ok = lieux_svc.memoriser_coords(base.donnees, (corps or {}).get("nom"),
                                    (corps or {}).get("lat"), (corps or {}).get("lon"))
    if ok:
        base.sauvegarder()
    return {"ok": ok}


@route("POST", r"^/api/lieux/geocoder$")
def geocoder(app, params, corps):
    """Géocode (opt-in) les lieux non encore géocodés — ou la liste fournie dans
    {lieux:[...]}. Mutation : passe la sécurité via Content-Type JSON. Persiste
    le cache de coordonnées après géocodage.
    Strictement opt-in : aucun appel réseau tant que le géocodage n'est pas
    autorisé dans les Réglages (comme la route `suggest`)."""
    reglages = app.lire_reglages()
    if not reglages.get("geocodage_ok"):
        return {"geocodes": 0, "echecs": 0, "traites": 0, "restants": 0,
                "geocodage_ok": False}
    base = _base(app)
    noms = (corps or {}).get("lieux")
    resultat = lieux_svc.geocoder(base.donnees, noms,
                                  pays_defaut=reglages.get("pays_defaut") or "")
    if resultat["geocodes"]:
        base.sauvegarder()
    return resultat
