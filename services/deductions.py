# -*- coding: utf-8 -*-
"""
Déductions & complétude — repérer et aider à corriger les fiches incomplètes.

- sexes_absents(donnees) : personnes dont le sexe n'est pas renseigné (U/vide) ;
  propose M/F d'après le rôle familial (mari → masculin, épouse → féminin).
  On ne touche PAS aux sexes explicitement « N » (non consigné) ou « X »
  (intersexe), qui sont des choix délibérés.
- noms_absents(donnees) : personnes à qui il manque le nom ou le prénom.
- appliquer_sexe(donnees, pid, sexe) : pose un sexe validé sur une personne.

Fonctions pures sur la base (donnees) ; la persistance est faite par la route.
"""

from core import modele
from core.modele import nom_complet

_SEXE_ABSENT = ("", "U", None)          # à compléter ; N et X sont volontaires


def _sexe_selon_role(donnees, pid):
    """('M'|'F', raison) déduit du rôle familial, ou (None, '')."""
    masculin = feminin = False
    for fam in donnees["familles"].values():
        if fam.get("mari") == pid:
            masculin = True
        if fam.get("epouse") == pid:
            feminin = True
    if masculin and not feminin:
        return "M", "figure comme mari/père dans une union"
    if feminin and not masculin:
        return "F", "figure comme épouse/mère dans une union"
    return None, ""


def sexes_absents(donnees):
    """Personnes sans sexe renseigné, avec une proposition quand elle est
    déductible du rôle familial. Les actionnables (proposition) d'abord."""
    out = []
    for pid, ind in donnees["individus"].items():
        if ind.get("sexe") in _SEXE_ABSENT:
            propose, raison = _sexe_selon_role(donnees, pid)
            out.append({"id": pid, "nom": nom_complet(ind),
                        "sexe_propose": propose or "", "raison": raison})
    out.sort(key=lambda p: (p["sexe_propose"] == "", p["nom"].lower()))
    return {"total": len(out),
            "nb_deductibles": sum(1 for p in out if p["sexe_propose"]),
            "personnes": out}


def noms_absents(donnees):
    """Personnes à qui il manque le nom ou le prénom (repli « ? »)."""
    out = []
    for pid, ind in donnees["individus"].items():
        a_nom = bool((ind.get("nom") or "").strip())
        a_prenom = bool((ind.get("prenoms") or ind.get("prenom_principal") or "").strip())
        if a_nom and a_prenom:
            continue
        manque = ("nom_et_prenom" if not a_nom and not a_prenom
                  else "nom" if not a_nom else "prenom")
        out.append({"id": pid, "nom": nom_complet(ind), "manque": manque})
    out.sort(key=lambda p: p["nom"].lower())
    return {"total": len(out), "personnes": out}


def appliquer_sexe(donnees, pid, sexe):
    """Pose le sexe (validé) sur une personne. Renvoie la personne. Lève
    ValueError si l'identifiant est inconnu ou le sexe invalide."""
    if sexe not in modele.SEXES:
        raise ValueError("Sexe invalide : %r" % (sexe,))
    ind = donnees["individus"].get(pid)
    if not ind:
        raise ValueError("Personne inconnue : %s" % pid)
    ind["sexe"] = sexe
    return ind


# ── Décès présumés (personnes présumées vivantes mais trop âgées) ─────────
# Au-delà de ce seuil d'âge MINIMAL déduit, une personne sans date de décès ne
# peut plus être vivante (durée de vie humaine max ≈ 122 ans). On reste large.
SEUIL_DECES_PRESUME = 105


def deces_presumes(donnees, seuil=SEUIL_DECES_PRESUME, annee_courante=None):
    """Personnes ENCORE présumées vivantes (aucune date de décès, pas de drapeau
    'décédé') dont l'âge MINIMAL déduit atteint `seuil` — elles sont donc trop
    âgées pour l'être, en général faute de date de naissance alors qu'un enfant
    ou une union situe leur époque. On ne propose que de poser « décédé·e sans
    date » — JAMAIS d'inventer une date de décès."""
    out = []
    for pid, ind in donnees["individus"].items():
        if not modele.est_vivant_presume(ind):
            continue
        am = modele.age_minimal(donnees, pid, ind, annee_courante)
        if am is None or am < seuil:
            continue
        ny, indice = modele.naissance_au_plus_tard(donnees, pid, ind)
        out.append({"id": pid, "nom": nom_complet(ind), "age_min": am,
                    "ne_au_plus_tard": ny, "indice": indice,
                    "sans_naissance": not modele.annee_naissance(ind)})
    out.sort(key=lambda p: -p["age_min"])
    return {"total": len(out), "seuil": seuil, "personnes": out}


def appliquer_deces(donnees, pid):
    """Marque une personne « décédée » SANS date (pose vivant=False). Ne touche
    JAMAIS une personne ayant déjà un décès renseigné. Renvoie la personne."""
    ind = donnees["individus"].get(pid)
    if not ind:
        raise ValueError("Personne inconnue : %s" % pid)
    dec = ind.get("deces") or {}
    if (dec.get("date") or "").strip() or (dec.get("lieu") or "").strip():
        return ind                       # décès déjà connu : rien à faire
    ind["vivant"] = False
    return ind


def appliquer_deces_tous(donnees, seuil=SEUIL_DECES_PRESUME, annee_courante=None):
    """Applique le décès présumé à TOUTES les personnes détectées. Renvoie la
    liste des identifiants corrigés."""
    cibles = deces_presumes(donnees, seuil, annee_courante)["personnes"]
    for c in cibles:
        appliquer_deces(donnees, c["id"])
    return {"corriges": [c["id"] for c in cibles], "total": len(cibles)}
