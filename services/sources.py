# -*- coding: utf-8 -*-
"""
Sources & preuves — le cœur d'Arboriane.

Le modèle distingue clairement : la PERSONNE, le FAIT (naissance, décès, union…),
la SOURCE (un registre, un acte), la CITATION (source + page + fiabilité qui
relie une source à un fait), et la PIÈCE (le scan). Une source PROUVE des faits ;
plus la fiabilité (QUAY) est haute, plus le fait est solide.
"""

from core import modele
from core.modele import nom_complet

# QUAY (0-3) → niveau de preuve lisible
NIVEAUX = {3: ("acte", "Prouvé par acte"), 2: ("declare", "Déclaré"),
           1: ("estime", "Estimé"), 0: ("estime", "Estimé")}
FAITS_VITAUX = ("naissance", "union", "deces")
# Libellés courts des événements de couple (balises GEDCOM famille).
_LIB_FAM = {"DIV": "Divorce", "ANUL": "Annulation", "DIVF": "Demande de divorce",
            "SEPR": "Séparation", "ENGA": "Fiançailles", "MARB": "Bans de mariage",
            "MARC": "Contrat de mariage", "MARL": "Mariage religieux",
            "MARS": "Contrat de séparation", "MARR": "Mariage"}


def _fichiers(src):
    fics = list(src.get("fichiers") or [])
    if src.get("fichier") and src["fichier"] not in fics:
        fics = [src["fichier"]] + fics
    return [f for f in fics if f]


def resume_source(src):
    fics = _fichiers(src)
    return {
        "id": src["id"],
        "titre": src.get("titre") or src["id"],
        "type": src.get("type", ""),
        "date": src.get("date", ""),
        "lieu": src.get("lieu") or src.get("ville", ""),
        "fiabilite": src.get("fiabilite", ""),
        "statut": src.get("statut", ""),
        "depot": src.get("depot", ""),
        "cote": src.get("cote", ""),
        "nb_fichiers": len(fics),
        "premier_fichier": fics[0] if fics else "",
        "nb_personnes": len(src.get("personnes") or []),
        "a_transcription": bool((src.get("transcription") or "").strip()),
        "orpheline": not fics,           # source sans scan rattaché
    }


def sources_vers_personnes(donnees):
    """Pour chaque source, l'ENSEMBLE des personnes qu'elle relie — que ce soit
    par le tag `src.personnes` OU par une CITATION sur un de leurs faits.
    Les citations d'union (portées par la famille) sont attribuées aux DEUX
    conjoints. Base d'un comptage « reliée / non reliée » exact."""
    liens = {}   # sid -> set(pids)

    def rel(sid, pid):
        if sid and pid:
            liens.setdefault(sid, set()).add(pid)

    def cits(citations, pid):
        for c in (citations or []):
            rel(c.get("source"), pid)

    inds = donnees.get("individus", {})
    for pid, ind in inds.items():
        cits(ind.get("citations"), pid)
        for cle in ("naissance", "deces"):
            ev = ind.get(cle)
            if isinstance(ev, dict):
                cits(ev.get("citations"), pid)
        for coll in ("residences", "professions", "evenements"):
            for it in (ind.get(coll) or []):
                if isinstance(it, dict):
                    cits(it.get("citations"), pid)

    for fam in donnees.get("familles", {}).values():
        conjoints = [fam.get("mari"), fam.get("epouse")]
        mariage = fam.get("mariage")
        if isinstance(mariage, dict):
            for pid in conjoints:
                cits(mariage.get("citations"), pid)
        for ev in (fam.get("evenements") or []):
            if isinstance(ev, dict):
                for pid in conjoints:
                    cits(ev.get("citations"), pid)

    for sid, src in (donnees.get("sources") or {}).items():
        for p in (src.get("personnes") or []):
            rel(sid, p.get("id"))
    return liens


