# -*- coding: utf-8 -*-
"""
Service Personnes — construit les données affichées par l'onglet Personnes et
la fiche : listes triables, fiche complète avec parenté immédiate résolue.

Ne touche pas au stockage directement pour muter : passe par la Base (qui
garantit cohérence des liens et sauvegarde). Ici, surtout de la lecture.
"""

from core import modele
from core.modele import nom_complet
from core.validation import ErreurValidation
from services import sources as src_svc
from services import sosa as sosa_svc
from services import parente as parente_svc


def _quartier(sosa):
    """Quartier grand-parental (Sosa 4..7) d'un numéro Sosa, sinon None.
    Sert à regrouper les ancêtres par branche (les 4 grands-parents)."""
    if not sosa or sosa < 4:
        return None
    import math
    g = int(math.floor(math.log2(sosa)))   # génération (Sosa 4..7 = génération 2)
    return sosa >> (g - 2)


def _categories(donnees, sosa_map):
    """Classe chaque personne selon son lien réel à la lignée directe :
      • « directe »  : ancêtre direct (a un numéro Sosa) ;
      • « elargie »  : relié·e par le sang ou le mariage à la lignée directe
                       (frères/sœurs d'un ascendant, oncles, cousins, conjoints,
                       enfants…) — bref, même composant familial ;
      • « hors »     : aucun lien de parenté (officier d'état civil, témoin,
                       partenaire de PACS non marié, personne isolée citée
                       dans un acte).

    Un couple ne compte comme lien familial que s'il a une DATE DE MARIAGE ou
    des ENFANTS communs : une union « vide » (PACS/concubinage non documenté)
    ne relie donc pas ses partenaires à la famille. Les co-parents restent
    reliés de toute façon, via leur enfant commun.

    Renvoie {} si aucune lignée directe n'est connue (pas de personne de
    référence) : dans ce cas on n'affiche pas de catégorie.
    """
    if not sosa_map:
        return {}
    inds = donnees["individus"]
    fams = donnees.get("familles", {})
    # graphe non orienté : arêtes sang (parent↔enfant) + alliance (mariage daté)
    adj = {pid: set() for pid in inds}
    def relier(a, b):
        if a in adj and b in adj and a != b:
            adj[a].add(b); adj[b].add(a)
    for fam in fams.values():
        parents = [p for p in (fam.get("mari"), fam.get("epouse")) if p]
        enfants = fam.get("enfants") or []
        for e in enfants:                       # sang : chaque enfant ↔ chaque parent
            for p in parents:
                relier(p, e)
        # alliance : conjoints reliés seulement si mariage daté (les couples avec
        # enfants sont déjà reliés via l'enfant ; ceci rattrape les couples mariés
        # sans enfant). Un PACS/concubinage sans mariage ni enfant ne relie pas.
        if len(parents) == 2 and (fam.get("mariage") or {}).get("date"):
            relier(parents[0], parents[1])
    # BFS depuis toute la lignée directe
    relies, pile = set(sosa_map), list(sosa_map)
    while pile:
        cur = pile.pop()
        for v in adj.get(cur, ()):
            if v not in relies:
                relies.add(v); pile.append(v)
    cats = {}
    for pid in inds:
        cats[pid] = ("directe" if pid in sosa_map
                     else "elargie" if pid in relies else "hors")
    return cats


def ids_hors_famille(donnees, racine_id):
    """Ensemble des id « hors famille » (officiers, témoins, partenaires non
    mariés isolés) — à exclure des index/statistiques. Vide si aucune personne
    de référence connue (on ne peut alors pas catégoriser)."""
    inds = donnees.get("individus", {})
    if not racine_id or racine_id not in inds:
        return set()
    sosa_map = modele.sosa_par_individu(donnees, racine_id)
    cats = _categories(donnees, sosa_map)
    return {pid for pid, c in cats.items() if c == "hors"}


def lister(base, racine_id=None):
    """Résumés de toutes les personnes (tri nom + prénom). Ajoute, quand une
    personne de référence est connue : le numéro Sosa et la branche (côté +
    nom du grand-parent) — pour les vues « Ligne directe » et « Par branche » —
    ainsi que la catégorie de parenté (directe / élargie / hors famille)."""
    inds = base.donnees["individus"]
    sosa_map = (modele.sosa_par_individu(base.donnees, racine_id)
                if racine_id and racine_id in inds else {})
    cats = _categories(base.donnees, sosa_map)
    # libellés de branche pour les 4 quartiers (Sosa 4..7)
    labels = {}
    for pid, s in sosa_map.items():
        if s in (4, 5, 6, 7):
            cote = "Paternelle" if s in (4, 5) else "Maternelle"
            labels[s] = cote + " · " + (modele.nom_de_famille(inds[pid]) or "?")

    lignes = []
    for ind in inds.values():
        r = modele.resume(ind)
        s = sosa_map.get(ind["id"])
        r["sosa"] = s
        r["branche"] = labels.get(_quartier(s)) if s else None
        r["categorie"] = cats.get(ind["id"])
        lignes.append(r)
    lignes.sort(key=lambda r: (r["nom_famille"].lower(), r["prenoms"].lower()))
    return lignes


def _mini(base, pid):
    ind = base.donnees["individus"].get(pid)
    if not ind:
        return None
    return {"id": pid, "nom": modele.nom_complet(ind),
            "sexe": ind.get("sexe", "U"), "periode": modele.periode(ind)}


