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

# La taxonomie complète (10 familles / ~100 types) enrichit la table SANS écraser
# les codes historiques : `setdefault` garde ceux déjà rangés chez l'utilisateur.
try:
    from services import taxonomie_actes as _tax
    for _lib, _code in _tax.codes_par_type().items():
        CODES_TYPE.setdefault(_lib, _code)
except Exception:               # la nomenclature doit marcher même sans taxonomie
    pass

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


# Tout ce qui SUIT la commune dans un lieu et n'a rien à faire dans un nom de
# fichier : lieu d'enregistrement (mairie, commissariat…), voie (rue, route,
# avenue…) et mentions (décédé, domicilié, n°…). « Alger, décédé rue du Numide
# n°7 » -> « Alger » ; « Ténès, Commissariat civil de la Mairie » -> « Ténès ».
_APRES_COMMUNE = re.compile(
    r"\s*\b(nella|nel|della|del|de\s+la|di|au|à\s+la)?\s*"
    r"(commissariat|mairie|bureau\s+municipal|bureau\s+de\s+l|maison\s+commune|"
    r"casa\s+comunale|casa\s+municipale|comune|paroisse|[ée]glise|chiesa|"
    r"annexe|[ée]tat[- ]?civil|tribunal|greffe|consulat|h[ôo]tel\s+de\s+ville|"
    r"rue|route|avenue|av|boulevard|bd|chemin|impasse|place|quai|faubourg|"
    r"all[ée]e|lotissement|r[ée]sidence|"
    r"d[ée]c[ée]d[ée]?|domicili[ée]e?|demeurant|habitant|n[°ºo])\b.*$", re.I)


def _ville(lieu):
    """Commune d'un lieu, débarrassée de tout ce qui la suit (voie, mentions,
    lieu d'enregistrement) : « Lyon, Rhône » → « Lyon » ; « Alger, décédé rue
    du Numide n°7 » → « Alger » ; « Ténès, Commissariat de la Mairie » →
    « Ténès » ; « Procida, casa comunale » → « Procida »."""
    v = (lieu or "").split(",")[0].strip()
    v = _APRES_COMMUNE.sub("", v)
    v = re.sub(r"\s+(nella|nel|della|del|de\s+la|di|au|à\s+la|dans)\s*$", "", v, flags=re.I)
    return v.strip(" -–—,")


def _variante(nom_origine):
    """Segment DISTINCTIF d'un scan, tiré de son nom d'origine : la dernière
    tranche « _… » — qualité, n° de page, mention marginale
    (« …_Procida_ameliore.jpg » → « ameliore », « …_p2-fin-acte16-HD » →
    « p2-fin-acte16-HD »). Sert à distinguer plusieurs vues d'un même acte sans
    perdre l'information : bien plus parlant qu'un compteur _1/_2. '' si le nom
    d'origine n'a pas de tranche exploitable."""
    stem = os.path.splitext(os.path.basename(nom_origine or ""))[0]
    segs = [s for s in stem.split("_") if s]
    return fragment(segs[-1]) if len(segs) >= 2 else ""


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
        # Plusieurs vues d'un même acte : on préserve le tag distinctif du nom
        # d'origine (ameliore, p2-HD, marge-deces1902…) plutôt qu'un compteur
        # anonyme. On retombe sur un compteur si le nom d'origine n'en a pas,
        # ou si ce tag n'est que la ville (redondant).
        tag = _variante(nom_origine)
        if not tag or tag.lower() == fragment(_ville(lieu)).lower():
            tag = str(rang + 1)
        base += "_%s" % tag

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


# Rôles qui font d'une personne le SUJET de l'acte (celui/ceux qu'il concerne
# vraiment). Les autres — témoin, « cité » (mention marginale), parent cité… —
# ne doivent PAS nommer le fichier : sur l'acte de naissance de Sophie, l'ex-
# conjoint cité en marge n'a rien à faire dans « …_GARGUILO-Sophie-et-CHETNIK ».
ROLES_SUJET = ("sujet", "de cujus", "défunt", "defunt",
               "époux", "epoux", "épouse", "epouse")


def _personnes_pour_nom(source, inds):
    """Personnes à faire figurer dans le NOM de fichier : uniquement les SUJETS
    (par rôle). S'il n'y a aucun rôle sujet renseigné (sources anciennes), on
    retombe sur toutes les personnes — comportement d'avant, sans régression."""
    gens = [p for p in (source.get("personnes") or []) if p.get("id")]
    sujets = [p for p in gens if (p.get("role") or "").strip().lower() in ROLES_SUJET]
    retenus = sujets or gens
    return [{"nom": (inds.get(p["id"]) or {}).get("nom", ""),
             "prenoms": (inds.get(p["id"]) or {}).get("prenoms", "")} for p in retenus]


def _date_evenement(donnees, source):
    """Date de l'ÉVÉNEMENT documenté par la source (naissance / décès / mariage),
    pour nommer le fichier au plus près du sens : un acte de naissance se range
    à la date de NAISSANCE, pas à la date où l'acte a été dressé. Renvoie '' si
    indéterminable → l'appelant retombe alors sur la date de la source."""
    typ = (source.get("type") or "").strip()
    inds = donnees.get("individus", {})
    gens = source.get("personnes") or []
    ids = [p.get("id") for p in gens if p.get("id")]
    principal = next((p.get("id") for p in gens
                      if (p.get("role") or "").strip().lower() in ROLES_SUJET), None)
    principal = principal or (ids[0] if ids else None)

    def _fait(pid, champ):
        return ((inds.get(pid) or {}).get(champ) or {}).get("date", "")

    if typ == "Acte de naissance":
        return _fait(principal, "naissance")
    if typ in ("Acte de décès", "Pierre tombale / sépulture"):
        return _fait(principal, "deces")
    if typ in ("Acte de mariage", "Publication de mariage"):
        autres = [i for i in ids if i != principal]
        for f in donnees.get("familles", {}).values():
            couple = {f.get("mari"), f.get("epouse")}
            if principal in couple and (not autres or any(a in couple for a in autres)):
                d = (f.get("mariage") or {}).get("date", "")
                if d:
                    return d
    return ""


def plan(donnees):
    """Aperçu du rangement (LECTURE SEULE) : pour chaque scan cité par une
    source, le nom de fichier proposé par la nomenclature s'il DIFFÈRE de
    l'actuel. La date employée est celle de l'ÉVÉNEMENT (défaut : la date de la
    source). Renvoie [{source, titre, de, vers}] (les fichiers déjà bien nommés
    sont omis). Aucune collision : `existants` protège les autres fichiers."""
    sources = donnees.get("sources", {})
    inds = donnees.get("individus", {})
    occupes = {f for s in sources.values() for f in (s.get("fichiers") or [])}
    assignes = set()
    items = []
    for sid in sorted(sources):
        s = sources[sid]
        fichiers = s.get("fichiers") or []
        if not fichiers:
            continue
        personnes = _personnes_pour_nom(s, inds)
        date = _date_evenement(donnees, s) or s.get("date", "")
        total = len(fichiers)
        for i, f in enumerate(fichiers):
            existants = (occupes | assignes) - {f}
            vers = nom_fichier(f, s.get("type", ""), personnes, date,
                               s.get("lieu", ""), existants=existants, rang=i, total=total)
            assignes.add(vers)
            if vers != f:
                items.append({"source": sid, "titre": s.get("titre") or "",
                              "de": f, "vers": vers})
    return items
