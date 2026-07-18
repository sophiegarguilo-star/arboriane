# -*- coding: utf-8 -*-
"""
Parenté — lien entre deux personnes, en vocabulaire généalogique précis.

Deux voies :
- `parente()` : lien du sang via l'ancêtre commun le plus proche (aïeul,
  bisaïeul, cousin germain, cousin issu de germain, éloigné au Nᵉ degré…) ;
- `parente_alliance()` : lien par mariage quand il n'y a pas d'ancêtre commun
  (époux, gendre/belle-fille, beau-frère/belle-sœur, beau-parent, bel-enfant).

Le libellé décrit B PAR RAPPORT À A (« B est <lien> de A »), accordé au sexe
de B. C'est l'un des points où Arboriane vise mieux que les outils courants.
"""

from collections import deque

from core import modele
from core.modele import (parents, conjoints, enfants, freres_soeurs,
                         genre, ordinal, nom_complet, nom_court)

# Vocabulaire des ascendants directs, par génération (aligné sur services.sosa).
# gen 3 = arrière-grand-parent (= bisaïeul) ; gen 4 = trisaïeul ; etc.
_AIEUX = {1: ("le père", "la mère"),
          2: ("le grand-père", "la grand-mère"),
          3: ("l'arrière-grand-père", "l'arrière-grand-mère"),
          4: ("le trisaïeul", "la trisaïeule"),
          5: ("le quadrisaïeul", "la quadrisaïeule"),
          6: ("le quintaïeul", "la quintaïeule"),
          7: ("le sextaïeul", "la sextaïeule"),
          8: ("le septaïeul", "la septaïeule"),
          9: ("l'octaïeul", "l'octaïeule"),
          10: ("le nonaïeul", "la nonaïeule"),
          11: ("le décaïeul", "la décaïeule")}


def _libelle_lien(da, db, sexe_b):
    """(distance A→ancêtre, distance B→ancêtre) → lien de B vis-à-vis de A."""
    f = lambda m, fem: genre(sexe_b, m, fem)
    if da == 0 and db == 0:
        return "la même personne"

    if db == 0:                          # B ascendant direct de A
        if da in _AIEUX:
            return f(*_AIEUX[da])
        return f("l'aïeul", "l'aïeule") + " à la %de génération" % da

    if da == 0:                          # B descendant direct de A
        base = {1: ("le fils", "la fille"), 2: ("le petit-fils", "la petite-fille"),
                3: ("l'arrière-petit-fils", "l'arrière-petite-fille")}
        if db in base:
            return f(*base[db])
        return f("le %d fois arrière-petit-fils" % (db - 2),
                 "la %d fois arrière-petite-fille" % (db - 2))

    if da == 1 and db == 1:
        return f("le frère", "la sœur")

    if db == 1:                          # oncle / grand-oncle…
        if da == 2:
            return f("l'oncle", "la tante")
        if da == 3:
            return f("le grand-oncle", "la grand-tante")
        if da == 4:
            return f("l'arrière-grand-oncle", "l'arrière-grand-tante")
        return f("le %d fois arrière-grand-oncle" % (da - 3),
                 "la %d fois arrière-grand-tante" % (da - 3))

    if da == 1:                          # neveu / petit-neveu…
        if db == 2:
            return f("le neveu", "la nièce")
        if db == 3:
            return f("le petit-neveu", "la petite-nièce")
        if db == 4:
            return f("l'arrière-petit-neveu", "l'arrière-petite-nièce")
        return f("le %d fois arrière-petit-neveu" % (db - 3),
                 "la %d fois arrière-petite-nièce" % (db - 3))

    # cousins : type par la plus courte distance, éloignement par l'écart
    proche, ecart = min(da, db), abs(da - db)
    socle = {2: ("cousin germain", "cousine germaine"),
             3: ("cousin issu de germain", "cousine issue de germain"),
             4: ("petit cousin", "petite cousine"),
             5: ("arrière-petit cousin", "arrière-petite cousine")}
    if proche in socle:
        masc, fem = socle[proche]
    else:
        masc = "%d fois arrière-petit cousin" % (proche - 4)
        fem = "%d fois arrière-petite cousine" % (proche - 4)
    if ecart:
        masc += " éloigné au %s degré" % ordinal(ecart)
        fem += " éloignée au %s degré" % ordinal(ecart)
    return f("le " + masc, "la " + fem)


def _ancetres_distance(donnees, ident):
    """{ ancetre_id: distance en générations } (0 = soi-même), via BFS."""
    dist = {ident: 0}
    file = deque([ident])
    while file:
        pid = file.popleft()
        for par in parents(donnees, pid):
            if par and par not in dist:
                dist[par] = dist[pid] + 1
                file.append(par)
    return dist


