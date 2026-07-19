# -*- coding: utf-8 -*-
"""
Publication & export GEDZIP — préparer un arbre à être diffusé.

Deux besoins couverts, sans jamais rien envoyer en ligne (on écrit un fichier
local que l'utilisateur diffuse lui-même) :

1) EXPORT DE PUBLICATION (vivants masqués)
   Les personnes PRÉSUMÉES VIVANTES (règle prudente de core.modele) sont
   anonymisées avant export : prénoms effacés (« Vivant·e »), nom masqué en
   « X… » (sauf option garder_noms), dates/lieux/professions/résidences/notes/
   citations/médias retirés. Les liens familiaux (parents, unions, enfants) et
   le sexe sont conservés pour que l'arbre reste navigable.
   On propose d'abord un APERÇU (qui serait masqué) pour vérifier AVANT.

2) EXPORT GEDZIP (.gdz)
   Archive ZIP contenant le GEDCOM + les images/photos référencées (portrait
   des personnes, scans des sources). Standard FamilySearch : le GEDCOM est
   nommé « gedcom.ged » à la racine du zip. Les ORIGINAUX ne sont jamais
   modifiés : on lit/copie les fichiers, on n'écrit que le .gdz.

Rien ici ne modifie la base d'origine : `preparer` travaille sur une
copie profonde (copy.deepcopy).

Bibliothèque standard uniquement (copy, os, zipfile). PAS de Pillow.
"""

import copy
import os
import zipfile

from core import gedcom, modele
from core.espace import chemins
from core.fichiers import dans, horodatage, nom_sur


# Étiquettes des personnes masquées (aucun nom réel : générique).
_PRENOM_MASQUE = {"F": "Vivante", "M": "Vivant"}
_PRENOM_MASQUE_DEFAUT = "Vivant·e"
_NOM_MASQUE = "X…"


def _est_masquee(ind, options):
    """Une personne est-elle masquée pour cet export ? Prudent : présumée
    vivante ET pas explicitement gardée visible par l'utilisateur."""
    if ind.get("id") in options["garder_visibles"]:
        return False
    return modele.est_vivant_presume(ind, options["annee_reference"])


def _normaliser_options(options):
    """Complète les options avec leurs valeurs par défaut (copie sûre)."""
    options = dict(options or {})
    return {
        "masquer_vivants": options.get("masquer_vivants", True),
        "garder_noms": bool(options.get("garder_noms", False)),
        "retirer_notes": options.get("retirer_notes", False),
        "retirer_notes_tous": bool(options.get("retirer_notes_tous", False)),
        "retirer_sources_vivants": bool(options.get("retirer_sources_vivants", False)),
        "retirer_photos_vivants": options.get("retirer_photos_vivants", True),
        "garder_visibles": set(options.get("garder_visibles") or []),
        "annee_reference": options.get("annee_reference"),
    }


# ---------------------------------------------------------------------------
# APERÇU (rien n'est écrit ni modifié)
# ---------------------------------------------------------------------------

def apercu_masques(donnees, options=None):
    """Liste des personnes qui seraient masquées (présumées vivantes), pour
    vérification AVANT export. Ne modifie rien, n'écrit rien.

    Renvoie une liste triée par nom : [{id, nom, sexe, annee}].
    options : garder_visibles=[ids], annee_reference=int (facultatifs).
    """
    modele.garantir_cles(donnees)
    opts = _normaliser_options(options)
    masques = []
    for ident, ind in donnees["individus"].items():
        if _est_masquee(ind, opts):
            masques.append({
                "id": ident,
                "nom": modele.nom_complet(ind),
                "sexe": ind.get("sexe", "U"),
                "annee": modele.annee_naissance(ind),
            })
    masques.sort(key=lambda m: (m["nom"] or "").lower())
    return masques


# ---------------------------------------------------------------------------
# PRÉPARATION : copie anonymisée (la base d'origine n'est JAMAIS touchée)
# ---------------------------------------------------------------------------

def _masquer_personne(ind, opts):
    """Anonymise une personne EN PLACE (dans la copie profonde)."""
    if opts["garder_noms"]:
        ind["prenoms"] = _PRENOM_MASQUE.get(ind.get("sexe"), _PRENOM_MASQUE_DEFAUT)
        # nom de famille conservé tel quel
    else:
        ind["prenoms"] = _PRENOM_MASQUE.get(ind.get("sexe"), _PRENOM_MASQUE_DEFAUT)
        ind["nom"] = _NOM_MASQUE
        ind["nom_particule"] = ""
        ind["nom_marital"] = ""
        ind["surnom"] = ""
    # Identité civile détaillée : effacée dans tous les cas.
    ind["prenom_principal"] = ""
    ind["prenoms_secondaires"] = ""
    ind["noms_alternatifs"] = []
    ind["naissance"] = {"date": "", "lieu": ""}
    ind["deces"] = {"date": "", "lieu": ""}
    ind["professions"] = []
    ind["residences"] = []
    ind["evenements"] = []
    ind["note"] = ""
    ind["citations"] = []
    ind["tags"] = []
    ind["pistes"] = []
    if opts["retirer_photos_vivants"]:
        ind["medias"] = []          # une photo de vivant = donnée personnelle


