# -*- coding: utf-8 -*-
"""
Banc de non-régression GEDCOM : un corpus de fichiers RÉELS, une empreinte figée.

Les tests unitaires vérifient ce qu'on a prévu. Ce banc vérifie ce qu'on n'avait
PAS prévu : il importe des fichiers écrits par d'autres logiciels (Heredis, PAF,
FTM, Gramps…), calcule une empreinte de l'arbre obtenu, et la compare à une
référence figée. Toute différence — un lien perdu, une source en moins, une
personne en trop — saute aux yeux à la mise à jour suivante.

C'est ainsi qu'on a découvert qu'un remariage du même couple perdait sa seconde
union : les deux modes d'import ne donnaient pas le même arbre.

    python -X utf8 outils/banc_gedcom.py            # compare à la référence
    python -X utf8 outils/banc_gedcom.py --figer    # (re)fige la référence
    python -X utf8 outils/banc_gedcom.py --detail   # affiche chaque empreinte

Le corpus vit dans gitignore/echantillons/ — ignoré par git : ce sont les
fichiers d'autrui. La référence y vit aussi. Sans corpus, le banc ne s'indigne
pas : il le dit et sort proprement (0), pour ne pas casser une machine neuve.

Sortie non nulle = régression. À lancer avant chaque publication.
"""

import base64
import hashlib
import json
import os
import sys
import tempfile
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ.setdefault("ARBORIANE_SANS_NAVIGATEUR", "1")

from core import modele                        # noqa: E402
from core.application import Application       # noqa: E402
import routes                                  # noqa: E402

routes.charger_modules()

CORPUS = os.path.join(RACINE, "gitignore", "echantillons")
REFERENCE = os.path.join(CORPUS, "reference.json")
MODES = (("remplacer", "/api/import/gedcom/appliquer"),
         ("fusionner", "/api/import/gedcom/fusionner"))
LENT_MS = 5000          # au-delà, on le signale : une lenteur est une régression


def _est_gedcom(chemin):
    """Un GEDCOM commence par « 0 HEAD » (après un éventuel BOM). Un
    téléchargement raté rend une page HTML avec la bonne extension : on l'a vu.
    Le banc refuse de mesurer ce qu'il n'a pas identifié."""
    with open(chemin, "rb") as f:
        debut = f.read(64)
    for bom in (b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff"):
        if debut.startswith(bom):
            debut = debut[len(bom):]
    return debut.lstrip().replace(b"\x00", b"").startswith(b"0 HEAD")


def _fichiers():
    for dossier, _, noms in os.walk(CORPUS):
        for n in sorted(noms):
            if not n.lower().endswith((".ged", ".gedcom")):
                continue
            chemin = os.path.join(dossier, n)
            if _est_gedcom(chemin):
                yield chemin
            else:
                print("   ignoré (pas un GEDCOM) : %s"
                      % os.path.relpath(chemin, CORPUS))


def _empreinte(donnees):
    """Résumé stable d'un arbre importé. Les compteurs disent QUOI a changé ;
    le condensé du graphe dit QUE quelque chose a changé, même à compteurs égaux
    (deux enfants échangés de famille, par exemple)."""
    inds, fams = donnees["individus"], donnees["familles"]
    liens = morts = 0
    for f in fams.values():
        for role in ("mari", "epouse"):
            if f.get(role):
                liens += 1
                morts += f[role] not in inds
        for c in f.get("enfants") or []:
            liens += 1
            morts += c not in inds

    # Le graphe est décrit par les PERSONNES, jamais par leurs identifiants :
    # « Fusionner » renumérote (I1, I2…), « Remplacer » garde les xrefs du
    # fichier. Une empreinte fondée sur les ids ne comparerait que la
    # numérotation, et croirait à une régression à chaque import.
    def qui(pid):
        ind = inds.get(pid)
        if ind is None:
            return "?%s" % pid
        return "%s#%s" % (modele.nom_complet(ind), modele.annee_naissance(ind) or "")

    graphe = sorted(
        "%s|%s|%s" % (qui(f["mari"]) if f.get("mari") else "",
                      qui(f["epouse"]) if f.get("epouse") else "",
                      ",".join(sorted(qui(c) for c in (f.get("enfants") or []))))
        for f in fams.values())
    condense = hashlib.sha1("\n".join(graphe).encode("utf-8")).hexdigest()[:12]

    return {"personnes": len(inds), "familles": len(fams),
            "sources": len(donnees.get("sources") or {}),
            "depots": len(donnees.get("depots") or {}),
            "lieux": len(donnees.get("lieux") or {}),
            "liens": liens, "pointeurs_morts": morts,
            "graphe": condense}


def _importer(chemin, url):
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "banc"})
    b64 = base64.b64encode(open(chemin, "rb").read()).decode("ascii")
    debut = time.perf_counter()
    code, rep = routes.dispatch(app, "POST", url, {}, {"octets_b64": b64})
    ms = int((time.perf_counter() - debut) * 1000)
    if code != 200:
        return {"erreur": "HTTP %s : %s" % (code, rep)}, ms
    return _empreinte(app.base.donnees), ms


