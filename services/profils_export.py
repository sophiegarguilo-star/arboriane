# -*- coding: utf-8 -*-
"""
Profils d'export GEDCOM — replier l'info riche là où CHAQUE site la conserve.

Un aller-retour GEDCOM n'est pas neutre : à l'import, chaque plateforme garde
et jette des choses différentes. Une transcription d'acte et un permalien (ARK)
placés dans le tiroir « standard » (SOUR.DATA.TEXT + WWW) survivent sur l'un et
disparaissent sur l'autre. Ce module prend une COPIE PROFONDE de l'arbre et
DÉPLACE ces informations vers le tiroir que le site cible lit vraiment, AVANT
l'appel à core.gedcom.exporter. La base d'origine n'est jamais touchée.

Cibles (d'après l'étude d'aller-retour) :

  GENERIQUE  — archivage : structure maximale (record source + DATA/TEXT + WWW +
               REPO + tags privés). Aucun repliage : c'est l'export actuel.
  GENEANET   — aplatit les sources mais garde tout (transcription + ARK) → on ne
               replie RIEN. En revanche GeneWeb ne sait pas ignorer un tag privé
               (« _XXX ») : au lieu de le sauter, il DÉVERSE le bloc GEDCOM brut
               dans la note de la personne/famille, qui affiche alors des choses
               comme « -- GEDCOM (FAM) -- 1 MARR 2 DATE 2 OCT 1924 3 _TIME
               18:00 ». On retire donc tous les tags privés du TEXTE exporté
               (voir `nettoyer_texte`), ce qui coûte l'heure des faits (_TIME),
               le sosa (_SOSA), les champs Arboriane des sources (_FIAB, _STATUT,
               _PAGE, _VILLE, _PAYS, _FORME, _COMPL, _VISI), les rôles (_ROLE),
               les libellés (_TAG, _TODO, _RUFNAME, _MARNM, _PRIM) — informations
               que Geneanet ne sait de toute façon pas exploiter.
  MYHERITAGE — garde les records + citations (PAGE/QUAY) mais jette la
               transcription DU RECORD et l'ARK ; conserve le TEXT DE LA
               CITATION → on replie transcription + ARK dans le DATA/TEXT de
               chaque citation de la source.
  ANCESTRY   — garde records + citations + PAGE + REPO mais jette la
               transcription et le WWW ; conserve un lien web de personne
               (_WLNK) et les NOTE de source → ARK dans un _WLNK au niveau
               personne (TITL = titre, NOTE = url), transcription dans la NOTE
               du record source.
  FILAE      — jette TOUTES les sources, citations, médias, dépôts ; ne garde
               que les NOTE de personne → on agrège titre + transcription/résumé
               + ARK dans la NOTE de chaque personne qui cite la source, puis on
               supprime tout l'appareil de sources.

BLOC PROVENANCE. Priorité de l'utilisatrice : sources, dépôts, actes et liens
d'abord ; la transcription est un bonus sacrifiable. Or seul Ancestry conserve
le tag REPO (Filae, Geneanet et MyHeritage le jettent) et aucun ne garde le WWW.
On fabrique donc une ligne compacte « Dépôt : X — Cote : Y — En ligne : Z »
(`bloc_provenance`) qu'on replie : dans la NOTE du record source pour MyHeritage
et Ancestry (tous deux la conservent), en plus de l'ARK ajouté au PAGE de chaque
citation pour MyHeritage (champ « Page/URL » de son interface) ; dans la note de
personne agrégée pour Filae (son seul canal survivant). Geneanet aplatit déjà la
source en texte inline avec dépôt, cote et lien : rien à faire. Le profil
GENERIQUE reste STRICTEMENT inchangé (archivage de fidélité maximale).

Option `transcription_complete` (défaut True) : True replie la transcription
intégrale ; False replie seulement un résumé court (1re ligne) + l'ARK. Le
profil GENERIQUE ignore cette option (il garde tout nativement).

Les photos/scans (OBJE) ne passent jamais par le GEDCOM à l'import sur ces
sites : ce n'est pas au profil de les retirer (l'UI rappelle qu'il faut les
réimporter à la main). On laisse donc les médias tels quels, SAUF pour Filae qui
jette de toute façon les médias attachés aux sources supprimées.

Bibliothèque standard uniquement (copy). Aucune dépendance externe.
"""

import copy
import re

from core import modele


PROFILS = ("generique", "geneanet", "myheritage", "ancestry", "filae")

