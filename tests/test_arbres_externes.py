# -*- coding: utf-8 -*-
"""Torture « arbres extérieurs » : on importe chaque GEDCOM réel du corpus
(gitignore/echantillons — findmypast, 5.5.1 samples : mariages même-sexe,
auto-mariage, familles vides, GoT, Simpsons, Habsburg…) et on fait tourner
TOUTES nos fonctions métier récentes dessus. Objectif : aucune exception sur
des données réelles et biscornues.

Ignoré silencieusement si le corpus n'est pas présent (il est git-ignoré).

Exécuter :  python -X utf8 tests/test_arbres_externes.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import gedcom, modele                                  # noqa: E402
from services import (personnes, coherence, sources, gedcom_dates,  # noqa: E402
                      listes, statistiques, index_pro, sosa, parente)

CORPUS = os.path.join(RACINE, "gitignore", "echantillons")
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _fichiers():
    if not os.path.isdir(CORPUS):
        return []
    out = []
    for dossier, _, noms in os.walk(CORPUS):
        for n in noms:
            if n.lower().endswith((".ged", ".gedcom")):
                out.append(os.path.join(dossier, n))
    return sorted(out)


# Au-delà de ce nombre de personnes, on ne fait que l'import + les catégories
# (les arbres royaux volumineux ne servent qu'à mesurer le débit ; les formes
# vraiment biscornues — même-sexe, auto-mariage, familles vides — sont petites).
_SEUIL_LEGER = 1500


def _passe_tout(donnees, racine):
    """Fait tourner toutes les fonctions métier récentes ; lève si l'une plante."""
    modele.garantir_cles(donnees)
    # catégories / hors-famille (nouveau) — toujours, même sur les gros arbres
    hors = personnes.ids_hors_famille(donnees, racine)
    if len(donnees["individus"]) > _SEUIL_LEGER:
        return hors
    # cohérence avec racine (nouveau : skip hors-famille)
    coherence.analyser(donnees, racine)
    # preuves par fait pour quelques personnes
    for pid in list(donnees["individus"])[:15]:
        sources.preuves_personne(donnees, pid)
    # dates douteuses (nouveau : accepte le FR)
    gedcom_dates.dates_invalides(donnees)
    # listes / stats / index (nouveau : exclusion hors-famille, date d'union)
    listes.unions(donnees)
    statistiques.calculer(donnees, exclure=hors)
    index_pro.index(donnees, exclure=hors)
    if racine:
        sosa.numero_sosa(donnees, racine, racine)
    return hors


def test_corpus_externe():
    fichiers = _fichiers()
    if not fichiers:
        verifie("corpus présent (sinon test ignoré)", True)
        print("  (corpus gitignore/echantillons absent — rien à tester)")
        return
    # Les très gros arbres (Habsburg 10 Mo, Queen 2,5 Mo…) ne testent que le débit
    # d'import, déjà couvert par outils/banc_gedcom.py. Ici on veut la robustesse
    # du métier sur les formes tordues, toutes présentes dans les petits fichiers.
    _MAX = 500 * 1024
    gros = [os.path.relpath(f, CORPUS) for f in fichiers if os.path.getsize(f) > _MAX]
    fichiers = [f for f in fichiers if os.path.getsize(f) <= _MAX]
    verifie("corpus trouvé (%d fichiers testés, %d gros ignorés → banc)"
            % (len(fichiers), len(gros)), True)
    if gros:
        print("  (gros arbres délégués au banc : %s)" % ", ".join(gros))
    plantes = []
    total_ind = 0
    for chemin in fichiers:
        nom = os.path.relpath(chemin, CORPUS).replace("\\", "/")
        try:
            with open(chemin, "rb") as f:
                donnees = gedcom.importer(f.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            plantes.append((nom, "import", type(e).__name__ + ": " + str(e)[:80]))
            continue
        inds = donnees.get("individus", {})
        total_ind += len(inds)
        racine = next(iter(inds), None)      # 1re personne comme référence
        try:
            _passe_tout(donnees, racine)
        except Exception as e:  # noqa: BLE001
            import traceback
            plantes.append((nom, "métier", type(e).__name__ + ": " + str(e)[:120]))
            traceback.print_exc()
    verifie("aucun plantage sur %d arbres (%d personnes)" % (len(fichiers), total_ind),
            not plantes)
    for nom, phase, err in plantes:
        print("     ✗ %s [%s] %s" % (nom, phase, err))


if __name__ == "__main__":
    test_corpus_externe()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
