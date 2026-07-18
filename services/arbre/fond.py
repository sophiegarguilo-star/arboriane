# -*- coding: utf-8 -*-
"""Arbre — fonds & cadres décoratifs (textures SVG, habillage). Module feuille."""

import re

_COULEUR_OK = re.compile(r"^#[0-9a-fA-F]{3,8}$|^[a-zA-Z]{3,20}$")


# Arrière-plans décoratifs générés (aucune image externe : tout est en SVG, donc
# l'export PNG/PDF/HTML/SVG reste autonome). Textes de l'arbre = sombres, on ne
# propose donc que des fonds CLAIRS pour rester lisibles.
_TEXTURES = ("parchemin", "vieux-papier", "toile", "sepia")


def _texture_svg(nom, x, y, w, h):
    """Renvoie un fond décoratif (defs + rects) couvrant la boîte (x,y,w,h)."""
    box = 'x="%g" y="%g" width="%g" height="%g"' % (x, y, w, h)
    if nom == "vieux-papier":
        lignes = "".join(
            '<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="#d8c7a0" '
            'stroke-width="0.6" opacity="0.35"/>' % (x, y + i, x + w, y + i)
            for i in range(6, int(h), 14))
        return ('<defs><radialGradient id="fbg" cx="50%%" cy="42%%" r="75%%">'
                '<stop offset="0%%" stop-color="#f7ecd4"/>'
                '<stop offset="100%%" stop-color="#e9d7b3"/></radialGradient></defs>'
                '<rect %s fill="url(#fbg)"/>%s') % (box, lignes)
    if nom == "sepia":
        return ('<defs><radialGradient id="fbg" cx="50%%" cy="40%%" r="85%%">'
                '<stop offset="0%%" stop-color="#efe0c4"/>'
                '<stop offset="70%%" stop-color="#e2cba3"/>'
                '<stop offset="100%%" stop-color="#c9a874"/></radialGradient></defs>'
                '<rect %s fill="url(#fbg)"/>') % box
    if nom == "toile":
        return ('<defs><pattern id="ftoile" width="7" height="7" '
                'patternUnits="userSpaceOnUse">'
                '<rect width="7" height="7" fill="#f1ead8"/>'
                '<path d="M0 0H7M0 0V7" stroke="#dccfab" stroke-width="0.5" '
                'opacity="0.5"/></pattern></defs>'
                '<rect %s fill="#f1ead8"/><rect %s fill="url(#ftoile)"/>') % (box, box)
    # parchemin (défaut) : dégradé crème + quelques taches douces + vignette
    taches = "".join(
        '<circle cx="%g" cy="%g" r="%g" fill="#d9c49a" opacity="0.12"/>' % (
            x + w * fx, y + h * fy, min(w, h) * fr)
        for fx, fy, fr in ((0.18, 0.22, 0.05), (0.72, 0.30, 0.07),
                           (0.40, 0.70, 0.06), (0.85, 0.78, 0.045),
                           (0.30, 0.45, 0.035)))
    return ('<defs><radialGradient id="fbg" cx="50%%" cy="45%%" r="80%%">'
            '<stop offset="0%%" stop-color="#f8efd9"/>'
            '<stop offset="72%%" stop-color="#f0e3c4"/>'
            '<stop offset="100%%" stop-color="#e3d0a6"/></radialGradient></defs>'
            '<rect %s fill="url(#fbg)"/>%s') % (box, taches)


