# -*- coding: utf-8 -*-
"""
Validation des entrées JSON.

Petites vérifications défensives : on ne fait jamais confiance au corps d'une
requête. `lire_json` refuse ce qui n'est pas un objet JSON valide ; `texte`,
`liste`, `choix` normalisent des champs individuels.
"""

import json


class ErreurValidation(ValueError):
    """Entrée invalide : le message est sûr à montrer à l'utilisateur."""


def lire_json(octets):
    """Décode un corps de requête en dict. Lève ErreurValidation sinon."""
    if not octets:
        return {}
    try:
        valeur = json.loads(octets.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ErreurValidation("Corps JSON illisible.")
    if not isinstance(valeur, dict):
        raise ErreurValidation("Un objet JSON est attendu.")
    return valeur


def texte(valeur, defaut="", maxi=20000):
    """Normalise en chaîne, coupe au-delà de `maxi` (garde-fou)."""
    if valeur is None:
        return defaut
    s = str(valeur).strip()
    return s[:maxi]


def liste(valeur):
    return valeur if isinstance(valeur, list) else []


def choix(valeur, valeurs, defaut):
    """Contraint une valeur à un ensemble autorisé (ex. sexe, statut)."""
    return valeur if valeur in valeurs else defaut