def _chemin_ascendant(donnees, depart, cible):
    """Plus court chemin ascendant [depart, …, cible] via les parents, ou None."""
    vient_de = {depart: None}
    file = deque([depart])
    while file:
        pid = file.popleft()
        if pid == cible:
            break
        for par in parents(donnees, pid):
            if par and par not in vient_de:
                vient_de[par] = pid
                file.append(par)
    if cible not in vient_de:
        return None
    chemin, cur = [], cible
    while cur is not None:
        chemin.append(cur)
        cur = vient_de[cur]
    chemin.reverse()
    return chemin


def _chaine_cartes(donnees, chemin):
    """Fiches d'une lignée [personne … ancêtre] avec Sosa relatif au bas."""
    cartes, sosa = [], 1
    for i, pid in enumerate(chemin):
        c = modele.carte_perso(donnees, pid)
        c["sosa"] = sosa
        cartes.append(c)
        if i + 1 < len(chemin):
            pere, _mere = parents(donnees, pid)
            sosa = sosa * 2 + (0 if chemin[i + 1] == pere else 1)
    return cartes


def parente(donnees, id_a, id_b):
    """Lien du sang : ancêtre commun le plus proche + libellé + filiation."""
    if id_a not in donnees["individus"] or id_b not in donnees["individus"]:
        return None
    anc_a = _ancetres_distance(donnees, id_a)
    anc_b = _ancetres_distance(donnees, id_b)
    communs = set(anc_a) & set(anc_b)
    if not communs:
        return None
    meilleur = min(communs, key=lambda x: anc_a[x] + anc_b[x])
    da, db = anc_a[meilleur], anc_b[meilleur]
    ind_b = donnees["individus"].get(id_b, {})
    ch_a = _chemin_ascendant(donnees, id_a, meilleur) or [id_a, meilleur]
    ch_b = _chemin_ascendant(donnees, id_b, meilleur) or [id_b, meilleur]

    def _g(n):
        return "%d génération%s" % (n, "s" if n > 1 else "")
    if db == 0:
        precision = "%s en ligne directe" % _g(da)
    elif da == 0:
        precision = "%s en ligne directe" % _g(db)
    elif da == db:
        precision = "ancêtre commun à %s de chacun" % _g(da)
    else:
        precision = "ancêtre commun à %s d'un côté, %s de l'autre" % (_g(da), _g(db))

    return {
        "lien": _libelle_lien(da, db, ind_b.get("sexe", "U")),
        "precision": precision,
        "ancetre_commun": meilleur,
        "ancetre_commun_nom": nom_complet(donnees["individus"].get(meilleur, {})),
        "distance_a": da, "distance_b": db,
        "chaine_a": _chaine_cartes(donnees, ch_a),
        "chaine_b": _chaine_cartes(donnees, ch_b),
    }


def parente_alliance(donnees, id_a, id_b):
    """Lien par alliance (mariage), quand aucun ancêtre commun. B vis-à-vis de A."""
    if id_a == id_b or id_b not in donnees["individus"]:
        return None
    sb = donnees["individus"].get(id_b, {}).get("sexe", "U")
    g = lambda m, f: genre(sb, m, f)
    nom = lambda pid: nom_court(donnees["individus"].get(pid, {}))
    conj = lambda pid: [c for c, _ in conjoints(donnees, pid) if c]
    mariage = lambda x, y: "Reliés par le mariage de %s et %s." % (nom(x), nom(y))
    conj_a = conj(id_a)

    if id_b in conj_a:
        return {"lien": g("l'époux", "l'épouse"), "alliance": True,
                "explication": "Ils sont mariés."}
    for ea in enfants(donnees, id_a):
        if id_b in conj(ea):
            return {"lien": g("le gendre", "la belle-fille"), "alliance": True,
                    "explication": mariage(ea, id_b)}
    for s in freres_soeurs(donnees, id_a):
        if id_b in conj(s):
            return {"lien": g("le beau-frère", "la belle-sœur"), "alliance": True,
                    "explication": mariage(s, id_b)}
    for sa in conj_a:
        if id_b in freres_soeurs(donnees, sa):
            return {"lien": g("le beau-frère", "la belle-sœur"), "alliance": True,
                    "explication": mariage(id_a, sa)}
    for sa in conj_a:
        if id_b in parents(donnees, sa):
            return {"lien": g("le beau-père", "la belle-mère"), "alliance": True,
                    "explication": mariage(id_a, sa)}
    for p in parents(donnees, id_a):
        if p and id_b in conj(p):
            return {"lien": g("le beau-père", "la belle-mère"), "alliance": True,
                    "explication": mariage(p, id_b)}
    enf_a = set(enfants(donnees, id_a))
    for sa in conj_a:
        if id_b in enfants(donnees, sa) and id_b not in enf_a:
            return {"lien": g("le beau-fils", "la belle-fille"), "alliance": True,
                    "explication": mariage(id_a, sa)}
    return None


def lien_complet(donnees, id_a, id_b):
    """Essaie le sang, puis l'alliance. Renvoie un dict {type, …} ou None."""
    p = parente(donnees, id_a, id_b)
    if p:
        p["type"] = "sang"
        return p
    a = parente_alliance(donnees, id_a, id_b)
    if a:
        a["type"] = "alliance"
        return a
    return None
