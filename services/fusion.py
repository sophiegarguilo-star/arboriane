# -*- coding: utf-8 -*-
"""
Fusion de deux personnes en doublon + détection de doublons probables.

Portage fidèle de la logique mature de la v1 (genea/store.fusionner_individus) :
on COMPLÈTE les champs vides de la personne gardée avec ceux de l'absorbée —
JAMAIS d'écrasement —, on fusionne les listes et les citations (dédupliquées),
on repointe toutes les références (familles, sources.personnes, associations),
puis on supprime l'absorbée. Les familles devenues identiques sont fusionnées
et fams/famc de tous les individus sont recalculés depuis la table des familles
(source de vérité). La base v2 n'expose ni `_fusionner_familles_doublons` ni
`_dedup_citations` : ils sont reconstruits ici, sans modifier `stockage.py`.
"""

from core import modele


# ── Helpers portés de la v1 (recréés ici, base v2 ne les fournit pas) ──────
def _dedup_citations(cits):
    """Déduplique une liste de citations (source, page, role identiques)."""
    vus, net = set(), []
    for c in cits or []:
        cle = (c.get("source"), c.get("page"), c.get("role"))
        if cle not in vus:
            vus.add(cle)
            net.append(c)
    return net


def _fusionner_familles_doublons(donnees):
    """Fusionne les familles au MÊME couple (mari, épouse tous deux non vides) :
    combine les enfants, garde la 1re, supprime les autres. Sert après une
    fusion d'individus (deux familles peuvent devenir identiques)."""
    fams = donnees["familles"]
    par_couple = {}
    for fid in list(fams.keys()):
        fam = fams[fid]
        mari, epouse = fam.get("mari"), fam.get("epouse")
        if not mari or not epouse:
            continue
        cle = tuple(sorted([mari, epouse]))
        if cle in par_couple:
            garde = par_couple[cle]
            for e in fam.get("enfants", []):
                if e not in garde.setdefault("enfants", []):
                    garde["enfants"].append(e)
            gm = garde.get("mariage") or {}
            fm = fam.get("mariage") or {}
            if (not gm.get("date") and not gm.get("lieu")
                    and (fm.get("date") or fm.get("lieu"))):
                garde["mariage"] = fam["mariage"]
            del fams[fid]
        else:
            par_couple[cle] = fam


# ── Fusion ─────────────────────────────────────────────────────────────────
def fusionner(base, garde_id, absorbe_id):
    """Fusionne 'absorbe' dans 'garde' : complète les champs VIDES de garde avec
    ceux d'absorbe (jamais d'écrasement), fusionne listes/citations, repointe
    toutes les références (familles, sources, associations), puis supprime
    absorbe. Recalcule fams/famc et sauvegarde. Renvoie un résumé
    {garde, absorbe, champs_completes:[]}, ou None si ids invalides/identiques.

    `base` est une instance de core.stockage.Base."""
    with base._verrou:
        inds = base.donnees["individus"]
        if garde_id == absorbe_id or garde_id not in inds or absorbe_id not in inds:
            return None
        g, a = inds[garde_id], inds[absorbe_id]
        resume = {"garde": garde_id, "absorbe": absorbe_id, "champs_completes": []}

        # 1) champs scalaires : compléter les VIDES de garde
        for cle in ("prenoms", "nom", "prenom_principal", "prenoms_secondaires",
                    "nom_particule", "nom_marital", "surnom", "refn", "resn",
                    "note"):
            if not (g.get(cle) or "").strip() and (a.get(cle) or "").strip():
                g[cle] = a[cle]
                resume["champs_completes"].append(cle)
        if g.get("sexe", "U") == "U" and a.get("sexe", "U") != "U":
            g["sexe"] = a["sexe"]
            resume["champs_completes"].append("sexe")

        # 2) naissance / décès : compléter date/lieu vides + fusionner citations
        for evt in ("naissance", "deces"):
            ge = g.setdefault(evt, {"date": "", "lieu": ""})
            ae = a.get(evt) or {}
            for k in ("date", "lieu"):
                if not (ge.get(k) or "").strip() and (ae.get(k) or "").strip():
                    ge[k] = ae[k]
                    if evt not in resume["champs_completes"]:
                        resume["champs_completes"].append(evt)
            cits = list(ge.get("citations") or []) + list(ae.get("citations") or [])
            if cits:
                ge["citations"] = _dedup_citations(cits)

        # 3) listes : append des éléments absents
        for cle in ("noms_alternatifs", "professions", "residences",
                    "associations", "tags", "pistes", "evenements", "medias"):
            fusion = list(g.get(cle) or [])
            for item in (a.get(cle) or []):
                if item not in fusion:
                    fusion.append(item)
            g[cle] = fusion

        # citations niveau-personne : concaténer + dédupliquer
        cits = list(g.get("citations") or []) + list(a.get("citations") or [])
        if cits:
            g["citations"] = _dedup_citations(cits)

        # 4) familles : absorbe -> garde (parent ou enfant)
        for fam in base.donnees["familles"].values():
            for role in ("mari", "epouse"):
                if fam.get(role) == absorbe_id:
                    autre = fam.get("epouse") if role == "mari" else fam.get("mari")
                    fam[role] = garde_id if autre != garde_id else ""
            if absorbe_id in fam.get("enfants", []):
                fam["enfants"] = list(dict.fromkeys(
                    garde_id if e == absorbe_id else e for e in fam["enfants"]))

        # 5) sources : re-pointer les personnes taguées + dédup
        for src in base.donnees.get("sources", {}).values():
            perss = src.get("personnes")
            if not perss:
                continue
            vus, net = set(), []
            for p in perss:
                if p.get("id") == absorbe_id:
                    p["id"] = garde_id
                k = (p.get("id"), p.get("role"))
                if k not in vus:
                    vus.add(k)
                    net.append(p)
            src["personnes"] = net

        # 6) associations pointant vers absorbe
        for ind in inds.values():
            for asso in ind.get("associations") or []:
                if asso.get("id") == absorbe_id:
                    asso["id"] = garde_id

        # 7) supprimer absorbe, fusionner familles identiques, recalculer, sauver
        del inds[absorbe_id]
        _fusionner_familles_doublons(base.donnees)
        base._nettoyer_familles_vides()
        base._recalc_tous_liens()
        base.sauvegarder()
        return resume


# ── Détection de doublons probables ────────────────────────────────────────
def _norm(txt):
    return " ".join((txt or "").lower().split())


def doublons_probables(donnees, ecart_max=3):
    """Paires suspectes : même nom complet normalisé ET années de naissance
    proches (écart <= ecart_max) OU l'une des deux absente. Renvoie une liste
    de {a, b, nom, raison}."""
    inds = list(donnees["individus"].values())
    paires = []
    for i in range(len(inds)):
        for j in range(i + 1, len(inds)):
            x, y = inds[i], inds[j]
            nom = _norm(modele.nom_complet(x))
            if not nom or nom == "(sans nom)" or nom != _norm(modele.nom_complet(y)):
                continue
            ax = modele.annee_naissance(x)
            ay = modele.annee_naissance(y)
            if ax is not None and ay is not None:
                if abs(ax - ay) > ecart_max:
                    continue
                raison = ("mêmes années de naissance"
                          if ax == ay else "années de naissance proches")
            else:
                raison = "même nom, année de naissance manquante"
            paires.append({"a": x["id"], "b": y["id"],
                           "nom": modele.nom_complet(x), "raison": raison})
    return paires
