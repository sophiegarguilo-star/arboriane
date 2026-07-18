# -*- coding: utf-8 -*-
"""
Validateur de dates GEDCOM (L12).

Repère les dates qui ne respectent pas une forme reconnue (et risquent d'être
mal comprises par d'autres logiciels) : on tolère les mois EN (JAN…) et FR
(janvier…), les préfixes GEDCOM (ABT/BEF/AFT/EST/CAL/INT) et français
(vers/avant/après/entre…et), les intervalles, l'année seule et les calendriers
spéciaux (@#DFRENCH R@…). Tout le reste est signalé.

`valider(date)` -> (ok, raison) ; `dates_invalides(donnees)` -> liste d'alertes.
"""

import re

from core import modele

_MOIS_EN = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
            "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
_MOIS_FR = ("JANVIER", "FÉVRIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN",
            "JUILLET", "AOÛT", "AOUT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE",
            "DECEMBRE")
_PREFIXES = ("ABT", "EST", "CAL", "BEF", "AFT", "INT", "FROM", "TO",
             "VERS", "AVANT", "APRÈS", "APRES", "ENV")

_ANNEE = re.compile(r"\b(1\d{3}|20\d{2}|\d{3})\b")


def _mois_ok(tok):
    t = tok.strip().upper()
    return t in _MOIS_EN or t in _MOIS_FR or any(t.startswith(m[:4]) for m in _MOIS_FR)


def _simple_ok(t):
    """Une date atomique : « 12 JAN 1850 » / « JAN 1850 » / « 1850 » / « 1850/51 »."""
    t = t.strip()
    if not t:
        return False
    m = re.match(r"^\d{1,2}\s+([A-Za-zÀ-ÿ]{3,})\s+\d{3,4}$", t)
    if m:
        return _mois_ok(m.group(1))
    m = re.match(r"^([A-Za-zÀ-ÿ]{3,})\s+\d{3,4}$", t)
    if m:
        return _mois_ok(m.group(1))
    # Format français numérique « JJ/MM/AAAA » (les dates sont stockées ainsi) et
    # « MM/AAAA ». On vérifie jour ≤ 31 / mois ≤ 12 pour ne pas valider n'importe quoi.
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{3,4})$", t)
    if m:
        return 1 <= int(m.group(1)) <= 31 and 1 <= int(m.group(2)) <= 12
    m = re.match(r"^(\d{1,2})/(\d{3,4})$", t)
    if m:
        return 1 <= int(m.group(1)) <= 12
    if re.match(r"^\d{3,4}(/\d{2,4})?$", t):        # année seule ou intervalle « 1850/51 »
        return True
    return False


def valider(brut):
    """(ok, raison). Une date vide est valide (pas de date). Renvoie une raison
    courte quand la forme n'est pas reconnue."""
    d = (brut or "").strip()
    if not d:
        return True, ""
    if d.startswith("@#D"):                    # échappement de calendrier (FRENCH R,
        return True, ""                        # JULIAN, HEBREW…) : forme valide par définition
    haut = d.upper()
    # intervalles
    m = re.match(r"^(BET|FROM|ENTRE|DE)\s+(.+?)\s+(AND|TO|ET|À|A)\s+(.+)$", haut)
    if m:
        ok = _simple_ok(m.group(2)) and _simple_ok(m.group(4))
        return (ok, "" if ok else "intervalle mal formé")
    # préfixe + date
    m = re.match(r"^([A-ZÀ-Ÿ]+)\s+(.+)$", haut)
    if m and m.group(1) in _PREFIXES:
        ok = _simple_ok(m.group(2))
        return (ok, "" if ok else "date après « %s » non reconnue" % m.group(1).lower())
    if _simple_ok(d):
        return True, ""
    if _ANNEE.search(d):
        return False, "forme inhabituelle (année présente mais structure non standard)"
    return False, "aucune année reconnue"


def dates_invalides(donnees):
    """Parcourt toutes les dates d'événements et renvoie les alertes :
    [{id, nom, contexte, date, raison}]."""
    inds = donnees["individus"]
    out = []

    def verif(pid, contexte, evt):
        d = (evt or {}).get("date")
        if not d:
            return
        ok, raison = valider(d)
        if not ok:
            out.append({"id": pid, "nom": modele.nom_complet(inds.get(pid, {})),
                        "contexte": contexte, "date": d, "raison": raison})

    for pid, ind in inds.items():
        verif(pid, "naissance", ind.get("naissance"))
        verif(pid, "décès", ind.get("deces"))
        for r in ind.get("residences", []):
            verif(pid, "résidence", r)
        for ev in ind.get("evenements", []):
            verif(pid, ev.get("type", "événement"), ev)
    for fam in donnees.get("familles", {}).values():
        conj = fam.get("mari") or fam.get("epouse") or ""
        verif(conj, "mariage", fam.get("mariage"))
    out.sort(key=lambda x: (x["nom"].lower(), x["contexte"]))
    return out
