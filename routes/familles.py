# -*- coding: utf-8 -*-
"""Routes des liens familiaux (ajout rapide parent / conjoint / enfant)."""

from routes import route
from services import personnes
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


def _verifier_pid(base, pid):
    """Garantit que la personne d'ancrage existe AVANT toute création — sinon on
    créerait une personne orpheline non rattachée (bug de pollution silencieuse)."""
    if pid not in base.donnees["individus"]:
        raise ErreurValidation("Personne introuvable.")


def _creer_ou_reutiliser(base, corps):
    """Renvoie l'id de la personne liée : soit `id` fourni, soit création à la
    volée depuis `champs`. Applique le garde-fou de saisie."""
    if corps.get("id"):
        return corps["id"]
    champs = corps.get("champs") or {}
    non_id = bool(corps.get("non_identifiee"))
    return personnes.creer(base, champs, non_identifiee=non_id)["id"]


@route("POST", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)/parent$")
def ajouter_parent(app, params, corps, pid):
    """Ajoute un père ou une mère à `pid`. `role` = 'pere' | 'mere'."""
    base = _base(app)
    _verifier_pid(base, pid)
    parent_id = _creer_ou_reutiliser(base, corps)
    ind = base.donnees["individus"].get(pid)
    fam = base.donnees["familles"].get((ind.get("famc") or [None])[0]) if ind else None
    pere = fam.get("mari") if fam else ""
    mere = fam.get("epouse") if fam else ""
    if corps.get("role") == "mere":
        mere = parent_id
    else:
        pere = parent_id
    base.definir_parents(pid, pere, mere)
    return {"ok": True, "id": parent_id}


@route("POST", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)/conjoint$")
def ajouter_conjoint(app, params, corps, pid):
    base = _base(app)
    _verifier_pid(base, pid)
    conjoint_id = _creer_ou_reutiliser(base, corps)
    base.ajouter_conjoint(pid, conjoint_id, corps.get("mariage"))
    return {"ok": True, "id": conjoint_id}


@route("POST", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)/enfant$")
def ajouter_enfant(app, params, corps, pid):
    base = _base(app)
    _verifier_pid(base, pid)
    enfant_id = _creer_ou_reutiliser(base, corps)
    base.ajouter_enfant(pid, enfant_id, nouvelle=bool(corps.get("nouvelle")))
    return {"ok": True, "id": enfant_id}


@route("POST", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)/frere_soeur$")
def ajouter_fratrie(app, params, corps, pid):
    """Ajoute un frère / une sœur : la personne devient un enfant de plus des
    parents de `pid`."""
    base = _base(app)
    _verifier_pid(base, pid)
    frere_id = _creer_ou_reutiliser(base, corps)
    base.ajouter_fratrie(pid, frere_id)
    return {"ok": True, "id": frere_id}


@route("POST", r"^/api/familles/(?P<fid>[A-Za-z0-9]+)/enfant$")
def ajouter_enfant_famille(app, params, corps, fid):
    """Ajoute un enfant à une union PRÉCISE (bouton « ＋ enfant » d'une union) —
    ne retombe jamais sur la première union du parent."""
    base = _base(app)
    if fid not in base.donnees["familles"]:
        return (404, {"erreur": "Famille introuvable."})
    enfant_id = _creer_ou_reutiliser(base, corps)
    base.ajouter_enfant_famille(fid, enfant_id)
    return {"ok": True, "id": enfant_id}


@route("PUT", r"^/api/familles/(?P<fid>[A-Za-z0-9]+)/conjoint$")
def remplacer_conjoint(app, params, corps, fid):
    """Remplace (ou retire, `id` absent/vide) un parent d'une union PRÉCISE.
    Corps : {role: 'mari'|'epouse', id?}."""
    base = _base(app)
    if fid not in base.donnees["familles"]:
        return (404, {"erreur": "Famille introuvable."})
    role = corps.get("role")
    if role not in ("mari", "epouse"):
        return (400, {"erreur": "Rôle invalide."})
    fam = base.remplacer_conjoint(fid, role, corps.get("id") or "")
    if fam is None:
        return (400, {"erreur": "Modification impossible."})
    return {"ok": True}


@route("POST", r"^/api/individus/(?P<eid>[A-Za-z0-9]+)/deplacer$")
def deplacer_enfant(app, params, corps, eid):
    """Déplace un enfant vers une autre famille (`famille` = fid) ou le détache
    de tout couple (`famille` vide)."""
    base = _base(app)
    _verifier_pid(base, eid)
    fid = corps.get("famille") or ""
    if fid:
        if fid not in base.donnees["familles"]:
            return (404, {"erreur": "Famille introuvable."})
        base.ajouter_enfant_famille(fid, eid)
    else:
        base.definir_parents(eid, "", "")
    return {"ok": True}


@route("PUT", r"^/api/familles/(?P<fid>[A-Za-z0-9]+)$")
def modifier_famille(app, params, corps, fid):
    fam = _base(app).modifier_famille(fid, corps)
    if not fam:
        return (404, {"erreur": "Famille introuvable."})
    return {"ok": True}
