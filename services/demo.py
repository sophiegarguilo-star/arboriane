# -*- coding: utf-8 -*-
"""
Arbre de démonstration Arboriane — famille 100 % FICTIVE.

~100 personnes, 12 générations d'ascendance depuis le Sosa 1 (Lucie MARTIN, née
en 2006 à Tours). Lignée principale MARTIN en Val de Loire (Chinon → Amboise →
Tours → Angers → Nantes), une branche anglaise (WHITAKER, de Londres et
Portsmouth) entrée par mariage après 1945, des branches collatérales pour tester
la parenté, et une petite famille « cas de test » aux incohérences VOLONTAIRES
et clairement identifiées pour l'écran Cohérence.

Aucune donnée réelle, aucune clé ni secret. Toutes les pièces (actes, portraits)
sont des SPÉCIMENS générés en SVG (aucune dépendance externe).

Numérotation Sosa : père d'un Sosa n = 2n, mère = 2n+1. À la génération g, le
père de la lignée directe porte le Sosa 2^g et la mère 2^g+1.

Résumé de l'histoire familiale : voir HISTOIRE, en bas de ce fichier.
"""

import os
import random

from core import espace as espace_mod
from core import stockage

VERSION = 4

MOIS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
        "NOV", "DEC")

# Année de naissance de référence par génération (Sosa 1 = génération 0).
# Écarts ~27 ans : la 12ᵉ génération naît vers 1678 (Ancien Régime), cohérent.
GEN = {0: 2006, 1: 1979, 2: 1952, 3: 1925, 4: 1898, 5: 1871, 6: 1844,
       7: 1817, 8: 1790, 9: 1762, 10: 1734, 11: 1706, 12: 1678}

# Lieux (Touraine et migrations) — libellés « Commune, Département ».
CHINON = "Chinon, Indre-et-Loire"
CRAVANT = "Cravant-les-Côteaux, Indre-et-Loire"
AMBOISE = "Amboise, Indre-et-Loire"
TOURS = "Tours, Indre-et-Loire"
LOCHES = "Loches, Indre-et-Loire"
ANGERS = "Angers, Maine-et-Loire"
NANTES = "Nantes, Loire-Atlantique"
LONDRES = "Londres, Angleterre"
PORTSMOUTH = "Portsmouth, Angleterre"
BRISTOL = "Bristol, Angleterre"

PRENOMS_M = ["Jean", "Pierre", "Louis", "Henri", "André", "Joseph", "François",
             "Émile", "Marcel", "Auguste", "Baptiste", "Gaston", "Léon",
             "Fernand", "Jules", "Eugène", "Prosper", "Antoine", "Lucien",
             "Paul", "Georges", "Étienne", "Mathurin", "Raymond", "Théophile"]
PRENOMS_F = ["Marie", "Jeanne", "Louise", "Marguerite", "Suzanne", "Yvonne",
             "Germaine", "Léontine", "Adèle", "Célestine", "Augustine",
             "Berthe", "Eugénie", "Joséphine", "Henriette", "Rose",
             "Madeleine", "Clémence", "Victorine", "Aimée", "Blanche",
             "Émilie", "Thérèse", "Denise", "Anne"]

METIERS_ANCIEN = ["laboureur", "vigneron", "meunier", "tisserand", "tonnelier",
                  "sabotier", "journalier", "closier", "charron"]
METIERS_19 = ["charpentier", "forgeron", "maréchal-ferrant", "aubergiste",
              "boulanger", "tailleur d'habits", "couturière", "clerc de notaire"]
METIERS_20 = ["employé des postes", "comptable", "mécanicien", "institutrice",
              "cheminot", "infirmière", "secrétaire", "ingénieur"]


# ── Pièces « spécimen » (SVG, aucune dépendance) ──────────────────────────
def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _ecrire(dossier, nom, contenu):
    os.makedirs(dossier, exist_ok=True)
    with open(os.path.join(dossier, nom), "w", encoding="utf-8") as f:
        f.write(contenu)


def _acte_svg(titre, meta, lignes, filigrane="SPÉCIMEN", entete=None):
    entete = entete or "RÉPUBLIQUE FRANÇAISE — EXTRAIT (SPÉCIMEN)"
    corps, y = [], 262
    for ln in lignes:
        corps.append('<text x="72" y="%d" font-family="Georgia,serif" '
                     'font-size="20" fill="#3a3226">%s</text>' % (y, _esc(ln)))
        y += 33
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 820 1060">'
        '<rect width="820" height="1060" fill="#ece3cd"/>'
        '<rect x="22" y="22" width="776" height="1016" fill="#f6f0df" '
        'stroke="#c8b788" stroke-width="2"/>'
        '<text x="410" y="86" text-anchor="middle" font-family="Georgia,serif" '
        'font-size="15" letter-spacing="3" fill="#7a6a45">%s</text>'
        '<text x="410" y="150" text-anchor="middle" font-family="Georgia,serif" '
        'font-size="29" font-weight="bold" fill="#2c2517">%s</text>'
        '<text x="410" y="188" text-anchor="middle" font-family="Georgia,serif" '
        'font-size="17" fill="#6b5d3e">%s</text>'
        '<line x1="72" y1="212" x2="748" y2="212" stroke="#c8b788"/>'
        '%s'
        '<text x="410" y="560" text-anchor="middle" font-family="Georgia,serif" '
        'font-size="120" fill="#b8462a" opacity="0.12" '
        'transform="rotate(-18 410 560)">%s</text>'
        '<text x="72" y="1000" font-family="Georgia,serif" font-size="13.5" '
        'fill="#8a7a55" font-style="italic">Document fictif — démonstration '
        'Arboriane. Aucune valeur légale.</text>'
        '</svg>'
    ) % (_esc(entete), _esc(titre), _esc(meta), "".join(corps), _esc(filigrane))


