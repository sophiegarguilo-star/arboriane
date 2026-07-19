# -*- coding: utf-8 -*-
"""Arbre — primitives partagées : palette, utilitaires texte, preuves/photos,
calculs Sosa/descendance, couleurs et cartes.

Module « feuille » : aucune dépendance interne au paquet arbre. Les rendus
(eventail/ascendance/descendance) importent ces primitives via ``import *``."""

import math

from urllib.parse import quote

from core import modele

# ---------------------------------------------------------------------------
# Palette — jetons du nouveau design d'Arboriane
# ---------------------------------------------------------------------------

# Fonds des cartes/secteurs par sexe (M/F, tout le reste = inconnu)
COULEURS = {"M": "#d2e2f1", "F": "#f2d9e2", "U": "#e4ece1"}
# Traits (bordures) par sexe — dérivés des bordures du design
TRAIT = {"M": "#9db8cf", "F": "#cfa9b8", "U": "#bcc7b6"}

ACCENT = "#c76b2a"        # accent chaud
VERT = "#1f4636"          # vert profond
BORDURE = "#e4e1d6"       # bordures neutres
TEXTE = "#2a2b28"         # texte principal
TEXTE_DOUX = "#6a6b64"    # texte secondaire (dates, lieux…)

# Palette « par génération » / « par branche » (teintes douces harmonisées)
_PALETTE_GEN = ["#d2e2f1", "#e4ece1", "#f2d9e2", "#efe6d8", "#e0e9ee",
                "#ece4de", "#e8ede4", "#e6dfea"]

# Niveaux de preuve → couleur du liseré / de la pastille (option ``preuves``).
# acte = vert ; déclaré = or ; estimé = terracotta pâle ; aucun = gris.
COULEUR_PREUVE = {"acte": "#3d7a54", "declare": "#d99a3c", "estime": "#e0b48a",
                  "non_qualifie": "#c9c4b8", "manquant": "#c9c4b8"}
# Du meilleur au pire : sert à synthétiser un niveau global.
_ORDRE_PREUVE = ["acte", "declare", "estime", "non_qualifie", "manquant"]


