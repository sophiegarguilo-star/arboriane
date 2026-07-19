# -*- coding: utf-8 -*-
"""GEDCOM — export : `exporter(donnees)` -> texte GEDCOM 5.5.1 (HEAD…TRLR)."""
import html
import os
import re

from core import modele
from core.gedcom.commun import *

def _date_gedcom(valeur):
    """Traduit une date INTERNE (français : « 20/07/1984 », « vers 1850 ») en
    date GEDCOM 5.5.1 (« 20 JUL 1984 », « ABT 1850 »). Idempotent : une date déjà
    au format GEDCOM ressort inchangée."""
    from services import dates_rep          # utilitaire pur (import tardif, aucun cycle)
    return dates_rep.fr_vers_gedcom(valeur)

def _ligne(niveau, tag, valeur="", xref=""):
    morceaux = [str(niveau)]
    if xref:
        morceaux.append(xref)
    morceaux.append(tag)
    if valeur != "":
        morceaux.append(valeur)
    return " ".join(morceaux)

def _prefixe_octets(s, budget):
    """Plus grand préfixe de s dont l'encodage UTF-8 tient dans 'budget' octets."""
    out = ""
    for ch in s:
        if len((out + ch).encode("utf-8")) > budget:
            break
        out += ch
    return out or s[:1]   # au moins un caractère, pour progresser

def _couper_255(texte):
    """Coupe une ligne logique en morceaux <= ~245 octets, à recoller par CONC.

    La coupure tombe TOUJOURS entre deux caractères qui ne sont pas des espaces.
    La norme 5.5.1 l'exige, et dit pourquoi : « Values that are split for a CONC
    tag must always be split at a non-space. If the value is split on a space the
    space will be lost when concatenation takes place. » Une espace en fin de
    morceau est rognée par les lecteurs conformes ; une espace en début du morceau
    suivant l'est aussi, beaucoup de logiciels cherchant le premier caractère non
    blanc après la balise. On coupe donc au milieu d'un mot : c'est laid dans le
    fichier, mais le texte de l'utilisateur revient intact.
    """
    budget = 245   # marge sous la limite GEDCOM de 255 (préfixe « N CONC » + UTF-8)
    if len(texte.encode("utf-8")) <= budget:
        return [texte]
    morceaux, reste = [], texte
    while len(reste.encode("utf-8")) > budget:
        pref = _prefixe_octets(reste, budget)
        # Reculer tant que la coupure isole une espace, d'un côté ou de l'autre.
        k = len(pref)
        while k > 1 and (reste[k - 1] == " " or reste[k] == " "):
            k -= 1
        if k <= 1:
            k = len(pref)          # que des espaces : on coupe où l'on peut
        morceaux.append(reste[:k])
        reste = reste[k:]
    if reste:
        morceaux.append(reste)
    return morceaux

def _ajouter(lignes, niveau, tag, valeur="", xref=""):
    """Ajoute une ligne, en la découpant si sa valeur l'exige.

    Un titre, un nom, une page de citation peuvent contenir un saut de ligne ou
    dépasser 255 octets — surtout venus d'un autre logiciel. Émis tels quels, ils
    produisent une ligne que le lecteur d'en face refuse ou tronque. On délègue
    donc à CONT/CONC dès que la valeur est multi-ligne ou trop longue ; sinon on
    écrit la ligne simple, sans surcoût. Les pointeurs (@…@) ne sont jamais
    concernés : ils sont courts et mono-ligne par construction."""
    v = valeur or ""
    if xref or ("\n" not in v and len(v.encode("utf-8")) <= 245):
        lignes.append(_ligne(niveau, tag, v, xref))
    else:
        _ecrire_tag_texte(lignes, niveau, tag, v)


