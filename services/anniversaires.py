# -*- coding: utf-8 -*-
"""
Éphéméride — anniversaires de naissance classés par jour de l'année.

Le jour et le mois sont extraits de la date GEDCOM au mieux (mois en lettres
anglais/français, ou format numérique jj/mm/aaaa). Les dates non exploitables
(année seule…) sont simplement ignorées.
"""

import re

from core.modele import nom_complet, annee

_MOIS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,          # GEDCOM anglais
    "janv": 1, "fev": 2, "fév": 2, "mars": 3, "avr": 4, "mai": 5, "juin": 6,
    "juil": 7, "aout": 8, "août": 8, "sept": 9, "octo": 10, "nove": 11, "déc": 12,
}

_NOMS_MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin",
              "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _jour_mois(date_str):
    """(mois, jour) au mieux, ou None."""
    if not date_str:
        return None
    s = str(date_str)
    m = re.search(r"\b(\d{1,2})\s+([A-Za-zÀ-ÿ]{3,})", s)
    if m:
        jour = int(m.group(1))
        mot = m.group(2).lower()
        mois = _MOIS.get(mot[:4]) or _MOIS.get(mot[:3])
        if mois and 1 <= jour <= 31:
            return (mois, jour)
    m = re.search(r"\b(\d{1,2})[/.](\d{1,2})[/.]\d{2,4}\b", s)
    if m:
        jour, mois = int(m.group(1)), int(m.group(2))
        if 1 <= mois <= 12 and 1 <= jour <= 31:
            return (mois, jour)
    return None


def ephemeride(donnees):
    """Personnes ayant une date de naissance exploitable, classées par jour
    de l'année (mois, jour), puis par nom."""
    out = []
    for pid, ind in donnees["individus"].items():
        d = (ind.get("naissance") or {}).get("date")
        jm = _jour_mois(d)
        if jm:
            out.append({"id": pid, "nom": nom_complet(ind),
                        "mois": jm[0], "jour": jm[1], "mois_nom": _NOMS_MOIS[jm[0]],
                        "date": d, "annee": annee(d)})
    out.sort(key=lambda x: (x["mois"], x["jour"], x["nom"].lower()))
    return {"total": len(out), "personnes": out}
