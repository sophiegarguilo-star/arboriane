# -*- coding: utf-8 -*-
"""
Liens de recherche web — construit LOCALEMENT des URL de recherche pré-remplies
vers des sites de généalogie / archives, à partir d'une personne.

L'application se contente d'OUVRIR ces URL dans le navigateur : aucune donnée de
l'arbre n'est transmise automatiquement, aucun contenu n'est posté. Opt-in, dans
le respect de l'ADN local et privé.

Un « site » est un gabarit d'URL dont les champs {nom} {prenom} {prenoms}
{annee} {lieu} sont substitués puis URL-encodés. Des sites personnels (stockés
dans les réglages) complètent la liste par défaut.
"""

import re
import urllib.parse

from core import modele

# Gabarits par défaut. Champs disponibles : {nom} {prenom} {prenoms} {annee} {lieu}
# NB : _remplir() n'URL-encode QUE les champs {…}. Tout texte fixe accentué doit
# donc être pré-encodé en UTF-8 dans le gabarit (ex. « g%C3%A9n%C3%A9alogie »).
SITES = [
    {"id": "geneanet", "nom": "Geneanet", "categorie": "Bases",
     "gabarit": "https://www.geneanet.org/fonds/individus/?go=1&nom={nom}&prenom={prenom}"},
    {"id": "familysearch", "nom": "FamilySearch", "categorie": "Bases",
     "gabarit": "https://www.familysearch.org/search/record/results?q.surname={nom}&q.givenName={prenom}"},
    {"id": "gallica", "nom": "Gallica (BnF)", "categorie": "Archives",
     "gabarit": "https://gallica.bnf.fr/services/engine/search/sru?operation=searchRetrieve&version=1.2&query=gallica+all+%22{nom}+{prenom}%22"},
    {"id": "repartition", "nom": "Répartition du nom (Geneanet)", "categorie": "Patronyme",
     "gabarit": "https://www.geneanet.org/nom-de-famille/{nom}"},
    {"id": "filae", "nom": "Filae — patronyme", "categorie": "Patronyme",
     "gabarit": "https://www.filae.com/nom-de-famille/{nom}"},
    {"id": "google", "nom": "Recherche Google", "categorie": "Web",
     "gabarit": "https://www.google.com/search?q={prenom}+{nom}+g%C3%A9n%C3%A9alogie+{lieu}"},
]

_CHAMP = re.compile(r"\{(\w+)\}")


def _champs(ind):
    return {
        "nom": modele.nom_de_famille(ind) or "",
        "prenom": modele.prenom_usuel(ind) or "",
        "prenoms": (ind.get("prenoms") or "").strip(),
        "annee": str(modele.annee_naissance(ind) or ""),
        "lieu": ((ind.get("naissance") or {}).get("lieu") or "").strip(),
    }


def _remplir(gabarit, champs):
    return _CHAMP.sub(
        lambda m: urllib.parse.quote((champs.get(m.group(1)) or "").strip()),
        gabarit)


def sites(reglages=None):
    """Sites par défaut + sites personnels des réglages (liste {nom, gabarit})."""
    perso = []
    for s in ((reglages or {}).get("liens_web_perso") or []):
        if s.get("nom") and s.get("gabarit"):
            perso.append({"id": "perso_%d" % len(perso), "nom": s["nom"],
                          "categorie": "Perso", "gabarit": s["gabarit"]})
    return SITES + perso


def liens_pour(ind, reglages=None):
    """Liens de recherche prêts à ouvrir pour une personne. Renvoie [] si la
    personne n'a ni nom ni prénom (rien d'utile à chercher)."""
    if not ind:
        return []
    champs = _champs(ind)
    if not champs["nom"] and not champs["prenoms"]:
        return []
    return [{"id": s["id"], "nom": s["nom"], "categorie": s["categorie"],
             "url": _remplir(s["gabarit"], champs)}
            for s in sites(reglages)]
