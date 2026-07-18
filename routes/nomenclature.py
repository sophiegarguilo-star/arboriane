# -*- coding: utf-8 -*-
"""Route de nomenclature : le formulaire de source demande au serveur le titre
et les noms de fichiers qu'il propose, pendant la saisie. La règle de nommage
vit dans services/nomenclature.py — un seul endroit, testable."""

from routes import route
from services import nomenclature as nm


def _personnes(app, ids):
    """Identifiants → {nom, prenoms}, dans l'ordre demandé. Les inconnus sont
    ignorés plutôt que de faire échouer une suggestion de confort."""
    inds = app.base.donnees["individus"]
    gens = []
    for pid in ids or []:
        ind = inds.get(pid)
        if ind:
            gens.append({"nom": ind.get("nom", ""), "prenoms": ind.get("prenoms", "")})
    return gens


@route("POST", r"^/api/nomenclature$")
def proposer(app, params, corps):
    """{type, personnes:[pid], date, lieu, fichiers:[nom]} → {titre, fichiers}."""
    return nm.apercu(
        type_acte=corps.get("type", ""),
        personnes=_personnes(app, corps.get("personnes")),
        date=corps.get("date", ""),
        lieu=corps.get("lieu", ""),
        fichiers=corps.get("fichiers") or [],
        existants=app.lister_medias("Sources"))