def _ecrire_tag_texte(lignes, niveau, tag, texte):
    """Ecrit <niveau> <tag> <texte> avec CONT (sauts de ligne) + CONC (limite
    GEDCOM de 255 octets/ligne). Générique : sert pour NOTE et pour DATA.TEXT."""
    premier = True
    for logique in (texte or "").split("\n"):
        # Une espace en FIN de valeur ne survit à aucun GEDCOM : la norme note
        # que « many GEDCOM values are trimmed of trailing spaces ». On la retire
        # nous-mêmes plutôt que d'écrire une ligne non conforme dont le lecteur
        # d'en face fera ce qu'il veut. Les espaces de TÊTE, elles, sont
        # significatives (mise en forme d'une note) : on les garde.
        logique = logique.rstrip(" \t")
        for i, morceau in enumerate(_couper_255(logique)):
            if premier:
                lignes.append(_ligne(niveau, tag, morceau))
                premier = False
            elif i == 0:
                lignes.append(_ligne(niveau + 1, "CONT", morceau))
            else:
                lignes.append(_ligne(niveau + 1, "CONC", morceau))
    if premier:   # texte entièrement vide
        lignes.append(_ligne(niveau, tag, ""))

def _ecrire_note(lignes, niveau, texte):
    """Ecrit une note (CONT/CONC) — cf. _ecrire_tag_texte."""
    _ecrire_tag_texte(lignes, niveau, "NOTE", texte)

def _ecrire_citations(lignes, niveau, citations):
    """Ecrit des citations SOUR (avec PAGE/QUAY) au niveau demandé."""
    for c in citations or []:
        sid = c.get("source")
        if not sid:
            continue
        lignes.append(_ligne(niveau, "SOUR", "@%s@" % sid))
        if c.get("page"):
            _ajouter(lignes, niveau + 1, "PAGE", c["page"])
        if c.get("quay") is not None:
            lignes.append(_ligne(niveau + 1, "QUAY", str(c["quay"])))
        if (c.get("texte") or "").strip():   # citation-extrait : la preuve mot pour mot
            lignes.append(_ligne(niveau + 1, "DATA"))
            _ecrire_tag_texte(lignes, niveau + 2, "TEXT", c["texte"].strip())
        if c.get("role"):
            lignes.append(_ligne(niveau + 1, "_ROLE", c["role"]))


# cache des coordonnées {lieu: {lat, lon}} pour l'export courant (posé par exporter)

_COORDS_EXPORT = {}

def _ecrire_plac(lignes, niveau, lieu):
    """Ecrit une ligne PLAC + coordonnées MAP/LATI/LONG si connues (cache export)."""
    if not lieu:
        return
    _ajouter(lignes, niveau, "PLAC", lieu)
    c = _COORDS_EXPORT.get(lieu)
    if c and c.get("lat") is not None and c.get("lon") is not None:
        lignes.append(_ligne(niveau + 1, "MAP"))
        lignes.append(_ligne(niveau + 2, "LATI",
                             ("N" if c["lat"] >= 0 else "S") + ("%.6f" % abs(c["lat"]))))
        lignes.append(_ligne(niveau + 2, "LONG",
                             ("E" if c["lon"] >= 0 else "W") + ("%.6f" % abs(c["lon"]))))

def _ecrire_evenement(lignes, niveau, tag, ev):
    if not ev:
        return
    if not (ev.get("date") or ev.get("lieu") or ev.get("cause")
            or ev.get("note") or ev.get("citations")):
        return
    lignes.append(_ligne(niveau, tag))
    # Réémet la date républicaine d'origine si conservée (aller-retour fidèle),
    # sinon la date grégorienne courante.
    date_ecrite = False
    if ev.get("date_rep"):
        lignes.append(_ligne(niveau + 1, "DATE", ev["date_rep"])); date_ecrite = True
    elif ev.get("date"):
        lignes.append(_ligne(niveau + 1, "DATE", _date_gedcom(ev["date"]))); date_ecrite = True
    # Heure du fait, sous le DATE : tag PRIVÉ _TIME (la norme ne définit pas
    # d'heure pour un événement — le « _ » garde le fichier valide).
    if date_ecrite and ev.get("heure"):
        lignes.append(_ligne(niveau + 2, "_TIME", ev["heure"]))
    _ecrire_plac(lignes, niveau + 1, ev.get("lieu"))
    if ev.get("cause"):
        _ajouter(lignes, niveau + 1, "CAUS", ev["cause"])
    # note de l'événement (GED-01) : relue par champs._evenement à l'import
    if ev.get("note"):
        _ecrire_note(lignes, niveau + 1, ev["note"])
    _ecrire_citations(lignes, niveau + 1, ev.get("citations"))

