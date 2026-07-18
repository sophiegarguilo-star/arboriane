# -*- coding: utf-8 -*-
"""
Calendrier républicain & dates complexes.

- Conversion républicain ↔ grégorien (« 12 germinal an III » = 1ᵉʳ avril 1795).
- Lecture/écriture des dates approximatives GEDCOM (ABT/BEF/AFT/BET/EST/CAL) en
  français lisible (« vers », « avant », « après », « entre … et … »).

Époque : 1 vendémiaire an I = 22 septembre 1792. Années sextiles (366 jours) =
an ≡ 3 (mod 4) → an III, VII, XI, XV… (reproduit les années bissextiles
observées I–XIV et prolonge la règle). Aucune dépendance externe.
"""

import datetime
import re

MOIS = ["vendémiaire", "brumaire", "frimaire", "nivôse", "pluviôse", "ventôse",
        "germinal", "floréal", "prairial", "messidor", "thermidor", "fructidor"]
# 13e « mois » = jours complémentaires (sansculottides), 5 ou 6 jours.
_MOIS_IDX = {m: i + 1 for i, m in enumerate(MOIS)}
_MOIS_IDX_SANS_ACCENT = {
    "nivose": 4, "pluviose": 5, "ventose": 6, "floreal": 8}

_EPOQUE = datetime.date(1792, 9, 22)

_ROMAINS = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"),
            (90, "XC"), (50, "L"), (40, "XL"), (10, "X"), (9, "IX"),
            (5, "V"), (4, "IV"), (1, "I")]


def _est_sextile(an):
    return an % 4 == 3


def _int_vers_romain(n):
    out = []
    for val, sym in _ROMAINS:
        while n >= val:
            out.append(sym)
            n -= val
    return "".join(out)


def _romain_vers_int(s):
    s = (s or "").strip().upper()
    if s.isdigit():
        return int(s)
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    if not s or any(c not in vals for c in s):
        return None
    total = prev = 0
    for c in reversed(s):
        v = vals[c]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


# ── Conversions ───────────────────────────────────────────────────────
def rep_vers_greg(an, mois, jour):
    """(an, mois 1-13, jour) républicain -> date grégorienne (datetime.date)."""
    if an < 1 or mois < 1 or mois > 13 or jour < 1:
        return None
    jours = sum(366 if _est_sextile(y) else 365 for y in range(1, an))
    jours += (mois - 1) * 30 + (jour - 1)
    return _EPOQUE + datetime.timedelta(days=jours)


def greg_vers_rep(d):
    """date grégorienne -> (an, mois, jour) républicain, ou None si antérieure."""
    delta = (d - _EPOQUE).days
    if delta < 0:
        return None
    an = 1
    while True:
        ylen = 366 if _est_sextile(an) else 365
        if delta < ylen:
            break
        delta -= ylen
        an += 1
    return an, delta // 30 + 1, delta % 30 + 1


def formater(an, mois, jour):
    """(an, mois, jour) -> « 12 germinal an III » (ou jour complémentaire)."""
    if mois == 13:
        return "jour complémentaire %d an %s" % (jour, _int_vers_romain(an))
    if not (1 <= mois <= 12):
        return ""
    return "%d %s an %s" % (jour, MOIS[mois - 1], _int_vers_romain(an))


def parser(texte):
    """« 12 germinal an III » -> (an, mois, jour), ou None."""
    if not texte:
        return None
    t = texte.strip().lower()
    m = re.search(r"(\d{1,2})\s+([a-zàâäéèêëîïôöûü]+)\s+an\s+([ivxlcdm]+|\d+)", t)
    if not m:
        return None
    jour = int(m.group(1))
    mot = m.group(2)
    mois = _MOIS_IDX.get(mot) or _MOIS_IDX_SANS_ACCENT.get(mot)
    an = _romain_vers_int(m.group(3))
    if not mois or not an:
        return None
    return an, mois, jour


def est_republicaine(texte):
    """Vrai si la chaîne ressemble à une date républicaine."""
    return parser(texte) is not None


