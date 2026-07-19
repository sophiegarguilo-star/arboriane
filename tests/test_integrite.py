# -*- coding: utf-8 -*-
"""Tests d'intégrité du stockage — durabilité disque, rétention des
sauvegardes, chargement défensif et cache de lecture.

Couvre : écritures atomiques + fsync (fichiers relisibles), fichier principal
compact vs archives indentées, rétention générationnelle de Sauvegardes/,
plafond des copies CORROMPU_*, JSON corrompu (quarantaine + avertissement
exposé par /api/espace) vs fichier inaccessible (ouverture refusée), et
invalidation du cache de services/personnes.lister après mutation.

Exécuter :  python -X utf8 tests/test_integrite.py
"""

import datetime
import json
import os
import sys
import tempfile
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
os.environ["ARBORIANE_SANS_NAVIGATEUR"] = "1"

from core.application import Application          # noqa: E402
from core import espace as espace_mod             # noqa: E402
from core import instance, stockage               # noqa: E402
from services import personnes as pers_svc        # noqa: E402
import routes                                     # noqa: E402

routes.charger_modules()

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


# ── 1. Écritures durables (fsync) + compact/indenté (DAT-04 / DAT-05) ─────
def test_ecritures_durables():
    app = Application(tempfile.mkdtemp())
    app.creer("Durable")
    base = app.base
    base.creer_individu({"nom": "DUR", "prenoms": "Été"})
    base.sauvegarder(forcer_horodatage=True)
    with open(base.chemin, "r", encoding="utf-8") as f:
        brut = f.read()
    verifie("arboriane.json relisible après fsync",
            "DUR" in json.dumps(json.loads(brut), ensure_ascii=False))
    verifie("arboriane.json COMPACT (sans indentation)", "\n  " not in brut)
    archives = sorted(n for n in os.listdir(base.dossier_sauvegardes)
                      if n.startswith("arboriane_") and n.endswith(".json"))
    verifie("archive horodatée déposée", bool(archives))
    with open(os.path.join(base.dossier_sauvegardes, archives[-1]),
              "r", encoding="utf-8") as f:
        brut_archive = f.read()
    verifie("archive INDENTÉE (lisible à la main)",
            "\n  " in brut_archive and json.loads(brut_archive))
    # les trois autres écritures atomiques : relisibles après coup
    espace_mod.sauver_manifeste(app.espace_chemin, dict(app.manifeste))
    verifie("manifeste relisible", espace_mod.charger(app.espace_chemin) is not None)
    app.ecrire_reglages({"pays_defaut": "France"})
    verifie("réglages relisibles", app.lire_reglages().get("pays_defaut") == "France")
    instance.ecrire_infos(app.dossier_donnees, {"pid": os.getpid(), "port": 1234})
    verifie("instance.json relisible",
            instance.lire_infos(app.dossier_donnees).get("port") == 1234)


# ── 2. Rétention générationnelle (DAT-06) ─────────────────────────────────
def _faux_fichier(dossier, nom, mtime):
    p = os.path.join(dossier, nom)
    with open(p, "w", encoding="utf-8") as f:
        f.write("{}")
    os.utime(p, (mtime, mtime))
    return p


def test_retention_generationnelle():
    app = Application(tempfile.mkdtemp())
    app.creer("Retention")
    base = app.base
    dossier = base.dossier_sauvegardes
    os.makedirs(dossier, exist_ok=True)
    for n in list(os.listdir(dossier)):            # partir d'un dossier net
        os.remove(os.path.join(dossier, n))
    # midi local d'aujourd'hui : évite tout chevauchement de jour calendaire
    midi = time.mktime(datetime.date.today().timetuple()) + 12 * 3600
    par_jour = {}
    for jour in range(1, 11):                      # 10 jours passés, 3 archives/jour
        par_jour[jour] = [
            _faux_fichier(dossier, "arboriane_j%02dk%d.json" % (jour, k),
                          midi - jour * 86400 + k * 3600)
            for k in range(3)]                     # k=0 = la PREMIÈRE du jour
    recentes = [_faux_fichier(dossier, "arboriane_rec%02d.json" % k,
                              midi - (35 - k))     # 35 archives « du jour »
                for k in range(35)]
    corrompus = [_faux_fichier(dossier, "CORROMPU_%02d.json" % k,
                               midi - 1000 + k) for k in range(8)]
    base._purger_sauvegardes(garder=30)
    restants = set(os.listdir(dossier))
    verifie("rétention : les 30 plus récentes gardées",
            all(os.path.basename(p) in restants for p in recentes[5:]))
    verifie("rétention : la 1re archive de chaque jour passé survit",
            all(os.path.basename(par_jour[j][0]) in restants for j in par_jour))
    verifie("rétention : les doublons intrajournaliers passés sont purgés",
            all(os.path.basename(par_jour[j][k]) not in restants
                for j in par_jour for k in (1, 2)))
    verifie("rétention : la 1re archive d'aujourd'hui survit aussi",
            os.path.basename(recentes[0]) in restants)
    corrompus_restants = [n for n in restants if n.startswith("CORROMPU_")]
    verifie("rétention : CORROMPU_* plafonnés à 5", len(corrompus_restants) == 5)
    verifie("rétention : ce sont les 5 CORROMPU les plus récents",
            set(corrompus_restants) == {os.path.basename(p) for p in corrompus[3:]})


