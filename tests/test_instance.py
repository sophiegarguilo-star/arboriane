# -*- coding: utf-8 -*-
"""
Test de l'instance unique (verrou OS) et des routes système.

Exécuter :  python -X utf8 tests/test_instance.py
"""

import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import instance                    # noqa: E402
from core.application import Application      # noqa: E402
from core.version import VERSION             # noqa: E402
import routes                                # noqa: E402

routes.charger_modules()

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_verrou():
    d = tempfile.mkdtemp()
    verifie("1re acquisition : on obtient le verrou", instance.acquerir(d) is True)
    # Une 2e tentative (autre descripteur) échoue : le verrou est déjà tenu.
    verifie("2e acquisition refusée (verrou tenu)", instance.acquerir(d) is False)
    instance.liberer(d)
    verifie("après libération : ré-acquisition possible", instance.acquerir(d) is True)
    instance.liberer(d)


def test_infos():
    d = tempfile.mkdtemp()
    verifie("lire_infos absent -> {}", instance.lire_infos(d) == {})
    instance.ecrire_infos(d, {"pid": os.getpid(), "port": 8770,
                              "url": "http://127.0.0.1:8770/", "version": VERSION})
    lu = instance.lire_infos(d)
    verifie("infos : port relu", lu.get("port") == 8770)
    verifie("infos : url relue", lu.get("url") == "http://127.0.0.1:8770/")
    # liberer retire instance.json quand il nous appartient (même pid)
    instance.acquerir(d)
    instance.liberer(d)
    verifie("liberer efface instance.json (même pid)", instance.lire_infos(d) == {})


def test_routes_systeme():
    app = Application(tempfile.mkdtemp())
    code, v = routes.dispatch(app, "GET", "/api/version", {}, {})
    verifie("/api/version -> 200", code == 200)
    verifie("/api/version : version = source unique", v.get("version") == VERSION)
    verifie("/api/version : build présent", bool(v.get("build")))
    code, s = routes.dispatch(app, "GET", "/api/systeme", {}, {})
    verifie("/api/systeme -> 200", code == 200)
    verifie("/api/systeme : app == arboriane", s.get("app") == "arboriane")
    verifie("/api/systeme : dossier = dossier_app",
            os.path.normcase(s.get("dossier", "")) == os.path.normcase(app.dossier_app))


if __name__ == "__main__":
    test_verrou()
    test_infos()
    test_routes_systeme()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
