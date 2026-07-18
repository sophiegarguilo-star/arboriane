# -*- coding: utf-8 -*-
"""Génère les images de l'assistant d'installation (Inno Setup), aux couleurs
d'Arboriane : une grande bannière verticale et un petit logo. Sorties en BMP
24 bits (format attendu par Inno Setup).

Usage : python outils/generer_images_installateur.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SORTIE = os.path.join(RACINE, "installateur")
os.makedirs(SORTIE, exist_ok=True)

VERT = (31, 70, 54)          # #1f4636 vert profond
VERT_BAS = (16, 38, 29)      # bas du dégradé, plus sombre
SAUGE = (139, 165, 141)      # #8ba58d
CREME = (247, 244, 236)      # #f7f4ec
ACCENT = (199, 107, 42)      # #c76b2a terracotta


def _police(taille, gras=False):
    for nom in (("georgiab.ttf" if gras else "georgia.ttf"),
                ("seguisb.ttf" if gras else "segoeui.ttf"), "arial.ttf"):
        try:
            return ImageFont.truetype(os.path.join(r"C:\Windows\Fonts", nom), taille)
        except Exception:
            continue
    return ImageFont.load_default()


def _degrade_vertical(w, h, haut, bas):
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px_col = tuple(int(haut[i] + (bas[i] - haut[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = px_col
    return img


def _logo_reel(taille):
    """Le vrai logo Arboriane (emblème), redimensionné, en RGBA. Fond blanc
    (le logo est en traits vert foncé) — destiné à être posé sur une carte
    claire pour rester lisible."""
    for nom in ("web-app-manifest-512x512.png", "apple-touch-icon.png",
                "logo-lanceur.png", "favicon-96x96.png"):
        chemin = os.path.join(RACINE, "web", nom)
        if os.path.exists(chemin):
            im = Image.open(chemin).convert("RGBA")
            im.thumbnail((taille, taille), Image.LANCZOS)
            return im
    return None


def _carte(w, h, rayon, fond, ombre=True):
    """Petite carte arrondie (avec ombre douce), en RGBA."""
    marge = 18
    im = Image.new("RGBA", (w + marge * 2, h + marge * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if ombre:
        for i in range(marge, 0, -2):
            a = int(40 * (1 - i / marge))
            d.rounded_rectangle([marge - i / 2, marge + i / 2, marge + w + i / 2, marge + h + i / 2],
                                radius=rayon, fill=(10, 25, 18, a))
    d.rounded_rectangle([marge, marge, marge + w, marge + h], radius=rayon,
                        fill=fond, outline=SAUGE, width=2)
    return im, marge


def _centrer_texte(draw, cx, y, texte, police, couleur):
    b = draw.textbbox((0, 0), texte, font=police)
    draw.text((cx - (b[2] - b[0]) / 2, y), texte, font=police, fill=couleur)
    return b[3] - b[1]


def grande_banniere():
    W, H = 410, 797
    img = _degrade_vertical(W, H, VERT, VERT_BAS)
    d = ImageDraw.Draw(img)
    # arcs discrets en fond
    for r in (520, 620, 720):
        d.ellipse([-140, H - r, W + 140, H + r], outline=(255, 255, 255, 18), width=1)
    # carte blanche portant le vrai logo (traits vert foncé → fond clair pour lisibilité)
    logo = _logo_reel(196)
    if logo:
        cw = ch = 236
        carte, mg = _carte(cw, ch, 28, (255, 255, 255, 255))
        cx = (W - carte.width) // 2
        img.paste(carte, (cx, 92), carte)
        lx = cx + mg + (cw - logo.width) // 2
        ly = 92 + mg + (ch - logo.height) // 2
        img.paste(logo, (lx, ly), logo)
    # marque + accroche
    y = 402
    y += _centrer_texte(d, W / 2, y, "Arboriane", _police(52, gras=True), CREME) + 22
    _centrer_texte(d, W / 2, y, "Votre atelier de généalogie", _police(21), SAUGE)
    _centrer_texte(d, W / 2, y + 30, "local et privé", _police(21), SAUGE)
    d.line([(W / 2 - 40, y + 82), (W / 2 + 40, y + 82)], fill=ACCENT, width=3)
    img.save(os.path.join(SORTIE, "wizard-grande.bmp"), "BMP")


def petit_logo():
    # petit logo en haut à droite des pages internes (fond clair) : le vrai
    # logo sur blanc, il se fond dans l'en-tête blanc de l'assistant.
    S = 138
    img = Image.new("RGB", (S, S), (255, 255, 255))
    logo = _logo_reel(122)
    if logo:
        img.paste(logo, ((S - logo.width) // 2, (S - logo.height) // 2), logo)
    img.save(os.path.join(SORTIE, "wizard-petite.bmp"), "BMP")


if __name__ == "__main__":
    grande_banniere()
    petit_logo()
    print("Images créées dans", SORTIE)
