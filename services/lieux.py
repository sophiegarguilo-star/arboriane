# -*- coding: utf-8 -*-
"""Lieux, carte et migrations — agrégation, géocodage OpenStreetMap (Nominatim)
et détection d'anachronismes de frontières.

La table ``donnees["lieux"]`` sert de CACHE de coordonnées :
``{nom_lieu: {"lat": float, "lon": float}}``. Rien n'y est écrit sans action
explicite de l'utilisateur (le géocodage est strictement opt-in).

Bibliothèque standard uniquement (urllib pour Nominatim).
"""

import json
import time
import urllib.parse
import urllib.request

from core import modele
from core.modele import annee, annee_naissance, annee_deces, nom_court

# Point d'accès Nominatim (OpenStreetMap). On n'envoie QUE le nom du lieu.
_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "Arboriane/1.0 (application de généalogie locale)"

# Codes de type d'événement : N=naissance, D=décès, M=mariage,
# R=résidence, E=autre événement.
_LIBELLES = {"N": "Naissance", "D": "Décès", "M": "Mariage",
             "R": "Résidence", "E": "Événement"}

# Anachronismes de frontières : le NOM d'un lieu cite une entité qui n'existait
# pas encore comme pays à l'année de l'événement. Volontairement conservateur
# (pays nettement datés) pour éviter les fausses alertes sur des communes.
_ANACHRONISMES = [
    ("italie", 1861, "l'Italie", "les États italiens (Piémont-Sardaigne, Deux-Siciles…)"),
    ("allemagne", 1871, "l'Allemagne", "les États allemands (Prusse, Bavière…)"),
    ("belgique", 1830, "la Belgique", "les Pays-Bas (anciens Pays-Bas autrichiens)"),
    ("roumanie", 1859, "la Roumanie", "les principautés de Moldavie et de Valachie"),
    ("yougoslavie", 1918, "la Yougoslavie", "l'Autriche-Hongrie / la Serbie"),
    ("tchécoslovaquie", 1918, "la Tchécoslovaquie", "l'Autriche-Hongrie"),
    ("tchecoslovaquie", 1918, "la Tchécoslovaquie", "l'Autriche-Hongrie"),
    ("états-unis", 1776, "les États-Unis", "les colonies britanniques d'Amérique"),
    ("etats-unis", 1776, "les États-Unis", "les colonies britanniques d'Amérique"),
]


def anachronisme(lieu, an):
    """Alerte si le NOM du lieu cite une entité qui n'existait pas encore comme
    pays à l'année `an` (sinon None)."""
    if not lieu or not an:
        return None
    bas = lieu.lower()
    for cle, seuil, nom, contexte in _ANACHRONISMES:
        if cle in bas and an < seuil:
            return ("%s n'existe comme pays qu'à partir de %d "
                    "(à cette date : %s)." % (nom, seuil, contexte))
    return None


# ── Agrégation des lieux ──────────────────────────────────────────────
def _occurrences(donnees):
    """{ nom_lieu: {"nb": int, "personnes": set(pid)} } — tous les lieux CITÉS
    dans l'arbre (naissance, décès, mariage, résidences, événements)."""
    agg = {}

    def ajouter(lieu, pid):
        lieu = (lieu or "").strip()
        if not lieu:
            return
        e = agg.setdefault(lieu, {"nb": 0, "personnes": set()})
        e["nb"] += 1
        if pid:
            e["personnes"].add(pid)

    for pid, ind in donnees["individus"].items():
        ajouter((ind.get("naissance") or {}).get("lieu"), pid)
        ajouter((ind.get("deces") or {}).get("lieu"), pid)
        for r in ind.get("residences", []):
            ajouter(r.get("lieu"), pid)
        for ev in ind.get("evenements", []):
            ajouter(ev.get("lieu"), pid)
    for fam in donnees["familles"].values():
        conj = [x for x in (fam.get("mari"), fam.get("epouse")) if x]
        lm = (fam.get("mariage") or {}).get("lieu")
        for pid in conj:
            ajouter(lm, pid)
        for ev in fam.get("evenements", []):
            for pid in conj:
                ajouter(ev.get("lieu"), pid)
    return agg


def sans_pays(donnees):
    """Lieux distincts dont la dernière partie (après virgule) n'est pas un pays
    reconnu — candidats à préciser (ex. « Neufchâteau »). Trié par fréquence."""
    from services import lieux_ref
    out = []
    for nom, e in _occurrences(donnees).items():
        parts = [p.strip() for p in (nom or "").split(",") if p.strip()]
        if parts and parts[-1].lower() not in lieux_ref._PAYS:
            out.append({"nom": nom, "nb": e["nb"], "nb_personnes": len(e["personnes"])})
    out.sort(key=lambda x: (-x["nb"], x["nom"].lower()))
    return out


