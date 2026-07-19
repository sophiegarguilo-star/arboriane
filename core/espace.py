# -*- coding: utf-8 -*-
"""
Espace de travail — UN ARBRE = UN DOSSIER.

Un espace est un dossier autonome contenant tout ce qu'Arboriane écrit :

    Mon arbre/
      espace.json            carte d'identité (format, nom, racine…)
      arboriane.json         l'arbre (personnes, familles, sources)
      annotations.json       tâches et notes par personne
      journal_sources.csv    carnet de recherche (1 ligne = 1 source consultée)
      README_ARBORIANE.txt   mode d'emploi du dossier (généré)
      PROMPT_ASSISTANT_IA.txt prompt modèle pour un assistant IA (généré)
      Personnes/  Sources/  Photos/  GEDCOM/  GEDCOM/Archives/
      Transcriptions/  Recherches/  Exports/  Sauvegardes/  Rapports/
      Carnet/carnet.md

Règles :
- aucun secret dans l'espace (les clés API restent dans les réglages locaux) ;
- l'arbre est 100 % autonome : aucun lien vers un dossier externe ;
- créer/ouvrir ne détruit jamais rien : on refuse d'écraser un manifeste et on
  n'écrit jamais par-dessus un fichier présent ;
- compatibilité silencieuse avec d'anciens fichiers, sans jamais afficher
  l'ancien nom du logiciel dans l'interface.
"""

import json
import os
import time

FORMAT = 1
MANIFESTE = "espace.json"
NOM_BASE = "arboriane.json"
NOM_BASE_LEGACY = "kintrace.json"   # ancien nom : lu si c'est le seul présent

DOSSIERS = [
    "Personnes",
    "Sources",
    "Photos",
    "GEDCOM/Archives",
    "Transcriptions",
    "Recherches",
    "Exports",
    "Sauvegardes",
    "Rapports",
    "Carnet",
]

ENTETE_JOURNAL = ("Date_acte;Type;Lieu;Reference;Personnes;Branche;"
                  "Fichier;Fiabilite;Statut;Notes\n")


def est_espace(chemin):
    """Vrai si 'chemin' contient un manifeste d'espace."""
    return bool(chemin) and os.path.isfile(os.path.join(chemin, MANIFESTE))


def charger(chemin):
    """Lit le manifeste. None si absent ou illisible."""
    if not est_espace(chemin):
        return None
    try:
        with open(os.path.join(chemin, MANIFESTE), "r", encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError):
        return None
    m.setdefault("format", FORMAT)
    m.setdefault("nom", os.path.basename(os.path.normpath(chemin)))
    m.setdefault("racine_id", "I1")
    return m


