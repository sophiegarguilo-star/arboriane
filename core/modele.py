# -*- coding: utf-8 -*-
"""
Modèle de données — helpers purs, sans état ni entrée/sortie.

La base d'un arbre est un simple dictionnaire JSON :

    {
      "individus": { "I1": {…}, … },
      "familles":  { "F1": {…}, … },
      "sources":   { "S1": {…}, … },
      "lieux":     { … },              # cache de coordonnées (Lot Lieux)
      "meta":      { … }
    }

Une PERSONNE :
    id, sexe (M|F|U|N|X), prenoms, nom, prenom_principal, prenoms_secondaires,
    nom_particule, nom_marital, surnom, noms_alternatifs[],
    naissance{date,lieu,citations[]}, deces{date,lieu,citations[]},
    professions[], residences[], note, tags[], evenements[], medias[],
    citations[], pistes[], vivant(bool|absent), famc[], fams[].

Une FAMILLE :
    id, mari, epouse, enfants[], mariage{date,lieu,citations[]},
    evenements[], note.

Tout le module est volontairement sans dépendance : on peut le tester seul.
"""

import datetime
import re

CLES_BASE = ("individus", "familles", "sources", "depots", "lieux", "lieux_ref",
             "favoris", "ensembles", "meta")

SEXES = ("M", "F", "U", "N", "X")   # U = inconnu, N = non consigné, X = intersexe


# ── Identifiants ──────────────────────────────────────────────────────
def nouvel_id(table, prefixe):
    """Premier identifiant libre « <prefixe><n> » (I1, F1, S1…) d'une table."""
    n = 1
    while ("%s%d" % (prefixe, n)) in table:
        n += 1
    return "%s%d" % (prefixe, n)


def _plus_grand_numero(table, prefixe):
    """Plus grand n des identifiants « <prefixe><n> » présents dans la table."""
    maxi = 0
    for cle in table:
        suffixe = str(cle)[len(prefixe):]
        if str(cle).startswith(prefixe) and suffixe.isdigit():
            maxi = max(maxi, int(suffixe))
    return maxi


def nouvel_id_monotone(donnees, cle_table, prefixe):
    """Identifiant JAMAIS réutilisé : compteur monotone persisté dans
    donnees["meta"]["compteurs"]. Après suppression de I57, le prochain individu
    ne redevient pas I57 (il hériterait des références orphelines : citations,
    associations…). Rétrocompatible : sans compteur, on part du plus grand
    identifiant existant."""
    meta = donnees.get("meta")
    if not isinstance(meta, dict):          # vieux fichier où meta n'est pas un dict
        meta = {}
        donnees["meta"] = meta
    compteurs = meta.get("compteurs")
    if not isinstance(compteurs, dict):
        compteurs = {}
        meta["compteurs"] = compteurs
    try:
        compteur = int(compteurs.get(prefixe, 0) or 0)
    except (TypeError, ValueError):
        compteur = 0
    n = max(compteur, _plus_grand_numero(donnees.get(cle_table) or {}, prefixe)) + 1
    compteurs[prefixe] = n
    return "%s%d" % (prefixe, n)


def base_vide():
    """Une base neuve, toutes les clés garanties."""
    return {cle: {} for cle in CLES_BASE}


def garantir_cles(donnees):
    """S'assure que toutes les tables existent (base chargée d'un vieux fichier)."""
    for cle in CLES_BASE:
        donnees.setdefault(cle, {})
    return donnees


# ── Dates ─────────────────────────────────────────────────────────────
def annee(date_str):
    """Extrait une année (int) d'une date GEDCOM, sinon None. Prend la dernière
    année plausible : les dates finissent par l'année, ce qui évite de
    confondre avec un numéro d'acte en début de chaîne."""
    if not date_str:
        return None
    nombres = [int(n) for n in re.findall(r"\d{3,4}", str(date_str))]
    plausibles = [n for n in nombres if 1000 <= n <= 2200]
    return plausibles[-1] if plausibles else None


def annee_naissance(ind):
    return annee((ind.get("naissance") or {}).get("date"))


def annee_deces(ind):
    return annee((ind.get("deces") or {}).get("date"))


def periode(ind):
    """« 1850-1912 », « 1850- », « -1912 » ou «  »."""
    n, d = annee_naissance(ind), annee_deces(ind)
    if n and d:
        return "%d-%d" % (n, d)
    if n:
        return "%d-" % n
    if d:
        return "-%d" % d
    return ""


