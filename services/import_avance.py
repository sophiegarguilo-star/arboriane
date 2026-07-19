# -*- coding: utf-8 -*-
"""
Import GEDCOM avancé — comparaison détaillée et import fusionnant (prudent).

Contrairement à services/echange.py (compteurs seulement, puis remplacement
brutal), ce module :
  - `comparer_detaille` liste NOMMÉMENT les personnes ajoutées, disparues et
    MODIFIÉES (avec les champs touchés), l'appariement se faisant par la clé
    approximative (nom complet + année de naissance) ;
  - `fusionner_import` importe en COMPLÉTANT les personnes existantes appariées
    (jamais d'écrasement) et en ajoutant les non-appariées — il ne supprime
    jamais d'existant ;
  - `importer_zip` lit un .zip d'arbre Arboriane et en extrait un aperçu, sans
    l'appliquer.

Bibliothèque standard uniquement.
"""

import base64 as _b64
import io
import json
import zipfile

from core import gedcom, modele


def _cle(ind):
    """Clé d'appariement d'une personne, ou None si elle ne discrimine rien.

    Apparier sur « nom + année de naissance » ne vaut QUE si les deux sont là.
    Sans année, tous les « Targaryen » du fichier deviennent la même personne ;
    sans nom, toutes les personnes anonymes n'en font plus qu'une. Sur GoT.ged,
    cela effaçait 81 individus sur 501 — en silence, à la fusion.

    Une clé None signifie : ne jamais apparier, toujours ajouter. Mieux vaut un
    doublon visible, que l'utilisateur peut fusionner à la main, qu'une personne
    disparue qu'il ne verra jamais.
    """
    nom = modele.nom_complet(ind).strip().lower()
    annee = modele.annee_naissance(ind)
    if not nom or nom == "(sans nom)" or annee is None:
        return None
    return (nom, annee)


# Champs comparés pour détecter une modification (scalaires + sous-faits).
_CHAMPS_SCALAIRES = ("sexe", "prenoms", "nom", "prenom_principal",
                     "prenoms_secondaires", "nom_particule", "nom_marital",
                     "surnom", "refn", "resn", "note")
# NB : « associations » n'est PAS fusionné — ses entrées référencent des ID de
# personnes qui deviennent périmés après import (on ne recrée pas de lien faux).
_CHAMPS_LISTES = ("noms_alternatifs", "professions", "residences",
                  "tags", "pistes", "evenements", "medias", "citations")


def _champs_differents(actuel, entrant):
    """Liste des champs qui diffèrent entre deux individus appariés."""
    diffs = []
    for cle in _CHAMPS_SCALAIRES:
        if (actuel.get(cle) or "") != (entrant.get(cle) or ""):
            diffs.append(cle)
    for evt in ("naissance", "deces"):
        ea, ee = actuel.get(evt) or {}, entrant.get(evt) or {}
        if ((ea.get("date") or "") != (ee.get("date") or "")
                or (ea.get("lieu") or "") != (ee.get("lieu") or "")):
            diffs.append(evt)
    for cle in _CHAMPS_LISTES:
        if (actuel.get(cle) or []) != (entrant.get(cle) or []):
            diffs.append(cle)
    return diffs


def comparer_detaille(app, texte):
    """Compare le GEDCOM entrant à la base actuelle (sans rien écrire) et détaille
    les personnes ajoutées / disparues / modifiées. L'appariement se fait sur la
    clé (nom + année de naissance)."""
    if not app.base:
        raise ValueError("Aucun arbre ouvert.")
    nouveau = gedcom.importer(texte)

    actuels = {}
    for ind in app.base.donnees["individus"].values():
        actuels.setdefault(_cle(ind), ind)
    entrants = {}
    for ind in nouveau["individus"].values():
        entrants.setdefault(_cle(ind), ind)

    n_actuel = len(app.base.donnees["individus"])
    n_nouveau = len(nouveau["individus"])

    ajoutees, disparues, modifiees = [], [], []
    for cle, ind in entrants.items():
        if cle not in actuels:
            ajoutees.append(modele.nom_complet(ind))
    for cle, ind in actuels.items():
        if cle not in entrants:
            disparues.append(modele.nom_complet(ind))
    for cle, ind in actuels.items():
        if cle in entrants:
            champs = _champs_differents(ind, entrants[cle])
            if champs:
                modifiees.append({"nom": modele.nom_complet(ind), "champs": champs})

    return {
        "total_actuel": n_actuel,
        "total_nouveau": n_nouveau,
        "ajoutees": sorted(ajoutees),
        "disparues": sorted(disparues),
        "modifiees": modifiees,
        # alerte si l'import fait perdre plus de 20 % des personnes existantes
        "reduction_forte": n_actuel > 0 and n_nouveau < n_actuel * 0.8,
    }


