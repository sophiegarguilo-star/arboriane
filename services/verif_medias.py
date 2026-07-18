# -*- coding: utf-8 -*-
"""
Vérifications sur les médias & sources — deux contrôles « orientés preuves ».

- fichiers_manquants(app) : chaque scan/photo référencé (par une source ou une
  personne) existe-t-il vraiment sur le disque de l'espace ? Un fichier déplacé,
  renommé ou perdu est signalé. Rassure notamment après un déménagement de dossier.
- a_transcrire(donnees) : les sources qui ont un scan mais dont le relevé
  (transcription) est encore vide — la pile « à saisir ».

Module volontairement isolé : ne touche ni au moteur de cohérence ni aux sources.
"""

import os

from core import espace as espace_mod
from core.modele import nom_complet
from services import sources as src_svc


def _dossiers_medias(espace_chemin):
    """Dossiers où Arboriane range les fichiers (scans, photos, fonds)."""
    c = espace_mod.chemins(espace_chemin)
    candidats = [c.get("sources"), c.get("photos"),
                 os.path.join(espace_chemin, "Fonds")]
    return [d for d in candidats if d]


def _index_fichiers(dossiers):
    """Ensemble des noms de fichiers présents (basename) dans les dossiers."""
    presents = set()
    for d in dossiers:
        try:
            presents.update(os.listdir(d))
        except OSError:
            continue
    return presents


def _medias_personne(ind):
    """Noms de fichiers référencés par une personne (medias), tolérant au format."""
    out = []
    for m in (ind.get("medias") or []):
        f = (m.get("fichier") or m.get("nom") or m.get("chemin")) if isinstance(m, dict) else m
        if f:
            out.append(os.path.basename(str(f)))
    return out


def fichiers_manquants(app):
    """Rapport des fichiers référencés mais introuvables sur le disque.
    Renvoie {total, presents, nb_manquants, manquants:[{fichier,origine,contexte,id}]}."""
    if not app.espace_chemin or not app.base:
        return {"total": 0, "presents": 0, "nb_manquants": 0, "manquants": []}
    donnees = app.base.donnees
    presents = _index_fichiers(_dossiers_medias(app.espace_chemin))

    references = []                       # (fichier, origine, contexte, id)
    for sid, src in (donnees.get("sources") or {}).items():
        titre = src.get("titre") or sid
        for f in src_svc._fichiers(src):
            references.append((os.path.basename(str(f)), "source", titre, sid))
    for pid, ind in donnees["individus"].items():
        for f in _medias_personne(ind):
            references.append((f, "personne", nom_complet(ind), pid))

    manquants = [{"fichier": f, "origine": o, "contexte": ctx, "id": i}
                 for (f, o, ctx, i) in references if f not in presents]
    total = len(references)
    return {"total": total, "presents": total - len(manquants),
            "nb_manquants": len(manquants), "manquants": manquants}


def a_transcrire(donnees):
    """Sources ayant au moins un scan mais sans transcription (relevé vide).
    Renvoie {total, sources:[resume_source, …]}, triées comme la liste standard."""
    out = [r for r in src_svc.lister(donnees)
           if r["nb_fichiers"] > 0 and not r["a_transcription"]]
    return {"total": len(out), "sources": out}
