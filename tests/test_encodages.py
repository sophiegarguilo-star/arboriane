# -*- coding: utf-8 -*-
"""Import GEDCOM : détection d'encodage (remarque utilisateur — les exports ANSI
de Brother's Keeper, ANSEL, UTF-16… doivent être lus correctement, pas seulement
l'UTF-8). Et pays par défaut au géocodage.

Exécuter :  python -X utf8 tests/test_encodages.py
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from services import gedcom_charset            # noqa: E402
from services.lieux import _avec_pays_defaut, sans_pays, _variantes_requete   # noqa: E402
from core import gedcom                          # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


def _gedcom(char):
    return ("0 HEAD\n1 CHAR %s\n1 GEDC\n2 VERS 5.5.1\n"
            "0 @I1@ INDI\n1 NAME François /Castagne/\n1 SEX M\n"
            "1 BIRT\n2 PLAC Neufchâteau\n0 TRLR\n" % char)


def _teste_encodage(nom_enc, char, codec):
    octets = _gedcom(char).encode(codec)
    texte, charset, fiable = gedcom_charset.decoder(octets)
    d = gedcom.importer(texte)
    i1 = d["individus"].get("I1", {})
    ok = (i1.get("prenoms") == "François"
          and (i1.get("naissance") or {}).get("lieu") == "Neufchâteau")
    verifie("%s : accents décodés (charset=%s)" % (nom_enc, charset), ok)


def test_encodages():
    _teste_encodage("ANSI (cp1252)", "ANSI", "cp1252")
    _teste_encodage("UTF-8", "UTF-8", "utf-8")
    _teste_encodage("UTF-16 (UNICODE)", "UNICODE", "utf-16")
    # BOM UTF-8 sans balise CHAR fiable
    octets = ("﻿" + _gedcom("UTF-8")).encode("utf-8")
    texte, charset, _ = gedcom_charset.decoder(octets)
    verifie("BOM UTF-8 reconnu", "François" in texte)


def test_ansi_avec_octet_invalide():
    # Retour Michel : un GEDCOM ANSI de Brother's Keeper contenant UN octet non
    # défini en cp1252 (0x81) faisait basculer TOUT le fichier en UTF-8 → tous les
    # accents en « � ». Avec les tables embarquées, l'octet est mappé sur son
    # identité Latin-1 et TOUS les accents sont conservés — ZÉRO « � ».
    octets = ("0 HEAD\n1 CHAR ANSI\n1 GEDC\n2 VERS 5.5.1\n"
              "0 @I1@ INDI\n1 NAME François /Castagné/\n"
              "1 BIRT\n2 PLAC Neufchâteau\n").encode("cp1252") \
             + b"1 NOTE bruit" + bytes([0x81]) \
             + " puis Généalogie\n0 TRLR\n".encode("cp1252")
    texte, charset, _ = gedcom_charset.decoder(octets)
    verifie("ANSI+octet invalide : charset reste cp1252", charset == "cp1252")
    verifie("ANSI+octet invalide : accents conservés",
            "François" in texte and "Neufchâteau" in texte and "Généalogie" in texte)
    verifie("ANSI+octet invalide : aucun « � » (table embarquée)", texte.count("�") == 0)


def test_tables_embarquees_sans_codec():
    """RENFORCEMENT (retour Sophie 2026-07-12) : les encodages hérités (ANSI/cp1252,
    IBMPC/cp850, Latin-1) sont décodés par des TABLES EMBARQUÉES, sans dépendre du
    registre de codecs de l'interpréteur. Un exe qui aurait mal empaqueté ses codecs
    (cas Michel) préserve quand même TOUS les accents : « � » devient impossible."""
    # 1) tables fidèles aux codecs de référence (octets définis)
    for charset, table in (("cp1252", gedcom_charset._HAUT_CP1252),
                           ("cp850", gedcom_charset._HAUT_CP850)):
        ecarts = [hex(b) for b in range(0x80, 0x100)
                  if bytes([b]).decode(charset, "replace") not in ("�", table[b - 0x80])]
        verifie("%s : table fidèle au codec de référence" % charset, not ecarts)
    # 2) les 256 octets, dans chaque encodage, ne produisent JAMAIS de « � »
    for cs in ("cp1252", "cp850", "latin-1", "ascii"):
        txt = gedcom_charset._decoder_table(bytes(range(256)), gedcom_charset._TABLES[cs])
        verifie("%s : 256 octets → 0 « � »" % cs, "�" not in txt and len(txt) == 256)
    # 3) codecs cp1252/cp850 RETIRÉS du registre → accents quand même préservés
    import codecs as _codecs
    ansi = ("1 CHAR ANSI\n1 NAME François /Hébert/ décédé à Nîmes âgé de 80 ans\n"
            ).encode("cp1252")
    ibm = ("1 CHAR IBMPC\n1 NAME Éléonore Drèze\n").encode("cp850")
    orig = _codecs.lookup

    def faux(name):
        n = name.lower().replace("-", "").replace("_", "")
        if n in ("cp1252", "windows1252", "cp850", "ibmpc", "oem850"):
            raise LookupError(name)
        return orig(name)

    _codecs.lookup = faux
    try:
        t1, c1, _ = gedcom_charset.decoder(ansi)
        t2, c2, _ = gedcom_charset.decoder(ibm)
    finally:
        _codecs.lookup = orig
    verifie("codec cp1252 hors registre : 0 « � » + accents intacts",
            t1.count("�") == 0 and "François" in t1 and "décédé à Nîmes âgé" in t1)
    verifie("codec cp850 hors registre : 0 « � » + « Éléonore »",
            t2.count("�") == 0 and "Éléonore" in t2)


def test_utf16_sans_bom():
    # Limitation relevée à l'audit : un UTF-16 SANS BOM (balise « 1 CHAR UNICODE »
    # illisible car elle-même en UTF-16) partait en charabia. Heuristique : forte
    # densité d'octets 0x00 → UTF-16, ordre deviné par la position des zéros.
    for codec, nom in (("utf-16-le", "LE"), ("utf-16-be", "BE")):
        octets = ("0 HEAD\n1 CHAR UNICODE\n0 @I1@ INDI\n1 NAME François /Castagné/\n"
                  "1 BIRT\n2 PLAC Neufchâteau\n0 TRLR\n").encode(codec)   # PAS de BOM
        texte, charset, _ = gedcom_charset.decoder(octets)
        verifie("UTF-16 %s sans BOM : accents lus (charset=%s)" % (nom, charset),
                "François" in texte and "Neufchâteau" in texte and texte.count("�") == 0)
    # Un vrai fichier ANSI (aucun 0x00) ne doit PAS être pris pour de l'UTF-16.
    ansi = ("0 HEAD\n1 CHAR ANSI\n1 NAME Éléonore Drèze\n0 TRLR\n").encode("cp1252")
    _, cs, _ = gedcom_charset.decoder(ansi)
    verifie("ANSI (sans octet nul) non confondu avec UTF-16", cs == "cp1252")


def test_pays_defaut():
    # lieu sans pays -> on ajoute le pays par défaut à la requête
    verifie("lieu sans pays -> pays ajouté",
            _avec_pays_defaut("Neufchâteau", "Belgique") == "Neufchâteau, Belgique")
    # lieu qui a déjà un pays reconnu -> inchangé
    verifie("lieu avec pays -> inchangé",
            _avec_pays_defaut("Paris, France", "Belgique") == "Paris, France")
    # pas de pays par défaut -> inchangé
    verifie("sans réglage -> inchangé",
            _avec_pays_defaut("Neufchâteau", "") == "Neufchâteau")
    # le libellé multi-parties sans pays reçoit quand même le pays
    verifie("multi-parties sans pays -> pays ajouté",
            _avec_pays_defaut("Neufchâteau, Luxembourg (province)", "Belgique")
            == "Neufchâteau, Luxembourg (province), Belgique")


def test_lieux_sans_pays():
    donnees = {"individus": {
        "I1": {"id": "I1", "naissance": {"lieu": "Neufchâteau"},
               "deces": {"lieu": "Paris, France"}},
        "I2": {"id": "I2", "naissance": {"lieu": "Bruxelles, Belgique"},
               "deces": {"lieu": "Namur"}},
    }, "familles": {}}
    noms = {x["nom"] for x in sans_pays(donnees)}
    verifie("sans-pays : « Neufchâteau » et « Namur » détectés",
            "Neufchâteau" in noms and "Namur" in noms)
    verifie("sans-pays : lieux avec pays exclus",
            "Paris, France" not in noms and "Bruxelles, Belgique" not in noms)


def test_scan_cite_importe():
    # Retour Michel : un scan attaché À UNE CITATION (2 SOUR / 3 OBJE / 4 FILE)
    # doit être rattaché à la source citée (nom de fichier seul).
    src = ("0 HEAD\n1 CHAR UTF-8\n1 GEDC\n2 VERS 5.5.1\n"
           "0 @I1@ INDI\n1 NAME Jean /Test/\n1 BIRT\n2 SOUR @S1@\n3 PAGE Acte 11\n"
           "3 OBJE\n4 FORM JPG\n4 FILE D:\\Docs\\Actes\\X-00169.jpg\n"
           "0 @S1@ SOUR\n1 TITL Registre 1840\n0 TRLR\n")
    d = gedcom.importer(src)
    fichiers = d["sources"]["S1"].get("fichiers", [])
    verifie("scan de citation rattaché à la source", "X-00169.jpg" in fichiers)
    verifie("chemin disque réduit au nom de fichier",
            all("\\" not in f and "/" not in f for f in fichiers))


def test_codec_manquant():
    """Simule un exe figé où le codec cp1252 est ABSENT (cas Michel : arboriane.json
    contenait « Neufch�teau »). Le décodeur doit alors préserver les accents via le
    repli Latin-1 sans codec, jamais les transformer en « � »."""
    octets = ("0 HEAD\n1 CHAR ANSI\n0 @I1@ INDI\n1 NAME Gérard /Castagne/\n"
              "1 BIRT\n2 PLAC Neufchâteau\n0 TRLR\n").encode("cp1252")
    vrai_detecter = gedcom_charset.detecter
    # on force un nom de codec introuvable -> bytes.decode lève LookupError
    gedcom_charset.detecter = lambda o: ("cp1252_absent_9999", True)
    try:
        texte, cs, fi = gedcom_charset.decoder(octets)
    finally:
        gedcom_charset.detecter = vrai_detecter
    verifie("codec manquant : aucun « � »", texte.count("�") == 0)
    verifie("codec manquant : accents préservés (Gérard/Neufchâteau)",
            "Gérard" in texte and "Neufchâteau" in texte)
    d = gedcom.importer(texte)
    lieu = (list(d["individus"].values())[0].get("naissance") or {}).get("lieu")
    verifie("codec manquant : import OK avec accents", lieu == "Neufchâteau")


def test_variantes_geocodage():
    verifie("lieu simple : une variante",
            _variantes_requete("Namur") == ["Namur"])
    verifie("multi-parties : complet puis ville+pays puis ville",
            _variantes_requete("Givet, Saint-Hilaire, Ardennes, France")
            == ["Givet, Saint-Hilaire, Ardennes, France", "Givet, France", "Givet"])
    verifie("parties vides nettoyées",
            _variantes_requete("Givet, , Ardennes, France")
            == ["Givet, Ardennes, France", "Givet, France", "Givet"])


if __name__ == "__main__":
    test_encodages()
    test_ansi_avec_octet_invalide()
    test_tables_embarquees_sans_codec()
    test_utf16_sans_bom()
    test_codec_manquant()
    test_scan_cite_importe()
    test_variantes_geocodage()
    test_pays_defaut()
    test_lieux_sans_pays()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
