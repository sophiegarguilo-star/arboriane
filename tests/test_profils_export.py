# -*- coding: utf-8 -*-
"""
Test des profils d'export GEDCOM (services.profils_export).

Un mini-arbre : 1 personne (I1) dont la naissance cite une source S1 (titre +
transcription + ARK). On vérifie que chaque profil replie l'info riche là où le
site cible la conserve, et que le générique reste identique à l'export actuel.

Exécuter :  python -X utf8 tests/test_profils_export.py
"""

import copy
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import gedcom                            # noqa: E402
from services import profils_export                # noqa: E402

_ok = _ko = 0


def verifie(nom, cond):
    global _ok, _ko
    if cond:
        _ok += 1; print("  ok  ", nom)
    else:
        _ko += 1; print("  FAIL", nom)


TITRE = "Acte de naissance de Jean Martin"
TRANS = "L'an mil huit cent cinquante, le trois janvier, est né Jean Martin.\nFils de Pierre et de Marie."
ARK = "https://www.geneanet.org/registres/view/12345/1"


def _base():
    """Mini-arbre : I1 + naissance citant S1 (titre/transcription/ark).

    Volontairement porteur de plusieurs tags PRIVÉS à l'export (_TIME sur la
    naissance et sur le mariage, _SOSA, _RUFNAME, _ROLE de citation, _FIAB /
    _PAGE de la source) : c'est ce que Geneanet déverse en clair dans les notes.
    """
    return {
        "individus": {
            "I1": {
                "id": "I1", "prenoms": "Jean", "nom": "MARTIN", "sexe": "M",
                "sosa": 4, "prenom_principal": "Jean", "fams": ["F1"],
                "naissance": {"date": "3 janvier 1850", "lieu": "Marseille",
                              "heure": "06:30",
                              "citations": [{"source": "S1", "page": "vue 1",
                                             "quay": 3, "role": "témoin"}]},
                "deces": {}, "citations": [],
            },
            "I2": {"id": "I2", "prenoms": "Marie", "nom": "DUPONT", "sexe": "F",
                   "fams": ["F1"], "naissance": {}, "deces": {}, "citations": []},
        },
        "familles": {
            "F1": {"id": "F1", "mari": "I1", "epouse": "I2", "enfants": [],
                   "mariage": {"date": "2 octobre 1924", "lieu": "Marseille",
                               "heure": "18:00", "citations": []}},
        },
        "sources": {
            "S1": {"id": "S1", "titre": TITRE, "type": "", "date": "", "lieu": "",
                   "transcription": TRANS, "ark": ARK, "note": "", "depot": "",
                   "cote": "", "page": "5", "fiabilite": "3", "statut": "vérifié",
                   "personnes": [], "fichiers": []},
        },
    }


# Une ligne GEDCOM de tag privé : « <niveau> _XXX … ».
_TAG_PRIVE = re.compile(r"(?m)^\d+ _")


def _export(donnees, profil):
    """Reproduit la chaîne d'export réelle : appliquer_profil → exporter →
    nettoyer_texte (cf. services/echange.py et services/publication.py)."""
    copie = profils_export.appliquer_profil(donnees, profil)
    return profils_export.nettoyer_texte(gedcom.exporter(copie), profil)


def test_generique_identique():
    donnees = _base()
    avant = gedcom.exporter(copy.deepcopy(donnees))
    copie = profils_export.appliquer_profil(donnees, "generique")
    apres = gedcom.exporter(copie)
    verifie("générique : export identique à l'actuel", avant == apres)
    verifie("générique : entrée non modifiée (copie profonde)",
            donnees["sources"]["S1"]["transcription"] == TRANS)


def test_generique_garde_les_tags_prives():
    """Le générique est le format de fidélité maximale : il garde tout."""
    ged = _export(_base(), "generique")
    verifie("générique : tags privés toujours émis",
            bool(_TAG_PRIVE.search(ged)))
    for tag in ("1 _SOSA 4", "3 _TIME 06:30", "1 _FIAB 3", "3 _ROLE témoin"):
        verifie("générique : « %s » présent" % tag, tag in ged)


def test_geneanet_aucun_repliage():
    """Geneanet garde transcription + ARK : aucune donnée n'est déplacée."""
    donnees = _base()
    copie = profils_export.appliquer_profil(donnees, "geneanet")
    verifie("geneanet : données identiques au générique (aucun repliage)",
            copie == profils_export.appliquer_profil(donnees, "generique"))


