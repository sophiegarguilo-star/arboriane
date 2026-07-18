# -*- coding: utf-8 -*-
"""
Test du coffre — chiffrement au repos de la clé API (DPAPI sous Windows).

Exécuter :  python -X utf8 tests/test_coffre.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import coffre                             # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def test_coffre():
    secret = "sk-ant-api03-XYZ-secret-1234"
    stocke = coffre.chiffrer(secret)
    verifie("round-trip conserve le secret", coffre.dechiffrer(stocke) == secret)
    verifie("valeur stockée préfixée (DPAPI/CLAIR)",
            stocke.startswith("DPAPI:") or stocke.startswith("CLAIR:"))
    verifie("secret absent de la valeur stockée", secret not in stocke)
    verifie("vide -> vide (chiffrer)", coffre.chiffrer("") == "")
    verifie("vide -> vide (déchiffrer)", coffre.dechiffrer("") == "")
    verifie("ancien format en clair toléré (non préfixé)",
            coffre.dechiffrer("cle-nue-heritee") == "cle-nue-heritee")
    if coffre.disponible():
        verifie("DPAPI : chiffrement non déterministe (sel aléatoire)",
                coffre.chiffrer(secret) != stocke)
        verifie("DPAPI : préfixe DPAPI utilisé", stocke.startswith("DPAPI:"))


if __name__ == "__main__":
    test_coffre()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
