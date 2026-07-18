# -*- coding: utf-8 -*-
"""
Sécurité locale.

Arboriane est un serveur qui ne parle qu'à la machine de l'utilisateur. Ces
garde-fous protègent contre les attaques « DNS rebinding » / CSRF où une page
web ouverte dans le navigateur tenterait de piloter le serveur local :

- le serveur n'écoute que sur 127.0.0.1 (fait dans app.py) ;
- toute MUTATION (POST/PUT/DELETE) doit :
    · viser un Host local (127.0.0.1 / localhost) ;
    · avoir une Origin absente ou locale (pas un site tiers) ;
    · être de type application/json ;
    · ne pas dépasser la limite de taille.

Aucune donnée n'est jamais émise en dehors : pas de télémétrie.
"""

LIMITE_CORPS = 64 * 1024 * 1024        # 64 Mo — garde-fou upload/import (scans HD compris)
HOTES_LOCAUX = ("127.0.0.1", "localhost", "[::1]", "::1")


def _hote_local(valeur):
    """Vrai si un en-tête Host/Origin désigne la machine locale."""
    if not valeur:
        return True                    # Origin absente = requête même-origine
    v = valeur.strip().lower()
    for prefixe in ("http://", "https://"):
        if v.startswith(prefixe):
            v = v[len(prefixe):]
    v = v.split("/")[0]                 # retirer un éventuel chemin
    hote = v.rsplit(":", 1)[0] if v.rsplit(":", 1)[-1].isdigit() else v
    return hote in HOTES_LOCAUX


def verifier_lecture(headers):
    """Contrôle une requête de LECTURE (GET) d'API ou de média. Vérifie que le
    Host visé est local : c'est ce qui neutralise le DNS rebinding (lors d'un
    rebinding, le Host reste le domaine attaquant et est donc rejeté), même si
    le navigateur croit la requête « même origine ». Renvoie None si OK."""
    if not _hote_local(headers.get("Host")):
        return (403, "Hôte non local refusé.")
    return None


def verifier_mutation(headers):
    """Contrôle une requête de mutation. Renvoie None si OK, sinon un couple
    (code_http, message) à renvoyer tel quel."""
    if not _hote_local(headers.get("Host")):
        return (403, "Hôte non local refusé.")
    if not _hote_local(headers.get("Origin")):
        return (403, "Origine externe refusée.")
    ctype = (headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if ctype and ctype != "application/json":
        return (415, "Content-Type application/json requis pour les mutations.")
    try:
        taille = int(headers.get("Content-Length") or 0)
    except ValueError:
        return (400, "Content-Length invalide.")
    if taille > LIMITE_CORPS:
        return (413, "Corps de requête trop volumineux (max %d Mo)."
                % (LIMITE_CORPS // (1024 * 1024)))
    return None
