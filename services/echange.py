# -*- coding: utf-8 -*-
"""
Échange GEDCOM — export et import avec comparaison AVANT application.

Import prudent : on montre d'abord ce qui changerait (ajoutées / disparues /
total), on alerte en cas de forte réduction, et on ne remplace la base
qu'après confirmation — toujours précédé d'une sauvegarde horodatée.
"""

from core import gedcom, modele
from core.espace import chemins
from core.fichiers import dans, horodatage, nom_sur


def _cle(ind):
    """Clé d'identité approximative pour comparer deux bases (nom + année)."""
    return (modele.nom_complet(ind).lower(), modele.annee_naissance(ind))


def exporter(app, profil=None, transcription_complete=True):
    """Écrit le GEDCOM de l'arbre actif dans Exports/ et renvoie (chemin, texte).

    `profil` (facultatif) optimise le fichier pour un site cible (Geneanet,
    MyHeritage, Ancestry, Filae) en repliant l'info riche là où le site la garde
    — voir services.profils_export. None ou « generique » = export standard.
    `transcription_complete` : False replie un résumé au lieu de l'intégrale."""
    if not app.espace_chemin:
        raise ValueError("Aucun arbre ouvert.")
    donnees = app.base.donnees
    profils_export = None
    if profil and profil != "generique":
        from services import profils_export
        donnees = profils_export.appliquer_profil(donnees, profil,
                                                   transcription_complete)
    texte = gedcom.exporter(donnees)
    if profils_export is not None:   # ex. Geneanet : retrait des tags privés
        texte = profils_export.nettoyer_texte(texte, profil)
    c = chemins(app.espace_chemin)
    suffixe = ("_" + profil) if (profil and profil != "generique") else ""
    cible = dans(c["exports"], "%s%s_%s.ged"
                 % (nom_sur(app.manifeste.get("nom", "arbre")), suffixe,
                    horodatage()))
    with open(cible, "w", encoding="utf-8") as f:
        f.write(texte)
    return cible, texte


def comparer(app, texte):
    """Compare le GEDCOM entrant à la base actuelle (sans rien écrire)."""
    if not app.base:
        raise ValueError("Aucun arbre ouvert.")
    nouveau = gedcom.importer(texte)
    actuels = {_cle(i) for i in app.base.donnees["individus"].values()}
    entrants = {_cle(i) for i in nouveau["individus"].values()}
    n_actuel = len(app.base.donnees["individus"])
    n_nouveau = len(nouveau["individus"])
    ajoutees = len(entrants - actuels)
    disparues = len(actuels - entrants)
    return {
        "total_actuel": n_actuel,
        "total_nouveau": n_nouveau,
        "ajoutees": ajoutees,
        "disparues": disparues,
        "familles_nouveau": len(nouveau["familles"]),
        # alerte si l'import fait perdre plus de 20 % des personnes existantes
        "reduction_forte": n_actuel > 0 and n_nouveau < n_actuel * 0.8,
    }


def appliquer(app, texte, corrections_lieux=None):
    """Sauvegarde la base actuelle puis la remplace par le GEDCOM importé.
    `corrections_lieux` {ancien: nouveau} : normalisation des lieux appliquée AVANT
    l'intégration (écran de correspondance des lieux à l'import)."""
    if not app.base:
        raise ValueError("Aucun arbre ouvert.")
    nouveau = gedcom.importer(texte)
    if corrections_lieux:
        from services import import_lieux
        import_lieux.appliquer_corrections(nouveau, corrections_lieux)
    # Scans référencés par un chemin absolu et présents sur le disque local :
    # copiés dans l'arbre (Arboriane tourne sur le PC de l'utilisateur).
    from services import import_medias
    bilan_scans = import_medias.importer_scans_locaux(app, nouveau)
    # Copie horodatée de SÉCURITÉ, forcée (jamais throttlée) : c'est le filet
    # avant un remplacement destructif de tout l'arbre.
    app.base.sauvegarder(forcer_horodatage=True)
    app.base.remplacer(nouveau)
    fams = nouveau["familles"]
    return {"personnes": len(nouveau["individus"]),
            "familles": len(fams),
            "sources": len(nouveau.get("sources", {})),
            # De quoi repérer un import qui « réussit » sans aucune parenté :
            # c'est arrivé (pointeurs mal lus), et rien ne le disait.
            "liens": sum(bool(f["mari"]) + bool(f["epouse"]) + len(f["enfants"])
                         for f in fams.values()),
            "liens_ignores": nouveau.get("meta", {}).get("liens_ignores", 0),
            # Version annoncée par le fichier. Arboriane lit la 5.5.1 ; un
            # fichier 7.0 s'importe, mais en perdant ce qu'elle ne connaît pas.
            "version_fichier": nouveau.get("meta", {}).get("version_fichier", ""),
            # Bilan des scans référencés : {copies, manquants} (images non
            # retrouvées sur ce PC → à compléter dans « Qualité des sources »).
            "scans": bilan_scans}