def lister(donnees):
    """Toutes les sources (résumés), triées par date puis titre. `nb_personnes`
    et `reliee` sont CONSCIENTS DES CITATIONS (pas seulement du tag personnes) :
    une preuve rattachée à un fait n'est plus comptée « non reliée »."""
    liens = sources_vers_personnes(donnees)
    lignes = []
    for s in donnees.get("sources", {}).values():
        r = resume_source(s)
        pids = liens.get(s["id"])
        r["nb_personnes"] = len(pids) if pids else 0
        r["reliee"] = bool(pids)
        r["personnes"] = sorted(pids) if pids else []   # pour filtrer par personne
        lignes.append(r)
    lignes.sort(key=lambda r: (r["date"], r["titre"].lower()))
    return lignes


def types(donnees):
    """Types de sources présents (pour le filtre)."""
    return sorted({(s.get("type") or "").strip()
                   for s in donnees.get("sources", {}).values() if s.get("type")})


def sources_de_personne(donnees, pid):
    """Sources rattachées à une personne : soit elle y figure (src.personnes),
    soit un de ses faits la cite (citations → source). Renvoie de quoi afficher
    une vignette cliquable sur la fiche."""
    srcs = donnees.get("sources") or {}
    inds = donnees["individus"]
    ind = inds.get(pid) or {}

    # 1) sources citées par les faits de la personne
    cite_ids = {}
    def _ajoute_cit(citations, contexte):
        for c in (citations or []):
            sid = c.get("source")
            if sid:
                cite_ids.setdefault(sid, set()).add(contexte)
    _ajoute_cit((ind.get("naissance") or {}).get("citations"), "naissance")
    _ajoute_cit((ind.get("deces") or {}).get("citations"), "décès")
    _ajoute_cit(ind.get("citations"), "")
    for fid in ind.get("fams", []):
        fam = donnees["familles"].get(fid) or {}
        _ajoute_cit((fam.get("mariage") or {}).get("citations"), "union")

    out = []
    for sid, src in srcs.items():
        role = None
        for p in (src.get("personnes") or []):
            if p.get("id") == pid:
                role = p.get("role", "") or "citée"
                break
        contextes = cite_ids.get(sid)
        if role is None and not contextes:
            continue
        fics = _fichiers(src)
        etiquette = role if role is not None else \
            "prouve : " + ", ".join(sorted(c for c in contextes if c))
        out.append({
            "id": sid, "titre": src.get("titre") or sid,
            "type": src.get("type", ""), "date": src.get("date", ""),
            "role": etiquette or "citée", "sujet": role is not None,
            # aperçu = 1re IMAGE (une vignette <img> d'un PDF resterait blanche) ;
            # une source PDF-seul retombe sur la pastille « 📄 » côté fiche.
            "nb_fichiers": len(fics),
            "apercu": next((f for f in fics if not f.lower().endswith(".pdf")), ""),
        })
    out.sort(key=lambda s: (not s["sujet"], s["titre"].lower()))
    return out


def fiche_source(donnees, sid):
    src = donnees.get("sources", {}).get(sid)
    if not src:
        return None
    d = dict(src)
    d["fichiers_resolus"] = _fichiers(src)
    d["personnes_resolues"] = [
        {"id": p.get("id"), "role": p.get("role", ""),
         "nom": nom_complet(donnees["individus"].get(p.get("id"), {}))}
        for p in (src.get("personnes") or [])]
    return d


def _niveau_citations(citations):
    """Meilleur niveau de preuve d'une liste de citations."""
    meilleur = None
    for c in citations or []:
        q = c.get("quay")
        if q is None:
            continue
        if meilleur is None or q > meilleur:
            meilleur = q
    if meilleur is None:
        return ("non_qualifie", "Source sans fiabilité") if citations else ("manquant", "Aucune source")
    return NIVEAUX.get(meilleur, ("estime", "Estimé"))