# ── 3. Chargement : corrompu (quarantaine) vs inaccessible (refus) DAT-03 ─
def test_chargement_corrompu():
    d = tempfile.mkdtemp()
    chemin = os.path.join(d, "arboriane.json")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("{ ceci n'est pas du JSON")
    base = stockage.Base(chemin, os.path.join(d, "Sauvegardes"))
    verifie("corrompu : avertissement posé", base.avertissement == "corrompu")
    verifie("corrompu : la base repart à vide", base.donnees["individus"] == {})
    verifie("corrompu : copie de quarantaine déposée",
            any(n.startswith("CORROMPU_")
                for n in os.listdir(os.path.join(d, "Sauvegardes"))))


def test_chargement_inaccessible():
    # Un DOSSIER portant le nom du fichier simule un fichier illisible (OSError
    # à l'open) : les données existent peut-être -> on REFUSE d'ouvrir, on ne
    # repart JAMAIS à vide, et rien n'est mis en quarantaine.
    d = tempfile.mkdtemp()
    chemin = os.path.join(d, "arboriane.json")
    os.makedirs(chemin)
    leve = False
    try:
        stockage.Base(chemin, os.path.join(d, "Sauvegardes"))
    except OSError:
        leve = True
    verifie("inaccessible : ouverture refusée (OSError claire)", leve)
    verifie("inaccessible : aucune quarantaine créée",
            not os.path.isdir(os.path.join(d, "Sauvegardes")))


def test_avertissement_expose_api():
    app = Application(tempfile.mkdtemp())
    app.creer("Corrompu")
    # corrompre le fichier de l'arbre PUIS le rouvrir (rechargement disque)
    ch = espace_mod.chemins(app.espace_chemin)
    with open(ch["base"], "w", encoding="utf-8") as f:
        f.write("%%% corrompu %%%")
    app.ouvrir(app.espace_chemin)
    code, p = routes.dispatch(app, "GET", "/api/espace", {}, {})
    verifie("API : GET /api/espace expose avertissement='corrompu'",
            code == 200 and p.get("avertissement") == "corrompu")
    # un arbre sain n'a pas d'avertissement
    app2 = Application(tempfile.mkdtemp())
    app2.creer("Sain")
    code2, p2 = routes.dispatch(app2, "GET", "/api/espace", {}, {})
    verifie("API : arbre sain -> avertissement vide",
            code2 == 200 and p2.get("avertissement") == "")


# ── 4. Cache de personnes.lister invalidé par les mutations (PERF-03) ─────
def test_cache_lister():
    app = Application(tempfile.mkdtemp())
    app.creer("Cache")
    base = app.base
    base.creer_individu({"nom": "UN"})
    l1 = pers_svc.lister(base)
    verifie("cache : même objet tant que rien ne change",
            pers_svc.lister(base) is l1)
    base.creer_individu({"nom": "DEUX"})
    l2 = pers_svc.lister(base)
    verifie("cache : invalidé après création (sauvegarder)",
            l2 is not l1 and len(l2) == len(l1) + 1)
    pid = l2[0]["id"]
    base.modifier_individu(pid, {"prenoms": "Zoé"})
    l3 = pers_svc.lister(base)
    verifie("cache : invalidé après modification",
            l3 is not l2 and any(r["id"] == pid and "Zoé" in r["prenoms"] for r in l3))
    # remplacer() (import) passe aussi par le point unique
    import copy
    base.remplacer(copy.deepcopy(base.donnees))
    verifie("cache : invalidé après remplacer()", pers_svc.lister(base) is not l3)
    # deux racines différentes ne partagent pas leur résultat
    r1 = pers_svc.lister(base, pid)
    verifie("cache : jeton distinct par racine", r1 is not pers_svc.lister(base))


if __name__ == "__main__":
    for fn in (test_ecritures_durables, test_retention_generationnelle,
               test_chargement_corrompu, test_chargement_inaccessible,
               test_avertissement_expose_api, test_cache_lister):
        print(fn.__name__)
        fn()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
