# -*- coding: utf-8 -*-
"""
Routage de l'API — un petit registre déclaratif.

Chaque module de routes déclare ses points d'entrée avec le décorateur
`@route(methode, motif)`. `motif` est une regex ; ses groupes nommés sont
passés en arguments au gestionnaire. Un gestionnaire reçoit
`(app, params, corps, **groupes)` et renvoie soit une valeur JSON (→ 200),
soit un couple `(code, valeur)`.

app.py importe les modules de routes (ce qui déclenche l'enregistrement) puis
appelle `dispatch()`.
"""

import re
import sys
import traceback

from core.validation import ErreurValidation

ROUTES = []


def _tracer():
    """Trace l'erreur côté serveur (console/log) sans jamais la propager."""
    try:
        traceback.print_exc(file=sys.stderr)
    except Exception:  # noqa: BLE001
        pass


def route(methode, motif):
    compile_motif = re.compile(motif)

    def deco(fn):
        ROUTES.append((methode.upper(), compile_motif, fn))
        return fn
    return deco


def dispatch(app, methode, chemin, params, corps):
    """Trouve et exécute la route. Renvoie (code, payload). 404 si aucune."""
    for m, motif, fn in ROUTES:
        if m != methode:
            continue
        correspond = motif.match(chemin)
        if not correspond:
            continue
        try:
            resultat = fn(app, params, corps, **correspond.groupdict())
        except ErreurValidation as e:
            return (400, {"erreur": str(e)})
        except ValueError as e:
            return (400, {"erreur": str(e)})
        except FileExistsError as e:
            return (409, {"erreur": str(e)})
        except (TypeError, AttributeError):
            # corps JSON d'un type inattendu (nombre/liste au lieu d'une chaîne…)
            # → requête invalide, sans divulguer le message d'exception interne.
            return (400, {"erreur": "Requête invalide."})
        except OSError as e:
            # Écriture/lecture impossible : dossier protégé (« accès contrôlé aux
            # dossiers » de Windows), droits insuffisants, disque plein, chemin
            # invalide… On répond PROPREMENT (sinon le navigateur voit juste un
            # « Failed to fetch » incompréhensible), avec la MANŒUVRE pour débloquer.
            _tracer()
            return (500, {"erreur":
                "Écriture impossible dans le dossier de données. "
                "C'est le plus souvent la protection Windows « Accès contrôlé aux "
                "dossiers » (ou un antivirus) qui bloque. Pour débloquer : ouvrez "
                "« Sécurité Windows » → « Protection contre les rançongiciels » → "
                "« Gérer la protection… » → « Autoriser une application… », puis "
                "ajoutez Arboriane. Vous pouvez aussi choisir un autre dossier à la "
                "création de l'arbre. (Détail technique : %s)" % e})
        except Exception as e:  # noqa: BLE001 — FILET ULTIME : jamais de connexion cassée
            _tracer()
            return (500, {"erreur": "Erreur interne : %s" % e})
        if isinstance(resultat, tuple) and len(resultat) == 2:
            return resultat
        return (200, resultat)
    return (404, {"erreur": "Route inconnue : %s %s" % (methode, chemin)})


def charger_modules():
    """Importe tous les modules de routes pour déclencher l'enregistrement."""
    from routes import (espaces, individus, familles,        # noqa: F401
                        analyse, gedcom, arbre, lieux,
                        sources, publication, qualite, avance, verif, liens,
                        implexe, listes, depots, lieux_ref, dates, systeme,
                        fusion, chronologie, favoris, maj, livres,
                        nomenclature, explorateur)
