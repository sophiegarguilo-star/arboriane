# -*- coding: utf-8 -*-
"""
Routes de généalogie avancée : fusion de doublons, détection de doublons,
export d'un rameau (ascendance/descendance), import GEDCOM détaillé/fusionnant,
duplication d'un espace.
"""

import base64
import io
import os
import shutil
import zipfile

from routes import route
from services import fusion, rameau, import_avance
from core import espace as espace_mod
from core.gedcom import bilan as bilan_gedcom
from core.fichiers import nom_sur
from core.validation import ErreurValidation


def _actif(app):
    if not app.base:
        raise ErreurValidation("Aucun arbre ouvert.")


@route("POST", r"^/api/individus/fusionner$")
def fusionner(app, params, corps):
    """Fusionne deux personnes en doublon (garde absorbe absorbe)."""
    _actif(app)
    garde = (corps.get("garde") or "").strip()
    absorbe = (corps.get("absorbe") or "").strip()
    if not garde or not absorbe:
        raise ErreurValidation("Indiquez les deux personnes (garde, absorbe).")
    if garde == absorbe:
        raise ErreurValidation("Impossible de fusionner une personne avec elle-même.")
    resume = fusion.fusionner(app.base, garde, absorbe)
    if resume is None:
        raise ErreurValidation("Personne(s) introuvable(s).")
    return {"ok": True, **resume}


@route("GET", r"^/api/doublons$")
def doublons(app, params, corps):
    """Paires de personnes probablement en doublon."""
    _actif(app)
    return {"doublons": fusion.doublons_probables(app.base.donnees)}


@route("POST", r"^/api/export/rameau$")
def export_rameau(app, params, corps):
    """Exporte l'ascendance ou la descendance d'une personne en GEDCOM."""
    _actif(app)
    personne = (corps.get("personne") or "").strip()
    if not personne:
        raise ErreurValidation("Indiquez la personne racine du rameau.")
    sens = (corps.get("sens") or "ascendance").strip()
    if sens not in ("ascendance", "descendance"):
        raise ErreurValidation("Sens invalide (ascendance ou descendance).")
    generations = corps.get("generations")
    chemin, texte = rameau.exporter_rameau(app, personne, sens, generations)
    return {"ok": True, "fichier": os.path.basename(chemin), "texte": texte}


def _texte_gedcom(corps):
    """Texte GEDCOM depuis le corps : `octets_b64` (octets bruts → détection
    d'encodage L12) ou `texte` (déjà décodé). Source unique : le service partagé,
    pour ne pas diverger de routes/gedcom (ex. calcul de `perdus`)."""
    from services import gedcom_charset
    return gedcom_charset.texte_depuis_corps(corps)


@route("POST", r"^/api/import/gedcom/comparer-detaille$")
def comparer_detaille(app, params, corps):
    """Compare un GEDCOM entrant à l'arbre actif, en détaillant les changements."""
    _actif(app)
    texte, enc = _texte_gedcom(corps)
    if not texte.strip():
        raise ErreurValidation("Aucun contenu GEDCOM reçu.")
    if enc:                                    # journal dès l'aperçu (diagnostic accents)
        from services import gedcom_charset
        gedcom_charset.journaliser(app.espace_chemin, enc.get("charset"),
                                   enc.get("fiable"), texte)
    res = import_avance.comparer_detaille(app, texte)
    # Balises niveau 1-2 non reconnues : montrées dès l'aperçu (PARC-11).
    res["non_lues"] = bilan_gedcom.compter_non_reconnues(texte)
    if enc:
        res["encodage"] = enc
    return res


@route("POST", r"^/api/import/gedcom/fusionner$")
def import_fusionner(app, params, corps):
    """Importe un GEDCOM en fusionnant (complète les existants, ajoute le reste)."""
    _actif(app)
    texte, enc = _texte_gedcom(corps)
    if not texte.strip():
        raise ErreurValidation("Aucun contenu GEDCOM reçu.")
    if enc:
        from services import gedcom_charset
        gedcom_charset.journaliser(app.espace_chemin, enc.get("charset"),
                                   enc.get("fiable"), texte)
    corr = (corps or {}).get("corrections_lieux") or None
    res = import_avance.fusionner_import(app, texte, corr)
    # Balises niveau 1-2 non reconnues du fichier entrant (PARC-11).
    res["non_lues"] = bilan_gedcom.compter_non_reconnues(texte)
    return {"ok": True, **res}


