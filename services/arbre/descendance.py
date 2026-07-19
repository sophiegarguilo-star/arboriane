# -*- coding: utf-8 -*-
"""Arbre — rendu « descendance » en cases avec conjoints."""

import math

from core import modele

from services.arbre.base import *

def _descendance(donnees, ident, generations, o):
    """Rendu de la descendance en cartes avec les conjoints. Voir :func:`rendre`."""
    racine = _descendance_couples(donnees, ident, generations)
    if not racine:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"></svg>'

    inds = donnees["individus"]
    k = max(70, min(140, int(o.get("taille", 100) or 100))) / 100.0
    police = ("Georgia, 'Times New Roman', serif" if o.get("police") == "serif"
              else "system-ui, 'Segoe UI', sans-serif")
    montre_dates = bool(o["dates"])
    montre_lieux = bool(o["lieux"])
    n_extra = (1 if montre_dates else 0) + (1 if montre_lieux else 0)
    mode_pastille = o.get("pastille", "monogramme")
    avec_pastille = mode_pastille != "aucune"
    avec_photo = mode_pastille == "photo"
    avec_preuves = bool(o.get("preuves"))
    avec_legende = avec_preuves and bool(o.get("legende", True))
    av_r_u = max(10.0, min(15.0, (26 + 15 * n_extra) / 2.0 - 3)) if avec_pastille else 0.0
    av_r = av_r_u * k
    tx0_u = (14 + 2 * av_r_u) if avec_pastille else 11
    card_w = (188 if avec_pastille else 158) * k
    card_h = (26 + 15 * n_extra) * k
    horizontal = o.get("sens") == "horizontal"

    if horizontal:
        cross_card, depth_card, couple_link = card_h, card_w, 14 * k
    else:
        cross_card, depth_card, couple_link = card_w, card_h, 22 * k
    level_gap = depth_card + 64 * k
    sib_gap = 30 * k

    def enfants_de(n):
        return [c for u in n["unions"] for c in u["enfants"]]

    def conjoints_de(n):
        # Descendance : on n'affiche le conjoint que si l'union a une descendance.
        # Une union sans enfant (PACS, mariage sans enfant) n'appartient pas à une
        # descendance ; alignée à côté des autres conjoints, elle donnait de plus
        # une fausse « chaîne » d'époux reliés entre eux.
        return [u["conjoint_id"] for u in n["unions"] if u["conjoint_id"] and u["enfants"]]

    def couple_cross(n):
        ns = len(conjoints_de(n))
        return cross_card * (1 + ns) + couple_link * ns

    def largeur(n):
        kids = enfants_de(n)
        cw = couple_cross(n)
        n["_w"] = cw if not kids else max(cw, sum(largeur(k2) for k2 in kids)
                                          + sib_gap * (len(kids) - 1))
        return n["_w"]
    largeur(racine)

    pos = {}          # id du nœud -> (cross0_couple, depth_pos)
    etat = {"maxd": 0}

    def assigner(n, cross0, depth):
        etat["maxd"] = max(etat["maxd"], depth)
        cc = cross0 + (n["_w"] - couple_cross(n)) / 2.0
        pos[n["id"]] = (cc, depth * level_gap)
        kids = enfants_de(n)
        if kids:
            total = sum(x["_w"] for x in kids) + sib_gap * (len(kids) - 1)
            c = cross0 + (n["_w"] - total) / 2.0
            for kid in kids:
                assigner(kid, c, depth + 1)
                c += kid["_w"] + sib_gap
    assigner(racine, 0, 0)

    cross_total = racine["_w"]
    depth_total = (etat["maxd"] + 1) * level_gap
    largeur_svg = (depth_total if horizontal else cross_total) + 20
    hauteur_svg = (cross_total if horizontal else depth_total) + 20

    def mapp(cross, depth):
        return (depth + 10, cross + 10) if horizontal else (cross + 10, depth + 10)

    tfs = 24 * k
    bandeau = int(tfs + 12 * k) if o["titre"] else 0
    total_w = largeur_svg
    total_h = hauteur_svg + bandeau
    forme = o.get("trait_forme", "courbe")
    ep = float(o.get("trait_epaisseur") or 0) or 1.0
    col_lien = (o.get("trait_couleur") or "").strip() or BORDURE

    leg_h = int(38 * k) if avec_legende else 0
    total_h = total_h + leg_h
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" '
             'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 %d %d" '
             'class="arbre-svg" font-family="%s">' % (total_w, total_h, police)]
    if o["titre"]:
        parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                     'font-weight="700" fill="%s">%s</text>'
                     % (total_w / 2, tfs + 10 * k, tfs, TEXTE, _echap(o["titre"])))
    parts.append('<g transform="translate(0,%d)">' % bandeau)

    # aplatir + tracer
    ordre = []
    branche_de = {}          # id -> index de branche (lignée) pour le thème « branche »

    def collect(n, br):
        ordre.append(n)
        branche_de[n["id"]] = br
        for i, kid in enumerate(enfants_de(n)):
            collect(kid, i if n is racine else br)   # chaque enfant de la racine ouvre une branche
    collect(racine, -1)

    # traits parent (centre du couple) -> chaque enfant (centre de son couple)
    for n in ordre:
        cc, dp = pos[n["id"]]
        p_cross = cc + couple_cross(n) / 2.0
        p_depth = dp + depth_card
        for kid in enfants_de(n):
            kcc, kdp = pos[kid["id"]]
            # arrivée sur la CARTE de l'enfant (1re du couple), pas au centre du couple
            c_cross = kcc + cross_card / 2.0
            x0, y0 = mapp(p_cross, p_depth)
            x1, y1 = mapp(c_cross, kdp)
            parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="%g"/>'
                         % (_lien_path(x0, y0, x1, y1, forme, not horizontal), col_lien, ep))

    def carte(px, py, ind, gen, sw, root, uid, branche=-1):
        sexe = ind.get("sexe", "U")
        fondc, trait = _couleur_carte(o["theme"], sexe, gen, branche)
        trait_c = _couleur_preuve(donnees, uid) if avec_preuves else trait
        nom = _nom_affiche(ind, o["prenoms"])
        parts.append('<g class="indi" data-id="%s"%s><title>%s</title>'
                     % (uid, ' data-root="1"' if root else "", _titre_carte(ind)))
        parts.append('<rect x="%g" y="%g" width="%g" height="%g" rx="8" fill="%s" '
                     'stroke="%s" stroke-width="%g"/>'
                     % (px, py, card_w, card_h, fondc, trait_c,
                        max(sw, 2.2) if avec_preuves else sw))
        if avec_pastille:
            acx = px + (10 + av_r_u) * k
            acy = py + card_h / 2
            _pastille_svg(parts, ind, acx, acy, av_r, trait, sexe, uid, avec_photo)
        tx = px + tx0_u * k
        ty = py + 17 * k
        dispo = card_w - tx0_u * k - 8 * k            # place utile jusqu'au bord droit
        sur = (ind.get("nom") or "").strip()
        if o.get("gras") and sur and nom.endswith(sur):
            pre_aff = nom[:len(nom) - len(sur)].rstrip()
            pre_aff = (pre_aff + " ") if pre_aff else ""
            larg = _larg_txt(pre_aff, 11 * k) + _larg_txt(sur, 11 * k, True)
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'pointer-events="none"%s>'
                         '%s<tspan font-weight="700">%s</tspan></text>'
                         % (tx, ty, 11 * k, TEXTE, _cale_l(larg, dispo),
                            _echap(pre_aff), _echap(sur)))
        else:
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'pointer-events="none"%s>%s</text>'
                         % (tx, ty, 11 * k, TEXTE, _cale(nom, dispo, 11 * k), _echap(nom)))
        if montre_dates:
            ty += 14 * k
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'pointer-events="none"%s>%s</text>'
                         % (tx, ty, 9 * k, TEXTE_DOUX,
                            _cale(modele.periode(ind), dispo, 9 * k),
                            _echap(modele.periode(ind))))
        if montre_lieux:
            ty += 13 * k
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'pointer-events="none"%s>%s</text>'
                         % (tx, ty, 8.5 * k, ACCENT,
                            _cale(_ville(ind), dispo, 8.5 * k), _echap(_ville(ind))))
        parts.append('</g>')

    for n in ordre:
        cc, dp = pos[n["id"]]
        gen = int(round(dp / level_gap))
        dind = inds.get(n["id"])
        if not dind:
            continue
        dx, dy = mapp(cc, dp)
        est_racine = n is racine
        br = branche_de.get(n["id"], -1)
        carte(dx, dy, dind, gen, 3 if est_racine else 1, est_racine, n["id"], br)
        # conjoints à côté (vertical) / dessous (horizontal), reliés par un trait d'union
        for i, cid in enumerate(conjoints_de(n)):
            cind = inds.get(cid)
            if not cind:
                continue
            scross = cc + (i + 1) * (cross_card + couple_link)
            sx, sy = mapp(scross, dp)
            # trait d'union reliant le conjoint à la personne / au voisin
            if horizontal:
                parts.append('<path d="M %g %g L %g %g" stroke="%s" stroke-width="1.6"/>'
                             % (sx + card_w / 2, dy + card_h, sx + card_w / 2, sy, ACCENT))
            else:
                y_mid = dy + card_h / 2
                gauche = (dx + card_w) if i == 0 else (sx - couple_link)
                parts.append('<path d="M %g %g L %g %g" stroke="%s" stroke-width="1.6"/>'
                             % (gauche, y_mid, sx, y_mid, ACCENT))
            carte(sx, sy, cind, gen, 1, False, cid, br)

    parts.append('</g>')
    if avec_legende:
        parts.append(_legende_preuve_svg(12 * k, hauteur_svg + bandeau + 16 * k, k))
    parts.append('</svg>')
    return "".join(parts)
