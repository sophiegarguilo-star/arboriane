# -*- coding: utf-8 -*-
"""UX-03 — Suppression de personne RÉVERSIBLE (Corbeille/).

Avant : supprimer une personne était définitif (la confirmation était le seul
filet). Désormais :

  - avant chaque suppression, un instantané JSON {fiche complète, liens
    familiaux (famille + rôle + place), favori, ensembles} est déposé dans
    <arbre>/Corbeille/ (les 20 derniers sont gardés) ;
  - POST /api/individus/restaurer-dernier rejoue le dernier instantané : la
    personne revient SOUS SON ID D'ORIGINE (jamais recyclé, compteurs
    monotones) et ses liens sont retissés dans les familles encore existantes.

Exécuter :  python -X utf8 tests/test_corbeille.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application         # noqa: E402
import routes                                    # noqa: E402

routes.charger_modules()
_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _ged(*lignes):
    return "\n".join(("0 HEAD", "1 GEDC", "2 VERS 5.5.1", "1 CHAR UTF-8")
                     + lignes + ("0 TRLR",)) + "\n"


_FICHIER = _ged(
    "0 @I1@ INDI", "1 NAME Pierre /DUPONT/", "1 SEX M", "1 FAMS @F1@",
    "0 @I2@ INDI", "1 NAME Marie /MARTIN/", "1 SEX F", "1 FAMS @F1@",
    "0 @I3@ INDI", "1 NAME Jean /DUPONT/", "1 SEX M", "1 FAMC @F1@",
    "0 @I4@ INDI", "1 NAME Luc /DUPONT/", "1 SEX M", "1 FAMC @F1@",
    "0 @F1@ FAM", "1 HUSB @I1@", "1 WIFE @I2@",
    "1 MARR", "2 DATE 12 JUN 1980",
    "1 CHIL @I3@", "1 CHIL @I4@",
)


def _app():
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "Corbeille"})
    routes.dispatch(app, "POST", "/api/import/gedcom/appliquer", {},
                    {"texte": _FICHIER})
    return app


def test_round_trip_enfant():
    """Supprimer un enfant favori puis annuler : tout revient, à sa place."""
    app = _app()
    routes.dispatch(app, "POST", "/api/favoris/basculer", {}, {"id": "I3"})
    code, r = routes.dispatch(app, "POST", "/api/ensembles", {},
                              {"nom": "Cousins", "ids": ["I3", "I4"]})
    eid = r["ensemble"]["id"]

    code, _ = routes.dispatch(app, "DELETE", "/api/individus/I3", {}, {})
    verifie("suppression : 200", code == 200)
    verifie("la personne a bien disparu", "I3" not in app.base.donnees["individus"])
    verifie("retirée des enfants de F1",
            "I3" not in app.base.donnees["familles"]["F1"]["enfants"])
    corbeille = app.base.dossier_corbeille
    verifie("un instantané est déposé dans Corbeille/",
            os.path.isdir(corbeille) and len(os.listdir(corbeille)) == 1)

    code, r = routes.dispatch(app, "POST", "/api/individus/restaurer-dernier", {}, {})
    verifie("restauration : 200 + ok", code == 200 and r.get("ok"))
    verifie("restaurée SOUS SON ID D'ORIGINE", r.get("id") == "I3")
    ind = app.base.donnees["individus"].get("I3") or {}
    verifie("le nom est intact", ind.get("nom") == "DUPONT" and "Jean" in ind.get("prenoms", ""))
    enfants = app.base.donnees["familles"]["F1"]["enfants"]
    verifie("re-rattachée à F1, À SA PLACE (avant I4)",
            enfants == ["I3", "I4"])
    verifie("famc re-dérivé", ind.get("famc") == ["F1"])
    verifie("favori restauré", "I3" in app.base.donnees.get("favoris", {}))
    verifie("membre de l'ensemble restauré",
            "I3" in app.base.donnees["ensembles"][eid]["membres"])
    verifie("l'instantané est consommé (corbeille vide)",
            not [n for n in os.listdir(corbeille) if n.endswith(".json")])

    code, _ = routes.dispatch(app, "POST", "/api/individus/restaurer-dernier", {}, {})
    verifie("plus rien à annuler -> 404", code == 404)


def test_conjoint_et_famille_disparue():
    """Supprimer un conjoint : sa place redevient libre et la restauration la
    reprend — mais JAMAIS en délogeant quelqu'un arrivé entre-temps."""
    app = _app()
    routes.dispatch(app, "DELETE", "/api/individus/I2", {}, {})
    verifie("place d'épouse libérée",
            app.base.donnees["familles"]["F1"].get("epouse") == "")
    code, r = routes.dispatch(app, "POST", "/api/individus/restaurer-dernier", {}, {})
    verifie("conjointe restaurée (200)", code == 200 and r.get("id") == "I2")
    verifie("elle reprend sa place d'épouse",
            app.base.donnees["familles"]["F1"].get("epouse") == "I2")
    verifie("fams re-dérivé",
            app.base.donnees["individus"]["I2"].get("fams") == ["F1"])

    # créneau repris entre-temps : la restauration n'écrase pas
    routes.dispatch(app, "DELETE", "/api/individus/I2", {}, {})
    with app.base._verrou:
        app.base.donnees["familles"]["F1"]["epouse"] = "I4"   # usurpatrice
        app.base.sauvegarder()
    code, r = routes.dispatch(app, "POST", "/api/individus/restaurer-dernier", {}, {})
    verifie("restauration OK même si la place est prise", code == 200)
    verifie("la nouvelle épouse n'est PAS délogée",
            app.base.donnees["familles"]["F1"].get("epouse") == "I4")
    verifie("I2 existe quand même à nouveau",
            "I2" in app.base.donnees["individus"])


