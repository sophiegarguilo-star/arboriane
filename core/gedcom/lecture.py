# -*- coding: utf-8 -*-
"""GEDCOM — import : `importer(texte)` -> base « donnees » complète."""
from core import modele
from core.gedcom.commun import *
from core.gedcom.champs import *
from core.gedcom.lecture_records import lire_indi, lire_fam, lire_sour

def _version_declaree(arbre):
    """Version annoncée par l'en-tête : HEAD.GEDC.VERS. « » si absente.

    Arboriane lit le GEDCOM 5.5.1. Un fichier 7.0 s'importe quand même — la
    grammaire des lignes n'a pas changé, les familles et les personnes non plus
    — mais certaines structures nouvelles (notes partagées, rôles d'association,
    phrases explicatives) ne sont pas comprises et seraient perdues en silence.
    On lit donc la version pour pouvoir le DIRE à l'utilisateur.
    """
    for rec in arbre:
        if rec["tag"] != "HEAD":
            continue
        gedc = _premier(rec, "GEDC")
        if gedc:
            vers = _premier(gedc, "VERS")
            if vers:
                return _fusion_texte(vers).strip()
    return ""


def _toutes_citations(individus, familles):
    """Génère chaque liste de citations de l'arbre (personne + événements +
    mariages), pour les parcourir toutes d'un seul endroit."""
    for ind in individus.values():
        if ind.get("citations"):
            yield ind["citations"]
        for ev in ("naissance", "deces"):
            e = ind.get(ev)
            if isinstance(e, dict) and e.get("citations"):
                yield e["citations"]
        for cle in ("residences", "evenements"):
            for e in ind.get(cle) or []:
                if isinstance(e, dict) and e.get("citations"):
                    yield e["citations"]
    for fam in familles.values():
        mar = fam.get("mariage")
        if isinstance(mar, dict) and mar.get("citations"):
            yield mar["citations"]
        for e in fam.get("evenements") or []:
            if isinstance(e, dict) and e.get("citations"):
                yield e["citations"]


def _materialiser_sources_inline(individus, familles, sources):
    """Transforme les sources EN LIGNE en vraies sources, dédupliquées par texte.

    Une citation « 1 SOUR <texte> » (sans enregistrement) porte son texte dans
    `source_texte`. On crée une source par texte distinct — titre = le texte —,
    et on pointe la citation vers elle. Ainsi une source aplatie par un autre
    logiciel redevient une source consultable, au lieu d'une citation morte.
    """
    par_texte = {}          # texte -> id de source créé
    n = len(sources)
    for liste in _toutes_citations(individus, familles):
        for c in liste:
            texte = c.pop("source_texte", "")
            if not texte or c.get("source"):
                continue
            sid = par_texte.get(texte)
            if sid is None:
                n += 1
                sid = "S%d" % n
                while sid in sources:
                    n += 1
                    sid = "S%d" % n
                sources[sid] = {
                    "id": sid, "titre": texte, "type": "", "date": "", "lieu": "",
                    "ville": "", "pays": "", "auteur": "", "depot": "", "cote": "",
                    "abbr": "", "publ": "", "ark": "", "note": "", "fichier": "",
                    "fichiers": [], "transcription": "", "personnes": [],
                    "origine": "source importée en ligne"}
                par_texte[texte] = sid
            c["source"] = sid


def _reconcilier_parente(individus, familles):
    """Complète la table des familles avec ce que les individus déclarent, et
    compte les pointeurs qui ne désignent personne.

    Un GEDCOM écrit la parenté DEUX FOIS : dans l'enregistrement FAM
    (HUSB/WIFE/CHIL) et sur chaque individu (FAMS/FAMC). Arboriane ne garde que
    la table des familles ; sans cette réconciliation, un FAM incomplet ferait
    disparaître des liens pourtant présents dans le fichier.

    Renvoie le nombre de pointeurs abandonnés (cible inexistante).
    """
    ignores = 0

    # 1) Nettoyer les pointeurs morts des familles (personne inexistante).
    for fam in familles.values():
        for role in ("mari", "epouse"):
            if fam[role] and fam[role] not in individus:
                fam[role] = ""
                ignores += 1
        vivants = [c for c in fam["enfants"] if c in individus]
        ignores += len(fam["enfants"]) - len(vivants)
        fam["enfants"] = vivants

    # 2) Compléter depuis FAMS (l'individu se dit parent) et FAMC (enfant).
    for pid, ind in individus.items():
        for fid in ind.get("fams", []):
            fam = familles.get(fid)
            if fam is None:
                ignores += 1
                continue
            if pid in (fam["mari"], fam["epouse"]):
                continue
            sexe = ind.get("sexe")
            if sexe == "M" and not fam["mari"]:
                fam["mari"] = pid
            elif sexe == "F" and not fam["epouse"]:
                fam["epouse"] = pid
            elif not fam["mari"]:
                fam["mari"] = pid
            elif not fam["epouse"]:
                fam["epouse"] = pid
            else:
                ignores += 1        # famille déjà pourvue de deux parents
        for fid in ind.get("famc", []):
            fam = familles.get(fid)
            if fam is None:
                ignores += 1
            elif pid not in fam["enfants"]:
                fam["enfants"].append(pid)

    return ignores