def lister(donnees):
    """Liste des lieux distincts : nombre d'occurrences, nombre de personnes,
    coordonnées connues (depuis le cache donnees['lieux'])."""
    cache = donnees.get("lieux", {}) or {}
    inds = donnees["individus"]
    out = []
    for nom, e in _occurrences(donnees).items():
        c = cache.get(nom) or {}
        out.append({
            "nom": nom,
            "nb": e["nb"],
            "nb_personnes": len(e["personnes"]),
            "lat": c.get("lat"),
            "lon": c.get("lon"),
            "personnes": [{"id": p, "nom": modele.nom_complet(inds[p])}
                          for p in list(e["personnes"])[:15] if p in inds],
        })
    out.sort(key=lambda x: (-x["nb"], x["nom"].lower()))
    nb_a_geocoder = sum(1 for x in out if x["lat"] is None)
    return {"lieux": out, "nb": len(out), "nb_a_geocoder": nb_a_geocoder}


# ── Carte / migrations ────────────────────────────────────────────────
def carte(donnees, pid=None, mode="personne"):
    """Événements datés ET géocodés pour la carte des migrations.

    mode="personne" : parcours de vie de la personne `pid`.
    mode="lignee"   : mêmes événements pour toute son ascendance (Sosa).

    Chaque événement : {pid, nom, sexe, annee, type, lieu, lat, lon, anachronisme}.
    Renvoie {evenements, min, max, nb_anachronismes} trié par année."""
    cache = donnees.get("lieux", {}) or {}
    inds = donnees["individus"]
    if mode == "lignee" and pid:
        table = modele.ascendance_sosa(donnees, pid, 40)   # {sosa: pid}
        pids = list(dict.fromkeys(table.values()))
    elif pid:
        pids = [pid]
    else:
        pids = list(inds.keys())

    evs = []

    def ajout(ident, an, type_, lieu):
        lieu = (lieu or "").strip()
        if not lieu or not an:
            return
        c = cache.get(lieu) or {}
        if c.get("lat") is None:
            return                                    # pas de coords -> hors carte
        ind = inds.get(ident, {})
        evs.append({
            "pid": ident, "nom": nom_court(ind), "sexe": ind.get("sexe", "U"),
            "annee": an, "type": type_, "lieu": lieu,
            "lat": c["lat"], "lon": c["lon"],
            "anachronisme": anachronisme(lieu, an),
        })

    for ident in pids:
        ind = inds.get(ident)
        if not ind:
            continue
        ajout(ident, annee_naissance(ind), "N", (ind.get("naissance") or {}).get("lieu"))
        ajout(ident, annee_deces(ind), "D", (ind.get("deces") or {}).get("lieu"))
        for r in ind.get("residences", []):
            ajout(ident, annee(r.get("date")), "R", r.get("lieu"))
        for ev in ind.get("evenements", []):
            ajout(ident, annee(ev.get("date")), "E", ev.get("lieu"))
        for fid in ind.get("fams", []):
            m = (donnees["familles"].get(fid) or {}).get("mariage") or {}
            ajout(ident, annee(m.get("date")), "M", m.get("lieu"))

    evs.sort(key=lambda e: (e["annee"], e["pid"]))
    annees = [e["annee"] for e in evs]
    return {
        "evenements": evs,
        "min": min(annees) if annees else None,
        "max": max(annees) if annees else None,
        "nb_anachronismes": sum(1 for e in evs if e["anachronisme"]),
    }


# ── Géocodage Nominatim (opt-in, jamais automatique) ──────────────────
def _variantes_requete(nom):
    """Requêtes à tenter, de la plus précise à la plus large, pour un lieu à
    plusieurs champs (« Givet, Saint-Hilaire, Ardennes, France »). On nettoie les
    parties vides (« Givet, , Ardennes, France ») et, à défaut de résultat, on se
    rabat sur « ville, pays » puis « ville » — Nominatim ne connaît pas les
    hameaux/paroisses saisis en 2e champ."""
    parts = [p.strip() for p in (nom or "").split(",") if p.strip()]
    if not parts:
        return []
    variantes = [", ".join(parts)]
    if len(parts) >= 3:
        court = parts[0] + ", " + parts[-1]      # ville + pays (ou dernier champ)
        if court not in variantes:
            variantes.append(court)
    if len(parts) >= 2 and parts[0] not in variantes:
        variantes.append(parts[0])               # ville seule (dernier recours)
    return variantes


def _nominatim_un(q):
    """Un seul appel Nominatim pour une requête déjà prête. (lat, lon) ou None."""
    url = _NOMINATIM + "?" + urllib.parse.urlencode(
        {"format": "json", "limit": 1, "q": q})
    req = urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT, "Accept-Language": "fr"})
    try:
        with urllib.request.urlopen(req, timeout=15) as rep:
            data = json.loads(rep.read().decode("utf-8"))
    except Exception:  # noqa: BLE001  (réseau/parse : on renonce silencieusement)
        return None
    if not data:
        return None
    try:
        return float(data[0]["lat"]), float(data[0]["lon"])
    except (KeyError, ValueError, IndexError, TypeError):
        return None