def _ecrire_evt_generique(lignes, niveau, ev):
    """Ecrit un événement de vie porté par ev['type'] (BAPM, BURI, DIV...) ou un
    attribut (TITL, RELI, DSCR...). Pour un attribut, la VALEUR est sur la ligne
    du tag ; pour un événement, une valeur éventuelle devient une note."""
    tag = (ev.get("type") or "EVEN").strip() or "EVEN"
    val = (ev.get("valeur") or "").strip()
    sur_ligne = val and (tag in ATTRIBUTS_INDI or tag == "EVEN" or tag.startswith("_"))
    if sur_ligne:
        _ajouter(lignes, niveau, tag, val)      # valeur libre : peut être longue/multi-ligne
    else:
        lignes.append(_ligne(niveau, tag))
    if ev.get("precision"):
        lignes.append(_ligne(niveau + 1, "TYPE", ev["precision"]))
    date_ecrite = False
    if ev.get("date_rep"):
        lignes.append(_ligne(niveau + 1, "DATE", ev["date_rep"])); date_ecrite = True
    elif ev.get("date"):
        lignes.append(_ligne(niveau + 1, "DATE", _date_gedcom(ev["date"]))); date_ecrite = True
    if date_ecrite and ev.get("heure"):
        lignes.append(_ligne(niveau + 2, "_TIME", ev["heure"]))
    _ecrire_plac(lignes, niveau + 1, ev.get("lieu"))
    if ev.get("cause"):
        _ajouter(lignes, niveau + 1, "CAUS", ev["cause"])
    note = ev.get("note") or ""
    if val and not sur_ligne:   # événement avec une précision libre -> note
        note = (note + "\n" + val).strip() if note else val
    if note:
        _ecrire_note(lignes, niveau + 1, note)
    _ecrire_citations(lignes, niveau + 1, ev.get("citations"))

