# -*- coding: utf-8 -*-
"""
Référentiel de lieux — hiérarchie + noms datés.

Un lieu cesse d'être une simple chaîne : il devient une entrée d'un référentiel
hiérarchique (lieu-dit → commune → canton → département → région → pays), avec
des NOMS ALTERNATIFS DATÉS (commune renommée à la Révolution, « Basses-Alpes »
devenue « Alpes-de-Haute-Provence » en 1970, fusions récentes…).

GEDCOM-first : les événements gardent leur CHAÎNE de lieu inchangée ; ce
référentiel est une couche PARALLÈLE (``donnees["lieux_ref"]``) qui n'écrase rien
et reste recalculable. On peut résoudre « chaîne + date » vers le nom
historiquement correct. Ne touche ni au cache de coordonnées ``donnees["lieux"]``
ni à la carte des migrations.
"""

from core import modele
from services import lieux as lieux_svc

TYPES = ("lieu-dit", "commune", "canton", "département", "région", "pays")


def _ref(donnees):
    return donnees.setdefault("lieux_ref", {})


# Pays fréquents (français-first) : lève l'ambiguïté des chaînes à 2 parties —
# « Amboise, Indre-et-Loire » (commune+département) vs « Bristol, Angleterre »
# (commune+pays). Un type reste corrigeable à la main dans l'éditeur.
_PAYS = {
    "france", "italie", "italia", "angleterre", "écosse", "ecosse", "irlande",
    "royaume-uni", "espagne", "allemagne", "belgique", "suisse", "luxembourg",
    "pays-bas", "portugal", "algérie", "algerie", "maroc", "tunisie", "malte",
    "états-unis", "etats-unis", "canada", "pologne", "russie", "autriche",
    "grèce", "grece", "turquie", "brésil", "bresil", "argentine",
    # Europe (centrale, du Sud-Est, nordique)
    "pays de galles", "grande-bretagne", "monaco", "andorre", "saint-marin",
    "pays basque", "catalogne", "roumanie", "hongrie", "tchéquie", "tchequie",
    "république tchèque", "slovaquie", "croatie", "slovénie", "slovenie",
    "serbie", "bosnie-herzégovine", "bosnie", "monténégro", "montenegro", "kosovo",
    "macédoine du nord", "macedoine du nord", "macédoine", "macedoine", "albanie",
    "bulgarie", "ukraine", "biélorussie", "bielorussie", "moldavie", "lituanie",
    "lettonie", "estonie", "finlande", "suède", "suede", "norvège", "norvege",
    "danemark", "islande", "chypre",
    # Maghreb, Proche & Moyen-Orient, Afrique
    "libye", "égypte", "egypte", "liban", "syrie", "israël", "israel", "palestine",
    "jordanie", "irak", "iran", "sénégal", "senegal", "mali", "mauritanie", "niger",
    "côte d'ivoire", "cote d'ivoire", "cameroun", "madagascar", "afrique du sud",
    "éthiopie", "ethiopie", "congo",
    # Amériques, Asie, Océanie
    "mexique", "chili", "colombie", "pérou", "perou", "uruguay", "venezuela",
    "cuba", "haïti", "haiti", "chine", "japon", "inde", "vietnam", "cambodge",
    "laos", "thaïlande", "thailande", "corée", "coree", "philippines", "indonésie",
    "indonesie", "australie", "nouvelle-zélande", "nouvelle-zelande",
}


def _types_pour(parts):
    """Types présumés des parties d'une chaîne (du plus précis au pays)."""
    n = len(parts)
    dernier_pays = n >= 1 and parts[-1].strip().lower() in _PAYS
    if n <= 1:
        return ["pays"] if dernier_pays else ["commune"]
    if n == 2:
        return ["commune", "pays"] if dernier_pays else ["commune", "département"]
    if n == 3:
        return ["commune", "département", "pays"]
    return ["lieu-dit"] * (n - 3) + ["commune", "département", "pays"]


def _parts(chaine):
    return [p.strip() for p in (chaine or "").split(",") if p.strip()]


# ── Noms datés & hiérarchie ───────────────────────────────────────────
def nom_a_date(entree, annee=None):
    """Nom valide à l'année donnée (parmi les noms datés), sinon le nom courant.
    Un nom daté {nom, apres, avant} vaut pour apres ≤ annee ≤ avant (bornes
    ouvertes si None)."""
    if annee:
        for nd in entree.get("noms_dates", []):
            ap, av = nd.get("apres"), nd.get("avant")
            if (ap is None or annee >= ap) and (av is None or annee <= av) and nd.get("nom"):
                return nd["nom"]
    return entree.get("nom", "")