def convertir(texte):
    """Convertit une date : républicaine -> grégorienne, ou grégorienne (jj/mm/aaaa
    ou « 12 JAN 1795 ») -> républicaine. Renvoie {entree, republicain, gregorien}
    ou None si non reconnue."""
    if not texte:
        return None
    rep = parser(texte)
    if rep:
        g = rep_vers_greg(*rep)
        if not g:
            return None
        return {"entree": texte.strip(), "republicain": formater(*rep),
                "gregorien": "%02d/%02d/%d" % (g.day, g.month, g.year)}
    g = _parser_gregorien(texte)
    if g:
        r = greg_vers_rep(g)
        return {"entree": texte.strip(),
                "gregorien": "%02d/%02d/%d" % (g.day, g.month, g.year),
                "republicain": formater(*r) if r else ""}
    return None


_MOIS_GREG = {  # abréviations 3 lettres, anglais + français
    "jan": 1, "feb": 2, "fev": 2, "fév": 2, "mar": 3, "apr": 4, "avr": 4,
    "may": 5, "mai": 5, "jun": 6, "jui": 6, "jul": 7, "aug": 8, "aou": 8,
    "aoû": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12, "déc": 12}


def _parser_gregorien(texte):
    t = texte.strip().lower()
    m = re.search(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{3,4})\b", t)
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})\s+([a-zà-ÿ]{3})[a-zà-ÿ]*\s+(\d{3,4})\b", t)
    if m and m.group(2) in _MOIS_GREG:
        try:
            return datetime.date(int(m.group(3)), _MOIS_GREG[m.group(2)], int(m.group(1)))
        except ValueError:
            return None
    return None


# ── Dates approximatives GEDCOM (ABT/BEF/AFT/BET/EST/CAL) ──────────────
_PREFIXES = [
    (r"^abt\.?\s+", "vers "), (r"^env\.?\s+", "vers "), (r"^vers\s+", "vers "),
    (r"^bef\.?\s+", "avant "), (r"^avant\s+", "avant "),
    (r"^aft\.?\s+", "après "), (r"^apr[eè]s\s+", "après "),
    (r"^est\.?\s+", "estimé "), (r"^cal\.?\s+", "calculé "),
    (r"^from\s+", "de "), (r"^to\s+", "à "),
]


def decrire(texte):
    """Rend une date GEDCOM lisible en français : « ABT 1850 » -> « vers 1850 »,
    « BET 1850 AND 1860 » -> « entre 1850 et 1860 », républicaine -> grégorienne
    entre parenthèses. Chaîne inchangée si rien à faire."""
    if not texte:
        return ""
    t = texte.strip()
    bas = t.lower()
    m = re.match(r"^bet\.?\s+(.+?)\s+and\s+(.+)$", bas) or \
        re.match(r"^entre\s+(.+?)\s+et\s+(.+)$", bas)
    if m:
        return "entre %s et %s" % (_decrire_simple(m.group(1)), _decrire_simple(m.group(2)))
    return _decrire_simple(t)


def _decrire_simple(t):
    t = t.strip()
    prefixe = ""
    bas = t.lower()
    for motif, remp in _PREFIXES:
        if re.match(motif, bas):
            prefixe = remp
            t = re.sub(motif, "", t, flags=re.IGNORECASE)
            break
    rep = parser(t)
    if rep:
        g = rep_vers_greg(*rep)
        if g:
            return "%s%s (%02d/%02d/%d)" % (prefixe, formater(*rep), g.day, g.month, g.year)
    return (prefixe + t).strip()


# ── Format INTERNE (français) ⇄ GEDCOM 5.5.1 ──────────────────────────
# Arboriane stocke et AFFICHE les dates en français (« 20/07/1984 »,
# « vers 1850 », « entre 1850 et 1860 »). Le GEDCOM, lui, veut « 20 JUL 1984 »,
# « ABT 1850 », « BET 1850 AND 1860 ». La traduction vit UNIQUEMENT à la
# frontière : import → français, export → GEDCOM. Les deux fonctions sont
# idempotentes (une entrée déjà dans la langue cible ressort inchangée), pour
# pouvoir migrer un arbre sans risque de double conversion.
_MON3 = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
_MON3_IDX = {m: i + 1 for i, m in enumerate(_MON3)}
# préfixes GEDCOM ⇄ mots français
_PREF_G2F = [("ABT", "vers"), ("BEF", "avant"), ("AFT", "après"),
             ("EST", "estimé"), ("CAL", "calculé")]
_PREF_F2G = {"vers": "ABT", "avant": "BEF", "après": "AFT", "apres": "AFT",
             "estimé": "EST", "estime": "EST", "calculé": "CAL", "calcule": "CAL"}


