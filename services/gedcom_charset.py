# -*- coding: utf-8 -*-
"""
Détection d'encodage GEDCOM (L12).

Les GEDCOM produits par de vieux logiciels ne sont PAS en UTF-8 : la norme 5.5.1
autorise ANSEL, ANSI (Windows-1252), IBMPC (CP850), UNICODE (UTF-16)… Lus en
UTF-8, les accents se cassent. Ce module détecte l'encodage (BOM + balise
`1 CHAR`) et décode les octets en texte, avec un décodeur ANSEL maison (aucun
codec ANSEL en standard) couvrant les diacritiques courants.

`decoder(octets)` -> (texte, charset, fiable).
"""

import os
import re
import time
import unicodedata

# ANSEL : lettres spéciales (0xA0–0xBF) → Unicode
_ANSEL_LETTRES = {
    0xA1: "Ł", 0xA2: "Ø", 0xA3: "Đ", 0xA4: "Þ", 0xA5: "Æ", 0xA6: "Œ",
    0xA7: "ʹ", 0xA8: "·", 0xAA: "®", 0xAB: "±", 0xAE: "ʼ",
    0xB0: "ʾ", 0xB1: "ł", 0xB2: "ø", 0xB3: "đ", 0xB4: "þ", 0xB5: "æ",
    0xB6: "œ", 0xB7: "ʺ", 0xB8: "ı", 0xB9: "£", 0xBA: "ð",
}
# ANSEL : diacritiques combinants (0xE0–0xFF) — PRÉCÈDENT la lettre de base
_ANSEL_DIACR = {
    0xE1: "̀", 0xE2: "́", 0xE3: "̂", 0xE4: "̃",
    0xE5: "̄", 0xE6: "̆", 0xE7: "̇", 0xE8: "̈",
    0xE9: "̌", 0xEA: "̊", 0xEE: "̋", 0xF0: "̧",
    0xF1: "̨", 0xF2: "̣",
}


def _decoder_ansel(octets):
    out = []
    i, n = 0, len(octets)
    while i < n:
        b = octets[i]
        if b < 0x80:
            out.append(chr(b)); i += 1
        elif b in _ANSEL_DIACR and i + 1 < n:
            base = octets[i + 1]
            base_c = chr(base) if base < 0x80 else _ANSEL_LETTRES.get(base, "")
            out.append(unicodedata.normalize("NFC", base_c + _ANSEL_DIACR[b]))
            i += 2
        elif b in _ANSEL_LETTRES:
            out.append(_ANSEL_LETTRES[b]); i += 1
        else:
            out.append(chr(b)); i += 1        # repli : latin-1
    return "".join(out)


_CHAR = re.compile(r"^\s*1\s+CHAR\s+(\S+)", re.MULTILINE)

_ALIAS = {
    "UTF-8": "utf-8", "UTF8": "utf-8", "UNICODE": "utf-16", "UTF-16": "utf-16",
    "ANSI": "cp1252", "WINDOWS-1252": "cp1252", "CP1252": "cp1252",
    "IBMPC": "cp850", "IBM": "cp850", "CP850": "cp850", "OEM": "cp850",
    "ASCII": "ascii", "ANSEL": "ansel", "LATIN1": "latin-1", "ISO-8859-1": "latin-1",
}

