# -*- coding: utf-8 -*-
"""
Validateur GEDCOM 5.5.1 — grammaire, pointeurs, structure.

Nos tests d'aller-retour ne prouvent rien : ils vérifient que notre lecteur
comprend notre écrivain. Si les deux partagent la même erreur, tout passe au
vert et c'est le logiciel d'en face qui trébuche. Ce validateur ne connaît que
la norme.

Grammaire (5.5.1, chapitre « Grammar Syntax ») :

    gedcom_line := level + delim + [xref_ID] + tag + [line_value] + terminator
    delim       := [(0x20)]        « a single space character »
    level       := digit | digit + digit   (pas de zéro non significatif)
    pointer     := (0x40) + alphanum + pointer_string + (0x40)
    tag         := alphanum+ ; les tags privés commencent par un souligné

Contrôles :
  - la ligne respecte la grammaire, un seul espace comme délimiteur ;
  - aucune espace en fin de ligne (une valeur en perdrait la sienne) ;
  - ligne <= 255 caractères, terminateur compris ;
  - le niveau ne croît que de 1 à la fois ; xref seulement au niveau 0 ;
  - tout pointeur désigne un enregistrement déclaré ;
  - CONC/CONT ont un parent ; une valeur coupée par CONC ne l'est pas sur une
    espace (la norme prévient que l'espace serait perdue) ;
  - le fichier commence par 0 HEAD et finit par 0 TRLR.

Usage :
    python -X utf8 outils/valider_gedcom.py fichier.ged [autre.ged …]
    python -X utf8 outils/valider_gedcom.py --export     # valide notre export

Sortie non nulle si une anomalie est trouvée.
"""

import glob
import os
import re
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ.setdefault("ARBORIANE_SANS_NAVIGATEUR", "1")

# level + delim + [xref + delim] + tag + [delim + value]
_LIGNE = re.compile(r"^(\d{1,2}) (@[^@\s]+@ )?([A-Za-z0-9_]{1,31})( .*)?$")
_POINTEUR = re.compile(r"^@[^@\s]+@$")
_MAX = 255


class Anomalie:
    def __init__(self, ligne, regle, detail):
        self.ligne, self.regle, self.detail = ligne, regle, detail

    def __str__(self):
        return "  ligne %-5d %-34s %s" % (self.ligne, self.regle, self.detail[:70])