def _distributeur_ids(table, prefixe):
    """Distributeur d'identifiants libres, équivalent à des appels répétés de
    `modele.nouvel_id` mais sans repartir de 1 à chaque fois : sur un gros
    import (GED-03), ce rebalayage rendait l'ajout de N personnes quadratique.
    La table ne fait que GROSSIR pendant l'import, donc avancer d'un cran après
    chaque attribution rend exactement la même suite d'identifiants (les trous
    sont comblés en ordre croissant, comme avant)."""
    n = 1

    def suivant():
        nonlocal n
        while ("%s%d" % (prefixe, n)) in table:
            n += 1
        nid = "%s%d" % (prefixe, n)
        n += 1
        return nid
    return suivant


def _cle_json(item):
    """Clé de dédoublonnage d'un élément de liste (dict, chaîne…) : sa forme
    JSON à clés triées. Deux dicts égaux donnent la même clé, quel que soit
    l'ordre de leurs champs — exactement ce que testait « item in liste »,
    mais en O(1) au lieu d'une comparaison à chaque élément déjà présent."""
    return json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)


def _fusionner_liste(fusion, entrants):
    """Ajoute à `fusion` les éléments de `entrants` qui n'y sont pas encore.
    Renvoie True si au moins un élément a été ajouté. Le test d'appartenance
    passe par un ensemble de clés sérialisées : sur un GEDCOM de 10 Mo, les
    « not in liste » répétés rendaient l'import quadratique (GED-03)."""
    vus = {_cle_json(x) for x in fusion}
    ajoute = False
    for item in entrants:
        cle = _cle_json(item)
        if cle not in vus:
            vus.add(cle)
            fusion.append(item)
            ajoute = True
    return ajoute


def _completer(actuel, entrant):
    """Complète les champs VIDES de `actuel` avec ceux de `entrant` (jamais
    d'écrasement). Renvoie la liste des champs complétés."""
    completes = []
    for cle in _CHAMPS_SCALAIRES:
        if not (actuel.get(cle) or "").strip() and (entrant.get(cle) or "").strip():
            actuel[cle] = entrant[cle]
            completes.append(cle)
    for evt in ("naissance", "deces"):
        ea = actuel.setdefault(evt, {"date": "", "lieu": ""})
        ee = entrant.get(evt) or {}
        for k in ("date", "lieu"):
            if not (ea.get(k) or "").strip() and (ee.get(k) or "").strip():
                ea[k] = ee[k]
                if evt not in completes:
                    completes.append(evt)
        # Fusionne les citations (preuves) de l'événement — sinon les actes de
        # naissance/décès de l'import seraient perdus. Les refs sont déjà réindexées.
        cits = list(ea.get("citations") or [])
        if _fusionner_liste(cits, ee.get("citations") or []):
            if evt not in completes:
                completes.append(evt)
        if cits:
            ea["citations"] = cits
    for cle in _CHAMPS_LISTES:
        fusion = list(actuel.get(cle) or [])
        ajoute = _fusionner_liste(fusion, entrant.get(cle) or [])
        actuel[cle] = fusion
        if ajoute:
            completes.append(cle)
    return completes