@_serialise
def franciser_dates(donnees):
    """Traduit toutes les dates stockées vers le format INTERNE français
    (« 20 JUL 1984 » → « 20/07/1984 », « ABT 1850 » → « vers 1850 »). Idempotent
    (une date déjà française ne bouge pas) : sert à l'import ET de migration au
    chargement d'un arbre ancien. Ne touche pas à `date_rep` (date républicaine
    d'origine, réémise telle quelle à l'export)."""
    from services import dates_rep          # utilitaire pur (import tardif)

    def _f(obj):
        if isinstance(obj, dict) and obj.get("date"):
            obj["date"] = dates_rep.gedcom_vers_fr(obj["date"])

    for ind in (donnees.get("individus") or {}).values():
        _f(ind.get("naissance"))
        _f(ind.get("deces"))
        for coll in ("residences", "professions", "evenements"):
            for it in ind.get(coll) or []:
                _f(it)
    for fam in (donnees.get("familles") or {}).values():
        _f(fam.get("mariage"))
        for ev in fam.get("evenements") or []:
            _f(ev)
    for src in (donnees.get("sources") or {}).values():
        _f(src)
    return donnees


def importer(texte):
    """Lit un texte GEDCOM et renvoie une base « donnees » complète.

    Toutes les tables (individus, familles, sources, lieux, meta) sont
    garanties via modele.garantir_cles.
    """
    noeuds = _lire_lignes(texte)
    arbre = _arborescence(noeuds)
    version_fichier = _version_declaree(arbre)

    # Table des NOTE records (0 @NT..@ NOTE), référencées par pointeur ailleurs.
    _NOTES.clear()
    for rec in arbre:
        if rec["tag"] == "NOTE" and rec["xref"]:
            _NOTES[_pointeur(rec["xref"])] = _fusion_texte(rec)

    # Dépôts d'archives (0 @R..@ REPO) -> ENTITÉS + carte xref->depot_id, pour
    # résoudre SOUR.REPO et reconstruire le 3e niveau du sourçage.
    depots_imp = {}          # depot_id -> entité
    repo_rx = {}             # xref REPO -> depot_id
    for rec in arbre:
        if rec["tag"] == "REPO" and rec["xref"]:
            did = "D%d" % (len(depots_imp) + 1)
            ent = {"id": did}
            for cle, tag in (("nom", "NAME"), ("type", "_TYPE"), ("lieu", "ADDR"),
                             ("www", "WWW")):
                n = _premier(rec, tag)
                ent[cle] = _fusion_texte(n).strip() if n else ""
            # La note peut être un pointeur (1 NOTE @N2@) : la résoudre, comme
            # partout ailleurs, sinon on stocke « @N2@ » et on le réexporte comme
            # un pointeur vers un enregistrement qu'on n'écrit pas — note perdue.
            note = _premier(rec, "NOTE")
            ent["note"] = _lire_note(note) if note else ""
            depots_imp[did] = ent
            repo_rx[_pointeur(rec["xref"])] = did

    individus = {}
    familles = {}
    sources = {}

    for rec in arbre:
        if rec["tag"] == "INDI" and rec["xref"]:
            ind = lire_indi(rec)
            individus[ind["id"]] = ind

        elif rec["tag"] == "FAM" and rec["xref"]:
            fam = lire_fam(rec)
            familles[fam["id"]] = fam

        elif rec["tag"] == "SOUR" and rec["xref"]:
            src = lire_sour(rec, repo_rx, depots_imp)
            # retire le repli lisible ajouté à l'export (+ récupère lien/date/lieu)
            src["note"] = _retirer_repli_source(src)
            sources[src["id"]] = src

    # Réconcilier les DEUX écritures de la parenté. Un GEDCOM la déclare deux
    # fois : dans FAM (HUSB/WIFE/CHIL) et sur l'individu (FAMS/FAMC). Arboriane
    # ne retient que la table des familles — les FAMS/FAMC lus seraient donc
    # perdus si un FAM les omettait. On complète, on ne remplace jamais.
    liens_ignores = _reconcilier_parente(individus, familles)

    # Sources EN LIGNE (1 SOUR <texte>) -> vraies sources. Geneanet et les sites
    # GeneWeb aplatissent une source structurée en une phrase collée sur la
    # personne. Sans ceci, la citation garderait ce texte comme identifiant et
    # pointerait vers une source inexistante.
    _materialiser_sources_inline(individus, familles, sources)

    # Scans référencés PAR UNE CITATION (2 SOUR / 3 OBJE / 4 FILE, fréquent chez
    # Brother's Keeper) : on les rattache à la source citée. Le chemin d'origine
    # étant sur le disque de l'export, le scan apparaîtra « à retrouver » tant que
    # l'utilisateur n'aura pas rejoint le vrai fichier.
    for liste in _toutes_citations(individus, familles):
        for c in liste:
            f, sid = c.get("fichier_source"), c.get("source")
            chemin = c.get("fichier_source_chemin")
            if f and sid in sources:
                src = sources[sid]
                if f not in src["fichiers"]:
                    src["fichiers"].append(f)
                if not src.get("fichier"):
                    src["fichier"] = f
                # Chemin d'origine mémorisé pour l'import local du scan (Arboriane
                # tournant sur le PC de l'utilisateur, cf. services.import_medias).
                if chemin:
                    src.setdefault("_chemins_scans", []).append(chemin)
            c.pop("fichier_source", None)         # champs de transport, non persistés
            c.pop("fichier_source_chemin", None)

    # Reconstruire source.personnes : les citations niveau-personne PORTANT un
    # rôle sont des tags d'acte -> on les remet dans la source et on les retire
    # des citations « ordinaires » (symétrique de l'export ci-dessous).
    for pid, ind in individus.items():
        gardees = []
        for c in ind.get("citations", []):
            sid = c.get("source")
            # Ne convertir en simple tag {id, role} QUE les citations sans autre
            # contenu : sinon page/quay/transcription seraient jetés (perte au
            # round-trip). Une citation qui porte du contenu reste une citation.
            a_du_contenu = any(c.get(k) for k in
                               ("page", "quay", "texte", "transcription", "note"))
            if c.get("role") and sid in sources and not a_du_contenu:
                sources[sid]["personnes"].append({"id": pid, "role": c["role"]})
            else:
                gardees.append(c)
        ind["citations"] = gardees

    # récolte des coordonnées PLAC/MAP -> cache central des lieux (clé = nom)
    lieux = {}

    def _harvest(ev):
        if not isinstance(ev, dict):
            return
        c = ev.pop("_coords", None)
        nom = (ev.get("lieu") or "").strip()
        if c and nom and nom not in lieux:
            lieux[nom] = {"lat": c[0], "lon": c[1]}
    for ind in individus.values():
        _harvest(ind.get("naissance"))
        _harvest(ind.get("deces"))
        for r in ind.get("residences", []):
            _harvest(r)
        for ev in ind.get("evenements", []):
            _harvest(ev)
    for fam in familles.values():
        _harvest(fam.get("mariage"))
        for ev in fam.get("evenements", []):
            _harvest(ev)

    donnees = {
        "individus": individus,
        "familles": familles,
        "sources": sources,
        "depots": depots_imp,
        "lieux": lieux,
        # liens_ignores : pointeurs de parenté qui ne désignaient personne. Non
        # nul = le fichier est incohérent, ou Arboriane l'a mal lu. Dans les deux
        # cas l'utilisateur doit le savoir : un import muet qui perd la parenté
        # est pire qu'un import qui échoue.
        "meta": {"source": "import GEDCOM", "liens_ignores": liens_ignores,
                 "version_fichier": version_fichier},
    }
    return franciser_dates(modele.garantir_cles(donnees))


# ---------------------------------------------------------------------------
# ECRITURE (export)
# ---------------------------------------------------------------------------
