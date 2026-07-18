# -*- coding: utf-8 -*-
"""Arbre — rendu « ascendance » en cases (gauche→droite ou bas→haut)."""

import math

from core import modele

from services.arbre.base import *

def _ascendance_bh(donnees, sosa, generations, o, k, police, tfs, repeats=None):
    """Ascendance VERTICALE « de bas en haut » : la racine en bas, les ancêtres
    montent en pyramide ; cartes portrait (prénom / NOM / dates centrés)."""
    repeats = repeats or {}
    montre_dates = bool(o["dates"])
    montre_lieux = bool(o["lieux"])
    montre_prof = bool(o.get("profession"))
    montre_sosa = bool(o.get("sosa"))
    n_extra = (1 if montre_dates else 0) + (1 if montre_lieux else 0) + (1 if montre_prof else 0)
    mode_pastille = o.get("pastille", "monogramme")           # monogramme | photo | aucune
    avec_pastille = mode_pastille != "aucune"
    avec_photo = mode_pastille == "photo"
    avec_preuves = bool(o.get("preuves"))
    avec_legende = avec_preuves and bool(o.get("legende", True))
    av_r = 16 * k if avec_pastille else 0
    past_h = (2 * av_r + 8 * k) if avec_pastille else 0
    # largeur ADAPTÉE au NOM (gras) / prénom le plus long, bornée
    _pieces = [10]
    for nn in sosa:
        ii = donnees["individus"].get(sosa[nn])
        if ii:
            _pieces.append(len((ii.get("nom") or "").strip()))
            _pieces.append(len(_prenom_principal(ii)))
    cw = max(134, min(210, max(_pieces) * 7.5 + 18)) * k
    ch = (34 + 15 * n_extra) * k + past_h
    pas_x = cw + 16 * k
    pas_y = ch + 52 * k

    cross, gen_of = {}, {}
    etat = {"cpt": -1, "gmax": 0}

    def place(numero, gen):
        if numero not in sosa:
            return None
        etat["gmax"] = max(etat["gmax"], gen)
        gen_of[numero] = gen
        feuille = (gen == generations - 1 or
                   (numero * 2 not in sosa and numero * 2 + 1 not in sosa))
        if feuille:
            etat["cpt"] += 1
            c = etat["cpt"] * pas_x
        else:
            cs = [v for v in (place(numero * 2, gen + 1),
                              place(numero * 2 + 1, gen + 1)) if v is not None]
            c = sum(cs) / len(cs)
        cross[numero] = c
        return c

    place(1, 0)
    gmax = etat["gmax"]
    positions = {n: (c, (gmax - gen_of[n]) * pas_y) for n, c in cross.items()}

    largeur = (etat["cpt"] + 1) * pas_x + 10 * k
    hauteur = gmax * pas_y + ch + 10 * k
    bandeau = int(tfs + 12 * k) if o["titre"] else 0
    total_w = largeur
    total_h = hauteur + bandeau

    forme = o.get("trait_forme", "courbe")
    ep = float(o.get("trait_epaisseur") or 0) or 1.6
    col_lien = (o.get("trait_couleur") or "").strip() or BORDURE

    leg_h = int(38 * k) if avec_legende else 0
    total_h = total_h + leg_h
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" '
             'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 %d %d" '
             'class="arbre-svg" font-family="%s">' % (total_w, total_h, police)]
    if o["titre"]:
        parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                     'font-weight="700" fill="%s">%s</text>'
                     % (largeur / 2, tfs + 10 * k, tfs, TEXTE, _echap(o["titre"])))
    parts.append('<g transform="translate(0,%d)">' % bandeau)

    # traits : de la carte enfant (bas) vers ses deux parents (haut)
    for numero, (x, y) in positions.items():
        for parent in (numero * 2, numero * 2 + 1):
            if parent in positions:
                px, py = positions[parent]
                parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="%g"/>'
                             % (_lien_path(x + cw / 2, y, px + cw / 2, py + ch,
                                           forme, True), col_lien, ep))

    def _pre_nom(ind):
        nom = (ind.get("nom") or "").strip()
        mode = o["prenoms"]
        if mode == "nom":
            return "", nom
        if mode == "initiale":
            p = _prenom_principal(ind)
            return ((p[:1].upper() + ".") if p else ""), nom
        if mode == "premier":
            return _prenom_principal(ind), nom
        return (ind.get("prenoms") or "").strip(), nom

    for numero, (x, y) in positions.items():
        ind = donnees["individus"].get(sosa[numero])
        if not ind:
            continue
        sexe = ind.get("sexe", "U")
        fond_c, trait = _couleur_secteur(o["theme"], numero, gen_of[numero], sexe)
        cx = x + cw / 2
        pre, nom = _pre_nom(ind)
        implexe_ici = numero in repeats
        attr_root = ' data-root="1"' if numero == 1 else ""
        sw = 3 if numero == 1 else 1.2
        titre = modele.nom_complet(ind)
        if implexe_ici:
            titre += " — implexe, voir Sosa %d" % repeats[numero]
        parts.append('<g class="indi" data-id="%s" data-sosa="%d"%s><title>%s</title>'
                     % (sosa[numero], numero, attr_root, _echap(titre)))
        trait_c = _couleur_preuve(donnees, sosa[numero]) if avec_preuves else trait
        if implexe_ici:                       # ancêtre répété : grisé + renvoi
            fond_c, trait_c = IMPLEXE_FOND, IMPLEXE_TRAIT
        parts.append('<rect x="%g" y="%g" width="%g" height="%g" rx="9" fill="%s" '
                     'stroke="%s" stroke-width="%g"/>'
                     % (x, y, cw, ch, fond_c, trait_c,
                        max(sw, 2.4) if avec_preuves else sw))
        if implexe_ici:                       # marqueur « ↻ Sosa principal »
            parts.append('<text x="%g" y="%g" text-anchor="end" font-size="%g" '
                         'fill="%s" pointer-events="none">↻%d</text>'
                         % (x + cw - 5 * k, y + 12 * k, 8.5 * k, IMPLEXE_TEXTE, repeats[numero]))
        if montre_sosa:                               # n° Sosa, coin haut-gauche
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'pointer-events="none">%d</text>'
                         % (x + 6 * k, y + 12 * k, 8.5 * k, TEXTE_DOUX, numero))
        if avec_pastille:                             # photo/monogramme en haut, centré
            acx, acy = cx, y + 4 * k + av_r
            _pastille_svg(parts, ind, acx, acy, av_r, trait, sexe,
                          sosa[numero], avec_photo)
        dispo = cw - 16 * k                           # place utile dans la carte
        ty = y + past_h + (16 if not pre else 15) * k
        if pre:
            parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                         'fill="%s" pointer-events="none"%s>%s</text>'
                         % (cx, ty, 10.5 * k, TEXTE, _cale(pre, dispo, 10.5 * k), _echap(pre)))
            ty += 14 * k
        parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                     'font-weight="700" fill="%s" pointer-events="none"%s>%s</text>'
                     % (cx, ty, 12 * k, TEXTE, _cale(nom, dispo, 12 * k, True), _echap(nom)))
        if montre_dates:
            ty += 14 * k
            parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                         'fill="%s" pointer-events="none"%s>%s</text>'
                         % (cx, ty, 9 * k, TEXTE_DOUX,
                            _cale(modele.periode(ind), dispo, 9 * k),
                            _echap(modele.periode(ind))))
        if montre_lieux:
            ty += 13 * k
            parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                         'fill="%s" pointer-events="none"%s>%s</text>'
                         % (cx, ty, 8.5 * k, ACCENT,
                            _cale(_ville(ind), dispo, 8.5 * k), _echap(_ville(ind))))
        if montre_prof:
            prof = _profession(ind)
            ty += 13 * k
            parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                         'fill="%s" pointer-events="none"%s>%s</text>'
                         % (cx, ty, 8.5 * k, TEXTE_DOUX,
                            _cale(prof, dispo, 8.5 * k), _echap(prof)))
        parts.append('</g>')

    parts.append('</g>')
    if avec_legende:
        parts.append(_legende_preuve_svg(12 * k, hauteur + bandeau + 16 * k, k))
    parts.append("</svg>")
    return "".join(parts)