def _remap_citations_personne(ind, carte):
    """Réécrit l'identifiant `source` de toutes les citations d'une personne
    (niveau personne + naissance/décès + résidences/événements/médias) selon la
    carte ancien_sid -> nouveau_sid."""
    def fix(cits):
        for c in (cits or []):
            if isinstance(c, dict) and c.get("source") in carte:
                c["source"] = carte[c["source"]]
    fix(ind.get("citations"))
    for ev in ("naissance", "deces"):
        e = ind.get(ev)
        if isinstance(e, dict):
            fix(e.get("citations"))
    for cle in ("residences", "evenements", "medias"):
        for e in (ind.get(cle) or []):
            if isinstance(e, dict):
                fix(e.get("citations"))


def _importer_sources(nouveau, donnees):
    """Importe dépôts et sources de l'arbre entrant avec de NOUVEAUX identifiants
    (évite d'écraser/de percuter les sources existantes) et renvoie la carte
    ancien_sid -> nouveau_sid pour réécrire les citations. Sans cela, une citation
    importée « S3 » pointerait vers la source « S3 » — différente — de l'arbre."""
    carte_dep = {}
    prochain_dep = _distributeur_ids(donnees.setdefault("depots", {}), "R")
    for did, dep in (nouveau.get("depots") or {}).items():
        nd = prochain_dep()
        d2 = dict(dep); d2["id"] = nd
        donnees["depots"][nd] = d2
        carte_dep[did] = nd
    carte = {}
    prochain_src = _distributeur_ids(donnees.setdefault("sources", {}), "S")
    for sid, src in (nouveau.get("sources") or {}).items():
        ns = prochain_src()
        s2 = dict(src); s2["id"] = ns
        if s2.get("depot_id") in carte_dep:
            s2["depot_id"] = carte_dep[s2["depot_id"]]
        elif s2.get("depot_id"):
            s2["depot_id"] = ""          # dépôt non importé : on n'invente pas de lien
        s2["personnes"] = []             # tags de personnes non re-résolus (ids distincts)
        donnees["sources"][ns] = s2
        carte[sid] = ns
    return carte


def _remap_citations_famille(fam, carte):
    """Même travail que pour une personne, sur le mariage et les événements
    du couple (divorce, fiançailles…)."""
    def fix(cits):
        for c in (cits or []):
            if isinstance(c, dict) and c.get("source") in carte:
                c["source"] = carte[c["source"]]
    fix((fam.get("mariage") or {}).get("citations"))
    for ev in (fam.get("evenements") or []):
        if isinstance(ev, dict):
            fix(ev.get("citations"))


def _index_familles_libres(donnees):
    """Index des familles DÉJÀ présentes, par couple : {(mari, epouse): [fids]}.

    Chaque fid est « libre » : une famille entrante ne peut en réclamer qu'UNE
    (retrait de la liste). Sans quoi un remariage du même couple (deux FAM
    distincts, deux dates de mariage — cas REMARR.GED de gedcom.org) serait
    replié sur une seule famille, et la seconde union disparaîtrait.

    Construit AVANT la boucle d'import : l'ancien balayage répété de la liste
    des familles rendait l'import fusionnant quadratique (GED-03, 107 s sur un
    GEDCOM de 10 Mo). Les listes gardent l'ordre d'insertion de la table, donc
    la première famille candidate reste la même qu'avant.
    """
    index = {}
    for fid, fam in donnees["familles"].items():
        mari, epouse = fam.get("mari"), fam.get("epouse")
        if mari and epouse:
            index.setdefault((mari, epouse), []).append(fid)
    return index


def _famille_du_couple(donnees, mari, epouse, index_libres):
    """Famille existante encore libre unissant exactement ces deux personnes,
    sinon None. La famille rendue est RETIRÉE des libres (réclamée)."""
    if not (mari and epouse):
        return None
    fids = index_libres.get((mari, epouse))
    if not fids:
        return None
    return donnees["familles"].get(fids.pop(0))


