# -*- coding: utf-8 -*-
"""
Taxonomie des documents généalogiques : la SOURCE DE VÉRITÉ unique qui alimente
à la fois le sélecteur (Famille → Sous-famille → Type), la nomenclature des
fichiers (le CODE court), et la légende auto-générée.

Principes :
  • 3 niveaux de NAVIGATION (famille / sous-famille / type) — pour choisir.
  • 1 CODE court par type-feuille — pour NOMMER le scan (il se trie, la légende
    en restitue le sens). Les codes sont volontairement STABLES : les changer
    renommerait des fichiers déjà rangés.
  • Les descripteurs (original/copie/extrait/transcription, complétude,
    visibilité) NE sont PAS des types : ce sont des PROPRIÉTÉS de la source
    (choix de Sophie — « nom court »). Une « transcription de naissance » = un
    acte de naissance (code N) avec forme=transcription. Le code peut donc être
    partagé par plusieurs types : c'est voulu.
"""

# Chaque famille : (libellé, code_famille, [ (sous-famille, [ (type, code) ]) ])
FAMILLES = [
 ("État civil et filiation", "EC", [
   ("Naissance et filiation", [
     ("Acte de naissance", "N"),
     ("Transcription de naissance", "N"),
     ("Acte d'enfant sans vie", "SV"),
     ("Acte de reconnaissance", "RECO"),
     ("Jugement d'adoption, légitimation ou filiation", "JFIL"),
   ]),
   ("Union, séparation et décès", [
     ("Acte de mariage", "M"),
     ("Publication ou bans de mariage", "PM"),
     ("Divorce, séparation ou annulation", "DIV"),
     ("Acte de décès", "D"),
     ("Livret de famille", "LF"),
   ]),
   ("Tables et index", [
     ("Index ou table des baptêmes", "IXB"),
     ("Index ou table des naissances", "IXN"),
     ("Index ou table des mariages", "IXM"),
     ("Index ou table des décès", "IXD"),
     ("Table décennale ou annuelle", "TD"),
   ]),
 ]),
 ("Religion et rites", "REL", [
   ("Naissance et initiation religieuse", [
     ("Acte de baptême", "B"),
     ("Présentation ou bénédiction d'enfant", "BENE"),
     ("Circoncision (registre de mohel)", "CIRC"),
     ("Première communion", "COMM"),
     ("Confirmation, bar/bat-mitsva", "CONF"),
   ]),
   ("Union, communauté et décès religieux", [
     ("Acte de mariage religieux", "MR"),
     ("Dossier matrimonial religieux", "DMR"),
     ("Dispense de consanguinité ou d'empêchement", "DISP"),
     ("Sépulture ou inhumation religieuse", "SEP"),
     ("Appartenance à une paroisse ou communauté", "PAR"),
   ]),
 ]),
 ("Population, domicile et identité", "POP", [
   ("Population et résidence", [
     ("Recensement de population", "REC"),
     ("Liste nominative des habitants", "LNH"),
     ("Registre de population", "RPOP"),
     ("Registre de domicile ou de résidence", "DOM"),
     ("Liste électorale", "ELEC"),
   ]),
   ("Identité administrative", [
     ("Carte nationale d'identité", "CNI"),
     ("Passeport", "PASS"),
     ("Fiche individuelle ou familiale d'état civil", "FEC"),
     ("Titre ou carte de séjour", "SEJ"),
     ("Carte de rationnement ou de circulation", "RAT"),
   ]),
 ]),
 ("Notariat, patrimoine et succession", "NOT", [
   ("Couple, famille et héritage", [
     ("Contrat de mariage", "CM"),
     ("Testament", "TEST"),
     ("Dossier de succession", "SUCC"),
     ("Inventaire après décès", "INV"),
     ("Donation entre vifs ou donation-partage", "DON"),
   ]),
   ("Biens et propriété", [
     ("Acte de partage", "PART"),
     ("Acte de vente ou d'acquisition", "VTE"),
     ("Titre de propriété", "PROP"),
     ("Acte hypothécaire", "HYP"),
     ("Cadastre, matrice ou plan parcellaire", "CAD"),
   ]),
 ]),
 ("Vie militaire et conflits", "MIL", [
   ("Recrutement et carrière militaire", [
     ("Conscription ou tableau de recrutement", "CONS"),
     ("Fiche matricule militaire", "MIL"),
     ("État signalétique et des services", "ESS"),
     ("Livret militaire", "LM"),
     ("Ordre de mobilisation ou feuille de route", "MOB"),
   ]),
   ("Guerre, distinctions et victimes", [
     ("Citation militaire", "CIT"),
     ("Médaille, décoration ou brevet", "DEC"),
     ("Dossier de prisonnier de guerre", "PG"),
     ("Pension militaire, blessure ou invalidité", "PENM"),
     ("Mort pour la France ou victime de guerre", "MPF"),
   ]),
 ]),
 ("Migration, nationalité et mobilité", "MIG", [
   ("Déplacements et immigration", [
     ("Liste de passagers", "LPAS"),
     ("Registre d'embarquement ou de débarquement", "EMB"),
     ("Dossier d'immigration ou d'émigration", "IMM"),
     ("Visa ou permis de passage", "VISA"),
     ("Dossier de réfugié, déplacé ou rapatrié", "REF"),
   ]),
   ("Nationalité et statut d'étranger", [
     ("Demande ou déclaration de naturalisation", "NATD"),
     ("Décret de naturalisation ou de réintégration", "NAT"),
     ("Certificat ou déclaration de nationalité", "NATC"),
     ("Admission à domicile", "ADOM"),
     ("Registre, carte ou dossier d'étranger", "ETR"),
   ]),
 ]),
 ("Études, travail et carrière", "TRA", [
   ("École et formation", [
     ("Registre matricule scolaire", "SCOL"),
     ("Dossier scolaire", "DSCO"),
     ("Bulletin ou certificat d'études", "CEP"),
     ("Diplôme", "DIPL"),
     ("Contrat ou livret d'apprentissage", "APPR"),
   ]),
   ("Vie professionnelle", [
     ("Livret ouvrier ou professionnel", "LO"),
     ("Dossier du personnel", "PERS"),
     ("Contrat de travail", "CTR"),
     ("Registre du commerce ou des métiers", "RCS"),
     ("Dossier de retraite ou pension professionnelle", "RETR"),
   ]),
 ]),
 ("Justice, administration et protection sociale", "JUS", [
   ("Justice et police", [
     ("Jugement civil", "JC"),
     ("Jugement pénal, correctionnel ou criminel", "JP"),
     ("Tutelle, curatelle ou conseil de famille", "TUT"),
     ("Faillite, liquidation ou insolvabilité", "FAIL"),
     ("Rapport de police ou de gendarmerie", "POL"),
   ]),
   ("Administration et assistance", [
     ("Registre de prison ou dossier de détenu", "PRIS"),
     ("Registre fiscal ou rôle d'imposition", "FISC"),
     ("Dossier d'aide sociale ou d'assistance", "SOC"),
     ("Enfant abandonné, pupille, orphelinat ou hospice", "PUP"),
     ("Pétition ou correspondance administrative", "ADM"),
   ]),
 ]),
 ("Santé, décès et mémoire funéraire", "SAN", [
   ("Santé et événements médicaux", [
     ("Dossier hospitalier", "HOSP"),
     ("Certificat médical", "CMED"),
     ("Carnet de santé ou de vaccination", "SANT"),
     ("Registre de maternité ou d'établissement de soins", "MAT"),
     ("Accident du travail, invalidité ou handicap", "ATMP"),
   ]),
   ("Décès et sépulture", [
     ("Rapport d'autopsie ou médico-légal", "AUT"),
     ("Permis d'inhumer ou de transport de corps", "INH"),
     ("Registre de cimetière ou d'inhumation", "CIM"),
     ("Acte ou titre de concession funéraire", "CONC"),
     ("Faire-part ou avis de décès", "AVD"),
     ("Article de presse (nécrologie, obsèques)", "NEC"),
     ("Photographie ou relevé de tombe", "TOMB"),
   ]),
 ]),
 ("Archives familiales, iconographie et mémoire", "ARC", [
   ("Photographies et documents personnels", [
     ("Portrait individuel", "PH"),
     ("Photographie de couple, famille ou groupe", "PHG"),
     ("Album photographique", "ALB"),
     ("Carte postale", "CP"),
     ("Lettre ou correspondance familiale", "COR"),
   ]),
   ("Témoignages et mémoire familiale", [
     ("Journal intime ou carnet personnel", "JRN"),
     ("Arbre, livre ou carnet généalogique ancien", "GEN"),
     ("Article de presse", "PR"),
     ("Faire-part de naissance, mariage ou décès", "FP"),
     ("Témoignage oral, audio ou vidéo", "TEM"),
   ]),
 ]),
]

