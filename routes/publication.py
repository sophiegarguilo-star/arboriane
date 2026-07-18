# -*- coding: utf-8 -*-
"""
Routes de publication & d'export GEDZIP.

Trois points d'entrée, tous adossés à services.publication :
  POST /api/publication/apercu  -> qui serait masqué (rien n'est écrit)
  POST /api/publication/gedcom  -> écrit un .ged public (vivants masqués)
  POST /api/export/gedzip       -> écrit un .gdz (GEDCOM + images)

Rien n'est publié en ligne : on écrit un fichier local dans Exports/ que
l'utilisateur diffuse lui-même.
"""

import os

from routes import route
from services import publication
from core.validation import ErreurValidation


def _actif(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")


def _options(corps):
    """Extrait les options de publication du corps de requête (tolérant)."""
    corps = corps or {}
    opts = corps.get("options")
    if not isinstance(opts, dict):
        # options passées à plat dans le corps -> on les récupère aussi
        opts = corps
    resultat = {}
    for cle in ("masquer_vivants", "garder_noms", "retirer_notes",
                "retirer_notes_tous", "retirer_sources_vivants",
                "retirer_photos_vivants"):
        if cle in opts:
            resultat[cle] = bool(opts[cle])
    if isinstance(opts.get("garder_visibles"), list):
        resultat["garder_visibles"] = [str(x) for x in opts["garder_visibles"] if x]
    an = opts.get("annee_reference")
    if isinstance(an, int):
        resultat["annee_reference"] = an
    elif isinstance(an, str) and an.strip().isdigit():
        resultat["annee_reference"] = int(an.strip())
    return resultat


@route("POST", r"^/api/publication/apercu$")
def apercu(app, params, corps):
    """Liste des personnes qui seraient masquées, pour vérification AVANT."""
    _actif(app)
    masques = publication.apercu_masques(app.base.donnees, _options(corps))
    return {"masques": masques, "total": len(masques)}


@route("POST", r"^/api/publication/gedcom$")
def gedcom_public(app, params, corps):
    """Exporte le GEDCOM public (vivants masqués) dans Exports/."""
    _actif(app)
    chemin = publication.exporter_gedcom_public(app, _options(corps))
    return {"ok": True, "fichier": os.path.basename(chemin)}


@route("POST", r"^/api/export/gedzip$")
def gedzip(app, params, corps):
    """Exporte un .gdz (GEDCOM + images référencées) dans Exports/.

    Si le corps contient des options de publication, l'arbre est anonymisé
    avant d'être archivé (GEDZIP public) ; sinon l'arbre complet est exporté.
    """
    _actif(app)
    corps = corps or {}
    # publication demandée uniquement si des options sont présentes/explicites
    opts = _options(corps) if (corps.get("publication")
                               or corps.get("options")
                               or corps.get("masquer_vivants")) else None
    taille_max = corps.get("taille_max")
    if not isinstance(taille_max, int):
        taille_max = None
    chemin = publication.exporter_gedzip(app, options=opts, taille_max=taille_max)
    return {"ok": True, "fichier": os.path.basename(chemin)}