def preuves_personne(donnees, pid):
    """État de preuve des faits vitaux d'une personne (pour la fiche)."""
    ind = donnees["individus"].get(pid)
    if not ind:
        return None
    faits = []

    def _bout(*parties):
        return " — ".join(p for p in parties if p)

    def fait(nom_fait, libelle, citations, present, famille=None, date=""):
        # `libelle` = le TYPE seul (« PACS », « Divorce ») ; la `date` va dans sa
        # propre colonne côté fiche → plus de libellés sur deux lignes.
        niveau, texte = _niveau_citations(citations)
        entree = {"fait": nom_fait, "libelle": libelle, "date": date or "",
                  "present": present, "niveau": niveau, "niveau_texte": texte,
                  "nb_sources": len(citations or [])}
        if famille:
            entree["famille"] = famille
        faits.append(entree)

    nais = ind.get("naissance") or {}
    fait("naissance", "Naissance", nais.get("citations"),
         bool(nais.get("date") or nais.get("lieu")), date=nais.get("date"))
    dec = ind.get("deces") or {}
    # On ne liste « Décès » que s'il y a une trace de décès (date/lieu/citation) OU
    # si la personne n'est PAS présumée vivante. Afficher « Décès — À prouver » pour
    # quelqu'un de présumé vivant n'a aucun sens.
    a_deces = bool(dec.get("date") or dec.get("lieu") or dec.get("citations"))
    if a_deces or not modele.est_vivant_presume(ind):
        fait("deces", "Décès", dec.get("citations"),
             bool(dec.get("date") or dec.get("lieu")), date=dec.get("date"))
    # union : citations de la 1re famille comme parent + date du mariage (1re
    # union datée) — sinon la colonne « Date » restait vide alors que le mariage
    # a bien une date, contrairement à la naissance et au décès.
    cit_union = []
    date_union = ""
    for fid in ind.get("fams", []):
        fam = donnees["familles"].get(fid) or {}
        mar = fam.get("mariage") or {}
        cit_union += mar.get("citations") or []
        if not date_union and mar.get("date"):
            date_union = mar.get("date")
    fait("union", "Union", cit_union, bool(ind.get("fams")), date=date_union)
    # événements du COUPLE (divorce, séparation…) : portés par la famille, donc
    # prouvables au même titre que le mariage. On les cible par « union_evenement:i »
    # + la famille concernée (indispensable en cas de remariage).
    for fid in ind.get("fams", []):
        fam = donnees["familles"].get(fid) or {}
        for j, ev in enumerate(fam.get("evenements") or []):
            if not isinstance(ev, dict):
                continue
            # Libellé : la balise standard (DIV → « Divorce »), sinon la PRÉCISION
            # d'un EVEN typé (« PACS », « Dissolution de PACS ») plutôt que « EVEN ».
            libelle = (_LIB_FAM.get(ev.get("type"))
                       or (ev.get("precision") or "").strip()
                       or ev.get("type") or "Fait du couple")
            fait("union_evenement:%d" % j, libelle, ev.get("citations"), True,
                 famille=fid, date=ev.get("date"))

    # faits secondaires : chaque résidence / profession / événement NOMMÉ devient
    # prouvable (identifiant stable « coll:index » ciblé par citer()).
    for i, r in enumerate(ind.get("residences") or []):
        if isinstance(r, dict):
            fait("residence:%d" % i, _bout("Résidence", r.get("lieu")),
                 r.get("citations"), True, date=r.get("date"))
    for i, p in enumerate(ind.get("professions") or []):
        if isinstance(p, dict):
            fait("profession:%d" % i, _bout("Profession", p.get("valeur")),
                 p.get("citations"), True, date=p.get("date"))
    for i, e in enumerate(ind.get("evenements") or []):
        if isinstance(e, dict):
            # Libellé = la PRÉCISION (« PACS ») plutôt que le tag générique « EVEN ».
            # La date part en colonne ; le détail narratif reste dans l'événement.
            fait("evenement:%d" % i,
                 e.get("precision") or e.get("type") or "Fait",
                 e.get("citations"), True, date=e.get("date"))

    prouves = sum(1 for f in faits if f["niveau"] == "acte")
    return {"faits": faits, "prouves": prouves, "total": len(faits),
            "citations_personne": ind.get("citations") or []}