# Libellés lisibles pour l'interface (ordre d'affichage).
LIBELLES = (
    ("generique", "Générique (archivage complet)"),
    ("geneanet", "Geneanet"),
    ("myheritage", "MyHeritage"),
    ("ancestry", "Ancestry"),
    ("filae", "Filae"),
)


def normaliser_profil(profil):
    """Renvoie un nom de profil valide (défaut « generique » si inconnu/vide)."""
    p = (profil or "").strip().lower()
    return p if p in PROFILS else "generique"


def _resume(transcription):
    """Première ligne non vide d'une transcription (résumé court)."""
    for ligne in (transcription or "").splitlines():
        ligne = ligne.strip()
        if ligne:
            return ligne
    return ""


def _texte_transcription(src, complete):
    """Transcription à replier : intégrale si `complete`, sinon résumé court."""
    trans = (src.get("transcription") or "").strip()
    if not trans:
        return ""
    return trans if complete else _resume(trans)


# ---------------------------------------------------------------------------
# Bloc « provenance » — dépôt / cote / lien en ligne
# ---------------------------------------------------------------------------

# Priorité de l'utilisatrice : conserver AVANT TOUT les sources, les dépôts, les
# actes et les liens (ARK). La transcription n'est qu'un bonus, sacrifiable. Les
# sites cibles jettent le tag REPO (sauf Ancestry) et le WWW : on replie donc
# dépôt + cote + lien dans une ligne de TEXTE compacte, qui survit partout où
# une note ou un PAGE survit.

PREFIXE_DEPOT = "Dépôt : "


def _nom_depot(donnees, src):
    """Nom du dépôt d'une source : texte libre, sinon entité `depot_id`."""
    nom = (src.get("depot") or "").strip()
    if nom:
        return nom
    ent = (donnees.get("depots") or {}).get(src.get("depot_id"))
    if isinstance(ent, dict):
        return (ent.get("nom") or "").strip()
    return ""


def bloc_provenance(donnees, src):
    """Ligne compacte « Dépôt : X — Cote : Y — En ligne : Z ».

    Ne retient que les parties non vides ; renvoie "" si aucune. C'est le
    véhicule minimal de la provenance d'un acte à travers un aller-retour
    GEDCOM (tous les sites conservent au moins une note de personne)."""
    parts = []
    depot = _nom_depot(donnees, src)
    if depot:
        parts.append(PREFIXE_DEPOT + depot)
    cote = (src.get("cote") or "").strip()
    if cote:
        parts.append("Cote : " + cote)
    ark = (src.get("ark") or "").strip()
    if ark:
        parts.append("En ligne : " + ark)
    return " — ".join(parts)


def _ajouter_provenance_note(src, bloc):
    """Ajoute `bloc` en tête de la note du record source, sans doublonner.

    Idempotent : si la note porte déjà ce bloc (ou déjà un « Dépôt : », signe
    d'un profil déjà appliqué), on ne touche à rien."""
    if not bloc:
        return
    note = (src.get("note") or "").strip()
    if bloc in note or PREFIXE_DEPOT in note:
        return
    src["note"] = (bloc + "\n" + note) if note else bloc


# ---------------------------------------------------------------------------
# Parcours des citations d'une personne (person-level + faits + tags source)
# ---------------------------------------------------------------------------

def _citations_de_personne(ind):
    """Itère sur TOUTES les listes de citations rattachées à une personne :
    citations directes, naissance, décès, résidences, événements. Renvoie une
    liste de dicts-citation (mutables : modifiés en place par les profils)."""
    out = list(ind.get("citations") or [])
    for cle in ("naissance", "deces"):
        bloc = ind.get(cle)
        if isinstance(bloc, dict):
            out.extend(bloc.get("citations") or [])
    for coll in ("residences", "evenements"):
        for item in ind.get(coll) or []:
            if isinstance(item, dict):
                out.extend(item.get("citations") or [])
    return out


def _sources_citees_par(ind, tags_personne):
    """Ids de sources (ordre stable, dédupliqués) citées par une personne :
    via ses citations ET via les « personnes citées » d'une source (tags)."""
    ids = []
    vus = set()
    for c in _citations_de_personne(ind):
        sid = c.get("source")
        if sid and sid not in vus:
            vus.add(sid); ids.append(sid)
    for sid in tags_personne.get(ind.get("id"), []):
        if sid and sid not in vus:
            vus.add(sid); ids.append(sid)
    return ids


def _index_tags_personne(donnees):
    """{pid: [sid, …]} d'après source['personnes'] (personnes citées sur l'acte)."""
    idx = {}
    for sid, src in (donnees.get("sources") or {}).items():
        for pers in src.get("personnes") or []:
            pid = pers.get("id")
            if pid:
                idx.setdefault(pid, []).append(sid)
    return idx