def sauver_manifeste(chemin, manifeste):
    tmp = os.path.join(chemin, MANIFESTE + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(manifeste, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())      # vraiment sur le disque avant le replace
    os.replace(tmp, os.path.join(chemin, MANIFESTE))


def chemin_base(chemin):
    """Fichier de base : arboriane.json ; repli sur l'ancien nom SEULEMENT s'il
    est le seul présent (arbres d'avant le renommage — aucune migration forcée)."""
    base = os.path.join(chemin, NOM_BASE)
    if not os.path.exists(base):
        legacy = os.path.join(chemin, NOM_BASE_LEGACY)
        if os.path.exists(legacy):
            return legacy
    return base


def chemins(chemin):
    """Chemins des fichiers de travail à l'intérieur d'un espace."""
    return {
        "base": chemin_base(chemin),
        "annotations": os.path.join(chemin, "annotations.json"),
        "journal": os.path.join(chemin, "journal_sources.csv"),
        "sauvegardes": os.path.join(chemin, "Sauvegardes"),
        "photos": os.path.join(chemin, "Photos"),
        "sources": os.path.join(chemin, "Sources"),
        "gedcom": os.path.join(chemin, "GEDCOM"),
        "exports": os.path.join(chemin, "Exports"),
        "carnet": os.path.join(chemin, "Carnet", "carnet.md"),
        "readme": os.path.join(chemin, "README_ARBORIANE.txt"),
        "prompt": os.path.join(chemin, "PROMPT_ASSISTANT_IA.txt"),
    }


def creer(chemin, nom=""):
    """Crée un espace complet (arbre 100 % autonome). Refuse si un manifeste
    existe déjà ; n'écrase AUCUN fichier existant. Renvoie le manifeste."""
    chemin = os.path.normpath(chemin)
    if est_espace(chemin):
        raise FileExistsError("Ce dossier est déjà un espace Arboriane.")
    nom = (nom or os.path.basename(chemin) or "Arboriane").strip()

    os.makedirs(chemin, exist_ok=True)
    for d in DOSSIERS:
        os.makedirs(os.path.join(chemin, d), exist_ok=True)

    manifeste = {
        "format": FORMAT,
        "nom": nom,
        "cree_le": time.strftime("%Y-%m-%d"),
        "racine_id": "I1",
    }
    sauver_manifeste(chemin, manifeste)

    c = chemins(chemin)
    _ecrire_si_absent(c["journal"], ENTETE_JOURNAL, newline="")
    _ecrire_si_absent(c["carnet"], _carnet_amorce(nom))
    _ecrire_si_absent(c["readme"], _readme(nom))
    _ecrire_si_absent(c["prompt"], _prompt_assistant(nom, chemin))
    return manifeste


def _ecrire_si_absent(chemin, contenu, newline=None):
    if os.path.exists(chemin):
        return
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    with open(chemin, "w", encoding="utf-8", newline=newline) as f:
        f.write(contenu)


def _carnet_amorce(nom):
    return ("# Carnet de bord — %s\n\n"
            "Votre journal de recherche : séances, pistes, trouvailles, "
            "réflexions.\n\n> Une piste va au carnet ; une preuve va aux "
            "sources.\n") % nom


def _readme(nom):
    return """ARBORIANE — ESPACE DE TRAVAIL « %s »
==================================================

Ce dossier est votre espace de travail. Tout y est en fichiers lisibles
(textes, CSV, GEDCOM, images) : vous pouvez les consulter et les modifier
sans Arboriane.

CE QUE CONTIENT CE DOSSIER
--------------------------
  espace.json           carte d'identité de l'espace (ne pas supprimer)
  arboriane.json        votre arbre (personnes, familles, sources)
  annotations.json      vos tâches et notes par personne
  journal_sources.csv   votre carnet de recherche (1 ligne = 1 source)
  Personnes/            fiches personne
  Sources/              fiches d'actes + vos scans
  Photos/               photos des personnes
  GEDCOM/               votre arbre au format d'échange standard
  Transcriptions/       transcriptions d'actes à relire
  Recherches/           pistes et décisions à prendre
  Exports/              tout ce qu'Arboriane exporte pour vous
  Sauvegardes/          copies de sécurité automatiques
  Rapports/             rapports générés
  Carnet/carnet.md      votre carnet de bord

RÈGLES DE CONFIANCE
-------------------
- Arboriane n'écrit QUE dans ce dossier.
- Avant de modifier un fichier, Arboriane en garde une copie dans Sauvegardes/.
- Aucune clé ni donnée secrète ici : vous pouvez copier ce dossier sans risque.
""" % nom


def _prompt_assistant(nom, chemin):
    return ("""PROMPT MODÈLE — assistant IA travaillant dans cet espace Arboriane
================================================================
Copiez ce texte au début d'une conversation avec un assistant quand vous lui
demandez de travailler dans ce dossier.
----------------------------------------------------------------

Tu assistes sur un ESPACE DE TRAVAIL ARBORIANE (généalogie locale, 100%% fichiers).
Arbre : « %(nom)s »
Dossier : %(chemin)s

RÈGLES ABSOLUES :
- Ne travaille QUE dans ce dossier. Ne rien envoyer en ligne.
- Sauvegarde avant toute écriture ; ne rien supprimer sans confirmation.
- Respecte les formats existants (arboriane.json, journal_sources.csv, GEDCOM).

BUT : m'aider à documenter, recouper et prouver mes ancêtres, sans jamais
mettre en danger mes données.
================================================================
""") % {"nom": nom, "chemin": chemin}
