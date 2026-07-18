# -*- coding: utf-8 -*-
"""
Nomenclature des sources : fabriquer un TITRE lisible et un NOM DE FICHIER
triable, à partir de ce que l'utilisateur a déjà saisi.

Pourquoi ici et pas dans le navigateur : c'est la règle métier de nommage, elle
doit être unique, testable, et réutilisable (formulaire, import, renommage en
lot). Le formulaire l'appelle en direct pendant la saisie.

Deux objets, deux usages — à ne pas confondre :

  TITRE    « Acte de naissance — Jean DUPONT — 12/03/1902 — Lyon, Rhône »
           Il DÉCRIT la source. Il se lit. C'est une citation, pas un nom.

  FICHIER  « 1902-03-12_N_DUPONT-Jean_Lyon.jpg »
           Il NOMME le scan sur le disque. Il se trie. Date en tête (ISO), donc
           l'explorateur Windows range les actes par ordre chronologique tout
           seul, sans rien demander à personne.
"""

import os
import re
import unicodedata

# Code court par type d'acte, pour le nom de fichier. Volontairement stable :
# le changer renommerait des fichiers déjà rangés chez les utilisateurs.
CODES_TYPE = {
    "Acte de naissance": "N",
    "Acte de mariage": "M",
    "Acte de décès": "D",
    "Publication de mariage": "PM",
    "Livret de famille": "LF",
    "Matricule militaire": "MIL",
    "Recensement": "REC",
    "Acte notarié": "NOT",
    "Acte de notoriété": "NOTO",
    "Naturalisation": "NAT",
    "Pierre tombale / sépulture": "SEP",
    "Faire-part": "FP",
    "Presse / article": "PR",
    "Document": "DOC",
}

_MOIS_GED = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
             "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}


def _sans_accents(t):
    t = unicodedata.normalize("NFD", t or "")
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def fragment(t, majuscules=False):
    """Fragment sûr pour un nom de fichier : sans accents, sans espaces, sans
    caractère interdit par Windows. Jamais vide n'est renvoyé : '' si rien."""
    t = _sans_accents(t).strip()
    if majuscules:
        t = t.upper()
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-")
    return t


def date_iso(date):
    """Date de source → préfixe triable. Accepte les formes que l'application
    manipule ('1902', '12 MAR 1902', 'MAR 1902', '12/03/1902', '1902-03-12').
    Une date approximative ('ABT 1902') garde son année : mieux vaut trier
    approximativement que pas du tout. '' si on ne comprend rien."""
    d = (date or "").strip().upper()
    if not d:
        return ""
    d = re.sub(r"^(ABT|ENV|CAL|EST|VERS|AV|APR|BEF|AFT)\s+", "", d)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", d)
    if m:
        return d
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", d)          # 12/03/1902
    if m:
        return "%s-%02d-%02d" % (m.group(3), int(m.group(2)), int(m.group(1)))
    m = re.match(r"^(\d{1,2})\s+([A-Z]{3})\s+(\d{4})$", d)     # 12 MAR 1902
    if m and m.group(2) in _MOIS_GED:
        return "%s-%02d-%02d" % (m.group(3), _MOIS_GED[m.group(2)], int(m.group(1)))
    m = re.match(r"^([A-Z]{3})\s+(\d{4})$", d)                 # MAR 1902
    if m and m.group(1) in _MOIS_GED:
        return "%s-%02d" % (m.group(2), _MOIS_GED[m.group(1)])
    m = re.search(r"(\d{4})", d)                               # 1902, ABT 1902…
    if m:
        return m.group(1)
    return ""


def _ville(lieu):
    """Première composante d'un lieu : « Lyon, Rhône, France » → « Lyon »."""
    return (lieu or "").split(",")[0].strip()


def _etiquette(personne):
    """{nom, prenoms} → « DUPONT-Jean » (nom en capitales, 1er prénom)."""
    nom = fragment((personne or {}).get("nom", ""), majuscules=True)
    prenoms = ((personne or {}).get("prenoms") or "").split()
    prenom = fragment(prenoms[0], majuscules=False).capitalize() if prenoms else ""
    return "-".join(p for p in (nom, prenom) if p)


def _nom_lisible(personne):
    """{nom, prenoms} → « Jean DUPONT » (pour le titre, accents conservés)."""
    prenoms = ((personne or {}).get("prenoms") or "").strip()
    nom = ((personne or {}).get("nom") or "").strip().upper()
    return " ".join(p for p in (prenoms, nom) if p)


def titre_suggere(type_acte="", personnes=(), date="", lieu=""):
    """Titre descriptif, lisible, stable. Les personnes au-delà de deux sont
    résumées : un titre qui déborde ne se lit plus dans une liste."""
    noms = [_nom_lisible(p) for p in (personnes or [])]
    noms = [n for n in noms if n]
    if len(noms) > 2:
        gens = "%s, %s et %d autres" % (noms[0], noms[1], len(noms) - 2)
    else:
        gens = " & ".join(noms)
    morceaux = [(type_acte or "").strip() or "Source", gens,
                (date or "").strip(), (lieu or "").strip()]
    return " — ".join(m for m in morceaux if m)


def nom_fichier(nom_origine, type_acte="", personnes=(), date="", lieu="",
                existants=(), rang=0, total=1):
    """Nom de scan triable : <date>_<code>_<PERSONNE>_<Ville>.<ext>

    - `nom_origine` ne sert qu'à récupérer l'extension : le contenu est le même.
    - `rang`/`total` numérotent les scans d'une même source (_1, _2…), sinon
      deux vues d'un même acte se recouvriraient.
    - `existants` évite d'écraser un fichier déjà présent (suffixe -2, -3…).
    Si l'on ne sait rien (ni date, ni type, ni personne, ni lieu), on rend le
    nom d'origine : inventer « sans-date_DOC.jpg » n'aide personne.
    """
    _, ext = os.path.splitext(nom_origine or "")
    ext = ext.lower() or ".jpg"

    morceaux = [date_iso(date),
                CODES_TYPE.get((type_acte or "").strip(), fragment(type_acte).upper()),
                "-et-".join(filter(None, (_etiquette(p) for p in (personnes or [])[:2]))),
                fragment(_ville(lieu))]
    morceaux = [m for m in morceaux if m]
    if not morceaux:
        return nom_origine or ("scan" + ext)

    base = "_".join(morceaux)
    if total > 1:
        base += "_%d" % (rang + 1)

    dejala = set(existants or ())
    candidat = base + ext
    n = 2
    while candidat in dejala:
        candidat = "%s-%d%s" % (base, n, ext)
        n += 1
    return candidat


def apercu(type_acte="", personnes=(), date="", lieu="", fichiers=(),
           existants=()):
    """Ce que le formulaire affiche pendant la saisie : le titre proposé et les
    noms de fichiers proposés, dans l'ordre des scans."""
    fichiers = list(fichiers or [])
    total = len(fichiers)
    pris = list(existants or [])
    renommes = []
    for i, f in enumerate(fichiers):
        nf = nom_fichier(f, type_acte, personnes, date, lieu,
                         existants=pris, rang=i, total=total)
        pris.append(nf)
        renommes.append({"origine": f, "propose": nf})
    return {"titre": titre_suggere(type_acte, personnes, date, lieu),
            "fichiers": renommes}
