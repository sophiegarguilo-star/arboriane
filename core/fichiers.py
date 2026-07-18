# -*- coding: utf-8 -*-
"""
Fichiers & chemins — helpers sûrs pour rester DANS le dossier d'un arbre.

Règle d'or d'Arboriane : un arbre lit et écrit UNIQUEMENT dans son propre
dossier. Toute résolution de chemin passe par `sous_dossier()` qui refuse de
sortir de la racine (protection contre « ../.. » et les chemins absolus).
"""

import os
import shutil
import time


def horodatage():
    """« 2026-07-06_231045 » — pour nommer sauvegardes et exports."""
    return time.strftime("%Y-%m-%d_%H%M%S")


def dans(racine, *parties):
    """Chemin absolu de racine/parties…, GARANTI sous racine.

    Lève ValueError si le résultat s'échappe de racine (chemin malveillant,
    « .. », chemin absolu injecté). C'est la barrière unique par laquelle
    passent tous les accès fichier déclenchés par une requête."""
    racine_abs = os.path.abspath(racine)
    cible = os.path.abspath(os.path.join(racine_abs, *parties))
    if cible != racine_abs and not cible.startswith(racine_abs + os.sep):
        raise ValueError("Chemin hors de l'espace de travail : %r" % (parties,))
    return cible


def nom_sur(nom, defaut="fichier"):
    """Nettoie un nom de fichier : garde lettres/chiffres/.-_ et espaces."""
    nom = (nom or "").strip()
    propre = "".join(c for c in nom if c.isalnum() or c in " .-_()").strip()
    return propre or defaut


def taille_dossier(chemin):
    """Taille totale (octets) d'un dossier, 0 si absent ou illisible."""
    total = 0
    try:
        for base, _dirs, fics in os.walk(chemin):
            for f in fics:
                try:
                    total += os.path.getsize(os.path.join(base, f))
                except OSError:
                    pass
    except OSError:
        pass
    return total


def humaniser_taille(octets):
    """« 1,4 Mo », « 812 Ko »… (séparateur décimal français)."""
    for unite, seuil in (("Go", 1024 ** 3), ("Mo", 1024 ** 2), ("Ko", 1024)):
        if octets >= seuil:
            return ("%.1f %s" % (octets / seuil, unite)).replace(".", ",")
    return "%d o" % octets


def copier_horodate(source, dossier_cible, prefixe):
    """Copie source vers dossier_cible/<prefixe>_<horodatage><ext>. Renvoie le
    chemin de la copie, ou None en cas d'échec (jamais bloquant)."""
    try:
        os.makedirs(dossier_cible, exist_ok=True)
        _, ext = os.path.splitext(source)
        cible = os.path.join(dossier_cible, "%s_%s%s" % (prefixe, horodatage(), ext))
        shutil.copy2(source, cible)
        return cible
    except OSError:
        return None
