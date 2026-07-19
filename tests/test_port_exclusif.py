# -*- coding: utf-8 -*-
"""Port exclusif (audit 2026-07-18, CARTO-01/DAT-02/PERF-01/TECH-02).

Sous Windows, ThreadingHTTPServer (allow_reuse_address=True) laissait un
DEUXIÈME serveur se lier au même port sans erreur → le navigateur pouvait
lire/écrire dans le mauvais arbre. ServeurArboriane doit refuser (OSError),
pour que la boucle « port suivant » de demarrer() prenne le relais.

Exécuter :  python -X utf8 tests/test_port_exclusif.py
"""

import os
import sys
from http.server import BaseHTTPRequestHandler

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from app import ServeurArboriane            # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass


def test_double_bind_refuse():
    # 1er serveur : prend un port libre choisi par l'OS
    s1 = ServeurArboriane(("127.0.0.1", 0), _H)
    port = s1.server_address[1]
    try:
        verifie("réutilisation désactivée", s1.allow_reuse_address is False)
        # 2e serveur sur le MÊME port : doit échouer franchement
        refuse = False
        try:
            s2 = ServeurArboriane(("127.0.0.1", port), _H)
            s2.server_close()
        except OSError:
            refuse = True
        verifie("2e bind sur le même port → OSError", refuse)
        # la stratégie « port suivant » reste possible
        s3 = ServeurArboriane(("127.0.0.1", 0), _H)
        verifie("un AUTRE port reste disponible", s3.server_address[1] != port)
        s3.server_close()
    finally:
        s1.server_close()


if __name__ == "__main__":
    test_double_bind_refuse()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
