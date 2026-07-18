# -*- coding: utf-8 -*-
"""Import LOCAL des scans référencés par un GEDCOM (retour utilisateur Michel).

Un GEDCOM exporté par Brother's Keeper (et d'autres) rattache à ses sources un
fichier image par son chemin absolu sur le disque de l'export
(« 4 FILE D:\\...\\Actes\\X-00021.png »). Arboriane tournant EN LOCAL sur le PC de
l'utilisateur, ce fichier est souvent réellement présent. On le copie alors dans
le dossier « Sources/ » de l'arbre (arbre autonome) et on remplace le nom
d'origine par le nom réellement enregistré dans `source.fichiers`.

Le lecteur GEDCOM dépose les chemins d'origine dans le champ transitoire
`source["_chemins_scans"]` (cf. core.gedcom.lecture). Ce module le consomme et le
retire. Fichier absent → laissé « à retrouver » (comportement inchangé).

`importer_scans_locaux(app, donnees)` -> {copies, manquants}.
"""

import base64
import os


def importer_scans_locaux(app, donnees):
    """Copie dans l'arbre actif les scans dont le chemin d'origine existe sur le
    disque. Met à jour `source.fichiers` avec le nom retenu. Renvoie un bilan."""
    if not getattr(app, "espace_chemin", None):
        return {"copies": 0, "manquants": 0}
    copies = manquants = 0
    deja = {}   # chemin absolu déjà copié -> nom enregistré (évite les doublons)
    for src in (donnees.get("sources") or {}).values():
        chemins = src.pop("_chemins_scans", None)
        if not chemins:
            continue
        for chemin in chemins:
            base = os.path.basename((chemin or "").replace("\\", "/"))
            if not base:
                continue
            if chemin in deja:
                nom = deja[chemin]
            elif os.path.isfile(chemin):
                try:
                    with open(chemin, "rb") as fh:
                        data = base64.b64encode(fh.read()).decode("ascii")
                    nom = app.enregistrer_media("Sources", base, data)
                except OSError:
                    manquants += 1
                    continue
                deja[chemin] = nom
                copies += 1
            else:
                manquants += 1
                continue
            # Remplacer le nom d'origine par le nom réellement enregistré.
            src["fichiers"] = [nom if x == base else x for x in src.get("fichiers", [])]
            if src.get("fichier") == base:
                src["fichier"] = nom
            if nom not in src["fichiers"]:
                src["fichiers"].append(nom)
    return {"copies": copies, "manquants": manquants}


def purger_transitoire(donnees):
    """Filet de sécurité : retire tout `_chemins_scans` résiduel avant persistance
    (chemins par lesquels on n'est pas passé, ex. aperçu d'import)."""
    for src in (donnees.get("sources") or {}).values():
        src.pop("_chemins_scans", None)
