# -*- coding: utf-8 -*-
"""Route de rendu d'arbre (SVG)."""

import base64
import mimetypes

from routes import route
from services import arbre as arbre_svc
from core.validation import ErreurValidation

# options acceptées depuis la requête et leur conversion
_BOOLS = ("dates", "lieux", "gras", "sosa", "profession", "preuves", "legende",
          "vignette", "implexe", "vierge")
_ENTIERS = ("generations", "angle", "taille", "trait_epaisseur", "fond_opacite")


def _resoudre_fond_image(app, options):
    """Si ``fond`` vaut « img:NOM », lit l'image du dossier Fonds/ de l'arbre et
    l'intègre en data-URI (l'arbre exporté reste donc autonome). Silencieux si
    le fichier est absent : on retombe simplement sur « aucun fond »."""
    # `fond_image_data` est un champ INTERNE : on neutralise toute valeur venue
    # de la requête (anti-injection dans le href du SVG).
    options.pop("fond_image_data", None)
    fond = options.get("fond") or ""
    if not fond.startswith("img:"):
        return
    nom = fond[4:]
    cible = app.chemin_media("Fonds", nom)
    if not cible:
        options["fond"] = ""
        return
    mime, _ = mimetypes.guess_type(cible)
    # Lecture protégée : un fond illisible (fichier verrouillé, droits) ne doit
    # PAS remonter en OSError vers le handler générique — qui l'afficherait à
    # tort comme un blocage d'ÉCRITURE anti-rançongiciel. On ignore le fond.
    try:
        with open(cible, "rb") as f:
            donnees = f.read()
    except OSError:
        options["fond"] = ""
        return
    options["fond"] = "image"
    options["fond_image_data"] = "data:%s;base64,%s" % (
        mime or "image/png", base64.b64encode(donnees).decode("ascii"))


@route("GET", r"^/api/arbre$")
def rendre(app, params, corps):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")
    racine = params.get("racine") or app.manifeste.get("racine_id")
    mode = params.get("mode") or "eventail"
    options = {}
    for cle, val in params.items():
        if cle in ("racine", "mode"):
            continue
        if cle in _BOOLS:
            options[cle] = val in ("1", "true", "oui", "on")
        elif cle in _ENTIERS:
            try:
                options[cle] = int(val)
            except ValueError:
                pass
        elif cle == "plies":
            # numéros Sosa des branches repliées, séparés par des virgules
            plies = set()
            for x in val.split(","):
                x = x.strip()
                if x.isdigit():
                    plies.add(int(x))
            options["plies"] = plies
        else:
            options[cle] = val
    _resoudre_fond_image(app, options)
    try:
        svg = arbre_svc.rendre(app.base.donnees, racine, mode, options)
    except ValueError as e:
        raise ErreurValidation(str(e))
    return {"svg": svg, "racine": racine, "mode": mode}