def _echap(t):
    """Échappe les caractères réservés du XML."""
    return (str(t).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _tronque(texte, n):
    """Tronque proprement avec une ellipse plutôt qu'une coupe brute."""
    texte = texte or ""
    return texte if len(texte) <= n else texte[:n - 1].rstrip() + "…"


def _larg_txt(texte, fs, gras=False):
    """Largeur estimée d'un texte (px). Volontairement un poil généreuse pour
    déclencher le calage un cheveu avant le débordement plutôt qu'après."""
    return len(texte or "") * fs * 0.63 * (1.07 if gras else 1.0)


def _cale_l(largeur_px, dispo_px):
    """Attribut SVG condensant un texte au pixel près (``textLength``) quand sa
    largeur estimée dépasse la place disponible. Le navigateur cale exactement
    -> jamais de débordement, sans couper le texte. Chaîne vide sinon."""
    if dispo_px > 1 and largeur_px > dispo_px:
        return ' textLength="%g" lengthAdjust="spacingAndGlyphs"' % dispo_px
    return ""


def _cale(texte, dispo_px, fs, gras=False):
    """Idem, pour un texte simple d'une seule fonte."""
    return _cale_l(_larg_txt(texte, fs, gras), dispo_px)


def _titre_carte(ind, suffixe=""):
    """Contenu du ``<title>`` d'une carte cliquable : « Nom (période) », déjà
    échappé XML. Lu par les lecteurs d'écran et affiché en info-bulle native
    du navigateur — point COMMUN à tous les rendus (éventail, ascendance,
    descendance, sablier) pour ne pas dupliquer la logique.
    ``suffixe`` : mention libre ajoutée à la fin (ex. renvoi d'implexe)."""
    if not ind:
        return _echap("?")
    titre = modele.nom_complet(ind)
    periode = modele.periode(ind)
    if periode:
        titre += " (%s)" % periode
    return _echap(titre + (suffixe or ""))


def _profession(ind):
    """Première profession d'une personne, en chaîne (schéma professions[{valeur}])."""
    profs = ind.get("professions") or []
    if not profs:
        return ""
    p = profs[0]
    if isinstance(p, dict):
        return (p.get("valeur") or "").strip()
    return str(p).strip()


def _prenom_principal(ind):
    """Premier prénom d'une personne (le nouveau schéma n'a pas de champ dédié)."""
    prenoms = (ind.get("prenoms") or "").split()
    return prenoms[0] if prenoms else ""


# ---------------------------------------------------------------------------
# Niveaux de preuve (option ``preuves``) et photos (``pastille="photo"``)
# ---------------------------------------------------------------------------

def _niveau_preuve_global(donnees, pid):
    """Niveau de preuve SYNTHÉTIQUE d'une personne, parmi
    ``acte`` > ``declare`` > ``estime`` > ``manquant``.

    On prend le MEILLEUR niveau atteint par l'un de ses faits vitaux
    (naissance / union / décès) via :func:`services.sources.preuves_personne` :
    « acte » si au moins un fait est prouvé par acte, sinon « déclaré », etc.
    Une personne sans aucune source qualifiée retombe sur « manquant ».

    L'import de ``sources`` est fait ICI (et non en tête de module) : ``sources``
    n'importe pas ``arbre`` — il n'y a donc pas de cycle réel — mais l'import
    différé garantit qu'aucune régression d'import ne peut apparaître et évite
    de payer le coût quand l'option ``preuves`` est désactivée."""
    from services import sources          # import différé volontaire (voir docstring)

    infos = sources.preuves_personne(donnees, pid)
    if not infos:
        return "manquant"
    meilleur = None                       # plus petit index dans _ORDRE_PREUVE = meilleur
    for fait in infos.get("faits", []):
        niv = fait.get("niveau", "manquant")
        if niv not in _ORDRE_PREUVE:
            niv = "manquant"
        idx = _ORDRE_PREUVE.index(niv)
        if meilleur is None or idx < meilleur:
            meilleur = idx
    if meilleur is None:
        return "manquant"
    return _ORDRE_PREUVE[meilleur]


def _couleur_preuve(donnees, pid):
    """Couleur du liseré/pastille selon le niveau de preuve global (ou None si
    le calcul échoue)."""
    niveau = _niveau_preuve_global(donnees, pid)
    return COULEUR_PREUVE.get(niveau, COULEUR_PREUVE["manquant"])


def _media_principal(ind):
    """Nom de fichier du média principal (``principale=True``) sinon le premier,
    ou '' si la personne n'a aucun média."""
    medias = ind.get("medias") or []
    if not medias:
        return ""
    for m in medias:
        if isinstance(m, dict) and m.get("principale") and (m.get("fichier") or "").strip():
            return m["fichier"].strip()
    premier = medias[0]
    if isinstance(premier, dict):
        return (premier.get("fichier") or "").strip()
    return str(premier).strip()


def _url_photo(fichier):
    """URL servie par l'app pour une photo de personne (dossier Photos/),
    nom de fichier URL-encodé. Vide si pas de fichier."""
    if not fichier:
        return ""
    return "/media/Photos/" + quote(fichier)


# ---------------------------------------------------------------------------
# Calculs de généalogie — portés en interne (aucune dépendance externe)
# ---------------------------------------------------------------------------

def _parents(donnees, ident):
    """Renvoie ``(pere_id, mere_id)`` ou ``('', '')``."""
    ind = donnees["individus"].get(ident)
    if not ind or not ind.get("famc"):
        return "", ""
    fam = donnees["familles"].get(ind["famc"][0])
    if not fam:
        return "", ""
    return fam.get("mari", ""), fam.get("epouse", "")


def _ascendance_sosa(donnees, ident, generations, plies=None):
    """Dict ``{ numero_sosa: individu_id }`` sur ``generations`` niveaux.
    1 = personne centrale, 2 = père, 3 = mère, 4-7 = grands-parents, etc.
    Garde anti-cycle : une filiation corrompue ne fait pas diverger la
    récursion (l'implexe légitime reste autorisé sur d'autres branches).
    ``plies`` : ensemble de numéros Sosa dont on n'explore PAS les ancêtres
    (branche repliée — la personne reste affichée)."""
    plies = plies or set()
    resultat = {}

    def remplir(pid, numero, niveau, chemin):
        if not pid or niveau > generations or pid in chemin:
            return
        resultat[numero] = pid
        if numero in plies:                # branche repliée : on s'arrête ici
            return
        pere, mere = _parents(donnees, pid)
        chemin2 = chemin | {pid}
        remplir(pere, numero * 2, niveau + 1, chemin2)
        remplir(mere, numero * 2 + 1, niveau + 1, chemin2)

    remplir(ident, 1, 1, frozenset())
    return resultat


def _descendance_couples(donnees, ident, generations):
    """Descendance par COUPLES : chaque personne avec ses union(s) (conjoint +
    enfants de CETTE union), récursivement. Structure d'un nœud :
    ``{ id, unions: [ {conjoint_id, enfants:[<noeud>, ...]} ] }``."""
    inds = donnees["individus"]

    def construire(pid, niveau, vus):
        ind = inds.get(pid)
        if not ind or pid in vus:
            return None
        noeud = {"id": pid, "unions": []}
        vus2 = vus | {pid}
        if niveau < generations:
            for fid in ind.get("fams", []):
                fam = donnees["familles"].get(fid)
                if not fam:
                    continue
                autre = fam["epouse"] if fam.get("mari") == pid else fam.get("mari")
                enfants_n = []
                for eid in fam.get("enfants", []):
                    child = construire(eid, niveau + 1, vus2)
                    if child:
                        enfants_n.append(child)
                if autre or enfants_n:
                    noeud["unions"].append({"conjoint_id": autre or "",
                                            "enfants": enfants_n})
        return noeud

    return construire(ident, 1, frozenset())
def _couleur_carte(theme, sexe, gen, branche=-1):
    """``(fond, trait)`` d'une carte de DESCENDANCE : par sexe (défaut), par
    génération, sobre, ou « par branche » = par lignée descendante."""
    if theme == "branche":
        if branche is None or branche < 0:            # la racine : teinte neutre
            return "#eef1f4", BORDURE
        return _PALETTE_GEN[branche % len(_PALETTE_GEN)], BORDURE
    if theme == "generation":
        return _PALETTE_GEN[gen % len(_PALETTE_GEN)], BORDURE
    if theme == "aucune":
        return "#ffffff", BORDURE
    return COULEURS.get(sexe, COULEURS["U"]), TRAIT.get(sexe, TRAIT["U"])
_MONO_BG = {"M": "#dbe7f2", "F": "#f2dfe7", "U": "#e4ece1"}
_MONO_TX = {"M": "#3f6486", "F": "#9c4d6a", "U": VERT}


def _nom_affiche(ind, prenoms_mode):
    """Nom pour une carte selon le mode :
      'tous' (défaut) : tous les prénoms + NOM (via ``modele.nom_complet``)
      'premier'  : premier prénom + NOM
      'initiale' : initiale du prénom + NOM (ex. « J. MARTIN »)
      'nom'      : nom de famille seul."""
    nom = modele.nom_de_famille(ind)
    if prenoms_mode == "nom":
        return nom or "(sans nom)"
    if prenoms_mode == "initiale":
        pre = _prenom_principal(ind)
        ini = (pre[:1].upper() + ".") if pre else ""
        return (ini + " " + nom).strip() or "(sans nom)"
    if prenoms_mode == "premier":
        pre = _prenom_principal(ind)
        return (pre + " " + nom).strip() or "(sans nom)"
    return modele.nom_complet(ind)


def _ville(ind):
    """Commune de naissance (avant la première virgule), ou ''."""
    lieu = (ind.get("naissance") or {}).get("lieu") or ""
    return lieu.split(",")[0].strip()


def _initiales(ind):
    """Monogramme : initiale du prénom + initiale du nom."""
    pre = _prenom_principal(ind)
    nom = (ind.get("nom") or "").strip()
    a = pre[:1].upper() if pre else ""
    b = nom[:1].upper() if nom else ""
    return (a + b) or "?"


def _pastille_svg(parts, ind, cx, cy, r, trait, sexe, uid, avec_photo):
    """Dessine la pastille d'une carte au centre (cx, cy), rayon r.

    - ``avec_photo`` vrai et la personne a un média principal → l'image clippée
      en cercle (repli sur monogramme sinon) ;
    - sinon → le monogramme (initiales).
    """
    fichier = _media_principal(ind) if avec_photo else ""
    url = _url_photo(fichier)
    if url:
        cid = "ph_%s" % str(uid).replace(" ", "_")
        parts.append('<clipPath id="%s"><circle cx="%g" cy="%g" r="%g"/></clipPath>'
                     % (cid, cx, cy, r))
        parts.append('<image href="%s" xlink:href="%s" x="%g" y="%g" width="%g" '
                     'height="%g" clip-path="url(#%s)" '
                     'preserveAspectRatio="xMidYMid slice" pointer-events="none"/>'
                     % (url, url, cx - r, cy - r, 2 * r, 2 * r, cid))
        parts.append('<circle cx="%g" cy="%g" r="%g" fill="none" stroke="%s" '
                     'stroke-width="2"/>' % (cx, cy, r, trait))
        return
    parts.append('<circle cx="%g" cy="%g" r="%g" fill="%s" stroke="%s" '
                 'stroke-width="1.8"/>'
                 % (cx, cy, r, _MONO_BG.get(sexe, _MONO_BG["U"]), trait))
    parts.append('<text x="%g" y="%g" text-anchor="middle" font-size="%g" '
                 'font-weight="700" fill="%s" pointer-events="none">%s</text>'
                 % (cx, cy + r * 0.34, r * 0.86,
                    _MONO_TX.get(sexe, _MONO_TX["U"]), _echap(_initiales(ind))))


def _legende_preuve_svg(x0, y0, k):
    """Petite légende horizontale des niveaux de preuve (option ``preuves``)."""
    out = ['<g class="legende-preuve" pointer-events="none">']
    out.append('<text x="%g" y="%g" font-size="%g" font-weight="600" fill="%s">'
               'Preuve</text>' % (x0, y0 + 4 * k, 10 * k, TEXTE))
    xx = x0 + 52 * k
    for niveau, label in (("acte", "Acte"), ("declare", "Déclaré"),
                          ("estime", "Estimé"), ("manquant", "Aucune")):
        out.append('<circle cx="%g" cy="%g" r="%g" fill="%s" stroke="%s" '
                   'stroke-width="1"/>'
                   % (xx + 6 * k, y0, 6 * k, COULEUR_PREUVE[niveau], BORDURE))
        out.append('<text x="%g" y="%g" font-size="%g" fill="%s">%s</text>'
                   % (xx + 16 * k, y0 + 4 * k, 10 * k, TEXTE_DOUX, _echap(label)))
        xx += (20 + len(label) * 6.6) * k
    out.append('</g>')
    return "".join(out)


def _lien_path(x0, y0, x1, y1, forme, vertical):
    """Trait entre deux cartes : 'coude' (équerre) ou 'courbe' (bézier)."""
    if forme == "coude":
        if vertical:
            my = (y0 + y1) / 2.0
            return "M %g %g V %g H %g V %g" % (x0, y0, my, x1, y1)
        mx = (x0 + x1) / 2.0
        return "M %g %g H %g V %g H %g" % (x0, y0, mx, y1, x1)
    # courbe
    if vertical:
        return "M %g %g C %g %g %g %g %g %g" % (
            x0, y0, x0, (y0 + y1) / 2, x1, (y0 + y1) / 2, x1, y1)
    return "M %g %g C %g %g %g %g %g %g" % (
        x0, y0, (x0 + x1) / 2, y0, (x0 + x1) / 2, y1, x1, y1)


# Thème « branche » (partagé éventail + ascendance).
_QUARTIERS = {4: (_PALETTE_GEN[0], "#7fa6c6"), 5: (_PALETTE_GEN[3], "#c79a5a"),
              6: (_PALETTE_GEN[2], "#cfa9b8"), 7: (_PALETTE_GEN[1], "#a7bfa0")}
_GEN1 = {0: (_PALETTE_GEN[0], "#7fa6c6"), 1: (_PALETTE_GEN[2], "#cfa9b8")}
_CENTRE_BRANCHE = ("#e4ece1", VERT)


def _couleur_secteur(theme, numero, gen, sexe):
    """``(fond, trait)`` d'un secteur/carte selon le thème (éventail + ascendance)."""
    if theme == "sexe":
        return COULEURS.get(sexe, COULEURS["U"]), TRAIT.get(sexe, TRAIT["U"])
    if theme == "generation":
        return _PALETTE_GEN[gen % len(_PALETTE_GEN)], BORDURE
    if theme == "aucune":
        return "#ffffff", BORDURE
    if gen == 0:
        return _CENTRE_BRANCHE
    if gen == 1:
        return _GEN1[numero - 2]
    quartier = numero >> (gen - 2)
    return _QUARTIERS.get(quartier, (BORDURE, "#999999"))


# ── Implexe : ancêtres répétés (même personne à plusieurs numéros Sosa) ──
# Une même personne peut occuper plusieurs positions Sosa (mariages entre
# parents, cousinages). Option ``implexe`` : on n'affiche qu'UNE fois le
# sous-arbre (sous l'occurrence de plus petit Sosa = « principal ») et on grise
# les autres occurrences en les renvoyant vers ce principal.
IMPLEXE_FOND = "#edeae3"     # gris chaud, discret
IMPLEXE_TRAIT = "#b7b2a5"
IMPLEXE_TEXTE = "#8c877c"


def _implexe_repeats(sosa):
    """Renvoie {numero: numero_principal} pour chaque occurrence NON principale
    d'un ancêtre (le principal = plus petit numéro Sosa portant ce pid)."""
    premier = {}
    for num in sorted(sosa):
        premier.setdefault(sosa[num], num)
    return {num: premier[sosa[num]] for num in sosa if premier[sosa[num]] != num}


def _elaguer_implexe(sosa, repeats):
    """Retire de `sosa` la portion d'ascendance située AU-DESSUS des occurrences
    répétées (identique au sous-arbre du principal). Le nœud répété lui-même
    reste (feuille marquée). Modifie et renvoie `sosa`."""
    a_retirer = set()
    for num in repeats:
        pile = [num * 2, num * 2 + 1]
        while pile:
            n = pile.pop()
            if n in sosa:
                a_retirer.add(n)
                pile.append(n * 2)
                pile.append(n * 2 + 1)
    for n in a_retirer:
        sosa.pop(n, None)
    return sosa


__all__ = [
    "COULEURS", "TRAIT", "ACCENT", "VERT", "BORDURE", "TEXTE", "TEXTE_DOUX",
    "IMPLEXE_FOND", "IMPLEXE_TRAIT", "IMPLEXE_TEXTE",
    "_implexe_repeats", "_elaguer_implexe",
    "_PALETTE_GEN", "COULEUR_PREUVE", "_ORDRE_PREUVE", "_couleur_secteur",
    "_echap", "_tronque", "_larg_txt", "_cale_l", "_cale", "_titre_carte",
    "_profession",
    "_prenom_principal", "_niveau_preuve_global", "_couleur_preuve",
    "_media_principal", "_url_photo", "_parents", "_ascendance_sosa",
    "_descendance_couples", "_couleur_carte", "_MONO_BG", "_MONO_TX",
    "_nom_affiche", "_ville", "_initiales", "_pastille_svg",
    "_legende_preuve_svg", "_lien_path",
]
