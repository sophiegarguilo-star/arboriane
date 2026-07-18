# -*- coding: utf-8 -*-
"""
Instance unique — un seul serveur Arboriane par dossier de données.

Pourquoi ? Deux serveurs sur le même dossier écrivent les mêmes JSON en
parallèle (le RLock de core/stockage.py n'est qu'IN-process) : risque de
corruption, et symptôme vécu du « vieux serveur périmé qui squatte le port ».

Mécanisme : un VERROU D'OCTET posé par le système d'exploitation sur
`donnees/instance.lock` (msvcrt sous Windows, fcntl ailleurs). Ce verrou est :
  • atomique — deux lancements simultanés : un seul l'obtient, pas de course ;
  • relâché AUTOMATIQUEMENT par l'OS à la mort du process (fermeture, crash,
    taskkill) — donc AUCUN verrou fantôme à nettoyer, et immunité totale au
    recyclage de PID (on ne teste JAMAIS un PID, piège mortel sous Windows où
    os.kill(pid, 0) tue le process).

Règles d'or (respectées ici) :
  • garder le descripteur du verrou OUVERT toute la vie du process (référence
    de module `_FD`), sinon le verrou se relâche ;
  • NE JAMAIS remplacer/renommer le fichier .lock (le verrou se détacherait) ;
  • les métadonnées mutables (pid, port, url, version) vont dans un fichier
    SÉPARÉ `instance.json`, écrit atomiquement.
"""

import json
import os

NOM_LOCK = "instance.lock"
NOM_INFOS = "instance.json"

_FD = None            # descripteur du verrou, gardé vivant pour tout le process


def _chemin(dossier_donnees, nom):
    return os.path.join(dossier_donnees, nom)


def _verrouiller(fd):
    """Pose un verrou exclusif NON bloquant. Lève OSError s'il est déjà tenu."""
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _deverrouiller(fd):
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def acquerir(dossier_donnees):
    """Tente de devenir l'instance unique pour ce dossier.

    Renvoie True si on détient le verrou (on peut démarrer le serveur), False si
    une autre instance vivante le détient déjà. En cas d'anomalie du mécanisme
    de verrou, dégrade en True (on démarre quand même — comportement historique)
    plutôt que de bloquer l'utilisateur.
    """
    global _FD
    try:
        os.makedirs(dossier_donnees, exist_ok=True)
        fd = os.open(_chemin(dossier_donnees, NOM_LOCK),
                     os.O_RDWR | os.O_CREAT, 0o644)
    except OSError:
        return True                      # impossible d'ouvrir : on ne bloque pas
    try:
        _verrouiller(fd)
    except OSError:
        os.close(fd)
        return False                     # déjà tenu par une instance vivante
    except Exception:                    # mécanisme indisponible : dégradation
        try:
            os.close(fd)
        except OSError:
            pass
        return True
    _FD = fd                             # garder le verrou vivant
    return True


def liberer(dossier_donnees):
    """Relâche le verrou et retire instance.json s'il nous appartient.
    (Le verrou serait de toute façon relâché par l'OS à la fin du process.)"""
    global _FD
    if _FD is not None:
        _deverrouiller(_FD)
        try:
            os.close(_FD)
        except OSError:
            pass
        _FD = None
    try:
        infos = lire_infos(dossier_donnees)
        if infos.get("pid") == os.getpid():
            os.remove(_chemin(dossier_donnees, NOM_INFOS))
    except OSError:
        pass


def ecrire_infos(dossier_donnees, infos):
    """Écrit instance.json de façon atomique (métadonnées de l'instance vive)."""
    try:
        tmp = _chemin(dossier_donnees, NOM_INFOS) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(infos, f, ensure_ascii=False)
        os.replace(tmp, _chemin(dossier_donnees, NOM_INFOS))
    except OSError:
        pass


def lire_infos(dossier_donnees):
    """Lit instance.json (port/url/version de l'instance en cours). {} si absent."""
    try:
        with open(_chemin(dossier_donnees, NOM_INFOS), "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}
