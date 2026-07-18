# -*- coding: utf-8 -*-
"""Correspondance des lieux À L'IMPORT (Palier 2, retour utilisateur Michel).

Avant de valider un import GEDCOM, on présente les lieux DISTINCTS du fichier
entrant, avec leur découpe hiérarchique et deux signalements : « sans pays » et
« doublon probable » (orthographes proches). L'utilisateur corrige (renommage,
ajout du pays par défaut), puis on applique ces corrections aux lieux du fichier
importé AVANT de l'intégrer.

Réutilise l'existant : `lieux._occurrences`, `lieux_ref` (types + pays),
`fusion_assistee._cle_lieu` (clé de regroupement des orthographes).

`analyser(donnees, pays_defaut)` -> dict d'aperçu.
`appliquer_corrections(donnees, {ancien: nouveau})` -> nb de champs réécrits.
"""

from services import lieux as lieux_svc
from services import lieux_ref
from services import fusion_assistee as fusion


def _a_un_pays(parts):
    return bool(parts) and parts[-1].strip().lower() in lieux_ref._PAYS


def analyser(donnees, pays_defaut=""):
    """Aperçu des lieux distincts du fichier importé, prêts à revoir."""
    occ = lieux_svc._occurrences(donnees)
    pays_defaut = (pays_defaut or "").strip()

    # doublons probables : on groupe par clé normalisée ; le plus fréquent = canonique.
    groupes = {}
    for nom in occ:
        groupes.setdefault(fusion._cle_lieu(nom), []).append(nom)
    canonique = {}
    for noms in groupes.values():
        if len(noms) > 1:
            principal = max(noms, key=lambda n: (occ[n]["nb"], n))
            for n in noms:
                if n != principal:
                    canonique[n] = principal

    out = []
    for nom, e in occ.items():
        parts = [p.strip() for p in (nom or "").split(",") if p.strip()]
        propre = ", ".join(parts)                 # version sans champs vides ni espaces
        parties_vides = propre != (nom or "").strip()
        sans_pays = not _a_un_pays(parts)
        # proposition pré-remplie, par priorité : pays manquant > doublon > nettoyage.
        if sans_pays and pays_defaut:
            propose = propre + ", " + pays_defaut
        elif nom in canonique:
            propose = canonique[nom]
        elif parties_vides:
            propose = propre
        else:
            propose = ""
        out.append({
            "nom": nom, "nb": e["nb"], "nb_personnes": len(e.get("personnes", [])),
            "parts": parts, "types": lieux_ref._types_pour(parts) if parts else [],
            "sans_pays": sans_pays, "doublon_de": canonique.get(nom),
            "parties_vides": parties_vides, "propose": propose,
        })
    out.sort(key=lambda x: (-x["nb"], x["nom"].lower()))
    return {"lieux": out, "nb": len(out),
            "nb_sans_pays": sum(1 for x in out if x["sans_pays"]),
            "nb_doublons": sum(1 for x in out if x["doublon_de"]),
            "nb_parties_vides": sum(1 for x in out if x["parties_vides"]),
            "pays_defaut": pays_defaut}


def appliquer_corrections(donnees, corrections):
    """Réécrit les lieux de `donnees` selon la carte {ancien: nouveau}. Met à jour
    le cache de coordonnées éventuel. Renvoie le nombre de champs réécrits."""
    corr = {}
    for a, b in (corrections or {}).items():
        a, b = (a or "").strip(), (b or "").strip()
        if a and b and a != b:
            corr[a] = b
    if not corr:
        return 0
    n = 0

    def maj(evt):
        nonlocal n
        if isinstance(evt, dict):
            l = (evt.get("lieu") or "").strip()
            if l in corr:
                evt["lieu"] = corr[l]; n += 1

    for ind in donnees.get("individus", {}).values():
        maj(ind.get("naissance")); maj(ind.get("deces"))
        for r in ind.get("residences") or []:
            maj(r)
        for e in ind.get("evenements") or []:
            maj(e)
    for fam in donnees.get("familles", {}).values():
        maj(fam.get("mariage"))
        for e in fam.get("evenements") or []:
            maj(e)
    # cache de coordonnées (rare à l'import, mais restons cohérents)
    cache = donnees.get("lieux")
    if isinstance(cache, dict):
        for a, b in corr.items():
            if a in cache:
                cache.setdefault(b, cache.pop(a))
    return n
