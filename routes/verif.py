# -*- coding: utf-8 -*-
"""
Routes du Lot 5 — « Qualité des sources ».

Un seul point d'entrée agrège l'écran (GET /api/verif) ; un second applique une
correction de sexe déduite (POST /api/verif/sexe). Les calculs vivent dans les
services (verif_medias, deductions, recherche, coherence) ; ici on ne fait que
router et persister.
"""

from routes import route
from services import verif_medias as vm_svc
from services import gedcom_dates as gedcom_dates_svc
from services import deductions as ded_svc
from services import recherche as recherche_svc
from services import coherence as coherence_svc
from services import lieux as lieux_svc
from core.validation import ErreurValidation


def _base(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    return app.base


@route("GET", r"^/api/verif$")
def verif(app, params, corps):
    """Tout ce qu'affiche l'écran « Qualité des sources », en une requête."""
    d = _base(app).donnees
    return {
        "fichiers_manquants": vm_svc.fichiers_manquants(app),
        "a_transcrire": vm_svc.a_transcrire(d),
        "sexes_absents": ded_svc.sexes_absents(d),
        "noms_absents": ded_svc.noms_absents(d),
        "deces_presumes": ded_svc.deces_presumes(d),
        "plan_depots": recherche_svc.par_depot(d),
        "coherence": coherence_svc.analyser(d, app.manifeste.get("racine_id")),
        "dates_douteuses": gedcom_dates_svc.dates_invalides(d),
        "lieux_sans_pays": lieux_svc.sans_pays(d),
        "pays_defaut": app.lire_reglages().get("pays_defaut") or "",
    }


@route("POST", r"^/api/verif/sexe$")
def appliquer_sexe(app, params, corps):
    """Pose un sexe (déduit puis validé par l'utilisateur) sur une personne."""
    base = _base(app)
    corps = corps or {}
    ded_svc.appliquer_sexe(base.donnees, corps.get("id"), corps.get("sexe"))
    base.sauvegarder()
    return {"ok": True, "id": corps.get("id"), "sexe": corps.get("sexe")}


@route("POST", r"^/api/verif/deces$")
def poser_deces(app, params, corps):
    """Marque « décédé·e (sans date) » une personne présumée vivante trop âgée
    (corps {id}), ou TOUTES celles détectées (corps {tous:true})."""
    base = _base(app)
    corps = corps or {}
    if corps.get("tous"):
        res = ded_svc.appliquer_deces_tous(base.donnees)
        base.sauvegarder()
        return {"ok": True, "corriges": res["total"]}
    ded_svc.appliquer_deces(base.donnees, corps.get("id"))
    base.sauvegarder()
    return {"ok": True, "id": corps.get("id")}
