# -*- coding: utf-8 -*-
"""
Coffre local — protège un secret (la clé API de l'assistant) AU REPOS.

Sous Windows, chiffre via DPAPI (CryptProtectData / CryptUnprotectData, portée
« utilisateur courant ») au travers de ctypes : le secret n'est déchiffrable
QUE par le compte Windows qui l'a écrit, et seulement sur cette machine. Aucune
dépendance (ctypes fait partie de la bibliothèque standard).

Ainsi une copie du fichier de réglages (autre compte local, PC volé non chiffré,
dossier synchronisé sur un cloud) devient illisible.

Repli quand DPAPI est indisponible (autre OS, ou appel en échec) : le secret est
seulement encodé en base64 et EXPLICITEMENT marqué « CLAIR: » ; `disponible()`
renvoie alors False, pour que l'appelant sache que la protection n'est pas active.

Format de stockage — une chaîne préfixée, sûre à placer dans un JSON :
    "DPAPI:<base64 du blob chiffré>"   (protégé)
    "CLAIR:<base64 du texte>"          (repli non protégé, hors Windows)
Une valeur SANS préfixe est traitée comme une ancienne clé en clair (migration).
"""

import base64
import sys

_PREF_DPAPI = "DPAPI:"
_PREF_CLAIR = "CLAIR:"


def disponible():
    """Vrai si le chiffrement réel (DPAPI) est opérationnel sur ce poste."""
    return _moteur() is not None


def chiffrer(clair):
    """Texte clair -> chaîne stockable préfixée. '' -> ''."""
    if not clair:
        return ""
    data = clair.encode("utf-8")
    m = _moteur()
    if m is None:
        return _PREF_CLAIR + base64.b64encode(data).decode("ascii")
    return _PREF_DPAPI + base64.b64encode(m.proteger(data)).decode("ascii")


def dechiffrer(stocke):
    """Chaîne stockée -> texte clair. Tolérante à l'ancien format non préfixé
    (clé en clair d'avant la sécurisation). '' -> ''."""
    if not stocke:
        return ""
    if stocke.startswith(_PREF_DPAPI):
        m = _moteur()
        if m is None:
            return ""                        # chiffré ailleurs : illisible ici
        try:
            return m.deproteger(base64.b64decode(stocke[len(_PREF_DPAPI):])).decode("utf-8")
        except Exception:
            return ""
    if stocke.startswith(_PREF_CLAIR):
        try:
            return base64.b64decode(stocke[len(_PREF_CLAIR):]).decode("utf-8")
        except Exception:
            return ""
    return stocke                            # ancien format : clé en clair


# ── DPAPI via ctypes (Windows) ────────────────────────────────────────────
_MEMO = []


def _moteur():
    """Instance DPAPI opérationnelle, ou None. Résultat mémoïsé (auto-test)."""
    if _MEMO:
        return _MEMO[0]
    moteur = None
    if sys.platform == "win32":
        try:
            m = _Dpapi()
            if m.deproteger(m.proteger(b"arboriane")) == b"arboriane":
                moteur = m                   # round-trip validé
        except Exception:
            moteur = None
    _MEMO.append(moteur)
    return moteur


class _Dpapi:
    """Enveloppe minimale de CryptProtectData / CryptUnprotectData."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self._ct = ctypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char))]
        self._BLOB = DATA_BLOB

        crypt = ctypes.windll.crypt32
        pblob = ctypes.POINTER(DATA_BLOB)
        for fn in (crypt.CryptProtectData, crypt.CryptUnprotectData):
            fn.argtypes = [pblob, wintypes.LPCWSTR, pblob, ctypes.c_void_p,
                           ctypes.c_void_p, wintypes.DWORD, pblob]
            fn.restype = wintypes.BOOL
        self._protect = crypt.CryptProtectData
        self._unprotect = crypt.CryptUnprotectData
        self._free = ctypes.windll.kernel32.LocalFree

    def _blob(self, data):
        buf = self._ct.create_string_buffer(data, len(data))
        blob = self._BLOB(len(data),
                          self._ct.cast(buf, self._ct.POINTER(self._ct.c_char)))
        return blob, buf                     # buf gardé vivant par l'appelant

    def _appliquer(self, fonction, data):
        entree, _vivant = self._blob(data)
        sortie = self._BLOB()
        ok = fonction(self._ct.byref(entree), None, None, None, None, 0,
                      self._ct.byref(sortie))
        if not ok:
            raise OSError("DPAPI a échoué")
        try:
            return self._ct.string_at(sortie.pbData, sortie.cbData)
        finally:
            self._free(self._ct.cast(sortie.pbData, self._ct.c_void_p))

    def proteger(self, data):
        return self._appliquer(self._protect, data)

    def deproteger(self, data):
        return self._appliquer(self._unprotect, data)