# ── Tables mono-octet EMBARQUÉES (octets 0x80–0xFF) ──────────────────────────
# Arboriane décode les encodages GEDCOM hérités (ANSI/cp1252, IBMPC/cp850,
# Latin-1) SANS dépendre du registre de codecs de l'interpréteur. Motif : dans
# un exe figé (PyInstaller), un codec peut manquer → `bytes.decode('cp1252')`
# lève LookupError et, autrefois, TOUS les accents devenaient « � » chez
# l'utilisateur (bug vécu). Avec une table interne, chaque octet 0x00–0xFF a une
# image définie : le « � » devient IMPOSSIBLE pour ces encodages, quel que soit
# le build, l'installation ou la machine. Octets < 0x80 = ASCII (identité).
# Tables générées à partir des codecs de référence (octets non définis en cp1252
# mappés sur leur identité Latin-1, jamais perdus).
_HAUT_CP1252 = ("€\x81‚ƒ„…†‡ˆ‰Š‹Œ\x8dŽ\x8f\x90‘’“”•–—˜™š›œ\x9džŸ\xa0\xa1\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xab\xac\xad\xae\xaf\xb0\xb1\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xbb\xbc\xbd\xbe\xbf\xc0\xc1\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xcb\xcc\xcd\xce\xcf\xd0\xd1\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xdb\xdc\xdd\xde\xdf\xe0\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xeb\xec\xed\xee\xef\xf0\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xfb\xfc\xfd\xfe\xff")
_HAUT_CP850 = ("\xc7\xfc\xe9\xe2\xe4\xe0\xe5\xe7\xea\xeb\xe8\xef\xee\xec\xc4\xc5\xc9\xe6\xc6\xf4\xf6\xf2\xfb\xf9\xff\xd6\xdc\xf8\xa3\xd8\xd7ƒ\xe1\xed\xf3\xfa\xf1\xd1\xaa\xba\xbf\xae\xac\xbd\xbc\xa1\xab\xbb░▒▓│┤\xc1\xc2\xc0\xa9╣║╗╝\xa2\xa5┐└┴┬├─┼\xe3\xc3╚╔╩╦╠═╬\xa4\xf0\xd0\xca\xcb\xc8ı\xcd\xce\xcf┘┌█▄\xa6\xcc▀\xd3\xdf\xd4\xd2\xf5\xd5\xb5\xfe\xde\xda\xdb\xd9\xfd\xdd\xaf\xb4\xad\xb1‗\xbe\xb6\xa7\xf7\xb8\xb0\xa8\xb7\xb9\xb3\xb2■\xa0")
_HAUT_LATIN1 = "".join(chr(b) for b in range(0x80, 0x100))

# charset détecté → table du haut (0x80–0xFF). ASCII : théoriquement pur < 0x80,
# mais si un octet ≥ 0x80 traîne, Latin-1 le préserve plutôt que de le perdre.
_TABLES = {
    "cp1252": _HAUT_CP1252, "cp850": _HAUT_CP850,
    "latin-1": _HAUT_LATIN1, "ascii": _HAUT_LATIN1,
}


def _decoder_table(octets, haut):
    """Décode octet par octet avec une table embarquée : < 0x80 = ASCII, sinon
    haut[b-0x80]. Aucun codec, aucun échec possible, jamais de « � »."""
    return "".join(chr(b) if b < 0x80 else haut[b - 0x80] for b in octets)


