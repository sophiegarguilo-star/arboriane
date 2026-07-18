# -*- coding: utf-8 -*-
"""Livret d'ascendance COMPLÈTE (Palier D) — un chapitre par COUPLE, regroupé en
parties par génération, de la personne de référence jusqu'aux aïeux.

Unité de chapitre = le couple (Sosa pair « père » + Sosa impair « mère ») : on
raconte l'histoire du couple ensemble puis on renvoie à leur enfant dans la
lignée. S'appuie sur services.sosa (parcours) et services.livre.recit (récit
d'une personne, jamais inventé). Les vivants peuvent être masqués.

`chapitres(base, referent, generations, masquer)` -> liste de parties :
  [{ generation, titre, chapitres: [{num, sosa, titre, paras, renvoi}] }]
"""

from core import modele
from services import sosa as sosa_svc
from services.livre import recit, ascendance as asc_notice

MASQUE = "———"
_LABELS = {0: "La personne de référence", 1: "Les parents",
           2: "Les grands-parents", 3: "Les arrière-grands-parents",
           4: "Les trisaïeuls", 5: "Les quadrisaïeuls",
           6: "Les quintaïeuls", 7: "Les sextaïeuls"}


def _label_gen(g):
    return _LABELS.get(g, "%dᵉ génération" % g)


def _gen_de(sosa):
    """Génération (0 = de-cujus) d'un numéro Sosa."""
    g = 0
    while (1 << (g + 1)) <= sosa:
        g += 1
    return g


def chapitres(base, referent, generations=4, masquer=True):
    donnees = base.donnees
    inds = donnees["individus"]
    generations = max(1, min(8, int(generations)))
    asc = sosa_svc.ascendance(donnees, referent, generations + 1)
    if not asc:
        return []

    par_sosa = {}                       # sosa -> {sosa,id,nom,periode,sexe}
    for gen in asc["generations"]:
        for p in gen["personnes"]:
            par_sosa[p["sosa"]] = p

    def masque(entry):
        return masquer and modele.est_vivant_presume(inds.get(entry["id"], {}))

    def nom(entry):
        return MASQUE if masque(entry) else entry["nom"]

    def paras_de(pid):
        from services import personnes
        try:
            f = personnes.fiche(base, pid)
        except Exception:               # noqa: BLE001 — fiche illisible : on saute
            return []
        return recit.biographie(base, f, masquer) if f else []

    # Numéro de chapitre dans l'ordre de lecture. Clé : 1 (référent) ou le Sosa
    # PAIR du couple. Sert aux renvois croisés « voir chapitre N ».
    num_par_cle, compteur = {}, [0]

    def cle_couple(sosa):
        return 1 if sosa == 1 else sosa - (sosa % 2)

    def prochain(cle):
        compteur[0] += 1
        num_par_cle[cle] = compteur[0]
        return compteur[0]

    parties = []
    for g in range(0, generations + 1):
        entrees = sorted((par_sosa[s] for s in par_sosa if _gen_de(s) == g),
                         key=lambda e: e["sosa"])
        if not entrees:
            continue
        chaps = []
        if g == 0:
            e = entrees[0]
            num = prochain(1)
            renvoi = ("Ses parents ouvrent le chapitre suivant."
                      if (par_sosa.get(2) or par_sosa.get(3)) else "")
            chaps.append({"num": num, "sosa": str(e["sosa"]), "titre": nom(e),
                          "paras": paras_de(e["id"]), "renvoi": renvoi})
        else:
            for pere_s in sorted({cle_couple(e["sosa"]) for e in entrees}):
                pere, mere = par_sosa.get(pere_s), par_sosa.get(pere_s + 1)
                if not pere and not mere:
                    continue
                num = prochain(pere_s)
                titre = " & ".join(x for x in
                                   [nom(pere) if pere else "", nom(mere) if mere else ""] if x)
                paras = []
                if pere:
                    paras += paras_de(pere["id"])
                    if mere and not masque(mere):
                        note = asc_notice._notice(inds.get(mere["id"], {}))
                        if note:
                            paras.append("%s, son épouse. %s" % (nom(mere), note))
                elif mere:
                    paras += paras_de(mere["id"])
                # Renvoi vers l'enfant dans la lignée (Sosa pere_s // 2).
                enf = par_sosa.get(pere_s // 2)
                renvoi = ""
                if enf:
                    ch = num_par_cle.get(cle_couple(pere_s // 2))
                    renvoi = ("Leur descendance directe : %s%s." %
                              (nom(enf), (" (chapitre %d)" % ch) if ch else ""))
                famille = _famille(donnees, inds, pere, mere, par_sosa, pere_s,
                                   nom, masque)
                chaps.append({"num": num, "sosa": _sosa_couple(pere, mere),
                              "titre": titre or "Ancêtres", "paras": paras,
                              "renvoi": renvoi, "famille": famille})
        if chaps:
            parties.append({"generation": g, "titre": _label_gen(g), "chapitres": chaps})
    return parties


def _sosa_couple(pere, mere):
    if pere and mere:
        return "%d–%d" % (pere["sosa"], mere["sosa"])
    return str((pere or mere)["sosa"])


def _periode(ind):
    an, ad = modele.annee_naissance(ind), modele.annee_deces(ind)
    if an and ad:
        return "%d–%d" % (an, ad)
    if an:
        return "°%d" % an            # ° = naissance (convention généalogique)
    if ad:
        return "†%d" % ad            # † = décès
    return ""


def _pers(inds, entry, nom_fn, masque_fn):
    """Petit descripteur {nom, periode} d'une personne (masquée si vivante)."""
    if not entry:
        return None
    if masque_fn(entry):
        return {"nom": MASQUE, "periode": ""}
    return {"nom": nom_fn(entry), "periode": _periode(inds.get(entry["id"], {}))}


def _famille(donnees, inds, pere, mere, par_sosa, pere_s, nom_fn, masque_fn):
    """Fiche familiale d'un couple : {pere, mere, mariage, enfants, aieux}.
    - enfants : tous les enfants de l'union (nom + période) ;
    - aieux   : les 4 grands-parents (pour le mini-arbre) : pp, pm, mp, mm."""
    fams = None
    pid = pere["id"] if pere else None
    mid = mere["id"] if mere else None
    for f in donnees.get("familles", {}).values():
        if (pid and f.get("mari") == pid) or (mid and f.get("epouse") == mid):
            if (not pid or f.get("mari") == pid) and (not mid or f.get("epouse") == mid):
                fams = f
                break
    mariage = (fams or {}).get("mariage") or {}
    enfants = []
    for cid in (fams or {}).get("enfants", []):
        ci = inds.get(cid)
        if ci:
            masc = masque_fn({"id": cid})
            enfants.append({"nom": MASQUE if masc else modele.nom_complet(ci),
                            "periode": "" if masc else _periode(ci)})
    aieux = {
        "pp": _pers(inds, par_sosa.get(pere_s * 2), nom_fn, masque_fn),
        "pm": _pers(inds, par_sosa.get(pere_s * 2 + 1), nom_fn, masque_fn),
        "mp": _pers(inds, par_sosa.get((pere_s + 1) * 2), nom_fn, masque_fn),
        "mm": _pers(inds, par_sosa.get((pere_s + 1) * 2 + 1), nom_fn, masque_fn),
    }
    return {
        "pere": _pers(inds, pere, nom_fn, masque_fn),
        "mere": _pers(inds, mere, nom_fn, masque_fn),
        "mariage": {"date": (mariage.get("date") or "").strip(),
                    "lieu": (mariage.get("lieu") or "").strip()},
        "enfants": enfants,
        "aieux": aieux,
    }