def valider(texte):
    """Renvoie la liste des anomalies d'un texte GEDCOM."""
    anomalies = []
    lignes = texte.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lignes and lignes[-1] == "":
        lignes.pop()

    xrefs, pointeurs, pile = set(), [], []
    # Une valeur peut se poursuivre sur les lignes CONT/CONC qui suivent : leur
    # « valeur » est du texte libre, pas une ligne GEDCOM à re-valider. Ce fanion
    # dit qu'on est à l'intérieur d'une telle continuation.
    dans_texte = False
    if not lignes or lignes[0].lstrip("﻿") != "0 HEAD":
        anomalies.append(Anomalie(1, "le fichier doit commencer par 0 HEAD",
                                  lignes[0][:40] if lignes else "(vide)"))
    if "0 TRLR" not in lignes:
        anomalies.append(Anomalie(len(lignes), "le fichier doit finir par 0 TRLR", ""))

    for n, brute in enumerate(lignes, 1):
        l = brute.lstrip("﻿") if n == 1 else brute
        if not l:
            anomalies.append(Anomalie(n, "ligne vide", ""))
            continue
        if len(l.encode("utf-8")) + 2 > _MAX:
            anomalies.append(Anomalie(n, "ligne > 255 octets (terminateur compris)",
                                      "%d octets" % (len(l.encode("utf-8")) + 2)))
        if l != l.rstrip(" \t"):
            anomalies.append(Anomalie(n, "espace en fin de ligne", repr(l[-12:])))
        if l[:1] in (" ", "\t"):
            anomalies.append(Anomalie(n, "espace en début de ligne", repr(l[:12])))

        m = _LIGNE.match(l)
        if not m:
            anomalies.append(Anomalie(n, "ne respecte pas gedcom_line", l[:60]))
            continue

        niveau_txt, xref, tag, valeur = m.group(1), m.group(2), m.group(3), m.group(4)
        if len(niveau_txt) > 1 and niveau_txt[0] == "0":
            anomalies.append(Anomalie(n, "zéro non significatif dans le niveau", niveau_txt))
        niveau = int(niveau_txt)

        if xref and niveau != 0:
            anomalies.append(Anomalie(n, "identifiant hors du niveau 0", l[:50]))
        if xref:
            x = xref.strip().strip("@")
            if x in xrefs:
                anomalies.append(Anomalie(n, "identifiant déclaré deux fois", x))
            xrefs.add(x)

        while pile and pile[-1][0] >= niveau:
            pile.pop()
        attendu = pile[-1][0] + 1 if pile else 0
        if niveau > attendu:
            anomalies.append(Anomalie(n, "le niveau saute (L+1 au plus)",
                                      "%d après %d" % (niveau, attendu - 1)))
        if tag in ("CONC", "CONT") and not pile:
            anomalies.append(Anomalie(n, "%s sans ligne parente" % tag, ""))

        v = valeur[1:] if valeur else ""
        if v and _POINTEUR.match(v):
            pointeurs.append((n, v.strip("@"), tag))

        # Une valeur coupée par CONC ne doit pas l'être sur une espace : le
        # lecteur d'en face la perdrait au recollage (norme, définition de CONC).
        if tag == "CONC" and v.startswith(" "):
            anomalies.append(Anomalie(n, "CONC commence par une espace", repr(v[:12])))

        pile.append((niveau, tag, v))

    for n, cible, tag in pointeurs:
        # Un tag privé (souligné) peut pointer vers un enregistrement d'extension
        # qu'on préserve sans le comprendre : ce n'est pas une anomalie de notre
        # part. On ne contrôle que les pointeurs des tags standard.
        if cible not in xrefs and cible != "VOID" and not tag.startswith("_"):
            anomalies.append(Anomalie(n, "pointeur vers un enregistrement absent",
                                      "%s @%s@" % (tag, cible)))
    return anomalies


def _texte_du_fichier(chemin):
    brut = open(chemin, "rb").read()
    for bom, enc in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"),
                     (b"\xef\xbb\xbf", "utf-8")):
        if brut.startswith(bom):
            return brut[len(bom):].decode(enc, "replace")
    return brut.decode("utf-8", "replace")


def _notre_export():
    """Importe chaque fichier du corpus, réexporte, et valide CE QUE NOUS
    écrivons. C'est le seul contrôle qui échappe à notre propre lecteur."""
    from core.application import Application
    from core import gedcom
    import routes
    routes.charger_modules()

    corpus = os.path.join(RACINE, "gitignore", "echantillons")
    fichiers = sorted(glob.glob(os.path.join(corpus, "**", "*.ged"), recursive=True)
                      + glob.glob(os.path.join(corpus, "**", "*.GED"), recursive=True))
    if not fichiers:
        print("Aucun corpus dans %s — validation ignorée." % corpus)
        return 0

    total = 0
    for chemin in fichiers:
        nom = os.path.relpath(chemin, corpus).replace("\\", "/")
        app = Application(tempfile.mkdtemp())
        import routes as R
        R.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "v"})
        try:
            R.dispatch(app, "POST", "/api/import/gedcom/appliquer", {},
                       {"texte": _texte_du_fichier(chemin)})
            sortie = gedcom.exporter(app.base.donnees)
        except Exception as e:                       # noqa: BLE001
            print("%-46s EXPORT IMPOSSIBLE : %s" % (nom, e))
            total += 1
            continue
        anos = valider(sortie)
        etat = "ok" if not anos else "%d anomalie(s)" % len(anos)
        print("%-46s %s" % (nom, etat))
        for a in anos[:5]:
            print(a)
        total += len(anos)
    print("\n%d anomalie(s) dans notre export, sur %d fichiers." % (total, len(fichiers)))
    return 1 if total else 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--export" in sys.argv[1:]:
        return _notre_export()
    if not args:
        print(__doc__)
        return 2
    total = 0
    for chemin in args:
        anos = valider(_texte_du_fichier(chemin))
        print("%s : %s" % (chemin, "conforme" if not anos else "%d anomalie(s)" % len(anos)))
        for a in anos[:20]:
            print(a)
        total += len(anos)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