def test_geneanet_sans_tags_prives():
    """GeneWeb déverse les tags privés en clair dans les notes : on les retire."""
    ged = _export(_base(), "geneanet")
    verifie("geneanet : AUCUNE ligne de tag privé (^\\d+ _)",
            _TAG_PRIVE.search(ged) is None)
    verifie("geneanet : plus d'heure de mariage (_TIME)", "_TIME" not in ged)
    verifie("geneanet : plus de _SOSA", "_SOSA" not in ged)
    verifie("geneanet : plus de _FIAB/_STATUT",
            "_FIAB" not in ged and "_STATUT" not in ged)
    # Ce que le nettoyage ne doit PAS emporter : le contenu standard.
    verifie("geneanet : MARR conservé", "1 MARR" in ged)
    verifie("geneanet : DATE du mariage conservée",
            "2 DATE 2 octobre 1924" in ged)
    verifie("geneanet : BIRT + DATE conservés",
            "1 BIRT" in ged and "2 DATE 3 janvier 1850" in ged)
    verifie("geneanet : citation SOUR conservée", "SOUR @S1@" in ged)
    verifie("geneanet : record source + transcription conservés",
            "0 @S1@ SOUR" in ged and "L'an mil huit cent cinquante" in ged)
    verifie("geneanet : ARK conservé", ARK in ged)
    verifie("geneanet : fichier bien clos", ged.rstrip("\n").endswith("0 TRLR"))


def test_retirer_tags_prives_sous_arbre():
    """Un tag privé emporte ses lignes subordonnées (CONT/CONC, sous-tags)."""
    texte = ("0 @I1@ INDI\n1 NAME Jean /MARTIN/\n1 _TODO Chercher l'acte\n"
             "2 _STAT done\n2 CONT suite de la piste\n1 SEX M\n0 TRLR\n")
    net = profils_export.retirer_tags_prives(texte)
    verifie("sous-arbre : _TODO et ses subordonnées retirés",
            "_TODO" not in net and "_STAT" not in net
            and "suite de la piste" not in net)
    verifie("sous-arbre : les lignes suivantes survivent",
            "1 SEX M" in net and "1 NAME Jean /MARTIN/" in net)


def test_autres_profils_gardent_les_tags_prives():
    """MyHeritage/Ancestry/Filae ignorent proprement les tags privés : on ne
    leur retire rien (seul Geneanet est concerné)."""
    for profil in ("myheritage", "ancestry", "filae"):
        ged = _export(_base(), profil)
        verifie("%s : tags privés conservés" % profil,
                bool(_TAG_PRIVE.search(ged)))


def test_myheritage():
    donnees = _base()
    ged = gedcom.exporter(profils_export.appliquer_profil(donnees, "myheritage"))
    # La transcription doit apparaître dans le TEXT de la CITATION (niveau 2/3).
    verifie("myheritage : citation SOUR sur la naissance", "2 SOUR @S1@" in ged)
    verifie("myheritage : transcription dans le TEXT de citation",
            "L'an mil huit cent cinquante" in ged
            and _apres(ged, "2 SOUR @S1@", "TEXT"))
    verifie("myheritage : ARK replié dans la citation",
            ("Source en ligne : " + ARK) in ged)
    # Le record source ne porte plus la transcription (jetée par MyHeritage).
    verifie("myheritage : PAGE/QUAY conservés",
            "3 PAGE vue 1" in ged and "3 QUAY 3" in ged)


def test_ancestry():
    donnees = _base()
    ged = gedcom.exporter(profils_export.appliquer_profil(donnees, "ancestry"))
    verifie("ancestry : _WLNK créé au niveau personne", "1 _WLNK" in ged)
    verifie("ancestry : _WLNK porte le titre de l'acte",
            ("2 TITL " + TITRE) in ged)
    verifie("ancestry : _WLNK porte l'URL en NOTE", ("2 NOTE " + ARK) in ged)
    verifie("ancestry : plus de WWW (ARK déplacé)", ("1 WWW " + ARK) not in ged)
    verifie("ancestry : transcription dans la NOTE du record source",
            "0 @S1@ SOUR" in ged and "L'an mil huit cent cinquante" in ged)


