# -*- coding: utf-8 -*-
"""Import / export GEDCOM 5.5.1 — bibliothèque standard uniquement (paquet).

API publique :
    importer(texte)   -> dict   base « donnees » (toutes clés garanties)
    exporter(donnees) -> str    texte GEDCOM 5.5.1 complet

Découpé en modules : commun (primitives + balises), champs (lecture des champs),
lecture (importer), ecriture (exporter).

AVANT DE MODIFIER CE PAQUET : lire la norme, ne pas la deviner.
    https://gedcom.io/specifications/ged551.pdf
Rappels de grammaire qu'on oublie et qui coûtent cher :

    gedcom_line := level + delim + [xref_ID] + tag + [line_value] + terminator
    delim       := [(0x20)]        « a single space character » — un seul, et
                                   aucune espace en fin de ligne.
    terminator  := CR | LF | CRLF | LFCR
    pointer     := (0x40) + alphanum + pointer_string + (0x40)   (« @I12@ »)

Les espaces de tête « should be ignored by the reading system ». En revanche la
norme constate elle-même que « many GEDCOM values are trimmed of trailing
spaces » : nous rognons donc les pointeurs par tolérance (voir _pointeur), sans
que cela rende conforme un fichier qui en contient.

Enfin, un GEDCOM déclare la parenté DEUX FOIS — dans FAM (HUSB/WIFE/CHIL) et sur
l'individu (FAMS/FAMC). Toute lecture doit réconcilier les deux ; toute écriture
doit produire les deux.
"""
from core.gedcom.lecture import importer
from core.gedcom.ecriture import exporter

__all__ = ["importer", "exporter"]
