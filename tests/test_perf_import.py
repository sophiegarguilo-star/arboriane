# -*- coding: utf-8 -*-
"""GED-03 — l'import fusionnant ne doit plus être quadratique.

Constat d'audit : 107 s pour fusionner un GEDCOM de 10 Mo. Trois foyers :
  - le balayage répété de la liste des familles « libres » (remplacé par un
    index {(mari, epouse): [fids]} construit AVANT la boucle) ;
  - les « item not in liste » de _completer (remplacés par des ensembles de
    clés JSON sérialisées) ;
  - modele.nouvel_id rappelé pour chaque ajout, qui rebalaye la table depuis 1
    (remplacé par un distributeur local qui rend la MÊME suite d'identifiants).

Ce test chronomètre grossièrement (2 000 familles < 10 s) et vérifie surtout
que l'EMPREINTE du résultat n'a pas changé : mêmes personnes, mêmes liens,
mêmes identifiants, même arbre que le mode « Remplacer ».

Exécuter :  python -X utf8 tests/test_perf_import.py
"""

import hashlib
import os
import sys
import tempfile
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core import modele                          # noqa: E402
from core.application import Application         # noqa: E402
from services import import_avance               # noqa: E402
import routes                                    # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _arbre_vide():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "P"})
    return app


def _gedcom_synthetique(n_familles):
    """GEDCOM de n familles (père, mère, enfant — tous distincts)."""
    lignes = ["0 HEAD", "1 GEDC", "2 VERS 5.5.1", "1 CHAR UTF-8"]
    num = 1
    for f in range(1, n_familles + 1):
        mari, epouse, enfant = num, num + 1, num + 2
        num += 3
        annee = 1500 + (f % 400)
        lignes += ["0 @I%d@ INDI" % mari, "1 NAME Pierre%d /FAMILLE%d/" % (f, f),
                   "1 SEX M", "1 BIRT", "2 DATE %d" % annee]
        lignes += ["0 @I%d@ INDI" % epouse, "1 NAME Jeanne%d /EPOUSE%d/" % (f, f),
                   "1 SEX F", "1 BIRT", "2 DATE %d" % annee]
        lignes += ["0 @I%d@ INDI" % enfant, "1 NAME Petit%d /FAMILLE%d/" % (f, f),
                   "1 SEX M", "1 BIRT", "2 DATE %d" % (annee + 25)]
        lignes += ["0 @F%d@ FAM" % f, "1 HUSB @I%d@" % mari,
                   "1 WIFE @I%d@" % epouse, "1 CHIL @I%d@" % enfant]
    lignes.append("0 TRLR")
    return "\n".join(lignes)


def _empreinte_graphe(donnees):
    """Empreinte de l'arbre INDÉPENDANTE des identifiants (même logique que
    outils/banc_gedcom.py) : les familles décrites par leurs personnes."""
    inds, fams = donnees["individus"], donnees["familles"]

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
    return (len(inds), len(fams),
            hashlib.sha1("\n".join(graphe).encode("utf-8")).hexdigest())


# Petit cas « complet » : remariage du même couple (deux FAM), un enfant,
# une source citée — tout ce que l'optimisation aurait pu casser.
PETIT = """0 HEAD
1 GEDC
2 VERS 5.5.1
1 CHAR UTF-8
0 @S1@ SOUR
1 TITL Registre de Mantoue
0 @I1@ INDI
1 NAME Peter /Sweet/
1 SEX M
1 BIRT
2 DATE 1875
2 SOUR @S1@
0 @I2@ INDI
1 NAME Mary /Encore/
1 SEX F
1 BIRT
2 DATE 1878
0 @I3@ INDI
1 NAME Paul /Sweet/
1 SEX M
1 BIRT
2 DATE 1901
0 @F1@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 CHIL @I3@
1 MARR
2 DATE 1 JAN 1900
1 DIV
2 DATE 10 OCT 1910
0 @F2@ FAM
1 HUSB @I1@
1 WIFE @I2@
1 MARR
2 DATE 1 JAN 1912
0 TRLR
"""


