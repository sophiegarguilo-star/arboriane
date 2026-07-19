# -*- coding: utf-8 -*-
"""
Cohérence — détection d'anomalies généalogiques, claires et actionnables.

Chaque alerte porte : un type, une gravité (haute/moyenne/basse), la personne
concernée (cliquable vers sa fiche) et un message explicite. On reste prudent :
mieux vaut ne rien signaler qu'inventer une fausse alerte.
"""

import datetime
import re

from core import modele
from core.modele import (annee_naissance, annee_deces, parents, enfants,
                         conjoints, nom_complet)

AGE_MIN_PARENT = 13          # âge minimal plausible pour avoir un enfant
AGE_MAX_MERE = 55
AGE_MAX_PERE = 75


def _annee_brute(date_str):
    """Année lue DANS LA CHAÎNE BRUTE, sans le filtre 1000-2200 de
    modele.annee() (qui rend l'alerte « date impossible » inatteignable).
    Comme modele.annee, on retient le DERNIER nombre de 3 chiffres ou plus
    (les dates finissent par l'année ; un numéro d'acte est en début de
    chaîne). Renvoie un int ou None."""
    if not date_str:
        return None
    nombres = re.findall(r"\d{3,}", str(date_str))
    return int(nombres[-1]) if nombres else None


def _parents_ids(donnees, pid):
    """Ids des parents de pid (toutes les familles famc), existants en base."""
    inds = donnees["individus"]
    res = []
    for fid in (inds.get(pid) or {}).get("famc", []) or []:
        fam = (donnees["familles"].get(fid) or {})
        for role in ("mari", "epouse"):
            q = fam.get(role)
            if q and q in inds and q not in res:
                res.append(q)
    return res


def _cycles_filiation(donnees):
    """Cycles de filiation (X ancêtre de lui-même) : parcours famc itératif
    avec ensemble de visite (coloration en-cours/fini). Renvoie une liste de
    cycles, chacun = liste ordonnée d'ids (chaque cycle signalé une fois)."""
    inds = donnees["individus"]
    etat = {}                      # pid -> "encours" | "fini"
    cycles, vus = [], set()
    for depart in inds:
        if etat.get(depart) == "fini":
            continue
        etat[depart] = "encours"
        chemin = [depart]
        pile = [(depart, iter(_parents_ids(donnees, depart)))]
        while pile:
            pid, it = pile[-1]
            avance = False
            for par in it:
                if etat.get(par) == "encours":
                    cyc = chemin[chemin.index(par):]      # le cycle lui-même
                    cle = frozenset(cyc)
                    if cle not in vus:
                        vus.add(cle)
                        cycles.append(list(cyc))
                elif etat.get(par) != "fini":
                    etat[par] = "encours"
                    chemin.append(par)
                    pile.append((par, iter(_parents_ids(donnees, par))))
                    avance = True
                    break
            if not avance:
                pile.pop()
                chemin.pop()
                etat[pid] = "fini"
    return cycles


def _alerte(type_, gravite, categorie, pid, nom, message):
    return {"type": type_, "gravite": gravite, "categorie": categorie,
            "personne": pid, "personne_nom": nom, "message": message}