def _habiller(svg, o):
    """Ajoute un fond (couleur ou texture) et/ou un cadre décoratif au SVG déjà
    rendu. Injecte le fond juste après <svg …>, et le cadre juste avant </svg>,
    en s'appuyant sur le viewBox pour couvrir tout le dessin."""
    fond = (o.get("fond") or "").strip()
    cadre = (o.get("cadre") or "aucun").strip()
    img_data = o.get("fond_image_data") or ""
    est_image = bool(img_data)
    est_texture = fond.lower() in _TEXTURES
    fond_ok = est_image or (
        fond and fond.lower() not in ("aucun", "none") and (
            est_texture or _COULEUR_OK.match(fond)))
    cadre_ok = cadre and cadre != "aucun"
    vignette = bool(o.get("vignette"))
    if not fond_ok and not cadre_ok and not vignette:
        return svg
    m = re.search(r'viewBox="([\-\d.]+)\s+([\-\d.]+)\s+([\-\d.]+)\s+([\-\d.]+)"', svg)
    if not m:
        return svg
    x, y, w, h = (float(m.group(i)) for i in range(1, 5))

    # marge : on agrandit le viewBox pour que fond + cadre entourent l'arbre
    # sans jamais le grignoter.
    pad = max(24.0, min(w, h) * 0.05)
    X, Y, W, H = x - pad, y - pad, w + 2 * pad, h + 2 * pad
    svg = re.sub(r'(viewBox=")[^"]*(")',
                 lambda mm: '%s%g %g %g %g%s' % (mm.group(1), X, Y, W, H, mm.group(2)),
                 svg, count=1)

    debut = ""
    if est_image:
        try:
            op = max(0.1, min(1.0, int(o.get("fond_opacite", 60)) / 100.0))
        except (TypeError, ValueError):
            op = 0.6
        # rect crème dessous : si l'image est transparente ou très claire, le
        # texte reste lisible ; l'image est « rognée » pour couvrir toute la boîte.
        debut = ('<rect x="%g" y="%g" width="%g" height="%g" fill="#f4efe4"/>'
                 '<image x="%g" y="%g" width="%g" height="%g" href="%s" '
                 'preserveAspectRatio="xMidYMid slice" opacity="%.2f"/>') % (
            X, Y, W, H, X, Y, W, H, img_data, op)
    elif fond_ok and est_texture:
        debut = _texture_svg(fond.lower(), X, Y, W, H)
    elif fond_ok:
        debut = '<rect x="%g" y="%g" width="%g" height="%g" fill="%s"/>' % (X, Y, W, H, fond)

    if vignette:
        # léger assombrissement des bords (effet « tirage ancien »), sous l'arbre
        debut += ('<defs><radialGradient id="fvig" cx="50%%" cy="50%%" r="72%%">'
                  '<stop offset="55%%" stop-color="#000000" stop-opacity="0"/>'
                  '<stop offset="100%%" stop-color="#000000" stop-opacity="0.22"/>'
                  '</radialGradient></defs>'
                  '<rect x="%g" y="%g" width="%g" height="%g" fill="url(#fvig)"/>') % (
            X, Y, W, H)

    fin = ""
    if cadre_ok:
        coul = (o.get("cadre_couleur") or "").strip()
        coul = coul if _COULEUR_OK.match(coul) else "#b79b6a"
        # cadre dans la marge, jamais sur l'arbre
        ins = pad * 0.45
        w, h = W, H
        x, y = X, Y

        def rect(i, sw):
            return ('<rect x="%g" y="%g" width="%g" height="%g" fill="none" '
                    'stroke="%s" stroke-width="%g"/>' % (x + i, y + i, w - 2 * i, h - 2 * i, coul, sw))

        if cadre == "simple":
            fin = rect(ins, 3)
        elif cadre == "passe-partout":
            # effet « tableau » : filet extérieur épais + fine ligne près du
            # dessin (la marge claire fait office de passe-partout).
            fin = rect(pad * 0.28, 6) + rect(pad * 0.9, 1.2)
        elif cadre == "double":
            fin = rect(ins, 2.5) + rect(ins * 2.4, 1.4)
        elif cadre == "coins":
            lg = min(w, h) * 0.06
            def coin(cx, cy, dx, dy):
                return ('<path d="M %g,%g L %g,%g L %g,%g" fill="none" stroke="%s" '
                        'stroke-width="4"/>' % (cx, cy + dy * lg, cx, cy, cx + dx * lg, cy, coul))
            fin = (coin(x + ins, y + ins, 1, 1) + coin(x + w - ins, y + ins, -1, 1)
                   + coin(x + ins, y + h - ins, 1, -1) + coin(x + w - ins, y + h - ins, -1, -1))

    svg = re.sub(r'(<svg\b[^>]*>)', lambda mm: mm.group(1) + debut, svg, count=1)
    if fin:
        svg = svg.replace('</svg>', fin + '</svg>', 1)
    return svg
