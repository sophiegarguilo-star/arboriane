# -*- coding: utf-8 -*-
"""
Routes système : identité de l'instance et version.

- GET /api/version  → {version, build} : consommé par le navigateur (handshake
  anti-cache : si le build a changé, le front se recharge) et par la page Aide.
- GET /api/systeme  → {app, dossier, version, pid} : identité de CETTE instance
  (utile au diagnostic et pour distinguer deux dossiers de données).
"""

import os

from core.version import VERSION, BUILD
from routes import route


@route("GET", r"^/api/version$")
def version(app, params, corps):
    return {"version": VERSION, "build": BUILD}


@route("GET", r"^/api/systeme$")
def systeme(app, params, corps):
    return {
        "app": "arboriane",
        "dossier": os.path.abspath(app.dossier_app),
        "version": VERSION,
        "pid": os.getpid(),
    }