# ---------------------------------------------------------------------------
# Profils
# ---------------------------------------------------------------------------

def _profil_myheritage(donnees, complete):
    """Replie transcription + ARK dans le DATA/TEXT de chaque citation, puis
    retire la transcription et l'ARK du record source (que MyHeritage jette)."""
    sources = donnees.get("sources") or {}
    # Texte à injecter par source citée + ARK à ajouter au PAGE (« Page/URL »).
    replis = {}
    arks = {}
    for sid, src in sources.items():
        # La NOTE du record source est conservée par MyHeritage : c'est là que
        # la provenance (dépôt/cote/lien) atterrit le plus sûrement.
        _ajouter_provenance_note(src, bloc_provenance(donnees, src))
        parts = []
        trans = _texte_transcription(src, complete)
        if trans:
            parts.append(trans)
        ark = (src.get("ark") or "").strip()
        if ark:
            arks[sid] = ark
            parts.append("Source en ligne : " + ark)
        if parts:
            replis[sid] = "\n".join(parts)
    for ind in donnees.get("individus", {}).values():
        for c in _citations_de_personne(ind):
            sid = c.get("source")
            bloc = replis.get(sid)
            if bloc:
                ancien = (c.get("texte") or "").strip()
                c["texte"] = (ancien + "\n\n" + bloc).strip() if ancien else bloc
            # Champ « Page/URL » de MyHeritage : on y accroche le permalien.
            ark = arks.get(sid)
            if ark:
                page = (c.get("page") or "").strip()
                if ark not in page:
                    c["page"] = (page + " — " + ark) if page else ark
    # Le record source ne doit plus porter la transcription ni l'ARK (repliés).
    for sid in replis:
        src = sources[sid]
        src["transcription"] = ""
        src["ark"] = ""


def _profil_ancestry(donnees, complete):
    """ARK → _WLNK au niveau personne (TITL = titre, NOTE = url) ;
    transcription → NOTE du record source. Retire ensuite ARK (WWW) du record."""
    sources = donnees.get("sources") or {}
    tags = _index_tags_personne(donnees)
    # Provenance + transcription repliées dans la NOTE du record source.
    # Ancestry conserve le REPO : la provenance y est donc en double (ceinture
    # et bretelles), volontairement — la note est le canal le plus sûr.
    for sid, src in sources.items():
        _ajouter_provenance_note(src, bloc_provenance(donnees, src))
        trans = _texte_transcription(src, complete)
        if trans:
            note = (src.get("note") or "").strip()
            src["note"] = (note + "\n\n" + trans).strip() if note else trans
        src["transcription"] = ""      # jetée par Ancestry au niveau record
    # ARK → _WLNK au niveau de chaque personne qui cite la source.
    for ind in donnees.get("individus", {}).values():
        liens = list(ind.get("_liens_web") or [])
        vus = {(l.get("url") or "").strip() for l in liens}
        for sid in _sources_citees_par(ind, tags):
            src = sources.get(sid) or {}
            url = (src.get("ark") or "").strip()
            if url and url not in vus:
                vus.add(url)
                liens.append({"titre": (src.get("titre") or "").strip(),
                              "url": url})
        if liens:
            ind["_liens_web"] = liens
    # ARK retiré du record (Ancestry jette le WWW) — désormais dans _WLNK.
    for src in sources.values():
        src["ark"] = ""


def _profil_filae(donnees, complete):
    """Agrège titre + transcription/résumé + ARK dans la NOTE de chaque personne
    qui cite la source, puis SUPPRIME tout l'appareil de sources (records,
    citations, tags, dépôts, médias de source) — seule la NOTE survit chez Filae."""
    sources = donnees.get("sources") or {}
    tags = _index_tags_personne(donnees)
    for ind in donnees.get("individus", {}).values():
        blocs = []
        for sid in _sources_citees_par(ind, tags):
            src = sources.get(sid)
            if not src:
                continue
            lignes = []
            titre = (src.get("titre") or "").strip()
            lignes.append("Source : " + titre if titre else "Source")
            # Provenance AVANT la transcription : c'est la priorité (l'acte, le
            # dépôt, la cote et le lien passent avant le texte de l'acte).
            prov = bloc_provenance(donnees, src)
            if prov:
                lignes.append(prov)
            # La transcription est un bonus : sacrifiée quand on veut alléger.
            if complete:
                trans = _texte_transcription(src, True)
                if trans:
                    lignes.append(trans)
            blocs.append("\n".join(lignes))
        if blocs:
            agg = "\n\n".join(blocs)
            note = (ind.get("note") or "").strip()
            ind["note"] = (note + "\n\n" + agg).strip() if note else agg
    # Filae jette tout : on retire sources, dépôts, citations et tags.
    donnees["sources"] = {}
    donnees["depots"] = {}
    for ind in donnees.get("individus", {}).values():
        ind["citations"] = []
        for cle in ("naissance", "deces"):
            bloc = ind.get(cle)
            if isinstance(bloc, dict) and bloc.get("citations"):
                bloc["citations"] = []
        for coll in ("residences", "evenements"):
            for item in ind.get(coll) or []:
                if isinstance(item, dict) and item.get("citations"):
                    item["citations"] = []
    for fam in donnees.get("familles", {}).values():
        mar = fam.get("mariage")
        if isinstance(mar, dict) and mar.get("citations"):
            mar["citations"] = []
        for ev in fam.get("evenements") or []:
            if isinstance(ev, dict) and ev.get("citations"):
                ev["citations"] = []