def age(ind):
    """Âge au décès, ou âge actuel si présumé vivant, sinon None."""
    n = annee_naissance(ind)
    if not n:
        return None
    d = annee_deces(ind)
    if d:
        return max(0, d - n)
    if est_vivant_presume(ind):
        return max(0, datetime.date.today().year - n)
    return None


def naissance_au_plus_tard(donnees, pid, ind=None):
    """Année de naissance connue, sinon BORNE SUPÉRIEURE déduite des indices
    indirects (personne née AU PLUS TARD en...). Renvoie (annee|None, indice) :
    - un événement/résidence/profession daté en Y => né au plus tard en Y ;
    - une union en Y => né au plus tard en Y-15 (âge minimal au mariage) ;
    - un enfant né en Y => né au plus tard en Y-12 (âge minimal pour procréer).
    On retient la borne la plus contraignante (min) — un âge MINIMAL sûr."""
    ind = ind if ind is not None else donnees["individus"].get(pid) or {}
    b = annee_naissance(ind)
    if b:
        return b, "date de naissance"

    def _an(x):
        return annee(x.get("date") if isinstance(x, dict) else x)

    cands = []
    for ev in (ind.get("evenements") or []):
        y = _an(ev)
        if y:
            cands.append((y, "événement en %d" % y))
    for it in (ind.get("residences") or []):
        y = _an(it)
        if y:
            cands.append((y, "résidence en %d" % y))
    for it in (ind.get("professions") or []):
        y = _an(it)
        if y:
            cands.append((y, "profession en %d" % y))
    for _conj, fid in conjoints(donnees, pid):
        fam = donnees["familles"].get(fid) or {}
        am = annee((fam.get("mariage") or {}).get("date")) or annee(fam.get("date"))
        if am:
            cands.append((am - 15, "union en %d" % am))
    for enf in enfants(donnees, pid):
        cy = annee_naissance(donnees["individus"].get(enf, {}))
        if cy:
            cands.append((cy - 12, "enfant né en %d" % cy))
    if not cands:
        return None, ""
    return min(cands, key=lambda t: t[0])


def age_minimal(donnees, pid, ind=None, annee_courante=None):
    """Âge MINIMAL déduit (la personne a AU MOINS cet âge), ou None si aucun
    indice de date n'est disponible. Sert à repérer les âges impossibles."""
    ny, _ = naissance_au_plus_tard(donnees, pid, ind)
    if ny is None:
        return None
    if annee_courante is None:
        annee_courante = datetime.date.today().year
    return max(0, annee_courante - ny)


# ── Affichage ─────────────────────────────────────────────────────────
def nom_complet(ind):
    if not ind:
        return "?"
    prenoms = (ind.get("prenoms") or "").strip()
    part = (ind.get("nom_particule") or "").strip()
    nom = (ind.get("nom") or "").strip()
    nom_aff = ("%s %s" % (part, nom)).strip() if part else nom
    libelle = ("%s %s" % (prenoms, nom_aff)).strip()
    return libelle or "(sans nom)"


def nom_de_famille(ind):
    """Nom seul (avec particule) — pour trier/regrouper."""
    part = (ind.get("nom_particule") or "").strip()
    nom = (ind.get("nom") or "").strip()
    return (("%s %s" % (part, nom)).strip() if part else nom) or ""


def est_identifie(ind):
    """Vrai dès qu'un nom OU un prénom est renseigné (garde-fou de saisie :
    on ne crée une personne « vide » que sur choix explicite de l'utilisateur)."""
    return bool((ind.get("nom") or "").strip()
                or (ind.get("prenoms") or "").strip()
                or (ind.get("prenom_principal") or "").strip())


def est_vivant_presume(ind, annee_courante=None):
    """Règle PRUDENTE pour la publication : présumé vivant tant que rien
    n'indique le contraire.
    - un décès renseigné (date ou lieu) => décédé (PRIORITAIRE : un décès prouvé
      prime sur un drapeau 'vivant' resté à True par oubli) ;
    - clé 'vivant' explicite (True/False) ;
    - naissance il y a 100 ans ou plus => présumé décédé ;
    - sinon => présumé vivant."""
    dec = ind.get("deces") or {}
    if (dec.get("date") or "").strip() or (dec.get("lieu") or "").strip():
        return False
    if ind.get("vivant") is True:
        return True
    if ind.get("vivant") is False:
        return False
    an = annee_naissance(ind)
    if annee_courante is None:
        annee_courante = datetime.date.today().year
    if an and annee_courante - an >= 100:
        return False
    return True