# ── Descripteurs orthogonaux (PROPRIÉTÉS de la source, pas des types) ──
FORMES = ["Original", "Extrait", "Copie", "Transcription", "Photocopie", "Photographie"]
COMPLETUDE = ["Complet", "Incomplet", "Fragment"]
VISIBILITE = ["Public", "Privé", "Sensible"]


def _iter_types():
    for fam, codef, sous in FAMILLES:
        for sf, types in sous:
            for lib, code in types:
                yield fam, codef, sf, lib, code


def code_de(type_label):
    """Libellé de type → code court (None si inconnu)."""
    for _, _, _, lib, code in _iter_types():
        if lib == (type_label or "").strip():
            return code
    return None


def codes_par_type():
    """{libellé_type: code} — pour fusionner avec la nomenclature."""
    return {lib: code for _, _, _, lib, code in _iter_types()}


def legende():
    """[{code, types:[...]}] trié par code : un code peut couvrir plusieurs
    libellés (ex. N = naissance ET transcription de naissance)."""
    par_code = {}
    for _, _, _, lib, code in _iter_types():
        par_code.setdefault(code, []).append(lib)
    return [{"code": c, "types": par_code[c]} for c in sorted(par_code)]


def legende_texte():
    """Légende lisible, à écrire dans Sources\\_LÉGENDE-codes.txt."""
    lignes = ["LÉGENDE DES CODES — noms de fichiers Arboriane",
              "=" * 48, ""]
    for e in legende():
        lignes.append("%-5s %s" % (e["code"], " / ".join(e["types"])))
    lignes += ["",
               "Format : <date>_<CODE>_<NOM-Prénom>[-et-<NOM-Prénom>]_<Ville>[_<variante>].<ext>",
               "Exemple : 1866_M_AMBROSINO-Michel-et-REFUTO-Marie_Procida_ameliore.jpg",
               "",
               "Forme (propriété, hors du nom)      : " + " · ".join(FORMES),
               "Complétude (propriété, hors du nom) : " + " · ".join(COMPLETUDE),
               "Visibilité (propriété, hors du nom) : " + " · ".join(VISIBILITE)]
    return "\n".join(lignes) + "\n"


def selecteur():
    """Arbre pour le formulaire : [{famille, code, sous:[{sous_famille,
    types:[{type, code}]}]}]."""
    return [{"famille": fam, "code": codef,
             "sous": [{"sous_famille": sf,
                       "types": [{"type": lib, "code": code} for lib, code in types]}
                      for sf, types in sous]}
            for fam, codef, sous in FAMILLES]