_HANDLERS = {
    "myheritage": _profil_myheritage,
    "ancestry": _profil_ancestry,
    "filae": _profil_filae,
    # « generique » et « geneanet » : aucune transformation (export tel quel).
}


def appliquer_profil(donnees, profil, transcription_complete=True):
    """Renvoie une COPIE PROFONDE de `donnees` repliée pour le site `profil`.

    Ne modifie JAMAIS l'entrée. `profil` ∈ PROFILS (défaut/inconnu → générique).
    Pour « generique » et « geneanet », renvoie une copie inchangée (l'export
    standard passe déjà bien). Voir la docstring du module pour la stratégie.
    """
    profil = normaliser_profil(profil)
    copie = copy.deepcopy(donnees)
    modele.garantir_cles(copie)
    handler = _HANDLERS.get(profil)
    if handler is not None:
        handler(copie, bool(transcription_complete))
    return copie


# ---------------------------------------------------------------------------
# Nettoyage du TEXTE exporté (après core.gedcom.exporter)
# ---------------------------------------------------------------------------

# Profils dont le site cible ne sait PAS ignorer un tag privé « _XXX ».
# Geneanet (GeneWeb) recrache le bloc GEDCOM brut dans la note de la fiche ;
# MyHeritage, Ancestry et Filae les ignorent proprement (constaté sur leurs
# fichiers réexportés) — on ne leur retire donc rien, et le profil « generique »
# (archivage, fidélité maximale) garde évidemment TOUT.
PROFILS_SANS_TAGS_PRIVES = frozenset({"geneanet"})

_LIGNE_GED = re.compile(r"^(\d+)\s+(@[^@]+@\s+)?(\S+)")


def _est_ligne_privee(ligne):
    """La ligne porte-t-elle un tag privé (« 2 _TIME 18:00 ») ?"""
    m = _LIGNE_GED.match(ligne)
    return bool(m) and m.group(3).startswith("_")


def retirer_tags_prives(texte):
    """Retire d'un texte GEDCOM toute ligne de tag privé « _XXX » AINSI QUE ses
    lignes subordonnées (niveau supérieur : CONT/CONC, sous-tags…).

    Travail au niveau du texte plutôt que des données : les tags privés sont
    émis depuis une douzaine d'endroits de core/gedcom/ecriture.py (heure des
    faits, sosa, champs de source, rôles, portrait…) et un filtre unique et
    ciblé sur la sortie garantit qu'aucun n'échappe, sans toucher à l'exporteur
    ni au modèle. La règle est celle de la norme : une ligne de niveau N est
    close par la première ligne de niveau <= N."""
    sortie = []
    seuil = None                       # niveau du tag privé en cours de coupe
    for ligne in (texte or "").split("\n"):
        m = _LIGNE_GED.match(ligne)
        if seuil is not None:
            if m and int(m.group(1)) <= seuil:
                seuil = None           # fin du sous-arbre privé
            else:
                continue               # ligne subordonnée : jetée aussi
        if m and _est_ligne_privee(ligne):
            seuil = int(m.group(1))
            continue
        sortie.append(ligne)
    return "\n".join(sortie)


def nettoyer_texte(texte, profil):
    """Adapte le TEXTE GEDCOM déjà produit au site cible.

    Aujourd'hui : retire les tags privés pour les profils qui ne les supportent
    pas (Geneanet). Sans effet pour tous les autres profils, « generique »
    compris. À appeler juste après core.gedcom.exporter()."""
    if normaliser_profil(profil) in PROFILS_SANS_TAGS_PRIVES:
        return retirer_tags_prives(texte)
    return texte