def fiche(base, pid, racine_id=None):
    """Fiche complète d'une personne, parenté immédiate résolue. None si absente.
    `racine_id` (personne de référence) permet d'ajouter le numéro Sosa."""
    inds = base.donnees["individus"]
    fams = base.donnees["familles"]
    ind = inds.get(pid)
    if not ind:
        return None

    peres, meres, fratrie = [], [], []
    for fid in ind.get("famc", []):        # peut être multiple (adoption, remariage)
        fam = fams.get(fid) or {}
        if fam.get("mari"):
            peres.append(_mini(base, fam["mari"]))
        if fam.get("epouse"):
            meres.append(_mini(base, fam["epouse"]))
        for e in fam.get("enfants", []):
            if e != pid:
                fratrie.append(_mini(base, e))

    unions = []
    for fid in ind.get("fams", []):
        fam = fams.get(fid) or {}
        conjoint_id = fam.get("epouse") if fam.get("mari") == pid else fam.get("mari")
        unions.append({
            "famille": fid,
            "conjoint": _mini(base, conjoint_id) if conjoint_id else None,
            "mariage": fam.get("mariage") or {},
            # Événements du couple (divorce, fiançailles, contrat…). Sans eux, un
            # divorce saisi — ou importé d'un GEDCOM — restait invisible partout.
            "evenements": fam.get("evenements") or [],
            "enfants": [_mini(base, e) for e in fam.get("enfants", [])],
        })

    d = dict(ind)
    d.update({
        "nom_complet": modele.nom_complet(ind),
        "periode": modele.periode(ind),
        "age": modele.age(ind),
        "vivant": modele.est_vivant_presume(ind),
        "peres": [p for p in peres if p],
        "meres": [m for m in meres if m],
        "fratrie": [f for f in fratrie if f],
        "unions": unions,
        "resume_auto": resume_de_vie(base, ind),
        "sources_liees": src_svc.sources_de_personne(base.donnees, pid),
    })
    sosa = sosa_svc.numero_sosa(base.donnees, racine_id, pid)
    d["sosa"] = sosa
    d["lien_racine"] = sosa_svc.libelle_lien_racine(sosa)
    # relation exacte à la personne de référence (« le grand-père de X »)
    d["racine_nom"] = ""
    d["relation_racine"] = ""
    if racine_id and racine_id != pid and racine_id in inds:
        d["racine_nom"] = nom_complet(inds[racine_id])
        lc = parente_svc.lien_complet(base.donnees, racine_id, pid)
        if lc and lc.get("lien"):
            d["relation_racine"] = lc["lien"]
    return d


def resume_de_vie(base, ind):
    """Petit résumé de vie généré, utilisé quand aucune note biographique
    n'existe. Purement descriptif, jamais inventé."""
    if (ind.get("note") or "").strip():
        return ""                       # une vraie biographie existe déjà
    accord = "e" if ind.get("sexe") == "F" else ""
    naiss, dec = ind.get("naissance") or {}, ind.get("deces") or {}
    bouts = []

    def evenement(verbe, an, lieu):
        morceau = verbe
        if an:
            morceau += " en %d" % an
        if lieu:
            morceau += " à %s" % lieu
        return morceau if (an or lieu) else ""

    if naiss.get("date") or naiss.get("lieu"):
        bouts.append(evenement("né" + accord, modele.annee_naissance(ind),
                               naiss.get("lieu")))
    profs = [p.get("valeur") for p in ind.get("professions", []) if p.get("valeur")]
    if profs:
        bouts.append("de profession %s" % ", ".join(profs))

    # Unions et enfants : uniquement ce qui est enregistré, jamais déduit.
    donnees = base.donnees
    fams = donnees.get("familles", {})
    inds = donnees.get("individus", {})
    nb_enfants = 0
    for fid in ind.get("fams", []):
        fam = fams.get(fid) or {}
        autre = (fam.get("epouse") if fam.get("mari") == ind.get("id")
                 else fam.get("mari"))
        mar = fam.get("mariage") or {}
        nom_autre = modele.nom_complet(inds.get(autre) or {}) if autre else ""
        if nom_autre or mar.get("date") or mar.get("lieu"):
            morceau = "marié" + accord
            an_m = modele.annee(mar.get("date"))
            if an_m:
                morceau += " en %d" % an_m
            if mar.get("lieu"):
                morceau += " à %s" % mar["lieu"]
            if nom_autre:
                morceau += " avec %s" % nom_autre
            bouts.append(morceau)
        divorce = next((e for e in (fam.get("evenements") or [])
                        if e.get("type") == "DIV"), None)
        if divorce and (divorce.get("date") or divorce.get("lieu")):
            an_d = modele.annee(divorce.get("date"))
            bouts.append("divorcé%s%s" % (accord, (" en %d" % an_d) if an_d else ""))
        nb_enfants += len(fam.get("enfants") or [])
    if nb_enfants:
        parent = "mère" if ind.get("sexe") == "F" else "père"
        bouts.append("%s de %d enfant%s" % (parent, nb_enfants,
                                            "s" if nb_enfants > 1 else ""))

    if dec.get("date") or dec.get("lieu"):
        bouts.append(evenement("décédé" + accord, modele.annee_deces(ind),
                               dec.get("lieu")))
    bouts = [b for b in bouts if b]
    if not bouts:
        return ""
    return "%s, %s." % (modele.nom_complet(ind), ", ".join(bouts))


def creer(base, champs, non_identifiee=False):
    """Crée une personne. Refuse une saisie vide sauf choix explicite
    « personne non identifiée » (garde-fou de fiabilité de saisie)."""
    factice = {"nom": champs.get("nom", ""), "prenoms": champs.get("prenoms", ""),
               "prenom_principal": champs.get("prenom_principal", "")}
    if not modele.est_identifie(factice) and not non_identifiee:
        raise ErreurValidation(
            "Renseigne au moins un nom ou un prénom — ou choisis explicitement "
            "« Créer une personne non identifiée ».")
    return base.creer_individu(champs)
