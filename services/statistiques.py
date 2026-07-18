# -*- coding: utf-8 -*-
"""Statistiques descriptives de l'arbre (lecture seule)."""

from core import modele
from core.modele import annee_naissance, annee_deces, parents


def _mediane(valeurs):
    v = sorted(valeurs)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def calculer(donnees, exclure=None):
    """Statistiques de l'arbre. `exclure` : ensemble d'id à ne pas compter
    (personnes hors famille : officiers, témoins, partenaires isolés)."""
    exclure = exclure or set()
    inds = {pid: i for pid, i in donnees["individus"].items() if pid not in exclure}
    fams = donnees["familles"]
    srcs = donnees.get("sources", {})
    total = len(inds)

    sexes = {"M": 0, "F": 0, "autre": 0}
    par_siecle = {}
    longevites = []
    avec_naissance = avec_deces = avec_lieu_nais = 0
    avec_pere = avec_mere = avec_parent = 0
    complets = 0
    lieux = {}
    patronymes = {}
    prenoms_freq = {}

    for pid, ind in inds.items():
        s = ind.get("sexe")
        sexes["M" if s == "M" else "F" if s == "F" else "autre"] += 1
        nomf = modele.nom_de_famille(ind).strip()
        if nomf:
            patronymes[nomf] = patronymes.get(nomf, 0) + 1
        p1 = ((ind.get("prenom_principal") or "").strip()
              or (ind.get("prenoms") or "").strip().split(" ")[0])
        if p1:
            prenoms_freq[p1] = prenoms_freq.get(p1, 0) + 1
        an, ad = annee_naissance(ind), annee_deces(ind)
        if an:
            avec_naissance += 1
            par_siecle[(an // 100) + 1] = par_siecle.get((an // 100) + 1, 0) + 1
        if ad:
            avec_deces += 1
        if an and ad and 0 <= ad - an <= 120:
            longevites.append(ad - an)
        nl = (ind.get("naissance") or {}).get("lieu")
        if nl:
            avec_lieu_nais += 1
            lieux[nl] = lieux.get(nl, 0) + 1
        pere, mere = parents(donnees, pid)
        if pere:
            avec_pere += 1
        if mere:
            avec_mere += 1
        if pere or mere:
            avec_parent += 1
        if an and (pere or mere) and nl:
            complets += 1

    # Taille des fratries : une entrée par famille AYANT des enfants.
    fratries = [len(f.get("enfants") or []) for f in fams.values() if f.get("enfants")]

    # sources : combien de personnes portent au moins une citation
    avec_source = 0
    for ind in inds.values():
        cites = list(ind.get("citations") or [])
        cites += (ind.get("naissance") or {}).get("citations") or []
        cites += (ind.get("deces") or {}).get("citations") or []
        if cites:
            avec_source += 1

    pct = lambda n: round(n * 100 / total) if total else 0
    return {
        "personnes": total,
        "familles": len(fams),
        "sources": len(srcs),
        "sexes": sexes,
        "avec_naissance": avec_naissance,
        "avec_deces": avec_deces,
        "avec_lieu_naissance": avec_lieu_nais,
        "avec_pere": avec_pere,
        "avec_mere": avec_mere,
        "avec_source": avec_source,
        "completude": {
            "date_naissance": pct(avec_naissance),
            "au_moins_un_parent": pct(avec_parent),
            "lieu_naissance": pct(avec_lieu_nais),
            "source": pct(avec_source),
            "fiche_complete": pct(complets),
        },
        "age_median": _mediane(longevites),
        # Enfants par COUPLE (= par famille qui a des enfants). L'ancien calcul
        # comptait par PARENT : chaque enfant était compté deux fois (père + mère),
        # ce qui gonflait la moyenne affichée « enfants / couple ».
        "enfants_moyen": (round(sum(fratries) / len(fratries), 1) if fratries else 0),
        "par_siecle": [{"siecle": s, "n": par_siecle[s]} for s in sorted(par_siecle)],
        "lieux_frequents": sorted(
            [{"lieu": l, "n": n} for l, n in lieux.items()],
            key=lambda x: -x["n"])[:12],
        "patronymes_frequents": sorted(
            [{"valeur": v, "n": n} for v, n in patronymes.items()],
            key=lambda x: (-x["n"], x["valeur"].lower()))[:12],
        "prenoms_frequents": sorted(
            [{"valeur": v, "n": n} for v, n in prenoms_freq.items()],
            key=lambda x: (-x["n"], x["valeur"].lower()))[:12],
    }
