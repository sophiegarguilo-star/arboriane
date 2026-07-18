# -*- coding: utf-8 -*-
"""
Rendu des arbres généalogiques en SVG (paquet).

API publique : :func:`rendre`. Le paquet est découpé en modules :
  base (primitives), eventail, ascendance, descendance, fond (habillage).
"""

from core import modele

from services.arbre.eventail import _eventail
from services.arbre.ascendance import _ascendance
from services.arbre.descendance import _descendance
from services.arbre.tableau_gen import _tableau
from services.arbre.sablier import _sablier
from services.arbre.fond import _habiller, _COULEUR_OK

_DEFAUTS = {
    "generations": None,      # None -> défaut par mode (éventail 6, cases 4)
    "angle": 360,             # éventail : 180 | 270 | 360
    "theme": "branche",       # branche | sexe | generation | aucune
    "dates": True,
    "lieux": False,
    "prenoms": "tous",        # tous | premier | initiale | nom
    "gras": None,             # None -> éventail True, cases False
    "police": "sans",         # sans | serif
    "taille": 100,            # 70..140 (%)
    "titre": "",
    "sosa": False,            # ascendance : afficher le n° Sosa
    "implexe": False,         # ascendance : grouper l'implexe (ancêtres répétés grisés)
    "profession": False,      # ascendance : afficher la 1re profession
    "pastille": "monogramme", # monogramme | photo | aucune
    "preuves": False,         # colorer un liseré selon le niveau de preuve
    "legende": True,          # afficher la légende des niveaux de preuve
    "sens": None,             # ascendance : 'gd'(défaut)|'bh' ; descendance : 'vertical'(défaut)|'horizontal'
    "trait_forme": "courbe",  # courbe | coude
    "trait_epaisseur": 0,     # 0 -> valeur par défaut du mode
    "trait_couleur": "",      # vide -> bordure du thème
    "fond": "",               # couleur de fond (vide/aucun -> transparent)
    "cadre": "aucun",         # aucun | simple | double | coins
    "cadre_couleur": "",      # vide -> doré par défaut
}


def _vierge(donnees):
    """Copie de l'arbre aux libellés VIDÉS, pour un arbre à imprimer et remplir
    à la main. On garde la STRUCTURE (fams/famc, sexe pour la couleur) et on
    remplace le nom par un caractère de largeur nulle : les cartes sont dessinées
    mais vides. Non destructif (copie ; l'arbre réel n'est pas touché)."""
    d = dict(donnees)                       # tables non lues par le rendu conservées
    d["individus"] = {
        pid: {"id": pid, "sexe": ind.get("sexe", "U"),
              "nom": chr(0x200b), "prenoms": "", "naissance": {}, "deces": {},
              "fams": ind.get("fams", []), "famc": ind.get("famc", [])}
        for pid, ind in donnees["individus"].items()
    }
    return d


def rendre(donnees, racine_id, mode="eventail", options=None):
    """Rend un arbre généalogique en SVG et renvoie la chaîne complète
    ``<svg …>…</svg>``.

    Paramètres
    ----------
    donnees : dict
        Base au schéma Arboriane ``{"individus", "familles", …}``.
    racine_id : str
        Identifiant de la personne centrale (de cujus).
    mode : str
        ``"eventail"`` (rosace d'ascendance), ``"ascendance"`` (cases) ou
        ``"descendance"`` (cases avec conjoints).
    options : dict, optionnel
        Personnalisation ; les clés reconnues (avec leurs valeurs par défaut)
        sont dans ``_DEFAUTS``. Résumé :

        - ``generations`` (int) : nombre de niveaux (défaut 6 en éventail, 4 en cases).
        - ``theme`` : ``branche`` | ``sexe`` | ``generation`` | ``aucune``.
        - ``dates`` / ``lieux`` (bool) : afficher période / commune de naissance.
        - ``prenoms`` : ``tous`` | ``premier`` | ``initiale`` | ``nom``.
        - ``gras`` (bool) : nom de famille en gras.
        - ``police`` : ``sans`` | ``serif`` ; ``taille`` (70..140, en %).
        - ``titre`` (str) : titre au-dessus de l'arbre.
        - ``angle`` (éventail) : 180 | 270 | 360.
        - ``sosa`` / ``profession`` (ascendance) : afficher le n° Sosa / la profession.
        - ``pastille`` : ``monogramme`` | ``photo`` | ``aucune`` (cases). Avec
          ``photo``, on insère le média principal de la personne clippé en cercle
          (repli sur le monogramme si aucune photo).
        - ``preuves`` (bool) : colore le liseré/bordure de chaque personne selon
          son niveau de preuve global (acte=vert, déclaré=or, estimé=terracotta,
          aucun=gris) et ajoute une petite légende dans le SVG.
        - ``sens`` : ascendance ``gd``|``bh`` ; descendance ``vertical``|``horizontal``.
        - ``trait_forme`` (``courbe``|``coude``), ``trait_epaisseur``, ``trait_couleur``.

    Notes
    -----
    Les « niveaux de preuve » (liseré coloré + légende, option ``preuves``) et
    les photos sur les cartes (``pastille="photo"``) sont portés de l'ancien
    ``trees.py`` et adaptés au schéma v2 : le niveau de preuve est synthétisé via
    :func:`services.sources.preuves_personne` et la photo pointe vers le média
    principal servi par ``/media/Photos/``. Les fonds/cadres décoratifs de la v1
    restent retirés ; le fond du SVG est transparent. Le champ ``professions``
    est lu au format ``[{"valeur": …}]``.
    """
    modele.garantir_cles(donnees)
    o = dict(_DEFAUTS)
    o.update(options or {})
    # couleur des traits : validée comme le fond/cadre (anti-injection SVG) ;
    # une valeur non conforme retombe sur la bordure du thème.
    if not _COULEUR_OK.match((o.get("trait_couleur") or "").strip()):
        o["trait_couleur"] = ""

    if o.get("vierge"):                 # arbre à remplir à la main : cartes vidées
        donnees = _vierge(donnees)
        o["pastille"] = "aucune"
        o["preuves"] = False

    if mode == "eventail":
        generations = o["generations"] if o["generations"] else 6
        if o["gras"] is None:
            o["gras"] = True
        svg = _eventail(donnees, racine_id, generations, o["angle"], o["theme"], o)
    elif mode == "ascendance":
        generations = o["generations"] if o["generations"] else 4
        if o["gras"] is None:
            o["gras"] = False
        if o["sens"] is None:
            o["sens"] = "gd"
        svg = _ascendance(donnees, racine_id, generations, o)
    elif mode == "descendance":
        generations = o["generations"] if o["generations"] else 4
        if o["gras"] is None:
            o["gras"] = False
        if o["sens"] is None:
            o["sens"] = "vertical"
        svg = _descendance(donnees, racine_id, generations, o)
    elif mode == "tableau":
        generations = o["generations"] if o["generations"] else 8
        svg = _tableau(donnees, racine_id, generations, o)
    elif mode == "sablier":
        generations = o["generations"] if o["generations"] else 4
        svg = _sablier(donnees, racine_id, generations, generations, o)
    else:
        raise ValueError("mode inconnu : %r (attendu "
                         "eventail|ascendance|descendance|tableau|sablier)" % mode)

    return _habiller(svg, o)
