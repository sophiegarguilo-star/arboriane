# -*- coding: utf-8 -*-
"""Arbre — rendu « tableau par génération » : liste d'ascendance imprimable,
les ancêtres (Sosa) regroupés par génération avec nom, période et lieu.

Rendu SVG texte (s'imprime et s'exporte comme les autres arbres). Réutilise
`_ascendance_sosa` et les couleurs de `base`."""

from core import modele

from services.arbre.base import *


def _tableau(donnees, ident, generations, o):
    sosa = _ascendance_sosa(donnees, ident, generations)
    inds = donnees["individus"]
    if not sosa:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40"></svg>'

    k = max(70, min(140, int(o.get("taille", 100) or 100))) / 100.0
    police = ("Georgia, 'Times New Roman', serif" if o.get("police") == "serif"
              else "system-ui, 'Segoe UI', sans-serif")
    montre_dates = bool(o["dates"])
    montre_lieux = bool(o["lieux"])
    montre_prof = bool(o.get("profession"))

    par_gen = {}
    for num in sosa:
        par_gen.setdefault(num.bit_length() - 1, []).append(num)

    W = int(680 * k)
    tfs = 24 * k
    bandeau = int(tfs + 12 * k) if o["titre"] else 0
    x = 16 * k
    row_h = 19 * k
    gen_h = 30 * k

    hauteur = bandeau + 10 * k
    for g in par_gen:
        hauteur += gen_h + len(par_gen[g]) * row_h
    hauteur += 14 * k

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
             'class="arbre-svg" font-family="%s">' % (W, int(hauteur), police)]
    if o["titre"]:
        parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                     'font-weight="700" fill="%s">%s</text>'
                     % (W / 2, tfs + 10 * k, tfs, TEXTE, _echap(o["titre"])))

    y = bandeau + 10 * k
    for g in sorted(par_gen):
        nums = sorted(par_gen[g])
        parts.append('<rect x="0" y="%g" width="%d" height="%g" rx="4" fill="#eef5ef"/>'
                     % (y, W, gen_h - 5 * k))
        lib = ("La personne racine" if g == 0 else
               ("Parents" if g == 1 else "Génération %d" % g))
        parts.append('<text x="%g" y="%g" font-size="%g" font-weight="700" fill="%s">'
                     '%s · %d ancêtre%s</text>'
                     % (x, y + 18 * k, 12 * k, VERT, _echap(lib),
                        len(nums), "s" if len(nums) > 1 else ""))
        y += gen_h
        for num in nums:
            ind = inds.get(sosa[num])
            nom = modele.nom_complet(ind) if ind else "?"
            extra = []
            if montre_dates and ind:
                extra.append(modele.periode(ind))
            if montre_lieux and ind:
                extra.append(_ville(ind))
            if montre_prof and ind:
                extra.append(_profession(ind))
            suffixe = "".join("  ·  " + e for e in extra if e)
            parts.append('<text x="%g" y="%g" font-size="%g" fill="%s">'
                         '<tspan fill="%s" font-weight="700">%d</tspan>  %s'
                         '<tspan fill="%s">%s</tspan></text>'
                         % (x, y + 13 * k, 11 * k, TEXTE, ACCENT, num,
                            _echap(nom), TEXTE_DOUX, _echap(suffixe)))
            y += row_h

    parts.append('</svg>')
    return "".join(parts)
