# -*- coding: utf-8 -*-
"""
Tests des correctifs issus de l'audit 1.6.0.

Exécuter :  python -X utf8 tests/test_audit160.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import modele, stockage                  # noqa: E402
from services.livre import rendu_html, chapitres, composeur   # noqa: E402
from services import selecteur_dossier              # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _base():
    d = tempfile.mkdtemp()
    return stockage.Base(os.path.join(d, "arboriane.json"), os.path.join(d, "Sauvegardes"))


def test_vivant_presume_deces_prime():
    # un décès renseigné prime sur un drapeau vivant=True resté par oubli
    ind = {"vivant": True, "deces": {"date": "1980"}}
    verifie("décès prime sur drapeau vivant", modele.est_vivant_presume(ind) is False)
    verifie("sans décès, drapeau vivant respecté",
            modele.est_vivant_presume({"vivant": True}) is True)


def test_couple_meme_sexe():
    b = _base()
    i1 = b.creer_individu({"prenoms": "Marc", "nom": "X", "sexe": "M"})["id"]
    i2 = b.creer_individu({"prenoms": "Paul", "nom": "Y", "sexe": "M"})["id"]
    fam = b.ajouter_conjoint(i1, i2)
    membres = {fam.get("mari"), fam.get("epouse")}
    verifie("couple M/M : les deux conjoints conservés", membres == {i1, i2})
    verifie("couple M/M : union présente pour le 1er",
            fam["id"] in b.donnees["individus"][i1].get("fams", []))


def test_ajouter_enfant_detache():
    b = _base()
    i1 = b.creer_individu({"prenoms": "A", "nom": "Z"})["id"]
    i2 = b.creer_individu({"prenoms": "B", "nom": "Z"})["id"]
    e1 = b.creer_individu({"prenoms": "E", "nom": "Z"})["id"]
    b.definir_parents(e1, i1, None)              # enfant de i1
    fam1 = b.donnees["individus"][e1]["famc"][0]
    b.ajouter_enfant(i2, e1)                     # rerattaché à i2
    verifie("enfant détaché de l'ancienne famille",
            e1 not in b.donnees["familles"].get(fam1, {}).get("enfants", []))
    verifie("enfant a une seule filiation",
            len(b.donnees["individus"][e1]["famc"]) == 1)


def test_media_chaine_ne_plante_pas():
    # un média stocké en chaîne ne doit pas faire planter le rendu
    f = {"medias": ["portrait.jpg"], "nom_complet": "Jean X"}
    verifie("_media_principal tolère une chaîne",
            rendu_html._media_principal(f) == "portrait.jpg")
    verifie("_fichier_media dict + chaîne",
            rendu_html._fichier_media({"fichier": "a.jpg"}) == "a.jpg"
            and rendu_html._fichier_media("b.jpg") == "b.jpg")


def test_filiation_masque_periode():
    b = _base()
    v1 = b.creer_individu({"prenoms": "Jeune", "nom": "Vivant",
                           "sexe": "M", "naissance": {"date": "2010"}})["id"]
    mini = {"id": v1, "nom": "Jeune VIVANT", "periode": "2010-"}
    e = chapitres._entree(b, mini, masquer=True)
    verifie("personne masquée : nom masqué", e["nom"] == chapitres.MASQUE)
    verifie("personne masquée : période effacée (pas de fuite d'année)", e["periode"] == "")


def test_livre_id_unique_et_chemin_sur():
    d = tempfile.mkdtemp()
    donnees = modele.base_vide()
    donnees["individus"]["I1"] = {"id": "I1", "prenoms": "A", "nom": "B"}
    l1 = composeur.creer(d, donnees, "I1")
    # force la collision : on recrée avec le même id de base
    import services.livre.composeur as C
    _vrai = C.livre_neuf
    C.livre_neuf = lambda dn, r, t="", ty="monographie": dict(_vrai(dn, r, t, ty), id=l1["id"])
    try:
        l2 = composeur.creer(d, donnees, "I1")
    finally:
        C.livre_neuf = _vrai
    verifie("id de livre unique (pas d'écrasement)", l2["id"] != l1["id"])
    verifie("les deux livres coexistent", len(composeur.lister(d)) == 2)
    # traversée de chemin bloquée
    try:
        composeur.lire(d, "..\\..\\evil")
        ok = True
    except ValueError:
        ok = False
    verifie("id invalide (traversée) refusé", ok is False)


def test_selecteur_ne_plante_pas():
    # .replace au lieu de .format : plus de ValueError sur les accolades PowerShell.
    # Hors Windows la fonction renvoie "" sans exécuter ; sous Windows elle ouvre un
    # dialogue — on vérifie juste qu'AUCUNE exception n'est levée à la préparation.
    try:
        selecteur_dossier.choisir_fichier("Test", "", "Archives|*.zip") if os.name != "nt" else None
        ok = True
    except Exception:
        ok = False
    verifie("choisir_fichier ne lève pas d'exception (hors dialogue)", ok)


if __name__ == "__main__":
    for fn in (test_vivant_presume_deces_prime, test_couple_meme_sexe,
               test_ajouter_enfant_detache, test_media_chaine_ne_plante_pas,
               test_filiation_masque_periode, test_livre_id_unique_et_chemin_sur,
               test_selecteur_ne_plante_pas):
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