def _requete_nominatim(nom):
    """Géocode un lieu (éventuellement à plusieurs champs) : essaie la requête
    complète, puis des variantes plus larges. N'envoie QUE le nom du lieu."""
    variantes = _variantes_requete(nom)
    for i, q in enumerate(variantes):
        if i:
            time.sleep(1.1)                      # politique Nominatim entre 2 essais
        coords = _nominatim_un(q)
        if coords:
            return coords
    return None


def suggerer(q, limite=6):
    """Suggestions de lieux géolocalisés (Nominatim) pour l'autocomplétion des
    champs « lieu ». Renvoie [{nom, lat, lon, ville, pays}] — nom = libellé
    complet OSM. N'envoie QUE la saisie de l'utilisatrice. À n'appeler que si le
    géocodage est autorisé (opt-in) : la vérification se fait côté route."""
    q = (q or "").strip()
    if len(q) < 3:
        return []
    url = _NOMINATIM + "?" + urllib.parse.urlencode({
        "format": "json", "addressdetails": 1, "limit": limite, "q": q})
    req = urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT, "Accept-Language": "fr"})
    try:
        with urllib.request.urlopen(req, timeout=12) as rep:
            data = json.loads(rep.read().decode("utf-8"))
    except Exception:  # noqa: BLE001  (réseau/parse : on renonce silencieusement)
        return []
    out = []
    for d in data or []:
        try:
            adr = d.get("address") or {}
            ville = (adr.get("city") or adr.get("town") or adr.get("village")
                     or adr.get("municipality") or adr.get("hamlet")
                     or adr.get("county") or "")
            out.append({"nom": d["display_name"], "lat": float(d["lat"]),
                        "lon": float(d["lon"]), "ville": ville,
                        "pays": adr.get("country") or ""})
        except (KeyError, ValueError, TypeError):
            continue
    return out


def memoriser_coords(donnees, nom, lat, lon):
    """Écrit directement des coordonnées connues dans le cache (ex. lieu choisi
    dans l'autocomplétion Nominatim), sans nouvelle requête réseau."""
    nom = (nom or "").strip()
    if not nom:
        return False
    try:
        donnees.setdefault("lieux", {})[nom] = {"lat": float(lat), "lon": float(lon)}
        return True
    except (TypeError, ValueError):
        return False


def _avec_pays_defaut(nom, pays_defaut):
    """Complète la REQUÊTE de géocodage avec le pays par défaut quand le lieu
    n'a pas de pays reconnu en dernière position (ex. « Neufchâteau » → recherché
    « Neufchâteau, Belgique » pour ne pas tomber sur les Vosges). Ne touche NI le
    libellé saisi NI la clé de cache : seul le texte envoyé à Nominatim change."""
    from services import lieux_ref
    q = (nom or "").strip()
    p = (pays_defaut or "").strip()
    if not p or not q:
        return q
    parts = [x.strip() for x in q.split(",") if x.strip()]
    if parts and parts[-1].lower() in lieux_ref._PAYS:
        return q                          # un pays est déjà présent : on n'ajoute rien
    return q + ", " + p


def geocoder(donnees, noms_lieux=None, lot=12, pays_defaut=""):
    """Géocode via Nominatim les lieux demandés (ou, à défaut, tous les lieux
    non encore géocodés), et écrit les coordonnées dans donnees['lieux'].

    `pays_defaut` (optionnel) est ajouté à la requête d'un lieu qui n'indique
    aucun pays — utile pour les arbres d'un pays donné (Belgique…).

    Respecte la politique Nominatim : 1 requête/seconde (time.sleep). Traite un
    lot borné par appel pour éviter une requête trop longue. Renvoie
    {geocodes, echecs, traites, restants}."""
    cache = donnees.setdefault("lieux", {})
    if not noms_lieux:
        noms_lieux = [x["nom"] for x in lister(donnees)["lieux"] if x["lat"] is None]
    cibles = [n.strip() for n in noms_lieux if n and n.strip()]
    cibles = [n for n in cibles if n not in cache][:lot]

    geocodes = echecs = 0
    for i, nom in enumerate(cibles):
        if i:
            time.sleep(1.1)              # politique Nominatim : ~1 requête/seconde
        coords = _requete_nominatim(_avec_pays_defaut(nom, pays_defaut))
        if coords:
            cache[nom] = {"lat": coords[0], "lon": coords[1]}
            geocodes += 1
        else:
            echecs += 1
    restants = sum(1 for x in lister(donnees)["lieux"] if x["lat"] is None)
    return {"geocodes": geocodes, "echecs": echecs,
            "traites": len(cibles), "restants": restants}