def _portrait_svg(initiales, couleur="#2d5c47"):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">'
        '<rect width="400" height="400" fill="#e7e0cf"/>'
        '<rect x="18" y="18" width="364" height="364" fill="none" '
        'stroke="#c8b788" stroke-width="3"/>'
        '<circle cx="200" cy="158" r="78" fill="%s" opacity="0.85"/>'
        '<path d="M96 372 a104 104 0 0 1 208 0 z" fill="%s" opacity="0.85"/>'
        '<text x="200" y="182" text-anchor="middle" font-family="Georgia,serif" '
        'font-size="66" fill="#fff">%s</text>'
        '<text x="200" y="392" text-anchor="middle" font-family="Georgia,serif" '
        'font-size="15" fill="#8a7a55">SPÉCIMEN</text>'
        '</svg>'
    ) % (couleur, couleur, _esc(initiales))


def generer(chemin_espace):
    """Peuple un espace neuf avec l'arbre de démonstration complet."""
    c = espace_mod.chemins(chemin_espace)
    base = stockage.Base(c["base"], c["sauvegardes"])
    rng = random.Random(31415926)          # reproductible

    sosa = {}          # numéro Sosa -> pid (lignée directe de Lucie)
    infos = {}         # pid -> (prenoms, nom, sexe, an_naiss)

    # ── petites fabriques ─────────────────────────────────────────────────
    def _date_exacte(annee):
        return "%d %s %d" % (rng.randint(1, 28), rng.choice(MOIS), annee)

    def creer(prenoms, nom, sexe, an_naiss, lieu, prof="", an_deces=None,
              lieu_deces="", vivant=False, naiss_approx=False, deces_approx=False,
              sans_jour=False, **extra):
        if naiss_approx:
            dn = "ABT %d" % an_naiss
        elif sans_jour:
            dn = "%d" % an_naiss
        else:
            dn = _date_exacte(an_naiss)
        champs = {"prenoms": prenoms, "nom": nom, "sexe": sexe,
                  "naissance": {"date": dn, "lieu": lieu}}
        if an_deces:
            dd = ("ABT %d" % an_deces) if deces_approx else _date_exacte(an_deces)
            champs["deces"] = {"date": dd, "lieu": lieu_deces or lieu}
        else:
            champs["deces"] = {"date": "", "lieu": ""}
            if vivant:
                champs["vivant"] = True
        if prof:
            champs["professions"] = [{"valeur": prof}]
        champs.update(extra)
        pid = base.creer_individu(champs)["id"]
        infos[pid] = (prenoms, nom, sexe, an_naiss)
        return pid

    def enfant(pid, pere, mere):
        base.definir_parents(pid, pere, mere)

    def marier(a, b, annee, lieu):
        base.ajouter_conjoint(a, b, {"date": "%d" % annee, "lieu": lieu})

    def naiss_lieu(pid):
        return base.donnees["individus"][pid]["naissance"]["lieu"]

    def metier_epoque(gen, sexe):
        if sexe == "F" and gen >= 4:
            return rng.choice(["couturière", "lingère", "sans profession", "servante"])
        if gen >= 8:
            return rng.choice(METIERS_ANCIEN)
        if gen >= 4:
            return rng.choice(METIERS_19)
        return rng.choice(METIERS_20)

    # ── Sosa 1 : Lucie MARTIN, née en 2006 (vivante, étudiante) ───────────
    lucie = creer("Lucie", "MARTIN", "F", 2006, TOURS, prof="étudiante",
                  vivant=True, prenom_principal="Lucie",
                  evenements=[{"type": "EDUC", "date": "2024", "lieu": TOURS,
                               "valeur": "Baccalauréat, lycée Descartes"}])
    sosa[1] = lucie
    tom = creer("Tom", "MARTIN", "M", 2009, TOURS, vivant=True)   # frère de Lucie

    # ── Lignée paternelle MARTIN : lignée directe jusqu'à la génération 12 ─
    # (prénom du père, nom, lieu, métier, année, décès|None, vivant)
    spine = {
        1:  ("Nicolas", "MARTIN", TOURS, "ingénieur", 1979, None, True),
        2:  ("Michel", "MARTIN", ANGERS, "comptable", 1952, None, True),
        3:  ("Raymond", "MARTIN", TOURS, "employé des postes", 1925, 1999, False),
        4:  ("Gaston", "MARTIN", TOURS, "cheminot", 1898, 1971, False),
        5:  ("Auguste", "MARTIN", AMBOISE, "charpentier", 1871, 1946, False),
        6:  ("Prosper", "MARTIN", AMBOISE, "tonnelier", 1844, 1913, False),
        7:  ("Mathurin", "MARTIN", AMBOISE, "tisserand", 1817, 1889, False),
        8:  ("Étienne", "MARTIN", CHINON, "vigneron", 1790, 1861, False),
        9:  ("Louis", "MARTIN", CRAVANT, "laboureur", 1762, 1829, False),
        10: ("Pierre", "MARTIN", CRAVANT, "vigneron", 1734, 1801, False),
        11: ("Jean", "MARTIN", CHINON, "laboureur", 1706, 1771, False),
        12: ("Mathurin", "MARTIN", CHINON, "closier", 1678, 1742, False),
    }
    # mères (épouses de la lignée directe). Génération 3 = branche anglaise
    # (Edith WHITAKER, Sosa 9). (prénom, nom, lieu, année, décès|None, vivante)
    meres = {
        1:  ("Claire", "FONTAINE", NANTES, 1981, None, True),
        2:  ("Martine", "LEROY", ANGERS, 1954, None, True),
        3:  ("Edith", "WHITAKER", LONDRES, 1927, 2009, False),   # anglaise
        4:  ("Germaine", "DUBOIS", TOURS, 1901, 1984, False),
        5:  ("Léontine", "BERNARD", AMBOISE, 1874, 1951, False),
        6:  ("Célestine", "MOREAU", AMBOISE, 1847, 1922, False),
        7:  ("Victorine", "GIRARD", AMBOISE, 1820, 1893, False),
        8:  ("Marguerite", "ROUSSEAU", CHINON, 1793, 1864, False),
        9:  ("Anne", "CHEVALIER", CRAVANT, 1765, 1836, False),
        10: ("Jeanne", "RENARD", CRAVANT, 1737, 1799, False),
        11: ("Marie", "MASSON", CHINON, 1709, 1774, False),
        12: ("Perrine", "BRUNET", CHINON, 1681, 1749, False),
    }

    for gen in range(1, 13):
        prenom, nom, lieu, prof, an_p, dec_p, viv_p = spine[gen]
        pm, nm, lm, an_m, dec_m, viv_m = meres[gen]
        pere = creer(prenom, nom, "M", an_p, lieu, prof, an_deces=dec_p,
                     vivant=viv_p, naiss_approx=(gen >= 7), deces_approx=(gen >= 7))
        mere = creer(pm, nm, "F", an_m, lm, "" if gen <= 3 else metier_epoque(gen, "F"),
                     an_deces=dec_m, vivant=viv_m,
                     naiss_approx=(gen >= 7), deces_approx=(gen >= 7), nom_marital=nom)
        sosa[2 ** gen] = pere
        sosa[2 ** gen + 1] = mere
        marier(pere, mere, an_p + rng.randint(23, 28), lieu)
        enfant(sosa[2 ** (gen - 1)], pere, mere)   # relie l'enfant de la lignée

    enfant(tom, sosa[2], sosa[3])                  # Tom, frère de Lucie

    # ── Fratries : frères et sœurs d'ancêtres (Sosa N -> enfants de 2N/2N+1) ─
    def fratrie(N, defs):
        pere, mere = sosa[2 * N], sosa[2 * N + 1]
        nom_pere = infos[sosa[N]][1]
        lieu = naiss_lieu(pere)
        cree = []
        for pr, sx, opts in defs:
            kw = dict(opts)
            fid = creer(pr, kw.pop("nom", nom_pere), sx, kw.pop("an"),
                        kw.pop("lieu", lieu), kw.pop("prof", ""), **kw)
            enfant(fid, pere, mere)
            cree.append(fid)
        return cree

    fratrie(2, [("Sophie", "F", {"an": 1977, "vivant": True, "nom_marital": "DUPUIS"})])
    freres_michel = fratrie(4, [("Bernard", "M", {"an": 1949, "vivant": True}),
                                ("Colette", "F", {"an": 1957, "vivant": True,
                                                  "nom_marital": "FAURE"})])
    grand_oncle = freres_michel[0]
    freres_raymond = fratrie(8, [
        ("Yvonne", "F", {"an": 1922, "an_deces": 1998, "nom_marital": "LEMOINE"}),
        ("Robert", "M", {"an": 1930, "an_deces": 1943,
                         "note": "Décédé à 13 ans (fièvre typhoïde, 1943)."})])
    grande_tante = freres_raymond[0]
    fratrie(16, [
        ("Émile", "M", {"an": 1896, "an_deces": 1916,
                        "note": "Mort pour la France, Verdun, 1916.",
                        "evenements": [{"type": "_MILT", "date": "1915",
                                        "lieu": "Verdun, Meuse",
                                        "valeur": "127ᵉ régiment d'infanterie"}]}),
        ("Berthe", "F", {"an": 1903, "an_deces": 1989, "nom_marital": "DENIS"})])
    fratrie(32, [("Rose", "F", {"an": 1869, "an_deces": 1948, "nom_marital": "PETIT"})])
    fratrie(64, [("Jean", "M", {"an": 1841, "an_deces": 1901}),
                 ("Louise", "F", {"an": 1849, "an_deces": 1920})])

    # Fratries « en volume » (auto) sur les générations profondes : donne du
    # relief aux statistiques et à la fratrie. Quelques décès inconnus (« sans
    # décès connu ») et quelques enfants morts en bas âge.
    AUTO = {8: 2, 16: 3, 32: 3, 64: 3, 128: 3, 256: 3, 512: 3, 1024: 2, 2048: 2}
    for N, nb in AUTO.items():
        pere, mere = sosa[2 * N], sosa[2 * N + 1]
        gen = N.bit_length() - 1
        nom_pere = infos[sosa[N]][1]
        lieu = naiss_lieu(pere)
        an_ref = infos[sosa[N]][3]
        for _ in range(nb):
            sx = rng.choice(["M", "F"])
            pr = rng.choice(PRENOMS_M if sx == "M" else PRENOMS_F)
            an = an_ref + rng.choice([-9, -7, -5, 4, 6, 8, 10])
            dec = None
            if an < 1930:
                if rng.random() < 0.15:               # mort en bas âge
                    dec = an + rng.randint(0, 4)
                elif rng.random() < 0.80:              # sinon décès plausible
                    dec = an + rng.randint(55, 84)
                # ~ le reste : décès inconnu
            kw = {"an_deces": dec, "naiss_approx": gen >= 7, "deces_approx": gen >= 7}
            if sx == "F" and rng.random() < 0.5:
                kw["nom_marital"] = rng.choice(["PETIT", "DENIS", "MOREAU", "GIRARD"])
            fid = creer(pr, nom_pere, sx, an, lieu, metier_epoque(gen, sx), **kw)
            enfant(fid, pere, mere)

    # ── Ascendance maternelle récente (côtés FONTAINE / LEROY) ────────────
    claire = sosa[3]
    gp_f = creer("Gérard", "FONTAINE", "M", 1948, NANTES, prof="mécanicien", vivant=True)
    gm_f = creer("Monique", "GAUTHIER", "F", 1950, NANTES, prof="secrétaire",
                 vivant=True, nom_marital="FONTAINE")
    sosa[6], sosa[7] = gp_f, gm_f
    enfant(claire, gp_f, gm_f)
    marier(gp_f, gm_f, 1974, NANTES)
    tante_m = creer("Valérie", "FONTAINE", "F", 1983, NANTES, vivant=True,
                    nom_marital="MARCHAND")
    enfant(tante_m, gp_f, gm_f)
    # parents de Gérard (Sosa 12/13) et de Monique (Sosa 14/15)
    for pere_pr, pere_nom, mere_pr, mere_nom, base_an, sN in [
            ("Fernand", "FONTAINE", "Odette", "LEMAIRE", 1920, 6),
            ("Marcel", "GAUTHIER", "Simone", "DUFOUR", 1923, 7)]:
        p = creer(pere_pr, pere_nom, "M", base_an, NANTES, metier_epoque(3, "M"),
                  an_deces=base_an + rng.randint(60, 82))
        mm = creer(mere_pr, mere_nom, "F", base_an + 3, NANTES, "",
                   an_deces=base_an + rng.randint(62, 85), nom_marital=pere_nom)
        sosa[2 * sN], sosa[2 * sN + 1] = p, mm
        enfant(sosa[sN], p, mm)
        marier(p, mm, base_an + 25, NANTES)
    # parents de Martine LEROY (Sosa 10/11)
    ggp_l = creer("Roland", "LEROY", "M", 1928, ANGERS, prof="boulanger", an_deces=2012)
    ggm_l = creer("Paulette", "MEUNIER", "F", 1931, ANGERS, an_deces=2019,
                  nom_marital="LEROY")
    sosa[10], sosa[11] = ggp_l, ggm_l
    enfant(sosa[5], ggp_l, ggm_l)
    marier(ggp_l, ggm_l, 1952, ANGERS)

    # ── Branche collatérale : descendance du grand-oncle Bernard (cousins) ─
    tante_b = creer("Danielle", "LEMAIRE", "F", 1951, ANGERS, vivant=True,
                    nom_marital="MARTIN")
    marier(grand_oncle, tante_b, 1974, ANGERS)
    cousin_j = creer("Julien", "MARTIN", "M", 1976, ANGERS, prof="professeur", vivant=True)
    cousin_s = creer("Sandra", "MARTIN", "F", 1980, ANGERS, prof="infirmière",
                     vivant=True, nom_marital="VASSEUR")
    enfant(cousin_j, grand_oncle, tante_b)
    enfant(cousin_s, grand_oncle, tante_b)
    conj_j = creer("Nadia", "DUFOUR", "F", 1978, TOURS, vivant=True, nom_marital="MARTIN")
    marier(cousin_j, conj_j, 2003, TOURS)
    for pr, sx, an in [("Léa", "F", 2005), ("Hugo", "M", 2008)]:
        enfant(creer(pr, "MARTIN", sx, an, TOURS, vivant=True), cousin_j, conj_j)
    conj_s = creer("Marc", "VASSEUR", "M", 1977, TOURS, prof="kinésithérapeute", vivant=True)
    marier(cousin_s, conj_s, 2006, TOURS)
    enfant(creer("Chloé", "VASSEUR", "F", 2010, TOURS, vivant=True), conj_s, cousin_s)

    # ── 2ᵉ collatérale : descendance de la grande-tante Yvonne (remariage) ─
    ep1_y = creer("Marcel", "LEMOINE", "M", 1919, TOURS, prof="typographe",
                  an_deces=1949)
    marier(grande_tante, ep1_y, 1946, TOURS)
    fils_y = creer("Alain", "LEMOINE", "M", 1947, TOURS, prof="électricien", an_deces=2018)
    enfant(fils_y, ep1_y, grande_tante)
    # Yvonne, veuve, se remarie (cas de remariage)
    ep2_y = creer("Fernand", "GUILLOU", "M", 1916, TOURS, prof="menuisier", an_deces=1994)
    marier(grande_tante, ep2_y, 1953, TOURS)
    enfant(creer("Nicole", "GUILLOU", "F", 1954, TOURS, an_deces=2020,
                 nom_marital="ROY"), ep2_y, grande_tante)

    # ── Branche anglaise : ascendance d'Edith WHITAKER (Sosa 9) ───────────
    # Migration : Edith, née à Londres en 1927, épouse Raymond MARTIN (Sosa 8)
    # en 1949 et s'installe à Tours. Ses ancêtres restent en Angleterre ; dates
    # souvent approximatives, un décès inconnu (piste ouverte).
    edith = sosa[9]
    thomas_w = creer("Thomas", "WHITAKER", "M", 1898, LONDRES, prof="marchand",
                     an_deces=1969,
                     evenements=[{"type": "IMMI", "date": "1949", "lieu": TOURS,
                                  "valeur": "Visite de sa fille installée en France"}])
    florence_a = creer("Florence", "ASHWORTH", "F", 1901, PORTSMOUTH, an_deces=1977,
                       nom_marital="WHITAKER")
    sosa[18], sosa[19] = thomas_w, florence_a
    enfant(edith, thomas_w, florence_a)
    marier(thomas_w, florence_a, 1924, LONDRES)
    for pr, sx, an, opt in [("William", "M", 1925, {"an_deces": 1990, "prof": "clerk"}),
                            ("Alice", "F", 1930, {"an_deces": 2011, "nom_marital": "CLAYTON"})]:
        enfant(creer(pr, "WHITAKER", sx, an, LONDRES, **opt), thomas_w, florence_a)
    # grands-parents anglais (Sosa 36/37 côté WHITAKER, 38/39 côté ASHWORTH)
    geo_w = creer("George", "WHITAKER", "M", 1868, LONDRES, prof="charpentier de marine",
                  naiss_approx=True, an_deces=1935, deces_approx=True)
    harriet_p = creer("Harriet", "PRESCOTT", "F", 1872, BRISTOL, naiss_approx=True,
                      an_deces=1939, deces_approx=True, nom_marital="WHITAKER")
    sosa[36], sosa[37] = geo_w, harriet_p
    enfant(thomas_w, geo_w, harriet_p)
    marier(geo_w, harriet_p, 1895, LONDRES)
    edw_a = creer("Edward", "ASHWORTH", "M", 1870, PORTSMOUTH, prof="tisserand",
                  naiss_approx=True, an_deces=1938, deces_approx=True)
    ada_h = creer("Ada", "HARGROVE", "F", 1874, PORTSMOUTH, naiss_approx=True,
                  an_deces=1941, deces_approx=True, nom_marital="ASHWORTH")
    sosa[38], sosa[39] = edw_a, ada_h
    enfant(florence_a, edw_a, ada_h)
    marier(edw_a, ada_h, 1899, PORTSMOUTH)
    # arrière-grands-parents anglais (Sosa 72/73) — décès inconnu (trou volontaire)
    art_w = creer("Arthur", "WHITAKER", "M", 1840, LONDRES, prof="tisserand",
                  naiss_approx=True)                 # décès inconnu
    mar_c = creer("Mary", "CLAYTON", "F", 1844, LONDRES, naiss_approx=True,
                  an_deces=1901, deces_approx=True, nom_marital="WHITAKER")
    sosa[72], sosa[73] = art_w, mar_c
    enfant(geo_w, art_w, mar_c)

    # ── Famille « CAS DE TEST » : incohérences VOLONTAIRES (écran Cohérence) ─
    # Isolée (non reliée à Lucie) et clairement étiquetée.
    ct = "⚠ CAS DE TEST — incohérence volontaire pour valider l'écran Cohérence."
    ct_pere = creer("Anatole", "TESTUS", "M", 1850, LOCHES, prof="notaire",
                    an_deces=1858, sans_jour=True,
                    note=ct + " Décès (1858) situé avant la naissance de son fils (1861).")
    ct_mere = creer("Philomène", "TESTUS", "F", 1855, LOCHES, sans_jour=True,
                    nom_marital="TESTUS",
                    note=ct + " Mariée à 9 ans (1864) : âge au mariage invraisemblable.")
    marier(ct_pere, ct_mere, 1864, LOCHES)
    ct_fils = creer("Célestin", "TESTUS", "M", 1861, LOCHES, sans_jour=True,
                    an_deces=1848, deces_approx=True,
                    note=ct + " Décès (1848) antérieur à la naissance (1861).")
    enfant(ct_fils, ct_pere, ct_mere)

    # ══════════════════════════════════════════════════════════════════════
    #  SOURCES, ACTES, TRANSCRIPTIONS, CITATIONS
    # ══════════════════════════════════════════════════════════════════════
    def scan(nom, svg):
        _ecrire(c["sources"], nom, svg)
        return nom

    # 1) Acte de naissance de Lucie (fiable, quay 3 = acte)
    f1 = scan("2006_NAISSANCE_Lucie_Martin_Tours.svg", _acte_svg(
        "Acte de naissance", "Tours (Indre-et-Loire) — 2006", [
            "L'an deux mille six, est née à Tours",
            "Lucie MARTIN, de sexe féminin,",
            "fille de Nicolas MARTIN, ingénieur,",
            "et de Claire FONTAINE, son épouse.",
        ]))
    s1 = base.creer_source({
        "titre": "Acte de naissance de Lucie MARTIN", "type": "Acte de naissance",
        "date": "2006", "lieu": TOURS, "depot": "Mairie de Tours — état civil",
        "cote": "Naissances 2006, acte n° 812", "page": "acte 812",
        "fiabilite": "haute", "statut": "RETENU", "fichiers": [f1],
        "transcription": "L'an deux mille six est née à Tours Lucie MARTIN, fille "
                         "de Nicolas MARTIN, ingénieur, et de Claire FONTAINE.",
    })["id"]
    base.taguer_personne_source(s1, lucie, "sujet")
    base.taguer_personne_source(s1, sosa[2], "père")
    base.taguer_personne_source(s1, sosa[3], "mère")
    base.citer(lucie, "naissance", {"source": s1, "page": "acte 812", "quay": 3, "role": "sujet"})

    # 2) Registre paroissial — baptême d'Étienne MARTIN (Sosa 256), 1790, quay 3
    f2 = scan("1790_BAPTEME_Etienne_Martin_Chinon.svg", _acte_svg(
        "Registre paroissial — baptême", "Paroisse Saint-Maurice de Chinon — 1790", [
            "Le douze may mil sept cent quatre-vingt-dix a esté",
            "baptisé Estienne MARTIN, fils de Louis MARTIN,",
            "laboureur, et d'Anne CHEVALIER sa femme.",
            "Parrain : Pierre MARTIN ; marraine : Jeanne RENARD.",
        ], entete="REGISTRE PAROISSIAL (SPÉCIMEN)"))
    s2 = base.creer_source({
        "titre": "Baptême d'Étienne MARTIN (registre paroissial)",
        "type": "Registre paroissial", "date": "12 MAY 1790", "lieu": CHINON,
        "depot": "Archives départementales d'Indre-et-Loire", "cote": "6 NUM 8/72",
        "page": "vue 41/210", "fiabilite": "haute", "statut": "RETENU", "fichiers": [f2],
        "transcription": "Le douze may 1790 a esté baptisé Estienne MARTIN, fils de "
                         "Louis MARTIN, laboureur, et d'Anne CHEVALIER.",
    })["id"]
    base.taguer_personne_source(s2, sosa[256], "baptisé")
    base.taguer_personne_source(s2, sosa[512], "père")
    base.taguer_personne_source(s2, sosa[513], "mère")
    base.citer(sosa[256], "naissance", {"source": s2, "page": "vue 41", "quay": 3, "role": "sujet"})

    # 3) Recensement 1901 Amboise (ménage d'Auguste, Sosa 32) — moyenne, quay 2
    f3 = scan("1901_RECENSEMENT_Martin_Amboise.svg", _acte_svg(
        "Liste nominative de recensement", "Amboise (Indre-et-Loire) — 1901", [
            "Ménage MARTIN, rue Nationale.",
            "MARTIN Auguste, chef de ménage, charpentier, 30 ans.",
            "BERNARD Léontine, épouse, 27 ans.",
            "MARTIN Gaston, fils, 3 ans.",
        ]))
    s3 = base.creer_source({
        "titre": "Recensement de 1901 — ménage MARTIN (Amboise)",
        "type": "Recensement", "date": "1901", "lieu": AMBOISE,
        "depot": "Archives départementales d'Indre-et-Loire", "cote": "6 M 112",
        "page": "district 3, page 14", "fiabilite": "moyenne", "statut": "RETENU",
        "fichiers": [f3],
        "transcription": "Ménage MARTIN recensé à Amboise en 1901 : Auguste "
                         "(charpentier), Léontine (épouse), Gaston (fils, 3 ans).",
    })["id"]
    base.taguer_personne_source(s3, sosa[32], "chef de ménage")
    base.taguer_personne_source(s3, sosa[33], "épouse")
    base.taguer_personne_source(s3, sosa[16], "fils")
    base.citer(sosa[16], "naissance", {"source": s3, "page": "p. 14", "quay": 2, "role": "sujet"})

    # 4) Acte de mariage MARTIN × WHITAKER (franco-anglais) — haute, quay 3
    f4 = scan("1949_MARIAGE_Raymond_Martin_Edith_Whitaker_Tours.svg", _acte_svg(
        "Acte de mariage", "Tours (Indre-et-Loire) — 1949", [
            "L'an mil neuf cent quarante-neuf ont comparu",
            "Raymond MARTIN, employé des postes, de Tours,",
            "et Edith WHITAKER, née à Londres (Angleterre),",
            "lesquels ont déclaré se prendre pour époux.",
        ]))
    s4 = base.creer_source({
        "titre": "Acte de mariage MARTIN × WHITAKER", "type": "Acte de mariage",
        "date": "1949", "lieu": TOURS, "depot": "Mairie de Tours",
        "cote": "Mariages 1949, acte n° 63", "page": "acte 63", "fiabilite": "haute",
        "statut": "RETENU", "fichiers": [f4],
        "transcription": "Mariage de Raymond MARTIN et d'Edith WHITAKER, née à "
                         "Londres, célébré à Tours en 1949.",
    })["id"]
    base.taguer_personne_source(s4, sosa[8], "époux")
    base.taguer_personne_source(s4, edith, "épouse")

    # 5) Fiche matricule militaire — Émile MARTIN (mort pour la France) — quay 2
    f5 = scan("1915_MATRICULE_Emile_Martin_Verdun.svg", _acte_svg(
        "Fiche matricule", "Bureau de recrutement de Tours — classe 1916", [
            "MARTIN Émile, né en 1896 à Amboise.",
            "Incorporé au 127ᵉ régiment d'infanterie.",
            "Mort pour la France le 21 février 1916,",
            "secteur de Verdun (Meuse).",
        ], entete="MINISTÈRE DE LA GUERRE (SPÉCIMEN)"))
    s5 = base.creer_source({
        "titre": "Fiche matricule d'Émile MARTIN",
        "type": "Registre matricule militaire", "date": "1915", "lieu": TOURS,
        "depot": "Archives départementales d'Indre-et-Loire",
        "cote": "1 R 998, matricule 1427", "fiabilite": "moyenne", "statut": "RETENU",
        "fichiers": [f5],
        "transcription": "MARTIN Émile, classe 1916, 127ᵉ RI, mort pour la France "
                         "à Verdun le 21 février 1916.",
    })["id"]
    emile = next((p for p, (pn, nn, sx, a) in infos.items()
                  if pn == "Émile" and nn == "MARTIN"), None)
    if emile:
        base.taguer_personne_source(s5, emile, "sujet")
        base.citer(emile, "deces", {"source": s5, "page": "matricule 1427", "quay": 2, "role": "sujet"})

    # 6) Acte notarié — contrat de mariage MARTIN × RENARD (Sosa 1024/1025) — quay 2
    s6 = base.creer_source({
        "titre": "Contrat de mariage MARTIN × RENARD (Me Dupleix, notaire)",
        "type": "Acte notarié", "date": "1756", "lieu": CRAVANT,
        "depot": "Archives départementales d'Indre-et-Loire", "cote": "3 E 44/318",
        "page": "minute du 4 février 1756", "fiabilite": "moyenne", "statut": "RETENU",
        "transcription": "Contrat de mariage entre Pierre MARTIN, vigneron, et "
                         "Jeanne RENARD, passé devant Me Dupleix à Cravant en 1756.",
    })["id"]
    base.taguer_personne_source(s6, sosa[1024], "époux")
    base.taguer_personne_source(s6, sosa[1025], "épouse")

    # 7) Acte anglais — naissance d'Edith (GRO Londres) — moyenne, quay 2
    f7 = scan("1927_BIRTH_Edith_Whitaker_London.svg", _acte_svg(
        "Certified copy of an entry of birth", "General Register Office — London, 1927", [
            "When and where born: 3rd March 1927, Islington, London.",
            "Name: Edith WHITAKER.",
            "Father: Thomas WHITAKER, merchant.",
            "Mother: Florence WHITAKER, formerly ASHWORTH.",
        ], filigrane="SPECIMEN", entete="GENERAL REGISTER OFFICE (SPECIMEN)"))
    s7 = base.creer_source({
        "titre": "Birth certificate of Edith WHITAKER (London)",
        "type": "Acte de naissance (anglais)", "date": "3 MAR 1927", "lieu": LONDRES,
        "depot": "General Register Office (GRO), England",
        "cote": "Islington, vol. 1b, p. 421", "fiabilite": "moyenne",
        "statut": "RETENU", "fichiers": [f7],
        "transcription": "Edith WHITAKER, born 3 March 1927 at Islington, London, "
                         "daughter of Thomas WHITAKER (merchant) and Florence ASHWORTH.",
    })["id"]
    base.taguer_personne_source(s7, edith, "sujet")
    base.taguer_personne_source(s7, thomas_w, "father")
    base.taguer_personne_source(s7, florence_a, "mother")
    base.citer(edith, "naissance", {"source": s7, "page": "vol. 1b p.421", "quay": 2, "role": "sujet"})

    # 8) Lettre familiale (source faible, quay 1 = estimé)
    s8 = base.creer_source({
        "titre": "Lettre d'Edith à sa mère (Tours → Portsmouth, 1950)",
        "type": "Lettre familiale", "date": "1950", "lieu": TOURS,
        "depot": "Archives familiales (privé)", "fiabilite": "faible", "statut": "RETENU",
        "transcription": "« Ma chère mère, la vie à Tours est douce… » — la lettre "
                         "mentionne la santé déclinante de la grand-mère Léontine.",
    })["id"]
    base.taguer_personne_source(s8, edith, "auteur")
    base.citer(sosa[33], "deces", {"source": s8, "page": "", "quay": 1, "role": "mention"})

    # 9) Faire-part de décès (source moyenne, quay 2)
    s9 = base.creer_source({
        "titre": "Faire-part de décès de Gaston MARTIN (1971)", "type": "Faire-part",
        "date": "1971", "lieu": TOURS, "depot": "Archives familiales (privé)",
        "fiabilite": "moyenne", "statut": "RETENU",
        "transcription": "« Vous êtes priés d'assister aux obsèques de M. Gaston "
                         "MARTIN, ancien cheminot, décédé à Tours le… »",
    })["id"]
    base.taguer_personne_source(s9, sosa[16], "défunt")
    base.citer(sosa[16], "deces", {"source": s9, "page": "", "quay": 2, "role": "sujet"})

    # 10) Photographie annotée (source faible + piste)
    f10 = scan("1929_PHOTO_annotee_Famille_Martin_Amboise.svg", _acte_svg(
        "Photographie annotée", "Amboise — dos de tirage, vers 1929", [
            "Au dos, à l'encre : « Auguste, Léontine et les enfants,",
            "devant l'atelier, Amboise 1929. »",
            "Trois personnes non identifiées à l'arrière-plan.",
        ], entete="PIÈCE FAMILIALE (SPÉCIMEN)"))
    s10 = base.creer_source({
        "titre": "Photographie annotée « Famille MARTIN, Amboise 1929 »",
        "type": "Photographie annotée", "date": "ABT 1929", "lieu": AMBOISE,
        "depot": "Archives familiales (privé)", "fiabilite": "faible", "statut": "PISTE",
        "fichiers": [f10],
        "transcription": "Annotation manuscrite au dos : « Auguste, Léontine et les "
                         "enfants, Amboise 1929 ».",
    })["id"]
    base.taguer_personne_source(s10, sosa[32], "identifié")
    base.taguer_personne_source(s10, sosa[33], "identifiée")

    # 11) Source ORPHELINE / incomplète (ni dépôt, ni cote, ni personne) — Santé
    base.creer_source({
        "titre": "Relevé collaboratif en ligne (à vérifier)",
        "type": "Relevé collaboratif", "date": "", "lieu": "",
        "ark": "https://www.exemple-releves.fictif/", "fiabilite": "faible",
        "statut": "PISTE",
        "note": "Source non rattachée : ni dépôt, ni cote, ni personne. "
                "Cas de test pour l'écran Santé.",
    })

    # 12) Citation NON qualifiée (quay 0) sur une naissance, sans source — « estimé »
    base.citer(sosa[6], "naissance", {"source": None, "page": "", "quay": 0, "role": "sujet"})

    # ══════════════════════════════════════════════════════════════════════
    #  PORTRAITS (médias) — noms de fichiers explicites
    # ══════════════════════════════════════════════════════════════════════
    portraits = [
        (lucie, "P001_Lucie_Martin_portrait.svg", "LM", "#1f4636"),
        (sosa[2], "P002_Nicolas_Martin_portrait.svg", "NM", "#2d5c47"),
        (sosa[3], "P003_Claire_Fontaine_portrait.svg", "CF", "#6a4a7a"),
        (sosa[8], "P008_Raymond_Martin_portrait.svg", "RM", "#7a5a2a"),
        (edith, "P009_Edith_Whitaker_portrait.svg", "EW", "#3a5a7a"),
        (sosa[16], "P016_Gaston_Martin_portrait.svg", "GM", "#5a3a2a"),
        (thomas_w, "P018_Thomas_Whitaker_portrait.svg", "TW", "#4a4a4a"),
        (sosa[256], "P256_Etienne_Martin_portrait.svg", "EM", "#3a5a3a"),
        (grand_oncle, "PC_Bernard_Martin_portrait.svg", "BM", "#2d5c47"),
    ]
    for pid, fichier, ini, coul in portraits:
        _ecrire(c["photos"], fichier, _portrait_svg(ini, coul))
        base.definir_medias(pid, [{"fichier": fichier, "titre": "Portrait (spécimen)",
                                   "principale": True}])

    # ══════════════════════════════════════════════════════════════════════
    #  PISTES DE RECHERCHE (Plan de recherche) — non prouvées
    # ══════════════════════════════════════════════════════════════════════
    base.modifier_individu(art_w, {"pistes": [
        {"texte": "Retrouver l'acte de décès d'Arthur WHITAKER (après 1901 ?) au "
                  "GRO de Londres.", "faite": False}]})
    base.modifier_individu(sosa[16], {"pistes": [
        {"texte": "Vérifier la date exacte de naissance d'Émile (matricule vs "
                  "état civil d'Amboise).", "faite": False}]})
    base.modifier_individu(sosa[64], {"pistes": [
        {"texte": "Chercher le contrat de mariage MARTIN × MOREAU (notaire "
                  "d'Amboise, vers 1866).", "faite": False}]})

    # ══════════════════════════════════════════════════════════════════════
    #  CARNET DE BORD (quelques entrées)
    # ══════════════════════════════════════════════════════════════════════
    try:
        from services import carnet as carnet_svc
        carnet_svc.ajouter(chemin_espace, {
            "type": "trouvaille", "titre": "Baptême d'Étienne MARTIN (1790) retrouvé",
            "texte": "Registre paroissial de Chinon, vue 41/210 (6 NUM 8/72). "
                     "Confirme les parents Louis MARTIN et Anne CHEVALIER.",
            "personne": sosa[256]})
        carnet_svc.ajouter(chemin_espace, {
            "type": "piste", "titre": "Branche anglaise WHITAKER",
            "texte": "Edith WHITAKER (Sosa 9) est née à Londres en 1927. Explorer "
                     "le GRO pour remonter au-delà de 1840.",
            "personne": edith})
    except Exception:  # noqa: BLE001
        pass

    # ══════════════════════════════════════════════════════════════════════
    #  DÉPÔTS (entités), COORDONNÉES, RÉFÉRENTIEL, FAVORIS & ENSEMBLES
    #  Met en valeur les fonctions récentes — 100 % local, aucun réseau.
    # ══════════════════════════════════════════════════════════════════════
    from services import depots as depots_svc
    from services import lieux as lieux_svc
    from services import lieux_ref as lieuxref_svc
    from services import favoris as favoris_svc

    # Dépôts : promeut les noms libres portés par les sources en ENTITÉS
    # réutilisables (Mairie de Tours, AD d'Indre-et-Loire, GRO…). → écran Dépôts.
    depots_svc.promouvoir(base.donnees)

    # Coordonnées connues (pré-géocodage) : la carte des lieux s'affiche
    # immédiatement, sans requête réseau.
    COORDS = {
        TOURS: (47.3941, 0.6848), AMBOISE: (47.4132, 0.9821),
        CHINON: (47.1670, 0.2416), CRAVANT: (47.1870, 0.3330),
        LOCHES: (47.1281, 1.0058), ANGERS: (47.4784, -0.5632),
        NANTES: (47.2184, -1.5536), LONDRES: (51.5074, -0.1278),
        PORTSMOUTH: (50.7989, -1.0912), BRISTOL: (51.4545, -2.5879),
    }
    for _nom, (_lat, _lon) in COORDS.items():
        lieux_svc.memoriser_coords(base.donnees, _nom, _lat, _lon)

    # Référentiel des lieux : construit la hiérarchie commune → département →
    # pays à partir des événements. → écran Référentiel des lieux (L15).
    lieuxref_svc.construire_depuis_evenements(base.donnees)

    base.sauvegarder()

    # Favoris (⭐) + ensembles de travail (L13).
    favoris_svc.basculer(base, lucie)
    favoris_svc.basculer(base, edith)
    if emile:
        favoris_svc.basculer(base, emile)
    favoris_svc.creer_ensemble(base, "Branche anglaise",
                               [edith, thomas_w, florence_a, geo_w, harriet_p, edw_a, ada_h])

    # ══════════════════════════════════════════════════════════════════════
    #  Manifeste : racine = Lucie
    # ══════════════════════════════════════════════════════════════════════
    m = espace_mod.charger(chemin_espace)
    m["racine_id"] = lucie
    m["demo_version"] = VERSION
    espace_mod.sauver_manifeste(chemin_espace, m)
    return base