def _fusionner_familles(nouveau, donnees, carte_ind, carte_src):
    """Reporte les familles entrantes dans la base, en traduisant leurs
    pointeurs par `carte_ind` (id entrant -> id retenu dans la base).

    Sans ceci, l'import fusionnant ajoutait les personnes et JETAIT la parenté :
    l'arbre ressortait plat, sans le moindre père ni enfant. Une famille dont on
    ne retrouve aucun membre est ignorée, pas inventée.
    """
    ajoutees = completees = 0
    # Seules les familles DÉJÀ présentes avant l'import peuvent être complétées,
    # et chacune une seule fois : on ne replie pas deux unions entrantes du même
    # couple l'une sur l'autre. L'index est figé AVANT la boucle : les familles
    # ajoutées pendant l'import n'y entrent jamais (comme avant, où `libres`
    # était un instantané des clés).
    libres = _index_familles_libres(donnees)
    prochain_fid = _distributeur_ids(donnees["familles"], "F")
    for fam in nouveau["familles"].values():
        mari = carte_ind.get(fam.get("mari") or "", "")
        epouse = carte_ind.get(fam.get("epouse") or "", "")
        enfants = [carte_ind[c] for c in (fam.get("enfants") or []) if c in carte_ind]
        # On ne jette RIEN : une famille sans époux connu peut porter une date de
        # mariage (« 10 MAY 1463 » chez les Habsbourg), et « Remplacer » la garde.
        # Les deux modes doivent rendre le même arbre — sinon l'utilisateur perd
        # des données selon le bouton qu'il a choisi.
        cible = _famille_du_couple(donnees, mari, epouse, libres)
        if cible is None:
            _remap_citations_famille(fam, carte_src)
            fid = prochain_fid()
            donnees["familles"][fid] = {
                "id": fid, "mari": mari, "epouse": epouse, "enfants": enfants,
                "mariage": dict(fam.get("mariage") or {}),
                "evenements": list(fam.get("evenements") or []),
                "note": fam.get("note", ""),
            }
            ajoutees += 1
        else:
            avant = len(cible["enfants"])
            for c in enfants:
                if c not in cible["enfants"]:
                    cible["enfants"].append(c)
            if len(cible["enfants"]) != avant:
                completees += 1
    return ajoutees, completees