def preparer(donnees, options=None):
    """Renvoie une COPIE PROFONDE de `donnees`, anonymisée selon `options`.

    Ne modifie JAMAIS la base d'origine (copy.deepcopy).

    options :
      masquer_vivants (défaut True) : masque les personnes présumées vivantes ;
      garder_noms (défaut False) : conserve le nom de famille des masqués
          (prénom remplacé par « Vivant·e ») au lieu de tout masquer en « X… » ;
      retirer_notes (défaut False) : vide la note des personnes masquées ;
      retirer_notes_tous (défaut False) : vide TOUTES les notes (personnes et
          familles), masquées ou non (aucun marqueur privé/public n'existe) ;
      retirer_sources_vivants (défaut False) : retire les enregistrements
          source qui ne sont plus cités par personne après masquage (une source
          citée seulement par un vivant révélerait son état civil par son titre) ;
      retirer_photos_vivants (défaut True) : retire les médias des masqués ;
      garder_visibles : liste d'ids explicitement gardés visibles (choix
          utilisateur) ;
      annee_reference : année de référence pour le calcul « présumé vivant ».
    """
    modele.garantir_cles(donnees)
    opts = _normaliser_options(options)
    pub = copy.deepcopy(donnees)
    modele.garantir_cles(pub)

    masques_ids = set()
    for ident, ind in pub["individus"].items():
        est_masquee = opts["masquer_vivants"] and _est_masquee(ind, opts)
        if est_masquee:
            masques_ids.add(ident)
            _masquer_personne(ind, opts)
        else:
            if opts["retirer_notes_tous"]:
                ind["note"] = ""
        # 'vivant' est une clé interne de saisie : on ne la publie jamais.
        ind.pop("vivant", None)

    # Familles : mariage d'un couple dont un époux est masqué -> effacé
    # (la date de mariage d'un vivant est une donnée personnelle).
    for fam in pub["familles"].values():
        if fam.get("mari") in masques_ids or fam.get("epouse") in masques_ids:
            fam["mariage"] = {"date": "", "lieu": ""}
            fam["evenements"] = []
        if opts["retirer_notes_tous"] and (fam.get("note") or "").strip():
            fam["note"] = ""

    # retirer_notes : ne vide QUE les notes des personnes masquées (déjà fait
    # dans _masquer_personne, qui remet note=""). L'option est donc satisfaite
    # dès qu'on masque ; on la traite ici explicitement pour le cas où
    # masquer_vivants=False mais retirer_notes=True (note des présumés vivants).
    if opts["retirer_notes"] and not opts["masquer_vivants"]:
        for ident, ind in pub["individus"].items():
            if _est_masquee(ind, opts):
                ind["note"] = ""

    # retirer_sources_vivants : ne conserver que les sources encore citées
    # après masquage (par un individu, un événement ou une famille visible).
    if opts["retirer_sources_vivants"]:
        cites = _sources_encore_citees(pub)
        avant = pub.get("sources") or {}
        pub["sources"] = {sid: src for sid, src in avant.items() if sid in cites}
        # nettoie aussi les 'personnes' d'une source qui pointent un masqué
        for src in pub["sources"].values():
            src["personnes"] = [p for p in src.get("personnes", [])
                                if p.get("id") not in masques_ids]

    return pub


def _sources_encore_citees(donnees):
    """Ensemble des ids de sources encore référencées quelque part."""
    cites = set()

    def _ajouter(bloc):
        if not isinstance(bloc, dict):
            return
        for c in bloc.get("citations") or []:
            sid = c.get("source")
            if sid:
                cites.add(sid)

    for ind in donnees["individus"].values():
        for c in ind.get("citations") or []:
            if c.get("source"):
                cites.add(c["source"])
        _ajouter(ind.get("naissance"))
        _ajouter(ind.get("deces"))
        for res in ind.get("residences") or []:
            _ajouter(res)
        for ev in ind.get("evenements") or []:
            _ajouter(ev)
    for fam in donnees["familles"].values():
        _ajouter(fam.get("mariage"))
        for ev in fam.get("evenements") or []:
            _ajouter(ev)
    return cites


# ---------------------------------------------------------------------------
# EXPORT GEDCOM PUBLIC (fichier .ged dans Exports/)
# ---------------------------------------------------------------------------

