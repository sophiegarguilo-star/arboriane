# -*- coding: utf-8 -*-
"""Arbre — rendu « sablier » : ascendance vers le HAUT + descendance vers le BAS,
la personne racine au centre. Layout dédié (pyramide d'ancêtres + arbre tidy de
descendants alignés sur la racine), réutilisant les primitives de `base`."""

from core import modele

from services.arbre.base import *


def _sablier(donnees, ident, gen_asc, gen_desc, o):
    inds = donnees["individus"]
    if ident not in inds:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"></svg>'

    k = max(70, min(140, int(o.get("taille", 100) or 100))) / 100.0
    police = ("Georgia, 'Times New Roman', serif" if o.get("police") == "serif"
              else "system-ui, 'Segoe UI', sans-serif")
    montre_dates = bool(o["dates"])
    montre_lieux = bool(o["lieux"])
    n_extra = (1 if montre_dates else 0) + (1 if montre_lieux else 0)
    cw = 132 * k
    ch = (32 + 14 * n_extra) * k
    slotW = cw + 16 * k
    row = ch + 48 * k

    # ── Ancêtres : pyramide vers le haut (chaque génération sur une rangée) ──
    sosa = _ascendance_sosa(donnees, ident, gen_asc)
    gmax = max((num.bit_length() - 1 for num in sosa), default=0)
    baseW = slotW * (2 ** gmax)
    apos = {}
    for num in sosa:
        g = num.bit_length() - 1
        idx = num - 2 ** g
        apos[num] = [(idx + 0.5) / (2 ** g) * baseW, -g * row]
    rax = apos[1][0]
    for num in apos:
        apos[num][0] -= rax                       # racine (Sosa 1) recentrée en x=0

    # ── Descendants : arbre « tidy » vers le bas ──
    dpos = {}
    leaf = [0.0]

    def place(pid, depth, chemin):
        if depth > gen_desc or pid in chemin or pid not in inds:
            return None
        kids = [c for c in modele.enfants(donnees, pid)
                if c not in chemin and c in inds]
        if depth == gen_desc or not kids:
            x = leaf[0]
            leaf[0] += slotW
        else:
            xs = [v for v in (place(c, depth + 1, chemin | {pid}) for c in kids)
                  if v is not None]
            if xs:
                x = (min(xs) + max(xs)) / 2.0
            else:
                x = leaf[0]
                leaf[0] += slotW
        dpos[pid] = [x, depth * row]
        return x

    place(ident, 0, frozenset())
    rdx = dpos[ident][0]
    for pid in dpos:
        dpos[pid][0] -= rdx                        # racine recentrée en x=0

    # ── Bornes + décalage vers des coordonnées positives ──
    xs = [p[0] for p in apos.values()] + [p[0] for p in dpos.values()]
    ys = [p[1] for p in apos.values()] + [p[1] for p in dpos.values()]
    minx, maxx = min(xs) - cw / 2 - 10 * k, max(xs) + cw / 2 + 10 * k
    miny, maxy = min(ys) - ch / 2 - 10 * k, max(ys) + ch / 2 + 10 * k
    tfs = 24 * k
    bandeau = int(tfs + 12 * k) if o["titre"] else 0
    W = int(maxx - minx)
    H = int(maxy - miny) + bandeau
    ox, oy = -minx, -miny + bandeau

    forme = o.get("trait_forme", "courbe")
    ep = float(o.get("trait_epaisseur") or 0) or 1.4
    col = (o.get("trait_couleur") or "").strip() or BORDURE

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" '
             'xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 %d %d" '
             'class="arbre-svg" font-family="%s">' % (W, H, police)]
    if o["titre"]:
        parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                     'font-weight="700" fill="%s">%s</text>'
                     % (W / 2, tfs + 10 * k, tfs, TEXTE, _echap(o["titre"])))

    def cxy(p):
        return (p[0] + ox, p[1] + oy)

    # traits : ancêtres (num vers son enfant num//2, plus bas)
    for num in apos:
        if num > 1 and num // 2 in apos:
            x0, y0 = cxy(apos[num]); x1, y1 = cxy(apos[num // 2])
            parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="%g"/>'
                         % (_lien_path(x0, y0 + ch / 2, x1, y1 - ch / 2, forme, True), col, ep))
    # traits : descendants (parent vers chaque enfant, plus bas)
    for pid in dpos:
        for c in modele.enfants(donnees, pid):
            if c in dpos:
                x0, y0 = cxy(dpos[pid]); x1, y1 = cxy(dpos[c])
                parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="%g"/>'
                             % (_lien_path(x0, y0 + ch / 2, x1, y1 - ch / 2, forme, True), col, ep))

    def carte(cx, cy, pid, racine=False, num=None):
        ind = inds.get(pid)
        if not ind:
            return
        sexe = ind.get("sexe", "U")
        fond, trait = COULEURS.get(sexe, COULEURS["U"]), TRAIT.get(sexe, TRAIT["U"])
        x, y = cx - cw / 2, cy - ch / 2
        parts.append('<g class="indi" data-id="%s"%s><title>%s</title>'
                     % (pid, ' data-root="1"' if racine else "", _titre_carte(ind)))
        parts.append('<rect x="%g" y="%g" width="%g" height="%g" rx="9" fill="%s" '
                     'stroke="%s" stroke-width="%g"/>'
                     % (x, y, cw, ch, fond, trait, 3 if racine else 1.2))
        if o.get("sosa") and num:
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s" '
                         'pointer-events="none">%d</text>' % (x + 5 * k, y + 11 * k, 8 * k, TEXTE_DOUX, num))
        dispo = cw - 14 * k
        ty = y + (15 if n_extra else 20) * k
        nom = _nom_affiche(ind, o["prenoms"])
        parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                     'font-weight="700" fill="%s" pointer-events="none"%s>%s</text>'
                     % (cx, ty, 11.5 * k, TEXTE, _cale(nom, dispo, 11.5 * k, True), _echap(nom)))
        if montre_dates:
            ty += 14 * k
            parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                         'fill="%s" pointer-events="none"%s>%s</text>'
                         % (cx, ty, 9 * k, TEXTE_DOUX, _cale(modele.periode(ind), dispo, 9 * k),
                            _echap(modele.periode(ind))))
        if montre_lieux:
            ty += 12 * k
            parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                         'fill="%s" pointer-events="none"%s>%s</text>'
                         % (cx, ty, 8.5 * k, ACCENT, _cale(_ville(ind), dispo, 8.5 * k),
                            _echap(_ville(ind))))
        parts.append('</g>')

    for num in apos:                               # ancêtres (racine = Sosa 1)
        cx, cy = cxy(apos[num])
        carte(cx, cy, sosa[num], racine=(num == 1), num=num if o.get("sosa") else None)
    for pid in dpos:                               # descendants (racine déjà dessinée)
        if pid == ident:
            continue
        cx, cy = cxy(dpos[pid])
        carte(cx, cy, pid)

    parts.append('</svg>')
    return "".join(parts)