def fusionner_import(app, texte, corrections_lieux=None):
    """Import fusionnant PRUDENT : chaque individu entrant apparié (nom + année)
    à un existant complète ses champs vides (sans écraser) ; les non-appariés
    sont ajoutés comme nouvelles personnes. Les familles entrantes sont
    reportées, leurs pointeurs traduits vers les identifiants retenus.
    Ne supprime jamais d'existant. Sauvegarde (horodatée) avant modification.
    `corrections_lieux` {ancien: nouveau} : normalisation des lieux avant fusion.
    Renvoie {ajoutees, completees, familles_ajoutees, familles_completees}."""
    if not app.base:
        raise ValueError("Aucun arbre ouvert.")
    nouveau = gedcom.importer(texte)
    if corrections_lieux:
        from services import import_lieux
        import_lieux.appliquer_corrections(nouveau, corrections_lieux)
    # Scans référencés par un chemin absolu et présents sur le disque local :
    # copiés dans l'arbre AVANT la fusion des sources (noms de fichiers corrigés).
    from services import import_medias
    bilan_scans = import_medias.importer_scans_locaux(app, nouveau)

    base = app.base
    with base._verrou:
        base.sauvegarder()                  # copie horodatée avant toute écriture
        donnees = base.donnees
        # Importe d'abord les sources (nouveaux ids) et fusionne le cache de
        # lieux (clé = nom), pour que les citations importées pointent vers les
        # bonnes sources et que les lieux gardent leurs coordonnées sur la carte.
        carte_src = _importer_sources(nouveau, donnees)
        for nom, coord in (nouveau.get("lieux") or {}).items():
            donnees.setdefault("lieux", {}).setdefault(nom, coord)

        # Index des personnes DÉJÀ dans l'arbre. On ne l'enrichit pas au fil de
        # l'import : un fichier entrant ne doit jamais se replier sur lui-même.
        # Deux personnes distinctes du même fichier, même homonymes, restent deux
        # personnes — c'est le fichier qui fait foi, pas notre heuristique.
        index = {}
        for ind in donnees["individus"].values():
            cle = _cle(ind)
            if cle is not None:
                index.setdefault(cle, ind)

        ajoutees = completees = 0
        carte_ind = {}          # id entrant -> id retenu dans la base
        prochain_iid = _distributeur_ids(donnees["individus"], "I")
        for entrant in nouveau["individus"].values():
            _remap_citations_personne(entrant, carte_src)   # réf. sources -> nouveaux ids
            cle = _cle(entrant)
            cible = index.pop(cle, None) if cle is not None else None
            if cible is not None:
                if _completer(cible, entrant):
                    completees += 1
                carte_ind[entrant["id"]] = cible["id"]
            else:
                nid = prochain_iid()
                copie = dict(entrant)
                copie["id"] = nid
                # famc/fams sont DÉRIVÉS de la table des familles : on les vide
                # ici, puis on les reconstruit après avoir reporté les familles.
                copie["famc"] = []
                copie["fams"] = []
                copie["associations"] = []  # réf. de personnes périmées après import
                donnees["individus"][nid] = copie
                carte_ind[entrant["id"]] = nid
                ajoutees += 1

        fam_ajoutees, fam_completees = _fusionner_familles(
            nouveau, donnees, carte_ind, carte_src)

        modele.garantir_cles(donnees)
        # On RECALCULE les liens dérivés, sans « nettoyer » les familles : ce
        # ménage-là efface les unions à parent unique et sans date, créées par
        # erreur dans l'interface. Dans un fichier importé, une famille qui ne
        # porte qu'un époux est une union à conjoint inconnu — une information,
        # pas un déchet. Elle coûtait 281 familles sur Habsburg.ged.
        base._recalc_tous_liens()
        base.sauvegarder()
    return {"ajoutees": ajoutees, "completees": completees,
            "familles_ajoutees": fam_ajoutees, "familles_completees": fam_completees,
            # Comme pour « Remplacer » : dire si le fichier est d'une autre version.
            "version_fichier": nouveau.get("meta", {}).get("version_fichier", ""),
            # Bilan des scans référencés (copiés / non retrouvés sur ce PC).
            "scans": bilan_scans}


def importer_zip(app, chemin_zip_ou_bytes):
    """Lit un .zip d'arbre Arboriane (contenant arboriane.json) et renvoie un
    aperçu {personnes, familles, sources} SANS l'appliquer. Accepte un chemin,
    des octets, ou une chaîne base64 (éventuellement en data-URI). L'application
    effective se fait via une route dédiée qui remplace la base."""
    source = chemin_zip_ou_bytes
    if isinstance(source, str):
        s = source.strip()
        # data-URI ou base64 pur : décoder ; sinon on suppose un chemin de fichier
        if s.startswith("data:") and "," in s:
            source = _b64.b64decode(s.split(",", 1)[1])
        elif not (("/" in s) or ("\\" in s) or s.lower().endswith(".zip")):
            try:
                source = _b64.b64decode(s, validate=True)
            except (ValueError, TypeError):
                pass

    if isinstance(source, (bytes, bytearray)):
        fichier = io.BytesIO(bytes(source))
    else:
        fichier = source                    # chemin de fichier

    with zipfile.ZipFile(fichier) as z:
        cible = None
        for nom in z.namelist():
            base_nom = nom.rsplit("/", 1)[-1]
            if base_nom in ("arboriane.json", "kintrace.json"):
                cible = nom
                break
        if cible is None:
            raise ValueError("Archive invalide : arboriane.json introuvable.")
        with z.open(cible) as f:
            donnees = json.loads(f.read().decode("utf-8"))

    if not isinstance(donnees, dict):
        raise ValueError("Archive invalide : base illisible.")
    modele.garantir_cles(donnees)
    return {
        "personnes": len(donnees.get("individus", {})),
        "familles": len(donnees.get("familles", {})),
        "sources": len(donnees.get("sources", {})),
        "donnees": donnees,
    }