def detecter(octets):
    """Renvoie (charset, fiable). fiable=False si on a dû deviner."""
    if octets[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig", True
    if octets[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16", True
    # Sniff de l'en-tête en Latin-1 PUR (sans codec) : cherche la balise `1 CHAR`.
    tete = "".join(map(chr, octets[:2000]))
    m = _CHAR.search(tete)
    if m:
        cle = m.group(1).strip().upper()
        if cle in _ALIAS:
            return _ALIAS[cle], True
    # UTF-16 SANS BOM (hors-spec, mais des logiciels en produisent) : un fichier
    # texte ne contient JAMAIS d'octet nul ; une forte proportion de 0x00 trahit
    # de l'UTF-16. Sans ce test, la balise « 1 CHAR UNICODE » (elle-même en UTF-16)
    # est illisible au sniff Latin-1 et le fichier partait en charabia. On devine
    # l'ordre par la position des zéros (LE : positions impaires ; BE : paires).
    ech = octets[:4000]
    if ech.count(0) > len(ech) * 0.15:
        impairs = sum(1 for i in range(1, len(ech), 2) if ech[i] == 0)
        pairs = sum(1 for i in range(0, len(ech), 2) if ech[i] == 0)
        return ("utf-16-le" if impairs >= pairs else "utf-16-be"), False
    # pas de balise fiable : UTF-8 si ça passe, sinon ANSI
    try:
        octets.decode("utf-8")
        return "utf-8", False
    except UnicodeDecodeError:
        return "cp1252", False


def _latin1_sans_codec(octets):
    """Décode en Latin-1 SANS dépendre d'aucun codec (chr(0..255) = Latin-1).
    Filet ultime quand le codec cp1252/cp850 manque à l'exécution : c'est arrivé
    dans un exe figé (PyInstaller) chez un utilisateur, où `bytes.decode('cp1252')`
    levait LookupError et l'ancien repli `utf-8,"replace"` transformait TOUS les
    accents en « � ». En Latin-1, é/è/à/â/ê/ç/î/ô/û gardent leur octet 0xA0–0xFF
    (identiques à cp1252) : aucun accent perdu. Seuls 0x80–0x9F (guillemets
    courbes cp1252) diffèrent — perte cosmétique mineure, jamais un accent."""
    return "".join(map(chr, octets))


def decoder(octets):
    """Décode des octets GEDCOM en (texte, charset, fiable).

    Robustesse : les encodages hérités mono-octet (ANSI/cp1252, IBMPC/cp850,
    Latin-1, ASCII) sont décodés par des TABLES EMBARQUÉES — aucune dépendance au
    registre de codecs de l'interpréteur, donc jamais de « � » même si un exe figé
    a mal empaqueté ses codecs. Seul l'Unicode (utf-8/16) passe par les codecs du
    cœur de Python (toujours présents), avec un filet Latin-1 en dernier recours."""
    if isinstance(octets, str):
        return octets, "utf-8", True
    charset, fiable = detecter(octets)
    if charset == "ansel":
        return _decoder_ansel(octets), "ansel", fiable
    # BOM UTF-8 : on la retire à la main (sans dépendre du codec utf-8-sig), tout
    # en gardant l'étiquette « utf-8-sig » qui renseigne que le fichier avait une BOM.
    if charset == "utf-8-sig" or octets[:3] == b"\xef\xbb\xbf":
        try:
            return octets[3:].decode("utf-8"), "utf-8-sig", fiable
        except (LookupError, UnicodeDecodeError):
            return _latin1_sans_codec(octets[3:]), "latin-1 (secours)", False
    # Encodages hérités : tables internes, décodage infaillible.
    if charset in _TABLES:
        return _decoder_table(octets, _TABLES[charset]), charset, fiable
    # Unicode : codecs du cœur (utf-8/utf-16). Si le fichier a été mal étiqueté
    # (en réalité « ANSI »), Latin-1 sans codec préserve les accents ; utf-8+replace
    # les détruirait. On garde ce filet ultime.
    try:
        return octets.decode(charset), charset, fiable
    except (LookupError, UnicodeDecodeError):
        return _latin1_sans_codec(octets), "latin-1 (secours)", False


def journaliser(dossier, charset, fiable, texte=""):
    """Trace l'encodage retenu lors d'un import dans « journal_encodage.log »
    (demandé par un utilisateur pour diagnostiquer les accents à distance).
    Best-effort : ne jamais faire échouer un import à cause du journal."""
    if not dossier:
        return
    try:
        n = texte.count("�") if texte else 0
        ligne = "%s  charset=%-28s  fiable=%-5s  car_remplacement(�)=%d\n" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), charset, str(bool(fiable)), n)
        with open(os.path.join(dossier, "journal_encodage.log"), "a",
                  encoding="utf-8") as f:
            f.write(ligne)
    except OSError:
        pass


def texte_depuis_corps(corps):
    """(texte, encodage|None) depuis un corps de requête d'import : `octets_b64`
    (octets bruts → détection d'encodage) sinon `texte` (déjà décodé)."""
    import base64
    ob = (corps or {}).get("octets_b64")
    if ob:
        texte, charset, fiable = decoder(base64.b64decode(ob))
        # `perdus` = caractères de remplacement (�) DÉJÀ présents dans le fichier
        # (typiquement un export fait par un logiciel qui avait cassé les accents) :
        # ils sont irrécupérables. On le remonte pour prévenir honnêtement l'utilisateur.
        return texte, {"charset": charset, "fiable": fiable, "perdus": texte.count("�")}
    return ((corps or {}).get("texte") or ""), None
