# -*- coding: utf-8 -*-
"""
Tests des correctifs issus de l'audit (1.5.8).

Exécuter :  python -X utf8 tests/test_audit.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import securite                            # noqa: E402
from core import stockage                            # noqa: E402
from core import modele                              # noqa: E402
from services import import_avance                   # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _base():
    d = tempfile.mkdtemp()
    return stockage.Base(os.path.join(d, "arboriane.json"),
                         os.path.join(d, "Sauvegardes"))


def test_lecture_anti_rebinding():
    verifie("lecture : hôte externe refusé (403)",
            securite.verifier_lecture({"Host": "evil.com"})[0] == 403)
    verifie("lecture : hôte local accepté",
            securite.verifier_lecture({"Host": "127.0.0.1:8770"}) is None)


def test_ajouter_enfant_fams_pendant():
    """Un pointeur fams pendant ne doit plus crasher (KeyError -> 500)."""
    b = _base()
    b.creer_individu({"id": "I1", "prenoms": "Jean", "nom": "Martin"})
    b.creer_individu({"id": "I2", "prenoms": "Petit", "nom": "Martin"})
    # Corrompt volontairement : I1 pointe une famille inexistante.
    b.donnees["individus"]["I1"]["fams"] = ["F404"]
    try:
        fam = b.ajouter_enfant("I1", "I2")
        ok = fam is not None and "I2" in fam["enfants"]
    except Exception:
        ok = False
    verifie("ajouter_enfant : pas de crash sur fams pendant", ok)


def test_remplacer_recalc_liens():
    """remplacer() doit réaligner fams/famc sur la table des familles
    (GEDCOM asymétrique : la famille cite le mari, mais l'INDI n'a pas de fams)."""
    b = _base()
    donnees = modele.base_vide()
    donnees["individus"]["I1"] = {"id": "I1", "prenoms": "A", "nom": "X",
                                  "fams": [], "famc": []}
    donnees["individus"]["I2"] = {"id": "I2", "prenoms": "B", "nom": "Y",
                                  "fams": [], "famc": []}
    donnees["familles"]["F1"] = {"id": "F1", "mari": "I1", "epouse": "I2",
                                 "enfants": []}
    b.remplacer(donnees)
    verifie("remplacer : fams reconstruit depuis les familles",
            b.donnees["individus"]["I1"]["fams"] == ["F1"])


def test_import_sources_reindex():
    """Les sources importées reçoivent de NOUVEAUX ids et les citations sont
    réécrites — pas de collision avec une source existante de même id."""
    donnees = modele.base_vide()
    donnees["sources"]["S1"] = {"id": "S1", "titre": "Acte de mariage (existant)"}
    nouveau = {"sources": {"S1": {"id": "S1", "titre": "Recensement (importé)"}},
               "depots": {}, "lieux": {}}
    carte = import_avance._importer_sources(nouveau, donnees)
    ns = carte.get("S1")
    verifie("import sources : nouvel id distinct", ns is not None and ns != "S1")
    verifie("import sources : source existante intacte",
            donnees["sources"]["S1"]["titre"] == "Acte de mariage (existant)")
    verifie("import sources : source importée ajoutée sous le nouvel id",
            donnees["sources"][ns]["titre"] == "Recensement (importé)")
    # une citation importée « S1 » doit être réécrite vers le nouvel id
    ind = {"citations": [{"source": "S1", "page": "vue 3"}]}
    import_avance._remap_citations_personne(ind, carte)
    verifie("import sources : citation réécrite vers le nouvel id",
            ind["citations"][0]["source"] == ns)


if __name__ == "__main__":
    test_lecture_anti_rebinding()
    test_ajouter_enfant_fams_pendant()
    test_remplacer_recalc_liens()
    test_import_sources_reindex()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