def _atome_g2f(a):
    """« 20 JUL 1984 »→« 20/07/1984 », « JUL 1984 »→« 07/1984 », « 1984 »→« 1984 »."""
    a = a.strip()
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{1,4})$", a)
    if m and m.group(2).upper() in _MON3_IDX:
        return "%02d/%02d/%s" % (int(m.group(1)), _MON3_IDX[m.group(2).upper()], m.group(3))
    m = re.match(r"^([A-Za-z]{3})\s+(\d{1,4})$", a)
    if m and m.group(1).upper() in _MON3_IDX:
        return "%02d/%s" % (_MON3_IDX[m.group(1).upper()], m.group(2))
    return a


def _atome_f2g(a):
    """« 20/07/1984 »→« 20 JUL 1984 », « 07/1984 »→« JUL 1984 », « 1984 »→« 1984 »."""
    a = a.strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{1,4})$", a)
    if m and 1 <= int(m.group(2)) <= 12:
        return "%d %s %s" % (int(m.group(1)), _MON3[int(m.group(2)) - 1], m.group(3))
    m = re.match(r"^(\d{1,2})/(\d{1,4})$", a)
    if m and 1 <= int(m.group(1)) <= 12:
        return "%s %s" % (_MON3[int(m.group(1)) - 1], m.group(2))
    return a


def gedcom_vers_fr(s):
    """Date GEDCOM → format interne français. Idempotent (une date déjà
    française ressort telle quelle). Ne touche pas aux calendriers non résolus."""
    if not s:
        return s or ""
    t = s.strip()
    # déjà français (slashé, ou mot-clé) : ne rien faire
    if re.search(r"\d{1,2}/\d", t) or \
       re.match(r"(?i)^(vers|avant|apr[eè]s|entre|de\s|depuis|jusqu|estim|calcul)", t):
        return t
    m = re.match(r"(?i)^BET\s+(.+?)\s+AND\s+(.+)$", t)
    if m:
        return "entre %s et %s" % (gedcom_vers_fr(m.group(1)), gedcom_vers_fr(m.group(2)))
    m = re.match(r"(?i)^FROM\s+(.+?)\s+TO\s+(.+)$", t)
    if m:
        return "de %s à %s" % (gedcom_vers_fr(m.group(1)), gedcom_vers_fr(m.group(2)))
    m = re.match(r"(?i)^FROM\s+(.+)$", t)
    if m:
        return "depuis %s" % gedcom_vers_fr(m.group(1))
    m = re.match(r"(?i)^TO\s+(.+)$", t)
    if m:
        return "jusqu'à %s" % gedcom_vers_fr(m.group(1))
    for g, f in _PREF_G2F:
        m = re.match(r"(?i)^%s\s+(.+)$" % g, t)
        if m:
            return "%s %s" % (f, gedcom_vers_fr(m.group(1)))
    return _atome_g2f(t)


def fr_vers_gedcom(s):
    """Format interne français → date GEDCOM 5.5.1. Idempotent (une date déjà
    GEDCOM — mois anglais ou préfixe — ressort telle quelle)."""
    if not s:
        return s or ""
    t = s.strip()
    if re.search(r"(?i)\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\b", t) or \
       re.match(r"(?i)^(ABT|BEF|AFT|EST|CAL|BET|FROM|TO)\b", t):
        return t
    m = re.match(r"(?i)^entre\s+(.+?)\s+et\s+(.+)$", t)
    if m:
        return "BET %s AND %s" % (fr_vers_gedcom(m.group(1)), fr_vers_gedcom(m.group(2)))
    m = re.match(r"(?i)^de\s+(.+?)\s+à\s+(.+)$", t)
    if m:
        return "FROM %s TO %s" % (fr_vers_gedcom(m.group(1)), fr_vers_gedcom(m.group(2)))
    m = re.match(r"(?i)^depuis\s+(.+)$", t)
    if m:
        return "FROM %s" % fr_vers_gedcom(m.group(1))
    m = re.match(r"(?i)^jusqu'?à\s+(.+)$", t)
    if m:
        return "TO %s" % fr_vers_gedcom(m.group(1))
    m = re.match(r"(?i)^(vers|avant|apr[eè]s|estim[eé]|calcul[eé])\s+(.+)$", t)
    if m:
        cle = m.group(1).lower()
        pref = _PREF_F2G.get(cle) or _PREF_F2G.get(cle.replace("è", "e").replace("é", "e"))
        return "%s %s" % (pref or "ABT", fr_vers_gedcom(m.group(2)))
    return _atome_f2g(t)