@_serialise
def exporter(donnees, nom_logiciel="Arboriane", avec_medias=True):
    """Convertit la base « donnees » en texte GEDCOM 5.5.1 (encodage UTF-8).

    avec_medias=False : n'écrit aucun lien d'image (OBJE/FILE) — GEDCOM « texte pur »."""
    modele.garantir_cles(donnees)
    global _COORDS_EXPORT
    _COORDS_EXPORT = donnees.get("lieux", {}) or {}
    lignes = []
    # En-tête
    lignes.append(_ligne(0, "HEAD"))
    lignes.append(_ligne(1, "SOUR", nom_logiciel))
    lignes.append(_ligne(1, "GEDC"))
    lignes.append(_ligne(2, "VERS", "5.5.1"))
    lignes.append(_ligne(2, "FORM", "LINEAGE-LINKED"))
    lignes.append(_ligne(1, "CHAR", "UTF-8"))

    # Tags « personnes citées sur un acte » (source.personnes) -> citations
    # niveau-personne avec _ROLE, pour un aller-retour GEDCOM complet.
    tags_personne = {}
    for sid, src in donnees.get("sources", {}).items():
        for pers in src.get("personnes", []):
            if pers.get("id"):
                tags_personne.setdefault(pers["id"], []).append((sid, pers.get("role", "")))

    # Individus
    for ident, ind in donnees["individus"].items():
        lignes.append(_ligne(0, "INDI", xref="@%s@" % ident))
        prenoms = ind.get("prenoms", "")
        nom = ind.get("nom", "")
        part = (ind.get("nom_particule") or "").strip()
        prefixe = (ind.get("nom_prefixe") or "").strip()
        suffixe = (ind.get("nom_suffixe") or "").strip()
        # NAME lisible (particule hors des barres, suffixe après) + sous-champs
        nom_val = "%s%s /%s/%s" % (prenoms, (" " + part) if part else "", nom,
                                   (" " + suffixe) if suffixe else "")
        _ajouter(lignes, 1, "NAME", nom_val)
        if prefixe:
            _ajouter(lignes, 2, "NPFX", prefixe)
        if prenoms:
            _ajouter(lignes, 2, "GIVN", prenoms)
        if part:
            _ajouter(lignes, 2, "SPFX", part)
        if nom:
            _ajouter(lignes, 2, "SURN", nom)
        if suffixe:
            _ajouter(lignes, 2, "NSFX", suffixe)
        if ind.get("surnom"):
            _ajouter(lignes, 2, "NICK", ind["surnom"])
        if ind.get("prenom_principal"):
            lignes.append(_ligne(2, "_RUFNAME", ind["prenom_principal"]))
        if ind.get("nom_marital"):
            _ajouter(lignes, 2, "_MARNM", ind["nom_marital"])
        for alt in ind.get("noms_alternatifs", []):
            _ajouter(lignes, 1, "NAME", "%s /%s/" % (alt.get("prenoms", ""), alt.get("nom", "")))
            lignes.append(_ligne(2, "TYPE", (alt.get("type") or "aka").strip() or "aka"))
        sexe = ind.get("sexe", "U")
        if sexe in ("M", "F", "X", "N"):
            lignes.append(_ligne(1, "SEX", sexe))
        if ind.get("sosa"):
            lignes.append(_ligne(1, "_SOSA", str(ind["sosa"])))
        _ecrire_evenement(lignes, 1, "BIRT", ind.get("naissance"))
        _ecrire_evenement(lignes, 1, "DEAT", ind.get("deces"))
        for ev in ind.get("evenements", []):
            _ecrire_evt_generique(lignes, 1, ev)
        for prof in ind.get("professions", []):
            # professions : [{valeur}] (schéma cible) ; tolère aussi une chaîne
            libelle = prof.get("valeur", "").strip() if isinstance(prof, dict) else str(prof).strip()
            if libelle:
                lignes.append(_ligne(1, "OCCU", libelle))
        for res in ind.get("residences", []):
            # NB : on n'exporte PAS le "type" de résidence (ex. "Domicile").
            # Aucun site ne l'exploite, et Geneanet le recrache en clair dans la
            # biographie. Le type reste stocké dans Arboriane ; on cesse juste de
            # le pousser au GEDCOM.
            _ecrire_evenement(lignes, 1, "RESI", res)
        # photos de la personne : OBJE / FILE / FORM / TITL (+ _PRIM pour le portrait)
        for m in (ind.get("medias", []) if avec_medias else []):
            f = (m.get("fichier") or "").strip()
            if not f:
                continue
            lignes.append(_ligne(1, "OBJE"))
            lignes.append(_ligne(2, "FILE", f))
            ext = os.path.splitext(f)[1].lstrip(".").lower()
            if ext:
                lignes.append(_ligne(2, "FORM", ext))
            if (m.get("titre") or "").strip():
                _ajouter(lignes, 2, "TITL", m["titre"].strip())
            if m.get("principale"):
                lignes.append(_ligne(2, "_PRIM", "Y"))
        for fc in ind.get("famc", []):
            lignes.append(_ligne(1, "FAMC", "@%s@" % fc))
            # Type de filiation (MET-01) : fam["pedi"] = {enfant: type FR}.
            # « adoption »→PEDI adopted, « accueil »→PEDI foster, « probable »
            # →PEDI birth + STAT challenged (lien ni prouvé ni réfuté, norme
            # 5.5.1). Absence de type = naissance : rien n'est écrit.
            typ = ((donnees["familles"].get(fc) or {}).get("pedi")
                   or {}).get(ident) or ""
            if typ in PEDI_DEPUIS_FR:
                lignes.append(_ligne(2, "PEDI", PEDI_DEPUIS_FR[typ]))
                if typ == "probable":
                    lignes.append(_ligne(2, "STAT", "challenged"))
        for fs in ind.get("fams", []):
            lignes.append(_ligne(1, "FAMS", "@%s@" % fs))
        # personnes associées (hors filiation) : ASSO @I@ / RELA <relation>
        for a in ind.get("associations", []):
            aid = (a.get("id") or "").strip()
            if not aid:
                continue
            lignes.append(_ligne(1, "ASSO", "@%s@" % aid))
            if a.get("relation"):
                _ajouter(lignes, 2, "RELA", a["relation"])
        if (ind.get("refn") or "").strip():
            lignes.append(_ligne(1, "REFN", ind["refn"].strip()))
        if (ind.get("resn") or "").strip():
            lignes.append(_ligne(1, "RESN", ind["resn"].strip()))
        for t in ind.get("tags", []):
            if t:
                lignes.append(_ligne(1, "_TAG", t))
        # pistes de recherche : _TODO (tag Arboriane, repris par Gramps) -> portable
        for pi in ind.get("pistes", []):
            piste = (pi.get("texte") or "").strip()
            if not piste:
                continue
            lignes.append(_ligne(1, "_TODO", piste))
            if pi.get("faite"):
                lignes.append(_ligne(2, "_STAT", "done"))
        if ind.get("note"):
            _ecrire_note(lignes, 1, ind["note"])
        _ecrire_citations(lignes, 1, ind.get("citations"))
        # tags d'actes (rôle) : SOUR @Sx@ / _ROLE <rôle> — sans doublonner
        deja = {(c.get("source"), c.get("role", "")) for c in ind.get("citations") or []}
        for sid, role in tags_personne.get(ident, []):
            if (sid, role) in deja:
                continue
            deja.add((sid, role))
            lignes.append(_ligne(1, "SOUR", "@%s@" % sid))
            if role:
                lignes.append(_ligne(2, "_ROLE", role))

    # Familles
    for ident, fam in donnees["familles"].items():
        lignes.append(_ligne(0, "FAM", xref="@%s@" % ident))
        if fam.get("mari"):
            lignes.append(_ligne(1, "HUSB", "@%s@" % fam["mari"]))
        if fam.get("epouse"):
            lignes.append(_ligne(1, "WIFE", "@%s@" % fam["epouse"]))
        _ecrire_evenement(lignes, 1, "MARR", fam.get("mariage"))
        for ev in fam.get("evenements", []):
            _ecrire_evt_generique(lignes, 1, ev)
        for enfant in fam.get("enfants", []):
            lignes.append(_ligne(1, "CHIL", "@%s@" % enfant))
        if fam.get("note"):
            _ecrire_note(lignes, 1, fam["note"])

    # Enregistrements source (référencés par les citations SOUR ci-dessus).
    # Stratégie EXPORT (maximiser la compatibilité sans perdre la complétude) :
    #  - le type/date/lieu de l'acte partent en STANDARD (DATA/EVEN/DATE/PLAC),
    #    lu par les logiciels à sources structurées (Heredis, Ancestry, MyHeritage) ;
    #  - le lien part en WWW (lu par Heredis/Ancestry) ET recopié en clair dans la
    #    NOTE (repli pour Geneanet/GeneWeb qui n'a qu'UN champ texte par source) ;
    #  - on abandonne les tags privés _TYPE/_DATE/_PLAC/_ARK à l'export (ignorés
    #    ailleurs, parfois recrachés en vrac). L'import relit standard + legacy.
    # Dépôts d'archives -> enregistrements REPO (dédupliqués par nom), référencés
    # par SOUR.REPO + CALN (cote). Citation d'archive normalisée et portable.
    depots = {}
    for src in donnees.get("sources", {}).values():
        d = (src.get("depot") or "").strip()
        if d and d not in depots:
            depots[d] = "R%d" % (len(depots) + 1)
    for sid, src in donnees.get("sources", {}).items():
        lignes.append(_ligne(0, "SOUR", xref="@%s@" % sid))
        if src.get("titre"):
            _ajouter(lignes, 1, "TITL", src["titre"])
        if src.get("auteur"):
            _ajouter(lignes, 1, "AUTH", src["auteur"])
        typ, dat, lieu = src.get("type", ""), src.get("date", ""), src.get("lieu", "")
        if typ or (src.get("transcription") or "").strip():
            # place standard : SOUR.DATA.EVEN(.DATE/.PLAC) + DATA.TEXT (transcription)
            lignes.append(_ligne(1, "DATA"))
            if typ:
                lignes.append(_ligne(2, "EVEN", typ))
                if dat:
                    lignes.append(_ligne(3, "DATE", _date_gedcom(dat)))
                if lieu:
                    lignes.append(_ligne(3, "PLAC", lieu))
            if (src.get("transcription") or "").strip():
                _ecrire_tag_texte(lignes, 2, "TEXT", src["transcription"].strip())
        if src.get("abbr"):
            _ajouter(lignes, 1, "ABBR", src["abbr"])
        if src.get("publ"):
            _ajouter(lignes, 1, "PUBL", src["publ"])
        # champs propres à Arboriane (fiabilité/statut/page/ville/pays) : tags
        # privés « _ », relus à l'import → aller-retour sans perte du cœur « preuve ».
        for cle, tg in (("fiabilite", "_FIAB"), ("statut", "_STATUT"),
                        ("page", "_PAGE"), ("ville", "_VILLE"), ("pays", "_PAYS")):
            if (src.get(cle) or "").strip():
                lignes.append(_ligne(1, tg, src[cle].strip()))
        dep = (src.get("depot") or "").strip()
        if dep:                                           # dépôt d'archives + cote
            lignes.append(_ligne(1, "REPO", "@%s@" % depots[dep]))
            if src.get("cote"):
                lignes.append(_ligne(2, "CALN", src["cote"]))
        if src.get("ark"):
            lignes.append(_ligne(1, "WWW", src["ark"]))   # permalien, forme standard
        # scans/photos de l'acte (une ou PLUSIEURS pièces)
        fichiers = list(src.get("fichiers") or [])
        if not fichiers and src.get("fichier"):
            fichiers = [src["fichier"]]
        for f in (fichiers if avec_medias else []):
            if not f:
                continue
            lignes.append(_ligne(1, "OBJE"))
            lignes.append(_ligne(2, "FILE", f))
            ext = os.path.splitext(f)[1].lstrip(".").lower()
            if ext:
                lignes.append(_ligne(2, "FORM", ext))
        # NOTE = note utilisateur + repli lisible (lien ; date/lieu si pas de type,
        # donc non portés par DATA/EVEN) — l'import retire ce repli (pas de doublon).
        repli = []
        if src.get("ark"):
            repli.append("Source en ligne : " + src["ark"].strip())
        if not typ and dat:
            repli.append("Date de l'acte : " + dat.strip())
        if not typ and lieu:
            repli.append("Lieu de l'acte : " + lieu.strip())
        note_exp = src.get("note") or ""
        if repli:
            bloc = "\n".join(repli)
            note_exp = (note_exp + "\n\n" + bloc).strip() if note_exp else bloc
        if note_exp:
            _ecrire_note(lignes, 1, note_exp)

    # Enregistrements REPO (dépôts d'archives). D'abord ceux cités par une source
    # (référencés par SOUR.REPO ci-dessus), puis les dépôts de l'arbre qu'AUCUNE
    # source ne cite encore : sans quoi un dépôt saisi mais pas encore rattaché
    # disparaîtrait à l'export.
    entite_par_nom = {(d.get("nom") or "").strip().lower(): d
                      for d in donnees.get("depots", {}).values()}
    for ent in donnees.get("depots", {}).values():
        nom = (ent.get("nom") or "").strip()
        if nom and nom not in depots:
            depots[nom] = "R%d" % (len(depots) + 1)

    for nom, rid in depots.items():
        lignes.append(_ligne(0, "REPO", xref="@%s@" % rid))
        _ajouter(lignes, 1, "NAME", nom)
        ent = entite_par_nom.get(nom.strip().lower())
        if ent:
            if ent.get("type"):
                lignes.append(_ligne(1, "_TYPE", ent["type"]))
            if ent.get("lieu"):
                _ajouter(lignes, 1, "ADDR", ent["lieu"])
            if ent.get("www"):
                lignes.append(_ligne(1, "WWW", ent["www"]))
            if ent.get("note"):
                _ecrire_note(lignes, 1, ent["note"])

    lignes.append(_ligne(0, "TRLR"))
    return "\n".join(lignes) + "\n"