# Résumé de l'histoire familiale fictive (affiché dans l'aide / le README).
HISTOIRE = """\
Famille MARTIN — une lignée du Val de Loire (démonstration fictive)

• Lignée principale (MARTIN) : on remonte de closiers et laboureurs de Chinon et
  Cravant-les-Côteaux (fin XVIIe s.), vignerons puis tisserands et tonneliers à
  Amboise au XIXe s., avant l'exode rural vers Tours (cheminots, postiers) au
  XXe s., puis Angers et Nantes. Sosa 1 : Lucie MARTIN, née à Tours en 2006.

• Guerres : Émile MARTIN, « mort pour la France » à Verdun en 1916 (fiche
  matricule) ; un enfant, Robert, emporté par la typhoïde à 13 ans en 1943.

• Branche anglaise (WHITAKER, ASHWORTH, PRESCOTT, HARGROVE, CLAYTON) : Edith
  WHITAKER (Sosa 9), née à Londres en 1927 (père marchand, mère de Portsmouth),
  épouse Raymond MARTIN à Tours en 1949 — une migration Londres → Tours. Ses
  ancêtres (charpentiers de marine, tisserands) restent à Londres, Portsmouth et
  Bristol ; dates souvent approximatives, un décès reste inconnu (piste ouverte).

• Branches collatérales : le grand-oncle Bernard MARTIN et la grande-tante
  Yvonne (remariée après veuvage) et leurs descendances (cousins, petits-cousins
  de Lucie) permettent de tester la parenté.

• Cas de test : une famille « TESTUS » isolée porte des incohérences VOLONTAIRES
  et étiquetées (décès avant naissance, mariage à 9 ans) pour l'écran Cohérence ;
  une source orpheline et une citation non qualifiée alimentent la Santé de
  l'arbre ; fiabilités haute / moyenne / faible et citations de niveaux variés
  (acte / déclaré / estimé) couvrent l'écran Sources & preuves.
"""