def _ascendance(donnees, ident, generations, o):
    """Rendu de l'arbre d'ascendance en cases. Voir :func:`rendre`."""
    sosa = _ascendance_sosa(donnees, ident, generations, o.get("plies"))

    # Implexe (option) : ne montrer qu'une fois le sous-arbre d'un ancêtre
    # répété ; les autres occurrences seront grisées et renvoyées au principal.
    repeats = {}
    if o.get("implexe"):
        repeats = _implexe_repeats(sosa)
        _elaguer_implexe(sosa, repeats)

    k = max(70, min(140, int(o.get("taille", 100) or 100))) / 100.0
    police = ("Georgia, 'Times New Roman', serif" if o["police"] == "serif"
              else "system-ui, 'Segoe UI', sans-serif")
    tfs = 24 * k
    # orientation VERTICALE « de bas en haut » → fonction dédiée (cartes portrait)
    if o.get("sens") == "bh":
        return _ascendance_bh(donnees, sosa, generations, o, k, police, tfs, repeats)

    montre_dates = bool(o["dates"])
    montre_lieux = bool(o["lieux"])
    montre_prof = bool(o.get("profession"))
    n_extra = (1 if montre_dates else 0) + (1 if montre_lieux else 0) + (1 if montre_prof else 0)
    mode_pastille = o.get("pastille", "monogramme")
    avec_pastille = mode_pastille != "aucune"
    avec_photo = mode_pastille == "photo"
    avec_preuves = bool(o.get("preuves"))
    avec_legende = avec_preuves and bool(o.get("legende", True))
    av_r_u = max(11.0, min(16.0, (26 + 15 * n_extra) / 2.0 - 3)) if avec_pastille else 0.0
    av_r = av_r_u * k
    tx0_u = (16 + 2 * av_r_u) if avec_pastille else 12
    # largeur de carte ADAPTÉE au nom le plus long affiché, bornée
    _noms = [_nom_affiche(donnees["individus"][sosa[nn]], o["prenoms"])
             for nn in sosa if sosa[nn] in donnees["individus"]]
    _lmax = max((len(s) for s in _noms), default=10)
    largeur_carte = max(198 if avec_pastille else 168,
                        min(300, tx0_u + _lmax * 6.4 + 18)) * k
    hauteur_carte = (26 + 15 * n_extra) * k
    esp_x = largeur_carte + 40 * k
    pas_y = hauteur_carte + 14 * k

    positions = {}
    etat_place = {"compteur": -1, "gen_max": 0}

    def place(numero, gen):
        if numero not in sosa:
            return None
        etat_place["gen_max"] = max(etat_place["gen_max"], gen)
        feuille = (gen == generations - 1 or
                   (numero * 2 not in sosa and numero * 2 + 1 not in sosa))
        if feuille:
            etat_place["compteur"] += 1
            y = etat_place["compteur"] * pas_y
        else:
            yp = place(numero * 2, gen + 1)
            ym = place(numero * 2 + 1, gen + 1)
            ys = [v for v in (yp, ym) if v is not None]
            y = sum(ys) / len(ys)
        positions[numero] = (gen * esp_x + 10, y)
        return y

    place(1, 0)
    largeur = (etat_place["gen_max"] + 1) * esp_x + 20
    hauteur = (etat_place["compteur"] + 1) * pas_y + 10 * k
    bandeau = int(tfs + 12 * k) if o["titre"] else 0

    total_w = largeur
    total_h = hauteur + bandeau
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
                     % (largeur / 2, tfs + 10 * k, tfs, TEXTE, _echap(o["titre"])))
    parts.append('<g transform="translate(0,%d)">' % bandeau)

    # traits (parent -> chacun de ses deux parents)
    for numero, (x, y) in positions.items():
        for enfant in (numero * 2, numero * 2 + 1):
            if enfant in positions:
                ex, ey = positions[enfant]
                parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="%g"/>'
                             % (_lien_path(x + largeur_carte, y + hauteur_carte / 2,
                                           ex, ey + hauteur_carte / 2, forme, False),
                                col_lien, ep))

    # cartes
    for numero, (x, y) in positions.items():
        ind = donnees["individus"].get(sosa[numero])
        if not ind:
            continue
        nom = _nom_affiche(ind, o["prenoms"])
        implexe_ici = numero in repeats
        attr_root = ' data-root="1"' if numero == 1 else ""
        sw = 3 if numero == 1 else 1
        sexe = ind.get("sexe", "U")
        fond_c, trait = _couleur_secteur(o["theme"], numero, numero.bit_length() - 1, sexe)
        trait_c = _couleur_preuve(donnees, sosa[numero]) if avec_preuves else trait
        if implexe_ici:                            # ancêtre répété : grisé + renvoi
            fond_c, trait_c = IMPLEXE_FOND, IMPLEXE_TRAIT
        titre = nom + (" — implexe, voir Sosa %d" % repeats[numero] if implexe_ici else "")
        parts.append('<g class="indi" data-id="%s" data-sosa="%d"%s><title>%s</title>' %
                     (sosa[numero], numero, attr_root, _echap(titre)))
        parts.append('<rect x="%g" y="%g" width="%g" height="%g" rx="8" fill="%s" '
                     'stroke="%s" stroke-width="%g"/>'
                     % (x, y, largeur_carte, hauteur_carte, fond_c, trait_c,
                        max(sw, 2.2) if avec_preuves else sw))
        if implexe_ici:                            # marqueur « ↻ Sosa principal »
            parts.append('<text x="%g" y="%g" text-anchor="end" font-size="%g" '
                         'fill="%s" pointer-events="none">↻%d</text>'
                         % (x + largeur_carte - 5 * k, y + 10 * k, 8 * k,
                            IMPLEXE_TEXTE, repeats[numero]))
        if o.get("sosa"):                          # n° Sosa, coin haut-gauche
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'pointer-events="none">%d</text>'
                         % (x + 5 * k, y + 10 * k, 8 * k, TEXTE_DOUX, numero))
        # pastille : photo / monogramme — ou rien si « aucune »
        if avec_pastille:
            acx = x + (10 + av_r_u) * k
            acy = y + hauteur_carte / 2
            _pastille_svg(parts, ind, acx, acy, av_r, trait, sexe,
                          sosa[numero], avec_photo)
        # textes
        tx = x + tx0_u * k
        ty = y + 17 * k
        dispo = largeur_carte - tx0_u * k - 8 * k     # place utile jusqu'au bord droit
        sur = (ind.get("nom") or "").strip()
        if o.get("gras") and sur and nom.endswith(sur):
            # nom de famille en gras (distinct du prénom) ; calé au pixel près si besoin
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
        if montre_prof:
            prof = _profession(ind)
            ty += 13 * k
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'pointer-events="none"%s>%s</text>'
                         % (tx, ty, 8.5 * k, TEXTE_DOUX,
                            _cale(prof, dispo, 8.5 * k), _echap(prof)))
        parts.append('</g>')

    parts.append('</g>')   # fin translate bandeau
    if avec_legende:
        parts.append(_legende_preuve_svg(12 * k, hauteur + bandeau + 16 * k, k))
    parts.append("</svg>")
    return "".join(parts)