def test_filae():
    donnees = _base()
    copie = profils_export.appliquer_profil(donnees, "filae")
    ged = gedcom.exporter(copie)
    verifie("filae : aucun record SOUR", "0 @S1@ SOUR" not in ged)
    verifie("filae : plus de citation SOUR", "SOUR @S1@" not in ged)
    verifie("filae : sources vidées dans les données", copie["sources"] == {})
    verifie("filae : titre de la source dans la NOTE de la personne",
            TITRE in ged)
    verifie("filae : transcription dans la NOTE de la personne",
            "L'an mil huit cent cinquante" in ged)
    verifie("filae : ARK dans la NOTE de la personne", ARK in ged)


def test_transcription_resume():
    donnees = _base()
    copie = profils_export.appliquer_profil(donnees, "myheritage",
                                            transcription_complete=False)
    ged = gedcom.exporter(copie)
    verifie("résumé : 1re ligne présente",
            "L'an mil huit cent cinquante" in ged)
    verifie("résumé : suite de la transcription absente",
            "Fils de Pierre" not in ged)
    verifie("résumé : ARK toujours replié", ARK in ged)


# ---------------------------------------------------------------------------
# Bloc provenance (dépôt / cote / lien) — la priorité : sources, dépôts,
# actes et liens avant tout ; la transcription n'est qu'un bonus.
# ---------------------------------------------------------------------------

DEPOT = "Archives départementales des Bouches-du-Rhône"
COTE = "202 E 1234"
NOTE_SRC = "Acte retrouvé grâce au recensement de 1846."


def _base_prov():
    """Mini-arbre dont S1 porte dépôt + cote + ark + note + transcription."""
    donnees = _base()
    src = donnees["sources"]["S1"]
    src["depot"] = DEPOT
    src["cote"] = COTE
    src["note"] = NOTE_SRC
    donnees["depots"] = {}
    return donnees


def test_bloc_provenance():
    donnees = _base_prov()
    src = donnees["sources"]["S1"]
    bloc = profils_export.bloc_provenance(donnees, src)
    verifie("provenance : format complet",
            bloc == "Dépôt : %s — Cote : %s — En ligne : %s" % (DEPOT, COTE, ARK))
    # Parties vides omises.
    partiel = dict(src, depot="", depot_id="", cote="")
    verifie("provenance : parties vides omises",
            profils_export.bloc_provenance(donnees, partiel)
            == "En ligne : " + ARK)
    verifie("provenance : vide si rien",
            profils_export.bloc_provenance(
                donnees, dict(src, depot="", depot_id="", cote="", ark="")) == "")
    # Résolution du dépôt par depot_id.
    d2 = dict(donnees, depots={"R1": {"id": "R1", "nom": "AD13"}})
    verifie("provenance : depot_id résolu via donnees['depots']",
            profils_export.bloc_provenance(
                d2, dict(src, depot="", depot_id="R1")).startswith("Dépôt : AD13"))


def test_myheritage_provenance():
    donnees = _base_prov()
    copie = profils_export.appliquer_profil(donnees, "myheritage")
    note = copie["sources"]["S1"]["note"]
    ged = gedcom.exporter(copie)
    verifie("myheritage : provenance dans la note du record source",
            DEPOT in note and COTE in note and ARK in note)
    verifie("myheritage : note d'origine conservée", NOTE_SRC in note)
    verifie("myheritage : provenance présente dans le GEDCOM exporté",
            DEPOT in ged and COTE in ged)
    page = copie["individus"]["I1"]["naissance"]["citations"][0]["page"]
    verifie("myheritage : PAGE se termine par l'ARK", page.endswith(ARK))
    verifie("myheritage : PAGE conserve la page d'origine",
            page.startswith("vue 1"))
    verifie("myheritage : PAGE exporté avec l'ARK",
            ("3 PAGE vue 1 — " + ARK) in ged)
    verifie("myheritage : transcription toujours repliée dans le TEXT",
            "L'an mil huit cent cinquante" in ged)


