# -*- coding: utf-8 -*-
"""
Moteur de récit biographique (L10b).

Règle d'or héritée de `personnes.resume_de_vie` : chaque phrase est traçable à
une donnée de la base. On ne romance pas, on ne suppose pas. Une donnée absente
ne produit ni phrase ni « inconnu » : le récit se resserre (silence élégant).

Version J1 « récit riche » : naissance + filiation, professions + résidences,
unions + enfants, décès. Les personnes présumées vivantes peuvent être masquées
(livre destiné à circuler).
"""

from core import modele

MASQUE = "———"                     # nom d'une personne vivante masquée


def _nom(base, mini, masquer):
    """Nom d'une personne (mini {id, nom, sexe}), masqué si vivante et demandé."""
    if not mini:
        return ""
    if masquer:
        ind = base.donnees["individus"].get(mini.get("id"))
        if ind and modele.est_vivant_presume(ind):
            return MASQUE
    return mini.get("nom", "")


def _lieu(ev):
    return (ev or {}).get("lieu", "").strip()


def _de(mot):
    """« de » ou « d' » selon l'initiale (élision devant voyelle/h muet)."""
    return ("d'" if mot[:1].lower() in "aeiouyhàâéèêîïôûü" else "de ") + mot


def _evenement(verbe, an, lieu):
    """« né en 1872 à Lille », « né à Lille », « né en 1872 » ou ""."""
    bout = verbe
    if an:
        bout += " en %d" % an
    if lieu:
        bout += " à %s" % lieu
    return bout if (an or lieu) else ""


def biographie(base, f, masquer=True):
    """Renvoie une liste de paragraphes (chaînes) pour la personne dont `f` est
    la fiche (issue de personnes.fiche). Liste vide si rien à raconter."""
    ind = base.donnees["individus"].get(f["id"]) or {}
    sexe = ind.get("sexe", "U")
    ne = modele.genre(sexe, "né", "née")
    il = modele.genre(sexe, "il", "elle")
    dcd = modele.genre(sexe, "décédé", "décédée")
    nom = f.get("nom_complet", "")
    paras = []

    # ── 1. Naissance + filiation ──────────────────────────────────────
    naiss = ind.get("naissance") or {}
    bout = _evenement(ne, modele.annee_naissance(ind), _lieu(naiss))
    phrase = "%s voit le jour" % nom if not bout else "%s est %s" % (nom, bout)
    peres = [_nom(base, p, masquer) for p in f.get("peres", [])]
    meres = [_nom(base, m, masquer) for m in f.get("meres", [])]
    parents = [p for p in (peres + meres) if p]
    if parents:
        fils = modele.genre(sexe, "fils", "fille")
        phrase += ", %s de %s" % (fils, " et ".join(parents))
    fratrie = [x for x in (_nom(base, s, masquer) for s in f.get("fratrie", [])) if x]
    p1 = phrase + "."
    if fratrie:
        mot = "sœurs et frères" if len(fratrie) > 1 else "un aîné"
        p1 += " La famille compte %d enfant%s." % (len(fratrie) + 1,
                                                    "s" if fratrie else "")
    paras.append(p1)

    # ── 2. Professions + résidences ───────────────────────────────────
    profs = [p.get("valeur") for p in ind.get("professions", []) if p.get("valeur")]
    lieux_res = []
    for r in ind.get("residences", []):
        lr = _lieu(r)
        if lr and lr not in lieux_res:
            lieux_res.append(lr)
    bouts2 = []
    if profs:
        art = "les" if len(profs) > 1 else "le"
        met = "métiers" if len(profs) > 1 else "métier"
        bouts2.append("%s exerce %s %s %s" % (il, art, met, _de(", ".join(profs))))
    if lieux_res:
        bouts2.append("%s réside notamment à %s" % (il, ", ".join(lieux_res)))
    if bouts2:
        paras.append(". ".join(b[0].upper() + b[1:] for b in bouts2) + ".")

    # ── 3. Unions + enfants ───────────────────────────────────────────
    for i, u in enumerate(f.get("unions", [])):
        conj = _nom(base, u.get("conjoint"), masquer)
        mar = u.get("mariage") or {}
        an, lieu = None, _lieu(mar)
        if mar.get("date"):
            an = modele.annee_naissance({"naissance": mar})   # extrait l'année d'une date
        epouse = modele.genre(sexe, "épouse", "épouse")
        debut = "En %d, " % an if an else ""
        quand = "Plus tard, " if (i and not an) else debut
        if conj:
            ph = "%s%s %s %s" % (quand, il, epouse, conj)
            if lieu:
                ph += " à %s" % lieu
            ph += "."
        elif lieu or an:
            ph = "%s%s se marie%s." % (quand, il, (" à %s" % lieu) if lieu else "")
        else:
            ph = ""
        enfants = [x for x in (_nom(base, e, masquer) for e in u.get("enfants", [])) if x]
        if enfants:
            if len(enfants) == 1:
                ph += " De cette union naît %s." % enfants[0]
            else:
                ph += " De cette union naissent %d enfants : %s." % (
                    len(enfants), ", ".join(enfants))
        p = ph.strip()
        if p:
            paras.append(p[0].upper() + p[1:])   # phrase d'union toujours capitalisée

    # ── 4. Décès ──────────────────────────────────────────────────────
    dec = ind.get("deces") or {}
    bout4 = _evenement(dcd, modele.annee_deces(ind), _lieu(dec))
    if bout4:
        age = modele.age(ind)
        ph = "%s s'éteint%s" % (nom, bout4[len(dcd):])   # « en 1945 à Nantes »
        if isinstance(age, int):
            ph += ", à l'âge de %d ans" % age
        paras.append(ph + ".")

    return paras