@route("POST", r"^/api/espaces/dupliquer$")
def dupliquer(app, params, corps):
    """Duplique un espace : copie tout le dossier vers « Mes arbres/<nouveau nom> ».
    N'écrase jamais un dossier existant (suffixe numéroté au besoin)."""
    chemin = (corps.get("chemin") or "").strip()
    if not chemin or not espace_mod.est_espace(chemin):
        raise ErreurValidation("Espace introuvable.")
    m = espace_mod.charger(chemin)
    nom = (corps.get("nom") or "").strip() or (
        (m.get("nom", "") if m else "") + " (copie)").strip() or "Copie"

    cible = os.path.join(app.dossier_arbres, nom_sur(nom))
    base = cible
    n = 2
    while os.path.exists(base):
        base = "%s (%d)" % (cible, n)
        n += 1
    shutil.copytree(chemin, base)

    # Refléter le nouveau nom dans le manifeste de la copie.
    mc = espace_mod.charger(base)
    if mc is not None:
        mc["nom"] = nom
        espace_mod.sauver_manifeste(base, mc)
    app._memoriser(base, actif=False)
    return {"ok": True, "chemin": os.path.normpath(base)}


def _installer_zip(app, zf, nom):
    """Extrait une archive-arbre (ZipFile déjà ouvert) dans un NOUVEAU dossier
    sous « Mes arbres/ » et l'ouvre. N'écrase aucun arbre existant. Gère les
    archives dont le contenu est niché dans un sous-dossier unique (ex. une
    sauvegarde « Ma généalogie/… »). Réutilisé par l'import base64 (petits
    fichiers) et par la restauration native (gros fichiers lus sur le disque)."""
    noms = zf.namelist()
    if not any(n.endswith("espace.json") or n.endswith("arboriane.json") for n in noms):
        raise ErreurValidation("Cette archive n'est pas un arbre Arboriane.")

    cible = os.path.join(app.dossier_arbres, nom_sur(nom or "Arbre importé"))
    base = cible
    n = 2
    while os.path.exists(base):
        base = "%s (%d)" % (cible, n)
        n += 1
    os.makedirs(base, exist_ok=True)
    # extraction sûre (empêche la sortie du dossier cible)
    racine = os.path.abspath(base)
    for membre in noms:
        dest = os.path.abspath(os.path.join(base, membre))
        if dest != racine and not dest.startswith(racine + os.sep):
            continue
        if membre.endswith("/"):
            os.makedirs(dest, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with zf.open(membre) as src, open(dest, "wb") as out:
                shutil.copyfileobj(src, out)
    # si l'archive contient un sous-dossier unique, remonter d'un cran
    if not espace_mod.est_espace(base):
        sous = [d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d))]
        for d in sous:
            if espace_mod.est_espace(os.path.join(base, d)):
                base = os.path.join(base, d)
                break
    if not espace_mod.est_espace(base):
        raise ErreurValidation("Archive importée mais aucun arbre valide trouvé.")
    m = app.ouvrir(base)
    return {"ok": True, "chemin": os.path.normpath(base), "nom": m.get("nom", nom)}


@route("POST", r"^/api/espaces/importer-zip$")
def importer_zip(app, params, corps):
    """Crée un NOUVEL arbre depuis une petite archive .zip transmise en base64
    (fichiers d'échange légers). Pour restaurer une SAUVEGARDE complète (lourde,
    avec les scans), utiliser plutôt /api/espaces/restaurer — voir ci-dessous."""
    data = corps.get("data") or ""
    if "," in data and data.strip().startswith("data:"):
        data = data.split(",", 1)[1]
    try:
        octets = base64.b64decode(data)
        zf = zipfile.ZipFile(io.BytesIO(octets))
    except Exception:
        raise ErreurValidation("Archive .zip illisible.")
    return _installer_zip(app, zf, (corps.get("nom") or "").strip())


@route("POST", r"^/api/espaces/restaurer$")
def restaurer(app, params, corps):
    """Restaure une sauvegarde .zip choisie via le sélecteur de fichier NATIF :
    le serveur lit l'archive directement sur le disque (aucun transfert par le
    navigateur → pas de saturation mémoire, même pour un arbre de plusieurs
    centaines de Mo avec ses scans). Renvoie {annule: True} si l'utilisateur
    ferme le dialogue."""
    from services import selecteur_dossier
    chemin = selecteur_dossier.choisir_fichier(
        "Choisissez la sauvegarde de votre arbre (.zip)")
    if not chemin:
        return {"annule": True}
    if not zipfile.is_zipfile(chemin):
        raise ErreurValidation("Ce fichier n'est pas une archive .zip valide.")
    nom = os.path.splitext(os.path.basename(chemin))[0]
    with zipfile.ZipFile(chemin) as zf:
        res = _installer_zip(app, zf, nom)
    res["annule"] = False
    return res