def mesurer(detail=False):
    resultats = {}
    for chemin in _fichiers():
        nom = os.path.relpath(chemin, CORPUS).replace("\\", "/")
        for mode, url in MODES:
            try:
                emp, ms = _importer(chemin, url)
            except Exception as e:                       # noqa: BLE001
                emp, ms = {"erreur": "%s: %s" % (type(e).__name__, e)}, 0
            resultats["%s [%s]" % (nom, mode)] = emp
            if detail:
                print("%-52s %-10s %s%s" % (nom[:52], mode, emp,
                                            "  ⏱ %d ms" % ms if ms > LENT_MS else ""))
            elif ms > LENT_MS:
                print("   lent : %s [%s] — %d ms" % (nom, mode, ms))
    return resultats


def divergences_entre_modes(resultats):
    """« Remplacer » et « Fusionner » dans un arbre VIDE doivent rendre le même
    arbre. Toute divergence est un bug de l'un des deux — c'est ce contrôle qui a
    révélé le remariage perdu, puis les homonymes fusionnés à tort."""
    par_fichier = {}
    for cle, emp in resultats.items():
        nom, mode = cle.rsplit(" [", 1)
        par_fichier.setdefault(nom, {})[mode.rstrip("]")] = emp
    ecarts = []
    for nom, modes in sorted(par_fichier.items()):
        r, f = modes.get("remplacer"), modes.get("fusionner")
        if r and f and r != f:
            champs = sorted(set(r) | set(f))
            ecarts.append((nom, [(c, r.get(c), f.get(c))
                                 for c in champs if r.get(c) != f.get(c)]))
    return ecarts


def comparer(actuel, reference):
    """Renvoie (nouveaux, disparus, changes)."""
    a, r = set(actuel), set(reference)
    changes = [(c, reference[c], actuel[c]) for c in sorted(a & r)
               if reference[c] != actuel[c]]
    return sorted(a - r), sorted(r - a), changes


def main():
    args = sys.argv[1:]
    if not os.path.isdir(CORPUS) or not any(_fichiers()):
        print("Aucun corpus dans %s — banc ignoré." % CORPUS)
        print("(Les fichiers d'exemple ne sont pas versionnés : voir le README "
              "du dossier.)")
        return 0

    actuel = mesurer(detail="--detail" in args)
    print("\n%d imports mesurés." % len(actuel))

    ecarts = divergences_entre_modes(actuel)
    if ecarts:
        print("\nLes deux modes d'import ne rendent PAS le même arbre :")
        for nom, champs in ecarts:
            print("  %s" % nom)
            for c, r, f in champs:
                print("      %-16s remplacer %s   fusionner %s" % (c, r, f))
    else:
        print("« Remplacer » et « Fusionner » rendent le même arbre partout.")

    if "--figer" in args:
        os.makedirs(CORPUS, exist_ok=True)
        with open(REFERENCE, "w", encoding="utf-8") as f:
            json.dump(actuel, f, ensure_ascii=False, indent=1, sort_keys=True)
        print("Référence figée : %s" % REFERENCE)
        return 0

    if not os.path.exists(REFERENCE):
        print("Aucune référence. Vérifiez la sortie, puis figez-la :")
        print("   python -X utf8 outils/banc_gedcom.py --figer")
        return 1

    with open(REFERENCE, encoding="utf-8") as f:
        reference = json.load(f)
    nouveaux, disparus, changes = comparer(actuel, reference)

    for n in nouveaux:
        print("  + nouveau  %s  %s" % (n, actuel[n]))
    for d in disparus:
        print("  - disparu  %s" % d)
    for cle, avant, apres in changes:
        print("  ! CHANGÉ   %s" % cle)
        for champ in sorted(set(avant) | set(apres)):
            va, vp = avant.get(champ), apres.get(champ)
            if va != vp:
                print("      %-16s %s  ->  %s" % (champ, va, vp))

    if changes:
        print("\nRÉGRESSION : %d import(s) ne rendent plus le même arbre." % len(changes))
        print("Si le changement est VOULU, refigez la référence (--figer) et "
              "dites dans le commit pourquoi l'arbre a changé.")
        return 1
    if nouveaux or disparus:
        print("\nLe corpus a bougé (aucune régression). Refigez : --figer")
        return 0
    print("Aucune régression : les %d imports rendent exactement le même arbre."
          % len(actuel))
    return 0


if __name__ == "__main__":
    sys.exit(main())
