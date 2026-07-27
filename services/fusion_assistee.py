# -*- coding: utf-8 -*-
"""
Fusion ASSISTÉE — L14.

Deux volets, non destructifs, qui s'appuient sur l'existant :
  • Personnes : un SCORE DE CONFIANCE sur les doublons probables
    (`services.fusion.doublons_probables`), une COMPARAISON champ par champ pour
    l'assistant, et une fusion guidée avec GARDE-FOU SEXE (refus si les sexes
    diffèrent, sauf confirmation explicite). La fusion réutilise
    `services.fusion.fusionner` (complète les vides, jamais d'écrasement).
  • Lieux : regroupe les ORTHOGRAPHES d'un même lieu (casse/accents/espaces) et
    réécrit les variantes vers une entrée canonique dans tous les événements.

Aucune écriture destructive silencieuse : la fusion de personnes passe par la
logique éprouvée de v1, et la fusion de lieux ne touche QUE la chaîne de lieu
(les données GEDCOM restent lisibles).
"""

import unicodedata

from core import modele
from services import fusion


# ── Personnes : score de confiance ─────────────────────────────────────────
def _parents(donnees, pid):
    p, m = modele.parents(donnees, pid)
    return {x for x in (p, m) if x}


def _conjoints(donnees, pid):
    return {c for c, _ in modele.conjoints(donnees, pid)}


def _lieu(evt):
    return ((evt or {}).get("lieu") or "").strip().lower()


def score_paire(donnees, ida, idb):
    """Score de confiance 0–100 qu'une paire soit bien un doublon (au-delà du
    simple homonyme). Renvoie (score, indices[])."""
    inds = donnees["individus"]
    a, b = inds.get(ida) or {}, inds.get(idb) or {}
    score, indices = 40, ["même nom"]      # base : même nom complet (pré-filtré)

    ax, ay = modele.annee_naissance(a), modele.annee_naissance(b)
    if ax is not None and ay is not None:
        if ax == ay:
            score += 25; indices.append("même année de naissance")
        elif abs(ax - ay) <= 3:
            score += 12; indices.append("naissances proches")
        else:
            score -= 20
    else:
        score += 6; indices.append("une naissance manquante")

    sa, sb = a.get("sexe", "U"), b.get("sexe", "U")
    if sa != "U" and sb != "U":
        if sa == sb:
            score += 10
        else:
            score -= 35; indices.append("⚠ sexes différents")

    if _parents(donnees, ida) & _parents(donnees, idb):
        score += 15; indices.append("parent commun")
    if _conjoints(donnees, ida) & _conjoints(donnees, idb):
        score += 12; indices.append("conjoint commun")
    if _lieu(a.get("naissance")) and _lieu(a.get("naissance")) == _lieu(b.get("naissance")):
        score += 8; indices.append("même lieu de naissance")
    if _lieu(a.get("deces")) and _lieu(a.get("deces")) == _lieu(b.get("deces")):
        score += 5

    return max(0, min(100, score)), indices


def _niveau(score):
    return "eleve" if score >= 70 else ("moyen" if score >= 45 else "faible")


def _cle_paire(a, b):
    """Clé stable d'une paire (indépendante de l'ordre)."""
    return "|".join(sorted([a, b]))


def _paires_ecartees(donnees):
    """Paires que l'utilisateur a marquées « pas un doublon » (persistées)."""
    return set((donnees.get("meta") or {}).get("doublons_ecartes") or [])


def paires_scorees(donnees):
    """Doublons probables enrichis d'un score de confiance, triés du plus au
    moins probable. Les paires explicitement écartées sont exclues."""
    ecartees = _paires_ecartees(donnees)
    out = []
    for p in fusion.doublons_probables(donnees):
        if _cle_paire(p["a"], p["b"]) in ecartees:
            continue
        score, indices = score_paire(donnees, p["a"], p["b"])
        out.append(dict(p, score=score, niveau=_niveau(score), indices=indices))
    out.sort(key=lambda x: -x["score"])
    return out


def ecarter_paire(base, ida, idb):
    """Marque une paire comme « ce n'est pas un doublon » : elle ne sera plus
    proposée dans la fusion assistée. Décision persistée dans meta."""
    if not ida or not idb or ida == idb:
        raise ValueError("Paire invalide.")
    inds = base.donnees.get("individus", {})
    if ida not in inds or idb not in inds:
        raise ValueError("Personne introuvable.")
    meta = base.donnees.setdefault("meta", {})
    lst = meta.setdefault("doublons_ecartes", [])
    cle = _cle_paire(ida, idb)
    if cle not in lst:
        lst.append(cle)
        base.sauvegarder()
    return {"ecartee": cle}


# ── Personnes : comparaison champ par champ ─────────────────────────────────
_CHAMPS_CMP = [
    ("prenoms", "Prénoms"), ("nom", "Nom"), ("prenom_principal", "Prénom usuel"),
    ("surnom", "Surnom"), ("nom_marital", "Nom marital"), ("sexe", "Sexe"),
    ("naissance.date", "Naissance — date"), ("naissance.lieu", "Naissance — lieu"),
    ("deces.date", "Décès — date"), ("deces.lieu", "Décès — lieu"),
    ("refn", "Référence"), ("note", "Note"),
]