def chemin(donnees, lid):
    """Entrées de `lid` jusqu'à la racine (du plus précis au pays), anti-cycle."""
    ref = _ref(donnees)
    out, vus = [], set()
    cur = ref.get(lid)
    while cur and cur["id"] not in vus:
        vus.add(cur["id"])
        out.append(cur)
        cur = ref.get(cur.get("parent"))
    return out


def chemin_texte(donnees, lid):
    return ", ".join(e.get("nom", "") for e in chemin(donnees, lid))


def _resume(donnees, e):
    return {"id": e["id"], "nom": e.get("nom", ""), "type": e.get("type", ""),
            "parent": e.get("parent", ""), "noms_dates": e.get("noms_dates", []),
            "lat": e.get("lat"), "lon": e.get("lon"),
            "chemin": chemin_texte(donnees, e["id"])}


def lister(donnees):
    """Toutes les entrées (chemin résolu), triées par chemin."""
    out = [_resume(donnees, e) for e in _ref(donnees).values()]
    out.sort(key=lambda x: (x["chemin"] or x["nom"]).lower())
    return {"total": len(out), "lieux": out}


# ── CRUD ──────────────────────────────────────────────────────────────
def creer(donnees, champs):
    ref = _ref(donnees)
    lid = modele.nouvel_id(ref, "L")
    e = {"id": lid, "nom": (champs.get("nom") or "").strip(),
         "type": (champs.get("type") or "").strip(),
         "parent": (champs.get("parent") or "").strip(),
         "noms_dates": _nettoyer_noms_dates(champs.get("noms_dates")),
         "lat": champs.get("lat"), "lon": champs.get("lon")}
    ref[lid] = e
    return e


def modifier(donnees, lid, champs):
    e = _ref(donnees).get(lid)
    if not e:
        return None
    for cle in ("nom", "type", "parent"):
        if cle in champs:
            e[cle] = (champs[cle] or "").strip()
    if "noms_dates" in champs:
        e["noms_dates"] = _nettoyer_noms_dates(champs["noms_dates"])
    for cle in ("lat", "lon"):
        if cle in champs:
            e[cle] = champs[cle]
    return e


def _nettoyer_noms_dates(liste):
    def _an(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return None
    out = []
    for nd in (liste or []):
        if isinstance(nd, dict) and (nd.get("nom") or "").strip():
            out.append({"nom": nd["nom"].strip(),
                        "apres": _an(nd.get("apres")), "avant": _an(nd.get("avant"))})
    return out


def supprimer(donnees, lid):
    ref = _ref(donnees)
    if lid not in ref:
        return False
    for e in ref.values():                 # les enfants perdent leur parent
        if e.get("parent") == lid:
            e["parent"] = ""
    del ref[lid]
    return True


# ── Résolution & migration ────────────────────────────────────────────
def resoudre(donnees, chaine, annee=None):
    """Fait correspondre une chaîne à une entrée (par la partie la plus précise).
    Renvoie {id, nom_resolu, chemin} ou None."""
    parts = _parts(chaine)
    if not parts:
        return None
    precis = parts[0].lower()
    for e in _ref(donnees).values():
        if (e.get("nom") or "").strip().lower() == precis:
            return {"id": e["id"], "nom_resolu": nom_a_date(e, annee),
                    "chemin": chemin_texte(donnees, e["id"])}
    return None


def construire_depuis_evenements(donnees):
    """Construit la hiérarchie à partir des chaînes de lieu citées dans l'arbre
    (via lieux._occurrences). Non destructif ; dédoublonne les niveaux partagés
    (un même département/pays n'est créé qu'une fois) ; idempotent. Renvoie
    {crees, total}."""
    ref = _ref(donnees)
    cache = donnees.get("lieux", {}) or {}
    par_cle = {((e.get("nom") or "").strip().lower(), e.get("type", "")): e["id"]
               for e in ref.values()}
    crees = 0
    for chaine in lieux_svc._occurrences(donnees):
        parts = _parts(chaine)
        if not parts:
            continue
        types = _types_pour(parts)
        parent_id = ""
        for part, typ in zip(reversed(parts), reversed(types)):
            cle = (part.lower(), typ)
            lid = par_cle.get(cle)
            if not lid:
                lid = creer(donnees, {"nom": part, "type": typ, "parent": parent_id})["id"]
                par_cle[cle] = lid
                crees += 1
            elif not ref[lid].get("parent") and parent_id:
                ref[lid]["parent"] = parent_id
            parent_id = lid
        coords = cache.get(chaine)          # coords -> entrée la plus précise
        if coords and parent_id and ref[parent_id].get("lat") is None:
            ref[parent_id]["lat"] = coords.get("lat")
            ref[parent_id]["lon"] = coords.get("lon")
    return {"crees": crees, "total": len(ref)}
