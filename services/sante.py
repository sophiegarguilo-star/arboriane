# -*- coding: utf-8 -*-
"""
Santé de l'arbre — la solidité DOCUMENTAIRE des données (pas la cohérence
généalogique, qui est ailleurs). Ton encourageant : on montre le chemin
parcouru et la prochaine action utile, jamais on ne culpabilise.
"""

from core import modele
from core.modele import nom_complet, periode
from services import sources as src_svc


def analyser(donnees):
    inds = donnees["individus"]
    fams = donnees["familles"]
    srcs = donnees.get("sources", {})

    # usage des sources + personnes sans aucune source
    usage = {sid: 0 for sid in srcs}
    sans_source = []
    for pid, ind in inds.items():
        cites = list(ind.get("citations") or [])
        cites += (ind.get("naissance") or {}).get("citations") or []
        cites += (ind.get("deces") or {}).get("citations") or []
        for ev in ind.get("evenements", []):
            cites += ev.get("citations") or []
        for fid in ind.get("fams", []):
            cites += ((fams.get(fid) or {}).get("mariage") or {}).get("citations") or []
        for c in cites:
            if c.get("source") in usage:
                usage[c["source"]] += 1
        if not cites:
            sans_source.append({"id": pid, "nom": nom_complet(ind),
                                "periode": periode(ind)})
    sans_source.sort(key=lambda x: x["nom"].lower())

    sources_sans_scan = [{"id": s["id"], "titre": s.get("titre") or s["id"]}
                         for s in srcs.values()
                         if not (s.get("fichiers") or s.get("fichier"))]
    sources_inutiles = [{"id": sid, "titre": srcs[sid].get("titre") or sid}
                        for sid, n in usage.items() if n == 0]

    # % de faits vitaux prouvés par acte
    tot = acte = 0
    for pid in inds:
        pv = src_svc.preuves_personne(donnees, pid)
        for f in pv["faits"]:
            if not f["present"]:
                continue
            tot += 1
            if f["niveau"] == "acte":
                acte += 1

    pistes = sum(1 for ind in inds.values()
                 for p in ind.get("pistes", []) if not (isinstance(p, dict) and p.get("faite")))

    pct = round(acte * 100 / tot) if tot else 0
    # message encourageant, adapté au niveau atteint
    if not inds:
        humeur = "Votre arbre est encore vide — c'est le bon moment pour commencer."
    elif pct >= 66:
        humeur = "Bel arbre, solidement sourcé. Continuez sur cette lancée !"
    elif pct >= 33:
        humeur = "Bon début : une bonne partie de vos faits est déjà prouvée."
    else:
        humeur = "Chaque source ajoutée renforce votre arbre. Une preuve à la fois."

    return {
        "nb_personnes": len(inds),
        "nb_sources": len(srcs),
        "pct_prouves": pct, "faits_actes": acte, "faits_total": tot,
        "humeur": humeur,
        "personnes_sans_source": sans_source[:200],
        "nb_personnes_sans_source": len(sans_source),
        "sources_sans_scan": sources_sans_scan,
        "sources_inutiles": sources_inutiles,
        "pistes_ouvertes": pistes,
    }
