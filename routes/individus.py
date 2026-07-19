# -*- coding: utf-8 -*-
"""Routes des personnes (individus)."""

from routes import route
from services import personnes
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


def _sources_citees(obj, acc=None):
    """Collecte récursivement les identifiants de sources cités par une personne."""
    if acc is None:
        acc = set()
    if isinstance(obj, dict):
        for cle, val in obj.items():
            if cle == "citations" and isinstance(val, list):
                for c in val:
                    if isinstance(c, dict) and c.get("source"):
                        acc.add(c["source"])
            else:
                _sources_citees(val, acc)
    elif isinstance(obj, list):
        for x in obj:
            _sources_citees(x, acc)
    return acc


@route("GET", r"^/api/individus$")
def lister(app, params, corps):
    racine = app.manifeste.get("racine_id") if app.manifeste else None
    return personnes.lister(_base(app), racine)


@route("GET", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)$")
def fiche(app, params, corps, pid):
    racine = app.manifeste.get("racine_id") if app.manifeste else None
    base = _base(app)
    f = personnes.fiche(base, pid, racine)
    if not f:
        return (404, {"erreur": "Personne introuvable."})
    # MET-01 : type de filiation (adoption / accueil / probable) lisible par la
    # fiche — côté personne (son lien à SES parents, lu dans ses familles famc)
    # et côté unions (le lien de chacun de ses enfants, fam["pedi"]).
    fams = base.donnees["familles"]
    f["filiation"] = ""
    for fid in f.get("famc") or []:
        t = ((fams.get(fid) or {}).get("pedi") or {}).get(pid)
        if t:
            f["filiation"] = t
            break
    for u in f.get("unions") or []:
        pedi = (fams.get(u.get("famille")) or {}).get("pedi")
        if pedi:
            u["pedi"] = dict(pedi)
    return f


@route("GET", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)/gedcom$")
def gedcom_individu(app, params, corps, pid):
    """GEDCOM d'une seule personne (ses faits + les sources qu'elle cite).
    Pratique pour copier/transmettre une fiche isolée sans exporter tout l'arbre."""
    import copy as _copy
    from core import gedcom
    base = _base(app)
    ind = base.donnees["individus"].get(pid)
    if not ind:
        return (404, {"erreur": "Personne introuvable."})
    copie = _copy.deepcopy(ind)
    copie["fams"] = []           # pas de pointeurs de familles pendants
    copie["famc"] = []
    ids = _sources_citees(copie)
    srcs = {sid: base.donnees["sources"][sid]
            for sid in ids if sid in base.donnees.get("sources", {})}
    mini = {"individus": {pid: copie}, "familles": {}, "sources": srcs,
            "lieux": base.donnees.get("lieux", {})}
    return {"ok": True, "gedcom": gedcom.exporter(mini, avec_medias=False)}


@route("POST", r"^/api/individus$")
def creer(app, params, corps):
    non_id = bool(corps.pop("non_identifiee", False))
    ind = personnes.creer(_base(app), corps, non_identifiee=non_id)
    # Première personne d'un arbre neuf : elle devient la racine (Sosa 1) au lieu
    # de laisser le « I1 » codé en dur du manifeste pointer dans le vide.
    app.garantir_racine(ind["id"])
    return {"ok": True, "id": ind["id"]}


@route("PUT", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)$")
def modifier(app, params, corps, pid):
    ind = _base(app).modifier_individu(pid, corps)
    if not ind:
        return (404, {"erreur": "Personne introuvable."})
    return {"ok": True, "id": ind["id"]}


@route("DELETE", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)$")
def supprimer(app, params, corps, pid):
    base = _base(app)
    if not base.supprimer_individu(pid):
        return (404, {"erreur": "Personne introuvable."})
    # Supprimer la personne RACINE laissait un manifeste pointant dans le vide :
    # Sosa n'affichait plus rien. On adopte alors une autre personne.
    inds = base.donnees["individus"]
    if inds and not app.racine_valide():
        app.garantir_racine(next(iter(inds)))
    return {"ok": True}


@route("POST", r"^/api/individus/restaurer-dernier$")
def restaurer_dernier(app, params, corps):
    """Annule la DERNIÈRE suppression de personne : l'instantané le plus récent
    de <arbre>/Corbeille/ est rejoué — la personne revient sous son id
    d'origine, avec ses liens dans les familles encore existantes."""
    base = _base(app)
    ind = base.restaurer_dernier_supprime()
    if not ind:
        return (404, {"erreur": "Aucune suppression récente à annuler."})
    # Si l'arbre s'était retrouvé sans racine valide, la personne restaurée
    # peut la reprendre (même auto-réparation qu'à la création).
    app.garantir_racine(ind["id"])
    from core.modele import nom_complet
    return {"ok": True, "id": ind["id"], "nom": nom_complet(ind)}


@route("PUT", r"^/api/individus/(?P<pid>[A-Za-z0-9]+)/medias$")
def medias(app, params, corps, pid):
    ind = _base(app).definir_medias(pid, corps.get("medias", []))
    if not ind:
        return (404, {"erreur": "Personne introuvable."})
    return {"ok": True, "medias": ind["medias"]}