def test_ancestry_provenance():
    donnees = _base_prov()
    copie = profils_export.appliquer_profil(donnees, "ancestry")
    note = copie["sources"]["S1"]["note"]
    ged = gedcom.exporter(copie)
    verifie("ancestry : provenance dans la note du record source",
            DEPOT in note and COTE in note and ARK in note)
    verifie("ancestry : note d'origine conservée", NOTE_SRC in note)
    verifie("ancestry : transcription toujours en note",
            "L'an mil huit cent cinquante" in note)
    verifie("ancestry : _WLNK toujours présent",
            "1 _WLNK" in ged and ("2 NOTE " + ARK) in ged)
    verifie("ancestry : REPO conservé (ceinture et bretelles)",
            ("1 REPO" in ged) and DEPOT in ged)


def test_filae_provenance():
    donnees = _base_prov()
    ged = gedcom.exporter(profils_export.appliquer_profil(donnees, "filae"))
    verifie("filae : dépôt dans la note de personne", DEPOT in ged)
    verifie("filae : cote dans la note de personne", COTE in ged)
    verifie("filae : ARK dans la note de personne", ARK in ged)
    verifie("filae : transcription présente si complète",
            "L'an mil huit cent cinquante" in ged)
    # Allégé : provenance seule, sans transcription.
    leger = gedcom.exporter(profils_export.appliquer_profil(
        donnees, "filae", transcription_complete=False))
    verifie("filae allégé : provenance conservée",
            DEPOT in leger and COTE in leger and ARK in leger)
    verifie("filae allégé : titre conservé", TITRE in leger)
    verifie("filae allégé : AUCUNE transcription",
            "L'an mil huit cent cinquante" not in leger
            and "Fils de Pierre" not in leger)
    verifie("filae allégé : fichier plus léger", len(leger) < len(ged))


def test_generique_inchange_avec_provenance():
    """Le générique reste l'archivage de fidélité maximale : aucun repliage."""
    donnees = _base_prov()
    avant = gedcom.exporter(copy.deepcopy(donnees))
    apres = gedcom.exporter(
        profils_export.appliquer_profil(donnees, "generique"))
    verifie("générique : export strictement identique (avec provenance)",
            avant == apres)
    verifie("générique : note de source non modifiée",
            profils_export.appliquer_profil(
                donnees, "generique")["sources"]["S1"]["note"] == NOTE_SRC)


def test_idempotence_provenance():
    """Appliquer un profil deux fois ne duplique pas le bloc provenance."""
    donnees = _base_prov()
    for profil in ("myheritage", "ancestry"):
        une = profils_export.appliquer_profil(donnees, profil)
        deux = profils_export.appliquer_profil(une, profil)
        note = deux["sources"]["S1"]["note"]
        verifie("%s : « Dépôt : » non dupliqué" % profil,
                note.count("Dépôt : ") == 1)
        verifie("%s : cote non dupliquée" % profil, note.count(COTE) == 1)
    # MyHeritage : le PAGE ne reçoit pas deux fois l'ARK.
    une = profils_export.appliquer_profil(donnees, "myheritage")
    deux = profils_export.appliquer_profil(une, "myheritage")
    page = deux["individus"]["I1"]["naissance"]["citations"][0]["page"]
    verifie("myheritage : ARK non dupliqué dans le PAGE", page.count(ARK) == 1)
    # Filae : la note de personne ne double pas non plus.
    une = profils_export.appliquer_profil(donnees, "filae")
    deux = profils_export.appliquer_profil(une, "filae")
    verifie("filae : provenance non dupliquée dans la note de personne",
            deux["individus"]["I1"]["note"].count(COTE) == 1)


def _apres(texte, ancre, motif):
    """Le motif apparaît-il après l'ancre dans le texte ?"""
    i = texte.find(ancre)
    return i >= 0 and texte.find(motif, i) >= 0


if __name__ == "__main__":
    test_generique_identique()
    test_generique_garde_les_tags_prives()
    test_geneanet_aucun_repliage()
    test_geneanet_sans_tags_prives()
    test_retirer_tags_prives_sous_arbre()
    test_autres_profils_gardent_les_tags_prives()
    test_myheritage()
    test_ancestry()
    test_filae()
    test_transcription_resume()
    test_bloc_provenance()
    test_myheritage_provenance()
    test_ancestry_provenance()
    test_filae_provenance()
    test_generique_inchange_avec_provenance()
    test_idempotence_provenance()
    print("\n%d ok, %d échec(s)" % (_ok, _ko))
    sys.exit(1 if _ko else 0)
