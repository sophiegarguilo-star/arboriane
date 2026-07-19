# -*- coding: utf-8 -*-
"""Arbre — rendu « éventail » (rosace d'ascendance / fan chart)."""

import math

from core import modele

from services.arbre.base import *

def _rad(deg):
    return deg * math.pi / 180.0


def _pt(cx, cy, r, deg):
    return cx + r * math.cos(_rad(deg)), cy + r * math.sin(_rad(deg))


def _eventail(donnees, ident, generations, angle, theme, o):
    """Rendu de la rosace d'ascendance. Voir :func:`rendre` pour les options."""
    k = max(0.6, min(1.6, o["taille"] / 100.0))          # facteur de taille texte
    police = ("Georgia, 'Times New Roman', serif" if o["police"] == "serif"
              else "sans-serif")
    char_w = 0.66 if o["police"] == "serif" else 0.58    # largeur moyenne d'un caractère

    sosa = _ascendance_sosa(donnees, ident, generations, o.get("plies"))
    angle = angle if angle in (180, 270, 360) else 360
    avec_preuves = bool(o.get("preuves"))
    avec_legende = avec_preuves and bool(o.get("legende", True))

    # largeur des anneaux : ils s'élargissent vers l'extérieur, pour donner au
    # texte radial des générations lointaines la longueur nécessaire.
    largeurs = {1: 82, 2: 82, 3: 84, 4: 94, 5: 104, 6: 112, 7: 118}
    r_centre = 58
    rayons = [r_centre]
    for g in range(1, generations):
        rayons.append(rayons[-1] + largeurs.get(g, 120))
    R = rayons[-1]

    marge = 10
    tfs = 21 * k if o["titre"] else 0
    bandeau = int(tfs + 12) if o["titre"] else 0
    cx, cy = R + marge, R + marge

    # balayage horaire, trou centre en bas (270) ; 180 = demi-cercle supérieur
    depart = 90 + (360 - angle) / 2.0

    # bbox du DESSIN RÉEL → viewBox recadrée au plus juste, quel que soit l'angle
    _bb = {"x0": cx - r_centre, "y0": cy - r_centre,
           "x1": cx + r_centre, "y1": cy + r_centre}

    def pt(r, a):
        x, y = _pt(cx, cy, r, a)
        _bb["x0"] = min(_bb["x0"], x)
        _bb["x1"] = max(_bb["x1"], x)
        _bb["y0"] = min(_bb["y0"], y)
        _bb["y1"] = max(_bb["y1"], y)
        return x, y

    # extrêmes de l'arc externe (points cardinaux tombant dans un secteur)
    for _a in (0, 90, 180, 270, 360, depart, depart + angle):
        if depart - 0.001 <= _a <= depart + angle + 0.001:
            pt(R, _a)

    parts = []            # contenu ; l'en-tête (viewBox) est assemblé À LA FIN

    def arc_path(pid_path, r, a0, a1, inverse):
        if inverse:
            a0, a1 = a1, a0
        x0, y0 = pt(r, a0)
        x1, y1 = pt(r, a1)
        grand = 1 if abs(a1 - a0) > 180 else 0
        sens = 0 if inverse else 1
        return ('<path id="%s" fill="none" d="M %g %g A %g %g 0 %d %d %g %g"/>'
                % (pid_path, x0, y0, r, r, grand, sens, x1, y1))

    def texte_arc(pid_path, contenu, fs, gras=False, fill=TEXTE):
        return ('<text font-size="%g"%s fill="%s" pointer-events="none">'
                '<textPath href="#%s" startOffset="50%%" text-anchor="middle">%s'
                '</textPath></text>'
                % (fs, ' font-weight="600"' if gras else "", fill, pid_path,
                   _echap(contenu)))

    def ville(ind_):
        lieu = (ind_.get("naissance", {}) or {}).get("lieu", "") or ""
        return lieu.split(",")[0].strip()

    def fs_base_gen(g):
        return {1: 13, 2: 12, 3: 11, 4: 10}.get(g, 9) * k

    # DÉCISION AUTOMATIQUE tangentiel/radial, PAR GÉNÉRATION : une génération
    # passe en radial dès que son plus long NOM ne tiendrait pas le long de
    # l'arc. En radial, les anneaux (élargis) portent le nom complet.
    nom_max_gen = {}
    for num_, pid_ in sosa.items():
        if num_ < 2:
            continue
        g_ = int(math.floor(math.log(num_, 2)))
        ind_ = donnees["individus"].get(pid_)
        if ind_:
            long_ = len((ind_.get("nom") or "").strip())
            nom_max_gen[g_] = max(nom_max_gen.get(g_, 0), long_)
    radial_gen = {}
    for g_, maxlen in nom_max_gen.items():
        if g_ < 1 or g_ >= len(rayons):
            continue
        pas_ = angle / float(2 ** g_)
        r_mid_ = (rayons[g_ - 1] + rayons[g_]) / 2.0
        arc_dispo_ = _rad(max(0.0, pas_ - 2.0)) * r_mid_
        besoin_ = maxlen * fs_base_gen(g_) * char_w * 1.14
        radial_gen[g_] = besoin_ > arc_dispo_

    for numero in sorted(sosa):
        pid = sosa[numero]
        ind = donnees["individus"].get(pid)
        if not ind:
            continue
        gen = int(math.floor(math.log(numero, 2)))
        fond, trait = _couleur_secteur(theme, numero, gen, ind.get("sexe", "U"))
        nom_prenoms = (ind.get("prenoms") or "").strip() or "?"
        if o["prenoms"] == "premier":
            nom_prenoms = nom_prenoms.split()[0] if nom_prenoms.split() else "?"
        nom_famille = modele.nom_de_famille(ind)
        periode = modele.periode(ind)

        if gen == 0:
            parts.append('<g class="indi" data-id="%s" data-sosa="%d" data-root="1"><title>%s</title>'
                         % (pid, numero, _titre_carte(ind)))
            trait_c = _couleur_preuve(donnees, pid) if avec_preuves else trait
            parts.append('<circle cx="%g" cy="%g" r="%g" fill="%s" stroke="%s" '
                         'stroke-width="%g"/>'
                         % (cx, cy, r_centre - 3, fond, trait_c,
                            4 if avec_preuves else 2.5))
            # police ajustée pour que le nom de la RACINE tienne dans le cercle
            _dispo = 2.0 * (r_centre - 10)
            _fsp = (max(8.0, min(12.5 * k, _dispo / (len(nom_prenoms) * char_w)))
                    if nom_prenoms else 12.5 * k)
            _fsn = (max(8.0, min(12.5 * k, _dispo / (len(nom_famille) * char_w)))
                    if nom_famille else 12.5 * k)
            parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                         'fill="%s" pointer-events="none">%s</text>'
                         % (cx, cy - 12, _fsp, TEXTE, _echap(nom_prenoms)))
            parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                         'font-weight="600" fill="%s" pointer-events="none">%s</text>'
                         % (cx, cy + 4, _fsn, TEXTE, _echap(nom_famille)))
            if o["dates"] and periode:
                parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                             'fill="%s" pointer-events="none">%s</text>'
                             % (cx, cy + 20, 10 * k, TEXTE_DOUX, _echap(periode)))
            parts.append('</g>')
            continue

        total = 2 ** gen
        pas = angle / float(total)
        a0 = depart + pas * (numero - total)
        a1 = a0 + pas
        am = (a0 + a1) / 2.0
        r_in, r_out = rayons[gen - 1], rayons[gen]

        # secteur
        x0o, y0o = pt(r_out, a0)
        x1o, y1o = pt(r_out, a1)
        x1i, y1i = pt(r_in, a1)
        x0i, y0i = pt(r_in, a0)
        grand = 1 if pas > 180 else 0
        d = ("M %g %g A %g %g 0 %d 1 %g %g L %g %g A %g %g 0 %d 0 %g %g Z"
             % (x0o, y0o, r_out, r_out, grand, x1o, y1o,
                x1i, y1i, r_in, r_in, grand, x0i, y0i))
        parts.append('<g class="indi" data-id="%s" data-sosa="%d"><title>%s</title>'
                     % (pid, numero, _titre_carte(ind)))
        parts.append('<path d="%s" fill="%s" stroke="#fff" stroke-width="1.6"/>'
                     % (d, fond))

        # liseré de preuve : arc coloré collé au bord externe du secteur
        if avec_preuves:
            cp = _couleur_preuve(donnees, pid)
            parts.append(
                arc_path("", r_out - 3.0, a0 + 1.2, a1 - 1.2, False)
                .replace('id="" fill="none" ',
                         'fill="none" stroke="%s" stroke-width="3.5" ' % cp))

        # texte : tangentiel (le long de l'arc) tant que le nom tient, sinon RADIAL
        inverse_arc = math.sin(_rad(am)) > 0.001          # secteur en bas -> retourner
        fs = fs_base_gen(gen)
        arc_dispo = _rad(max(0.0, pas - 2.0)) * (r_in + (r_out - r_in) * 0.5)

        if not radial_gen.get(gen, False):
            # ---- TANGENTIEL : le nom tient le long de l'arc (aucune troncature) ----
            pre = nom_prenoms
            fs_pre = fs
            if len(pre) * fs_pre * char_w > arc_dispo:
                mots = pre.split()
                pre = mots[0] if mots else pre
            if pre and len(pre) * fs_pre * char_w > arc_dispo:
                fs_pre = max(6.5, arc_dispo / (len(pre) * char_w))
            lignes = [(pre, fs_pre, False, TEXTE),
                      (nom_famille, fs, bool(o.get("gras", True)), TEXTE)]
            if o["dates"] and periode:
                lignes.append((periode, fs - 2.2 * k, False, TEXTE_DOUX))
            if o["lieux"] and ville(ind) and gen <= 4:
                lignes.append((ville(ind), fs - 2.6 * k, False, TEXTE_DOUX))
            fracs = {1: [0.44], 2: [0.58, 0.30], 3: [0.66, 0.40, 0.16],
                     4: [0.74, 0.52, 0.30, 0.10]}[len(lignes)]
            if inverse_arc:                    # garder l'ordre de lecture haut->bas
                fracs = [1.0 - f + 0.04 for f in fracs]
            for i, ((txt, fs_l, gras, coul), frac) in enumerate(zip(lignes, fracs)):
                if not txt:
                    continue
                r_ligne = r_in + (r_out - r_in) * frac
                pid_path = "ev%d_%d" % (numero, i)
                parts.append(arc_path(pid_path, r_ligne, a0 + 1.0, a1 - 1.0, inverse_arc))
                parts.append(texte_arc(pid_path, txt, fs_l, gras, coul))
        else:
            # ---- RADIAL : le nom file vers l'extérieur, police ajustée pour qu'il
            #      passe EN ENTIER ; dates ajoutées seulement si elles tiennent. ----
            longueur = (r_out - r_in) - 12.0
            mots_pre = nom_prenoms.split()
            tient = lambda lbl: longueur / (max(1, len(lbl)) * char_w) >= 6.5
            plein = ((mots_pre[0] + " " + nom_famille).strip()
                     if mots_pre else nom_famille) or "?"
            ini_pre = (mots_pre[0][:1] + ". ") if mots_pre else ""
            court = (ini_pre + nom_famille).strip() or plein
            candidats = []
            if o["dates"] and periode:
                candidats.append(plein + "  " + periode)
            candidats.append(plein)
            candidats.append(court)
            label = next((c for c in candidats if tient(c)), None)
            if label is None:                                # NOM seul démesuré : dernier recours
                fs_min = 6.5
                label = _tronque(nom_famille or plein, max(3, int(longueur / (fs_min * char_w))))
            fs_r = max(6.5, min(fs, longueur / (max(1, len(label)) * char_w)))
            gauche = math.cos(_rad(am)) < 0                  # moitié gauche -> retourner
            r_a, r_b = (r_out - 5, r_in + 5) if gauche else (r_in + 5, r_out - 5)
            xa, ya = pt(r_a, am)
            xb, yb = pt(r_b, am)
            pid_path = "ev%d_r" % numero
            parts.append('<path id="%s" fill="none" d="M %g %g L %g %g"/>'
                         % (pid_path, xa, ya, xb, yb))
            parts.append(texte_arc(pid_path, label, fs_r, False, TEXTE))
        parts.append('</g>')

    # légende des niveaux de preuve, sous le dessin (option ``preuves``)
    legende = ""
    bas_leg = 0
    if avec_legende:
        bas_leg = 30 * k
        ly = _bb["y1"] + bas_leg - 6 * k
        legende = _legende_preuve_svg(_bb["x0"], ly, k)

    # viewBox recadrée sur le dessin réel + titre collé juste au-dessus
    haut = bandeau if o["titre"] else marge
    vb_x = _bb["x0"] - marge
    vb_y = _bb["y0"] - haut
    vb_w = (_bb["x1"] - _bb["x0"]) + 2 * marge
    vb_h = (_bb["y1"] - _bb["y0"]) + haut + marge + bas_leg
    entete = ('<svg xmlns="http://www.w3.org/2000/svg" '
              'xmlns:xlink="http://www.w3.org/1999/xlink" '
              'viewBox="%g %g %g %g" class="arbre-svg" font-family="%s">'
              % (vb_x, vb_y, vb_w, vb_h, police))
    titre = ""
    if o["titre"]:
        titre = ('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                 'font-weight="600" fill="%s" letter-spacing="1">%s</text>'
                 % ((_bb["x0"] + _bb["x1"]) / 2.0, _bb["y0"] - 6, tfs, TEXTE,
                    _echap(o["titre"])))
    return entete + titre + "".join(parts) + legende + "</svg>"
