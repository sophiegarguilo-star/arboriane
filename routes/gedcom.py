# -*- coding: utf-8 -*-
"""Routes d'import / export GEDCOM."""

import os

from routes import route
from services import echange
from services import gedcom_charset
from services import import_lieux
from core import gedcom as gedcom_svc
from core.validation import ErreurValidation


def _actif(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")


@route("GET", r"^/api/export/gedcom$")
def exporter(app, params, corps):
    _actif(app)
    chemin, texte = echange.exporter(app)
    return {"ok": True, "fichier": os.path.basename(chemin), "texte": texte}


@route("POST", r"^/api/import/gedcom/comparer$")
def comparer(app, params, corps):
    _actif(app)
    texte, _enc = gedcom_charset.texte_depuis_corps(corps)
    if not texte.strip():
        raise ErreurValidation("Aucun contenu GEDCOM reçu.")
    return echange.comparer(app, texte)


@route("POST", r"^/api/import/gedcom/lieux$")
def apercu_lieux(app, params, corps):
    """Aperçu des lieux distincts d'un GEDCOM entrant (écran de correspondance à
    l'import) : ne touche PAS l'arbre, se contente d'analyser le fichier."""
    _actif(app)
    texte, _enc = gedcom_charset.texte_depuis_corps(corps)
    if not texte.strip():
        raise ErreurValidation("Aucun contenu GEDCOM reçu.")
    nouveau = gedcom_svc.importer(texte)
    pays = app.lire_reglages().get("pays_defaut") or ""
    return import_lieux.analyser(nouveau, pays)


@route("POST", r"^/api/import/gedcom/appliquer$")
def appliquer(app, params, corps):
    _actif(app)
    texte, enc = gedcom_charset.texte_depuis_corps(corps)
    if not texte.strip():
        raise ErreurValidation("Aucun contenu GEDCOM reçu.")
    if enc:
        gedcom_charset.journaliser(app.espace_chemin, enc.get("charset"),
                                   enc.get("fiable"), texte)
    corr = (corps or {}).get("corrections_lieux") or None
    resultat = echange.appliquer(app, texte, corr)
    # Le manifeste porte « I1 » par défaut ; un GEDCOM importé peut n'avoir aucun
    # I1 → Sosa et arbre resteraient muets. On adopte alors la 1re personne.
    inds = app.base.donnees["individus"]
    if inds and not app.racine_valide():
        app.garantir_racine(next(iter(inds)))
    return {"ok": True, **resultat}