def test_id_jamais_recycle():
    """L'id d'origine reste libre après suppression (compteurs monotones) :
    créer quelqu'un entre la suppression et l'annulation ne le vole pas."""
    app = _app()
    routes.dispatch(app, "DELETE", "/api/individus/I4", {}, {})
    code, r = routes.dispatch(app, "POST", "/api/individus", {},
                              {"nom": "NOUVEAU", "prenoms": "Paul"})
    verifie("le nouvel individu ne reprend pas I4", r.get("id") != "I4")
    code, r = routes.dispatch(app, "POST", "/api/individus/restaurer-dernier", {}, {})
    verifie("I4 restauré sous son id d'origine",
            code == 200 and r.get("id") == "I4")


def test_retention_20():
    """La corbeille garde les 20 instantanés les plus récents."""
    app = _app()
    for i in range(23):
        code, r = routes.dispatch(app, "POST", "/api/individus", {},
                                  {"nom": "JETABLE", "prenoms": "N%d" % i})
        routes.dispatch(app, "DELETE", "/api/individus/" + r["id"], {}, {})
    fichiers = [n for n in os.listdir(app.base.dossier_corbeille)
                if n.startswith("personne_") and n.endswith(".json")]
    verifie("au plus 20 instantanés conservés", len(fichiers) == 20)


def test_arbre_a_une_personne():
    """Supprimer LA seule personne puis annuler : la racine se répare."""
    app = Application(tempfile.mkdtemp())
    routes.dispatch(app, "POST", "/api/espaces/creer", {}, {"nom": "Solo"})
    code, r = routes.dispatch(app, "POST", "/api/individus", {},
                              {"nom": "SEULE", "prenoms": "Anne"})
    pid = r["id"]
    routes.dispatch(app, "DELETE", "/api/individus/" + pid, {}, {})
    verifie("arbre vide après suppression",
            not app.base.donnees["individus"])
    code, r = routes.dispatch(app, "POST", "/api/individus/restaurer-dernier", {}, {})
    verifie("restauration : 200", code == 200 and r.get("id") == pid)
    verifie("la racine repointe sur elle",
            app.manifeste.get("racine_id") == pid)


if __name__ == "__main__":
    for t in (test_round_trip_enfant, test_conjoint_et_famille_disparue,
              test_id_jamais_recycle, test_retention_20,
              test_arbre_a_une_personne):
        print(t.__name__)
        t()
    print("\n%d ok, %d ko" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