def analyser(donnees, racine_id=None):
    from services import personnes as personnes_svc   # import local : évite un cycle
    inds = donnees["individus"]
    fams = donnees["familles"]
    alertes = []
    # Personnes hors famille (officiers d'état civil, témoins… cités sans lien de
    # parenté) : on ne les signale pas comme « isolées » — leur absence de lien
    # est voulue, pas une anomalie.
    hors_famille = personnes_svc.ids_hors_famille(donnees, racine_id)

    for pid, ind in inds.items():
        nom = nom_complet(ind)
        an = annee_naissance(ind)
        ad = annee_deces(ind)

        # dates impossibles — analyse de la CHAÎNE BRUTE : modele.annee()
        # filtre déjà 1000-2200, donc an/ad ne peuvent jamais être aberrants ;
        # on relit le texte saisi pour attraper « 987 » ou « 3054 ».
        annee_max = datetime.date.today().year + 1
        for etiquette, evt in (("naissance", ind.get("naissance")),
                               ("décès", ind.get("deces"))):
            brut = _annee_brute((evt or {}).get("date"))
            if brut is not None and not (1000 <= brut <= annee_max):
                alertes.append(_alerte("date_impossible", "haute", "Dates", pid, nom,
                    "Année de %s hors plage plausible (%s)." % (etiquette, brut)))

        # décès avant naissance
        if an and ad and ad < an:
            alertes.append(_alerte("deces_avant_naissance", "haute", "Dates", pid, nom,
                "Décès (%d) antérieur à la naissance (%d)." % (ad, an)))

        # longévité invraisemblable
        if an and ad and ad - an > 115:
            alertes.append(_alerte("longevite", "moyenne", "Dates", pid, nom,
                "Longévité de %d ans — à vérifier." % (ad - an)))

        # parent trop jeune / trop âgé à la naissance d'un enfant
        for enf in enfants(donnees, pid):
            ae = annee_naissance(inds.get(enf, {}))
            if an and ae:
                ecart = ae - an
                if ecart < AGE_MIN_PARENT:
                    alertes.append(_alerte("parent_jeune", "haute", "Filiation", pid, nom,
                        "Aurait eu un enfant à %d ans (%s)." % (ecart,
                         nom_complet(inds.get(enf, {})))))
                elif ind.get("sexe") == "F" and ecart > AGE_MAX_MERE:
                    alertes.append(_alerte("mere_agee", "moyenne", "Filiation", pid, nom,
                        "Mère à %d ans (%s) — à vérifier." % (ecart,
                         nom_complet(inds.get(enf, {})))))
                elif ind.get("sexe") == "M" and ecart > AGE_MAX_PERE:
                    alertes.append(_alerte("pere_age", "basse", "Filiation", pid, nom,
                        "Père à %d ans (%s) — à vérifier." % (ecart,
                         nom_complet(inds.get(enf, {})))))
            # enfant né APRÈS le décès du parent : impossible pour une mère,
            # tolérance d'un an pour un père (enfant posthume).
            if ad and ae and ind.get("sexe") == "F" and ae > ad:
                alertes.append(_alerte("enfant_apres_deces_mere", "haute",
                    "Filiation", pid, nom,
                    "Enfant (%s) né en %d, après le décès de sa mère (%d)." % (
                     nom_complet(inds.get(enf, {})), ae, ad)))
            elif ad and ae and ind.get("sexe") == "M" and ae > ad + 1:
                alertes.append(_alerte("enfant_apres_deces_pere", "haute",
                    "Filiation", pid, nom,
                    "Enfant (%s) né en %d, plus d'un an après le décès de son "
                    "père (%d)." % (nom_complet(inds.get(enf, {})), ae, ad)))

        # mariage hors de la vie
        for _conj, fid in conjoints(donnees, pid):
            mar = (fams.get(fid) or {}).get("mariage") or {}
            am = modele.annee(mar.get("date"))
            if am and an and am < an:
                alertes.append(_alerte("mariage_avant_naissance", "haute", "Union", pid, nom,
                    "Mariage (%d) avant la naissance (%d)." % (am, an)))
            elif am and ad and am > ad + 1:
                alertes.append(_alerte("mariage_apres_deces", "moyenne", "Union", pid, nom,
                    "Mariage (%d) après le décès (%d)." % (am, ad)))

        # présumé·e vivant·e mais trop âgé·e (aucune date de décès, mais des
        # indices — enfant, union, événement — situent un grand âge)
        if modele.est_vivant_presume(ind):
            am = modele.age_minimal(donnees, pid, ind)
            if am is not None and am >= 105:
                alertes.append(_alerte("vivant_improbable", "moyenne", "Statut de vie",
                    pid, nom, "Présumé·e vivant·e mais âgé·e d'au moins %d ans "
                    "(aucune date de décès)." % am))

        # personne isolée (aucun lien) — sauf si elle est « hors famille » (officier,
        # témoin…), auquel cas l'absence de lien est normale.
        if not ind.get("famc") and not ind.get("fams") and pid not in hors_famille:
            alertes.append(_alerte("isolee", "basse", "Structure", pid, nom,
                "Personne sans aucun lien familial."))

        # liens cassés
        for fid in ind.get("famc", []) + ind.get("fams", []):
            if fid not in fams:
                alertes.append(_alerte("lien_casse", "haute", "Structure", pid, nom,
                    "Référence vers une famille inexistante (%s)." % fid))

    # cycles de filiation : X ancêtre de lui-même (base corrompue ou lien faux)
    for cyc in _cycles_filiation(donnees):
        noms = " → ".join(nom_complet(inds.get(p, {})) for p in cyc)
        a = _alerte("cycle_filiation", "haute", "Structure", cyc[0],
                    nom_complet(inds.get(cyc[0], {})),
                    "Cycle de filiation : %s — chacune de ces personnes est "
                    "son propre ancêtre." % noms)
        a["personnes"] = list(cyc)
        alertes.append(a)

    # doublons probables : même nom complet + années de naissance proches
    par_cle = {}
    for pid, ind in inds.items():
        an = annee_naissance(ind)
        cle = (nom_complet(ind).lower(), (an // 5) if an else None)
        if cle[0] and cle[0] != "(sans nom)":
            par_cle.setdefault(cle, []).append(pid)
    for (nomcle, _), ids in par_cle.items():
        if len(ids) > 1:
            for pid in ids:
                alertes.append(_alerte("doublon", "moyenne", "Doublons", pid,
                    nom_complet(inds[pid]),
                    "Doublon possible : %d personnes très semblables." % len(ids)))

    ordre = {"haute": 0, "moyenne": 1, "basse": 2}
    alertes.sort(key=lambda a: (ordre[a["gravite"]], a["categorie"]))

    parc = {}
    for a in alertes:
        parc[a["categorie"]] = parc.get(a["categorie"], 0) + 1
    return {
        "total": len(alertes),
        "par_gravite": {g: sum(1 for a in alertes if a["gravite"] == g)
                        for g in ("haute", "moyenne", "basse")},
        "par_categorie": parc,
        "alertes": alertes,
    }