def _val(ind, cle):
    if "." in cle:
        a, b = cle.split(".", 1)
        return ((ind.get(a) or {}).get(b) or "").strip()
    return (ind.get(cle) or "").strip() if isinstance(ind.get(cle), str) else (ind.get(cle) or "")


def comparer(donnees, ida, idb):
    """Comparaison champ par champ des deux fiches, pour l'assistant. Chaque
    entrée : {cle, libelle, a, b, conflit} (conflit = deux valeurs non vides et
    différentes)."""
    inds = donnees["individus"]
    a, b = inds.get(ida), inds.get(idb)
    if not a or not b:
        return None
    lignes = []
    for cle, lib in _CHAMPS_CMP:
        va, vb = _val(a, cle), _val(b, cle)
        if not va and not vb:
            continue
        lignes.append({"cle": cle, "libelle": lib, "a": va, "b": vb,
                       "conflit": bool(va and vb and va != vb)})
    return {"a": ida, "b": idb, "nom_a": modele.nom_complet(a),
            "nom_b": modele.nom_complet(b), "lignes": lignes}


def _poser(ind, cle, valeur):
    if "." in cle:
        a, b = cle.split(".", 1)
        ind.setdefault(a, {})[b] = valeur
    else:
        ind[cle] = valeur


def fusionner_assiste(base, garde_id, absorbe_id, choix=None, forcer_sexe=False):
    """Fusion guidée. `choix` = {cle: "a"|"b"} : pour un champ en conflit, "b"
    impose la valeur de l'absorbée sur la gardée AVANT la fusion (sinon la
    fusion ne complète que les vides). Garde-fou : refuse si les sexes diffèrent
    et que `forcer_sexe` n'est pas vrai. Renvoie le résumé de fusion."""
    inds = base.donnees["individus"]
    g, a = inds.get(garde_id), inds.get(absorbe_id)
    if not g or not a or garde_id == absorbe_id:
        raise ValueError("Personnes invalides pour la fusion.")
    sg, sa = g.get("sexe", "U"), a.get("sexe", "U")
    if sg != "U" and sa != "U" and sg != sa and not forcer_sexe:
        raise ValueError("Les deux personnes ont des sexes différents "
                         "(%s vs %s). Confirmez si c'est bien un doublon." % (sg, sa))
    for cle, qui in (choix or {}).items():
        if qui == "b":
            _poser(g, cle, _val(a, cle))
    return fusion.fusionner(base, garde_id, absorbe_id)


# ── Lieux : regroupement des orthographes + fusion ──────────────────────────
def _cle_lieu(nom):
    """Clé de regroupement : minuscules, sans accents, espaces/ponctuation
    normalisés (« Saint-Étienne » ≈ « saint etienne »)."""
    s = unicodedata.normalize("NFKD", (nom or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    for p in ("-", ".", ",", "'", "’", "/"):
        s = s.replace(p, " ")
    return " ".join(s.split())


def lieux_doublons(donnees):
    """Groupes de lieux qui ne diffèrent que par l'orthographe. Chaque groupe :
    {canonique (variante la plus fréquente), total, variantes:[{nom,nb,nb_personnes}]}."""
    from services import lieux as lieux_svc
    occ = lieux_svc._occurrences(donnees)
    groupes = {}
    for nom, e in occ.items():
        groupes.setdefault(_cle_lieu(nom), []).append(
            {"nom": nom, "nb": e["nb"], "nb_personnes": len(e["personnes"])})
    out = []
    for cle, variantes in groupes.items():
        if len(variantes) < 2:
            continue
        variantes.sort(key=lambda v: (-v["nb"], v["nom"].lower()))
        out.append({"canonique": variantes[0]["nom"],
                    "total": sum(v["nb"] for v in variantes),
                    "variantes": variantes})
    out.sort(key=lambda g: -g["total"])
    return out


def fusionner_lieux(base, canonique, absorbes):
    """Réécrit toutes les occurrences des lieux `absorbes` vers `canonique`
    (naissance, décès, résidences, événements, mariages). Met à jour le cache de
    coordonnées. Renvoie {modifies}."""
    canonique = (canonique or "").strip()
    cibles = {(x or "").strip() for x in (absorbes or []) if (x or "").strip()
              and (x or "").strip() != canonique}
    if not canonique or not cibles:
        return {"modifies": 0}
    n = 0

    def maj(evt):
        nonlocal n
        if evt and (evt.get("lieu") or "").strip() in cibles:
            evt["lieu"] = canonique; n += 1

    with base._verrou:
        d = base.donnees
        for ind in d["individus"].values():
            maj(ind.get("naissance")); maj(ind.get("deces"))
            for r in ind.get("residences", []):
                maj(r)
            for ev in ind.get("evenements", []):
                maj(ev)
        for fam in d["familles"].values():
            maj(fam.get("mariage"))
            for ev in fam.get("evenements", []):
                maj(ev)
        # cache de coordonnées : récupérer des coords si le canonique n'en a pas
        cache = d.setdefault("lieux", {})
        for nom in list(cache.keys()):
            if nom in cibles:
                if nom == canonique:
                    continue
                if canonique not in cache and cache[nom]:
                    cache[canonique] = cache[nom]
                del cache[nom]
        base.sauvegarder()
    return {"modifies": n}