def test_vitesse_2000_familles():
    """2 000 familles (6 000 personnes) doivent fusionner en moins de 10 s.
    Avant correction, l'allocation d'identifiants seule prenait déjà ~3,5 s à
    cette taille, et le tout explosait quadratiquement (107 s sur 10 Mo)."""
    app = _arbre_vide()
    texte = _gedcom_synthetique(2000)
    debut = time.perf_counter()
    code, r = routes.dispatch(app, "POST", "/api/import/gedcom/fusionner", {},
                              {"texte": texte})
    duree = time.perf_counter() - debut
    print("      (durée mesurée : %.1f s)" % duree)
    verifie("import : 200", code == 200)
    d = app.base.donnees
    verifie("6 000 personnes importées", len(d["individus"]) == 6000)
    verifie("2 000 familles importées", len(d["familles"]) == 2000)
    verifie("moins de 10 s (avant : quadratique)", duree < 10)


def test_empreinte_inchangee_petit_cas():
    """« Fusionner » dans un arbre vide doit rendre le même arbre que
    « Remplacer » — remariage, enfant et source compris."""
    a1 = _arbre_vide()
    routes.dispatch(a1, "POST", "/api/import/gedcom/fusionner", {}, {"texte": PETIT})
    a2 = _arbre_vide()
    routes.dispatch(a2, "POST", "/api/import/gedcom/appliquer", {}, {"texte": PETIT})
    e1, e2 = _empreinte_graphe(a1.base.donnees), _empreinte_graphe(a2.base.donnees)
    verifie("même empreinte fusionner/remplacer %s" % (e1,), e1 == e2)
    verifie("les deux unions du remariage survivent",
            len(a1.base.donnees["familles"]) == 2)
    verifie("la source est importée", len(a1.base.donnees["sources"]) == 1)


def test_identifiants_identiques_a_nouvel_id():
    """Le distributeur local doit rendre EXACTEMENT la même suite que des
    appels répétés à modele.nouvel_id (trous comblés en ordre croissant)."""
    # table à trous : I2 et I5 libres, puis I7, I8…
    table = {"I1": 1, "I3": 1, "I4": 1, "I6": 1}
    temoin = dict(table)
    suivant = import_avance._distributeur_ids(table, "I")
    obtenus, attendus = [], []
    for _ in range(6):
        nid = suivant(); table[nid] = 1
        obtenus.append(nid)
        aid = modele.nouvel_id(temoin, "I"); temoin[aid] = 1
        attendus.append(aid)
    verifie("même suite d'identifiants %s" % obtenus, obtenus == attendus)
    verifie("les trous sont comblés d'abord", obtenus[:2] == ["I2", "I5"])


def test_completer_dedoublonne_comme_avant():
    """_completer passe par des clés JSON : même résultat que « not in liste »,
    y compris pour des dicts égaux aux champs écrits dans un autre ordre."""
    actuel = {"professions": [{"valeur": "forgeron", "date": ""}],
              "naissance": {"date": "1900", "lieu": "",
                            "citations": [{"source": "S1", "page": "3"}]}}
    entrant = {"professions": [{"date": "", "valeur": "forgeron"},   # doublon (ordre ≠)
                               {"valeur": "maire", "date": ""}],     # nouveau
               "naissance": {"citations": [{"page": "3", "source": "S1"},  # doublon
                                           {"source": "S2", "page": ""}]}}  # nouveau
    completes = import_avance._completer(actuel, entrant)
    verifie("le doublon de profession n'est pas rajouté",
            [p["valeur"] for p in actuel["professions"]] == ["forgeron", "maire"])
    verifie("la citation en double n'est pas rajoutée",
            len(actuel["naissance"]["citations"]) == 2)
    verifie("les champs complétés sont annoncés",
            "professions" in completes and "naissance" in completes)
    # rien à ajouter -> rien d'annoncé
    verifie("re-compléter à l'identique ne signale rien",
            import_avance._completer(actuel, entrant) == [])


def test_fusion_double_reste_idempotente():
    """Fusionner deux fois le même fichier ne duplique ni personnes, ni
    familles, ni citations (le dédoublonnage sérialisé fait le même travail
    que l'ancien « not in »)."""
    app = _arbre_vide()
    routes.dispatch(app, "POST", "/api/import/gedcom/fusionner", {}, {"texte": PETIT})
    e1 = _empreinte_graphe(app.base.donnees)
    routes.dispatch(app, "POST", "/api/import/gedcom/fusionner", {}, {"texte": PETIT})
    e2 = _empreinte_graphe(app.base.donnees)
    verifie("même empreinte après la seconde fusion", e1 == e2)


if __name__ == "__main__":
    for t in (test_vitesse_2000_familles, test_empreinte_inchangee_petit_cas,
              test_identifiants_identiques_a_nouvel_id,
              test_completer_dedoublonne_comme_avant,
              test_fusion_double_reste_idempotente):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