def resume(ind):
    """Petit dictionnaire pratique pour les listes et les arbres."""
    return {
        "id": ind["id"],
        "nom": nom_complet(ind),
        "nom_famille": nom_de_famille(ind),
        "prenoms": ind.get("prenoms", ""),
        "sexe": ind.get("sexe", "U"),
        "periode": periode(ind),
        "vivant": est_vivant_presume(ind),
        "naissance": ind.get("naissance") or {},
        "deces": ind.get("deces") or {},
        "nb_medias": len(ind.get("medias") or []),
        "identifie": est_identifie(ind),
    }


def prenom_usuel(ind):
    p = (ind.get("prenoms") or "").split() if ind else []
    return p[0] if p else ""


def nom_court(ind):
    """Prénom usuel + nom (ex. « Marie DUBOIS »), pour les liens."""
    if not ind:
        return "?"
    return ("%s %s" % (prenom_usuel(ind), nom_de_famille(ind))).strip() or "(sans nom)"


def carte_perso(donnees, pid):
    """Fiche minimale pour l'affichage d'une lignée / d'un arbre."""
    ind = donnees["individus"].get(pid, {})
    return {"id": pid, "nom": nom_complet(ind), "sexe": ind.get("sexe", "U"),
            "periode": periode(ind)}


# ── Navigation dans la parenté (requêtes pures) ───────────────────────
def parents(donnees, ident):
    """(pere_id, mere_id) ou ('', '')."""
    ind = donnees["individus"].get(ident)
    if not ind or not ind.get("famc"):
        return "", ""
    fam = donnees["familles"].get(ind["famc"][0])
    if not fam:
        return "", ""
    return fam.get("mari", ""), fam.get("epouse", "")


def conjoints(donnees, ident):
    """Liste des (conjoint_id, famille_id)."""
    res = []
    ind = donnees["individus"].get(ident)
    for fid in (ind or {}).get("fams", []):
        fam = donnees["familles"].get(fid)
        if not fam:
            continue
        autre = fam["epouse"] if fam.get("mari") == ident else fam.get("mari")
        res.append((autre or "", fid))
    return res


def enfants(donnees, ident):
    """Ids des enfants (toutes unions)."""
    res = []
    ind = donnees["individus"].get(ident)
    for fid in (ind or {}).get("fams", []):
        fam = donnees["familles"].get(fid)
        if fam:
            res.extend(fam.get("enfants", []))
    return res


def freres_soeurs(donnees, ident):
    ind = donnees["individus"].get(ident)
    if not ind or not ind.get("famc"):
        return []
    fam = donnees["familles"].get(ind["famc"][0])
    return [e for e in (fam or {}).get("enfants", []) if e != ident] if fam else []


# ── Sosa-Stradonitz ───────────────────────────────────────────────────
def ascendance_sosa(donnees, ident, generations=40):
    """{ numero_sosa: individu_id } : 1 = personne, 2 = père, 3 = mère…
    Garde anti-cycle sur chaque branche (filiation corrompue)."""
    resultat = {}

    def remplir(pid, numero, niveau, chemin):
        if not pid or niveau > generations or pid in chemin:
            return
        resultat[numero] = pid
        pere, mere = parents(donnees, pid)
        chemin2 = chemin | {pid}
        remplir(pere, numero * 2, niveau + 1, chemin2)
        remplir(mere, numero * 2 + 1, niveau + 1, chemin2)

    remplir(ident, 1, 1, frozenset())
    return resultat


def sosa_par_individu(donnees, racine_id, generations=40):
    """{ individu_id: numero_sosa } (plus petit numéro en cas d'implexe)."""
    par_id = {}
    for num, pid in ascendance_sosa(donnees, racine_id, generations).items():
        if pid not in par_id or num < par_id[pid]:
            par_id[pid] = num
    return par_id


# ── Accord en genre / ordinaux (vocabulaire de parenté) ───────────────
def genre(sexe, masculin, feminin):
    return feminin if sexe == "F" else masculin


_ORDINAUX = {1: "premier", 2: "deuxième", 3: "troisième", 4: "quatrième",
             5: "cinquième", 6: "sixième", 7: "septième", 8: "huitième"}


def ordinal(n):
    return _ORDINAUX.get(n, "%de" % n)
