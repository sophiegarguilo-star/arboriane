# -*- coding: utf-8 -*-
"""
Version d'Arboriane — SOURCE UNIQUE de vérité.

Tout le reste en dérive (route /api/version, verrou d'instance, page Aide,
ressource Windows de l'exe, installeur). Ne jamais recopier ce numéro à la
main ailleurs : importer VERSION depuis ce module, ou le lire via /api/version.

Format : MAJEUR.MINEUR.CORRECTIF (entiers). BUILD est une chaîne courte
comparable côté navigateur pour détecter un backend d'une autre version.
"""

VERSION = "1.10.1"

# Empreinte de build servie au navigateur (handshake anti-cache).
# = la version ; suffit à détecter « le serveur a changé, recharge ».
BUILD = VERSION