def exporter_gedcom_public(app, options=None):
    """Prépare la base anonymisée puis écrit un .ged public dans Exports/.

    Renvoie le chemin absolu du fichier écrit. La base d'origine est intacte.
    """
    if not app.espace_chemin or not app.base:
        raise ValueError("Aucun arbre ouvert.")
    pub = preparer(app.base.donnees, options)
    texte = gedcom.exporter(pub)
    c = chemins(app.espace_chemin)
    os.makedirs(c["exports"], exist_ok=True)   # un .zip restauré peut ne pas contenir Exports/
    cible = dans(c["exports"], "%s_publication_%s.ged"
                 % (nom_sur(app.manifeste.get("nom", "arbre")), horodatage()))
    with open(cible, "w", encoding="utf-8") as f:
        f.write(texte)
    return cible


# ---------------------------------------------------------------------------
# EXPORT GEDZIP (.gdz = ZIP contenant le GEDCOM + les images référencées)
# ---------------------------------------------------------------------------

# Nom imposé du GEDCOM à la racine de l'archive (convention FamilySearch GEDZIP).
_NOM_GEDCOM_INTERNE = "gedcom.ged"


def _fichiers_references(donnees):
    """Liste (dédupliquée, ordre stable) des chemins de fichiers référencés :
    médias des personnes + scans/photos des sources."""
    rels = []
    for ind in donnees.get("individus", {}).values():
        for m in ind.get("medias") or []:
            f = (m.get("fichier") or "").strip()
            if f:
                rels.append(f)
    for src in donnees.get("sources", {}).values():
        for f in src.get("fichiers") or []:
            f = (f or "").strip()
            if f:
                rels.append(f)
        f = (src.get("fichier") or "").strip()
        if f:
            rels.append(f)
    return list(dict.fromkeys(rels))


def _resoudre_media(espace_chemin, rel):
    """Chemin absolu d'un fichier média référencé, ou None s'il est introuvable
    ou s'il tente de sortir de l'espace de travail.

    Un chemin de média peut être relatif à l'espace, ou déjà pointer vers
    Photos/ / Sources/. On tente plusieurs emplacements plausibles, toujours
    contraints À L'INTÉRIEUR de l'espace via fichiers.dans (garde-fou)."""
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if not rel:
        return None
    c = chemins(espace_chemin)
    candidats = [
        (espace_chemin, rel),          # chemin relatif à la racine de l'espace
        (c["photos"], rel),            # nom de fichier seul dans Photos/
        (c["sources"], rel),
        (c["photos"], os.path.basename(rel)),
        (c["sources"], os.path.basename(rel)),
    ]
    for racine, partie in candidats:
        try:
            plein = dans(racine, partie)
        except ValueError:
            continue                   # chemin qui s'échappe de l'espace : refusé
        if os.path.isfile(plein):
            return plein
    return None


def exporter_gedzip(app, options=None, taille_max=None):
    """Écrit un .gdz (ZIP : GEDCOM + images référencées) dans Exports/.

    - options : si fournies, la base est d'abord anonymisée par `preparer`
      (export GEDZIP public). Si None, l'arbre complet est exporté tel quel.
    - taille_max : redimension optionnelle des images (en octets). Voir TODO.

    Les fichiers d'origine ne sont JAMAIS modifiés : on les copie dans le zip.
    Renvoie le chemin absolu du .gdz écrit.

    TODO (redimension) : Pillow n'étant pas disponible, `taille_max` n'est PAS
    appliqué — les images sont copiées telles quelles, quelle que soit leur
    taille. Le paramètre est accepté pour compatibilité d'API : quand une
    bibliothèque d'images sera disponible, redimensionner ici les fichiers dont
    la taille dépasse `taille_max` avant de les écrire dans l'archive.
    """
    if not app.espace_chemin or not app.base:
        raise ValueError("Aucun arbre ouvert.")

    donnees = preparer(app.base.donnees, options) if options is not None \
        else app.base.donnees
    texte = gedcom.exporter(donnees)
    rels = _fichiers_references(donnees)

    c = chemins(app.espace_chemin)
    suffixe = "publication_" if options is not None else ""
    os.makedirs(c["exports"], exist_ok=True)   # un .zip restauré peut ne pas contenir Exports/
    cible = dans(c["exports"], "%s_%s%s.gdz"
                 % (nom_sur(app.manifeste.get("nom", "arbre")),
                    suffixe, horodatage()))

    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(_NOM_GEDCOM_INTERNE, texte)   # GEDCOM à la racine (imposé)
        deja = {_NOM_GEDCOM_INTERNE}
        for rel in rels:
            source = _resoudre_media(app.espace_chemin, rel)
            if not source:
                continue                          # média introuvable : ignoré
            arcname = rel.replace("\\", "/").lstrip("/")
            if not arcname or arcname in deja:
                continue
            deja.add(arcname)
            # TODO redimension (taille_max) : copie telle quelle sans Pillow.
            try:
                z.write(source, arcname)          # copie ; l'original est intact
            except OSError:
                pass                              # fichier illisible : on saute
    return cible
