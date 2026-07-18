# -*- coding: utf-8 -*-
"""
Mises à jour — deux briques strictement séparées :

  1. « Quoi de neuf » LOCAL : le journal des changements (NOTES) est embarqué
     dans l'app. On compare la version courante à la « dernière version vue »
     (rangée dans les réglages) pour n'afficher que ce qui est nouveau. AUCUN
     réseau.

  2. Vérification EN LIGNE, OPT-IN : `verifier_en_ligne()` interroge GitHub pour
     lire le numéro de la dernière version publiée. C'est le SEUL appel réseau de
     tout Arboriane ; il n'est déclenché que si l'utilisateur l'a explicitement
     autorisé (réglage « verif_maj »), et n'envoie AUCUNE donnée personnelle —
     juste une requête de lecture publique.
"""

import json
import urllib.request

from core.version import VERSION

DEPOT = "sophiegarguilo-star/arboriane"
PAGE = "https://sophiegarguilo-star.github.io/arboriane/"

# Journal des nouveautés, du plus récent au plus ancien. À COMPLÉTER à chaque
# version livrée (une entrée = ce que l'utilisateur gagne, en clair).
NOTES = [
    {"version": "1.9.5", "date": "2026-07-12", "points": [
        "Import GEDCOM ANSI : correction d'un cas où un seul caractère non "
        "reconnu suffisait à casser TOUS les accents du fichier (ils "
        "devenaient « � »). Les fichiers ANSI (Windows-1252) sont maintenant "
        "lus correctement même s'ils contiennent un octet douteux.",
        "Import GEDCOM : les scans référencés dans une source (OBJE/FILE, y "
        "compris sous une citation) sont désormais rattachés à la source. Si le "
        "fichier était sur un autre disque, il apparaît « à retrouver » — il "
        "suffit de rejoindre le vrai fichier.",
        "Géocodage des lieux à plusieurs champs (« Ville, Paroisse, "
        "Département, Pays ») : les champs vides sont nettoyés et, à défaut de "
        "résultat, Arboriane retente avec « ville, pays » puis « ville ».",
    ]},
    {"version": "1.9.4", "date": "2026-07-12", "points": [
        "Bouton « Télécharger » de l'annonce de mise à jour : il récupère "
        "désormais directement l'installeur (.exe), au lieu d'ouvrir une page "
        "d'où l'on repartait avec un fichier non exécutable.",
        "Choix du navigateur : dans Réglages › « Navigateur d'ouverture », vous "
        "pouvez imposer Edge, Chrome, Firefox ou le navigateur par défaut du "
        "système (au lieu du choix automatique). Prend effet au prochain "
        "démarrage.",
        "Arbre en Descendance : une union sans enfant (PACS, mariage sans "
        "enfant) n'apparaît plus — elle encombrait l'arbre et « chaînait » les "
        "conjoints par erreur. La fiche Personne garde, elle, toutes les unions.",
    ]},
    {"version": "1.9.3", "date": "2026-07-12", "points": [
        "Qualité des sources : nouvelle carte « Lieux sans pays ». Elle repère "
        "les lieux qui n'indiquent pas de pays et, si vous avez défini un « Pays "
        "par défaut » (Réglages), permet de l'ajouter à tous en un clic — très "
        "pratique après avoir importé un GEDCOM d'un autre logiciel.",
    ]},
    {"version": "1.9.2", "date": "2026-07-12", "points": [
        "Barre de défilement plus jolie : fine, arrondie, dans les tons verts, "
        "qui fonce au survol — elle apparaît là où ça défile (menus, longues "
        "listes) sans encombrer. L'arbre reste sans barre (navigation au glisser).",
        "Un indicateur « Traitement en cours… » s'affiche pour les opérations "
        "qui prennent un peu de temps (import volumineux, géocodage…).",
        "Géocodage : nouveau réglage « Pays par défaut ». Il est ajouté à la "
        "recherche d'un lieu qui n'indique pas de pays — pratique si votre arbre "
        "est surtout dans un pays (ex. « Neufchâteau » cherché en Belgique, pas "
        "dans les Vosges).",
        "Import GEDCOM : l'Aide rappelle que les encodages UTF-8, UTF-16, ANSI "
        "(Windows-1252) et ANSEL sont détectés automatiquement.",
        "Correctif : l'infobulle d'une carte d'arbre sans dates n'affiche plus "
        "« nullnullnull ».",
    ]},
    {"version": "1.9.1", "date": "2026-07-12", "points": [
        "Cohérence : les personnes hors famille (officier d'état civil, témoin… "
        "cités sans lien de parenté) ne sont plus signalées comme « sans lien "
        "familial » — leur absence de lien est normale, ce n'est pas une "
        "anomalie.",
    ]},
    {"version": "1.9.0", "date": "2026-07-12", "points": [
        "Qualité des sources : le contrôle « dates douteuses » reconnaît "
        "désormais le format français JJ/MM/AAAA. Vos vraies dates (12/06/1925, "
        "etc.) ne sont plus signalées à tort — seules les dates vraiment mal "
        "formées restent listées.",
    ]},
    {"version": "1.8.9", "date": "2026-07-11", "points": [
        "Onglet Famille plus lisible : chaque fait d'un couple a désormais sa "
        "propre ligne, dans l'ordre — PACS, Mariage, Divorce. Un mariage ne "
        "peut plus « disparaître » derrière un PACS ou un divorce.",
    ]},
    {"version": "1.8.8", "date": "2026-07-11", "points": [
        "Preuves par fait, plus clair : une personne présumée vivante n'affiche "
        "plus « Décès — À prouver » (ça n'avait pas de sens), et un PACS est "
        "libellé « PACS » / « Dissolution de PACS » au lieu de « EVEN ».",
        "Chronologie : un couple pacsé (sans mariage) n'affiche plus de ligne "
        "« Mariage » fantôme — seul le PACS apparaît.",
        "Robustesse renforcée : une donnée mal formée ne peut plus abîmer une "
        "fiche, et les preuves d'une naissance ou d'un décès ne sont plus "
        "perdues lors d'une simple modification de date.",
    ]},
    {"version": "1.8.7", "date": "2026-07-11", "points": [
        "Personnes — on distingue d'un coup d'œil qui est de la famille : dans "
        "« Tout le monde », une pastille de couleur indique la lignée directe "
        "(ancêtres), la famille élargie (frères/sœurs, oncles, cousins, "
        "conjoints, enfants) et les personnes hors famille (officier d'état "
        "civil, témoin, partenaire cité). Un filtre « Hors famille : afficher / "
        "masquer / seules » permet de désencombrer la liste.",
        "PACS / union libre : on peut enregistrer un couple non marié dans "
        "l'éditeur d'union — date de début, lieu, et date de fin si l'union est "
        "terminée. La fiche affiche « en cours » ou « dissolution … (terminée) ». "
        "Conservé à l'export GEDCOM (EVEN / TYPE PACS).",
    ]},
    {"version": "1.8.6", "date": "2026-07-11", "points": [
        "Galerie photos repensée : cliquez une photo pour l'ouvrir en grand "
        "(zoom à la molette, déplacement, navigation ←/→, Échap pour fermer). "
        "On peut écrire une légende sous chaque photo, changer leur ordre "
        "(◀ ▶), désigner le portrait, et télécharger une photo. Vignettes plus "
        "grandes et actions au même endroit.",
        "Cadrage des photos : vous pouvez choisir quelle partie d'une photo "
        "apparaît dans le carré (portrait de la fiche, cartes de l'arbre, "
        "vignettes) — pratique quand un visage n'est pas centré. Le cadrage est "
        "non destructif : la photo d'origine n'est jamais modifiée.",
        "Le portrait en haut de la fiche se met à jour tout de suite quand on "
        "ajoute une photo, désigne un portrait ou le recadre — sans recharger.",
    ]},
    {"version": "1.8.5", "date": "2026-07-11", "points": [
        "Le menu des événements d'une personne est réorganisé par moment de vie "
        "(Enfance & religion · Vie civile · Décès & sépulture · Militaire · Autre) "
        "— plus facile de trouver le bon.",
        "Nouveaux événements standard : baptême de nourrisson, ordination, "
        "bar / bat mitzvah, et les fiançailles (sur l'union, à côté du mariage "
        "et du divorce). Tous au format GEDCOM standard, interopérables.",
    ]},
    {"version": "1.8.4", "date": "2026-07-10", "points": [
        "Après avoir prouvé un fait, la fiche revient sur l'onglet "
        "« Sources & preuves » (et non plus « Synthèse ») : on enchaîne les "
        "preuves sans avoir à y retourner à chaque fois.",
        "Deux nouveaux types de source : « Pierre tombale / sépulture » (pour une "
        "photo de tombe) et « Faire-part ».",
    ]},
    {"version": "1.8.3", "date": "2026-07-10", "points": [
        "La date d'une union s'affiche maintenant dans « Preuves par fait », "
        "comme la naissance et le décès (elle restait vide auparavant).",
        "Les événements militaires utilisent désormais le format GEDCOM standard "
        "(EVEN / TYPE), lisible par tous les logiciels de généalogie, et leur "
        "intitulé précis (« Affectation », « Prisonnier de guerre »…) apparaît "
        "dans la chronologie plutôt que « Autre événement ».",
    ]},
    {"version": "1.8.2", "date": "2026-07-10", "points": [
        "Correctif important : Arboriane s'ouvre désormais de préférence dans "
        "Edge ou Chrome, jamais dans Internet Explorer. Sur certaines machines, "
        "IE empêchait l'application de fonctionner et bloquait le téléchargement "
        "des mises à jour — c'est réglé.",
        "Nouveau filtre « par personne » dans Actes / Sources : n'afficher que "
        "les actes et sources qui citent une personne donnée.",
        "Petit défaut d'affichage corrigé dans le carnet : une note « À faire » "
        "montrait deux fois la même étiquette.",
        "Nouveau groupe d'événements « Militaire » (affectation, décoration, "
        "prisonnier de guerre, blessure, campagne, fait libre) pour retracer une "
        "carrière militaire directement sur la fiche d'une personne.",
    ]},
    {"version": "1.8.1", "date": "2026-07-10", "points": [
        "Les PDF joints à une source s'affichent enfin directement dans "
        "Arboriane (visionneuse du navigateur, avec un lien pour l'ouvrir en "
        "grand), au lieu d'une vignette blanche. On peut aussi déposer des PDF "
        "depuis l'interface, pas seulement des images.",
        "Garde-fou sur les formats de photo et de scan : un fichier que le "
        "navigateur ne sait pas afficher (HEIC — le format par défaut des "
        "iPhone —, TIFF, RAW d'appareil photo) est maintenant refusé avec un "
        "message clair (« convertissez-le en JPEG ou PNG »), au lieu de créer "
        "une image blanche silencieuse.",
    ]},
    {"version": "1.8.0", "date": "2026-07-10", "points": [
        "Le carnet de bord parle enfin avec l'arbre : une note peut désormais "
        "citer PLUSIEURS personnes, et une note de type « piste » ou « à faire » "
        "remonte automatiquement dans le plan de recherche, sous chaque personne "
        "concernée. Le carnet n'est plus un cul-de-sac.",
        "Chaque fiche gagne un onglet « Carnet » qui rassemble toutes les notes "
        "du carnet citant cette personne (trouvailles, réflexions, pistes…). Une "
        "case « fait / à faire » permet de sortir une piste du plan une fois traitée.",
        "Sur une source, vous pouvez maintenant CRÉER une personne (témoin, "
        "officier d'état civil…) et la citer directement, sans devoir la créer "
        "ailleurs au préalable.",
        "Correction : supprimer une personne nettoie désormais les sources qui la "
        "citaient — plus de « lien fantôme » vers quelqu'un qui n'existe plus.",
    ]},
    {"version": "1.7.9", "date": "2026-07-10", "points": [
        "Les dates s'affichent en français partout dans l'application "
        "(« 20/07/1984 », « vers 1850 », « entre 1850 et 1860 »), tout en étant "
        "exportées au format exact de la norme GEDCOM (« 20 JUL 1984 ») : vos "
        "fichiers sont mieux relus par les autres logiciels, sans que vous ayez "
        "jamais à voir de mois en anglais. Les arbres déjà existants sont "
        "convertis automatiquement à l'ouverture.",
        "Un divorce — et plus largement tout événement de couple — peut "
        "désormais être « prouvé » comme le mariage : le bouton « Prouver » et le "
        "badge « Prouvé par acte » apparaissent bien sur la frise de vie.",
        "L'écran « Preuves par fait » est réorganisé en tableau clair "
        "(fait, date, preuve, action), avec des libellés courts au lieu de longs "
        "textes sur plusieurs lignes.",
    ]},
    {"version": "1.7.8", "date": "2026-07-10", "points": [
        "Interopérabilité renforcée : les fichiers GEDCOM produits par Arboriane "
        "sont désormais pleinement conformes à la norme 5.5.1. Les titres, noms, "
        "lieux et longues valeurs sont correctement découpés — plus aucune perte "
        "de caractère quand un autre logiciel relit votre export.",
        "Une source qui vous revient d'un autre logiciel « aplatie » en une "
        "simple phrase (comportement de Geneanet et des sites GeneWeb) redevient "
        "une vraie source consultable, au lieu d'une citation vide.",
        "La note d'un dépôt d'archives n'est plus perdue lors d'un import.",
        "Un dépôt que vous avez saisi mais pas encore rattaché à une source "
        "figure maintenant dans l'export.",
        "Un fichier au format GEDCOM 7.0 s'importe toujours, mais l'application "
        "vous prévient que certaines informations récentes peuvent manquer — "
        "Arboriane lit le 5.5.1.",
    ]},
    {"version": "1.7.7", "date": "2026-07-10", "points": [
        "Export GEDCOM : une note longue perdait une espace à chaque coupure de "
        "ligne, lorsqu'elle était relue par un AUTRE logiciel de généalogie. Le "
        "texte est désormais transmis au caractère près.",
        "L'indentation d'une note (espaces en début de ligne) était écrasée à "
        "chaque import ou export. Elle est préservée.",
        "Arboriane est publiée sous licence libre AGPL v3 : vous pouvez l'étudier, "
        "la modifier et la partager, à condition que vos versions restent libres.",
    ]},
    {"version": "1.7.6", "date": "2026-07-10", "points": [
        "Correctif important : « Fusionner » un fichier GEDCOM pouvait faire "
        "disparaître des personnes. Deux homonymes sans date de naissance, ou "
        "deux personnes sans nom, étaient confondus en un seul individu. Sur un "
        "arbre de 501 personnes, 81 s'évanouissaient en silence. Une personne "
        "n'est désormais rapprochée d'une autre que si son nom ET son année de "
        "naissance concordent.",
        "Correctif important : « Fusionner » supprimait les familles dont un "
        "seul époux est connu, même lorsqu'elles portent une date de mariage. "
        "Sur un grand arbre, cela effaçait des centaines d'unions.",
        "Les deux modes d'import, « Remplacer » et « Fusionner », donnent enfin "
        "exactement le même arbre — vérifié sur 26 fichiers réels produits par "
        "d'autres logiciels de généalogie.",
        "Chaque publication est désormais vérifiée automatiquement avant d'être "
        "mise en ligne, et l'empreinte SHA-256 de l'installateur est publiée : "
        "vous pouvez contrôler que le fichier téléchargé est bien le nôtre.",
    ]},
    {"version": "1.7.5", "date": "2026-07-10", "points": [
        "Correctif important, signalé par un utilisateur : « Fusionner » un "
        "fichier GEDCOM importait bien les personnes mais AUCUN lien de parenté. "
        "Père, mère, conjoint et enfants restaient vides, et l'arbre se réduisait "
        "à une seule personne. Les familles sont désormais reprises, sans "
        "dupliquer un couple déjà présent.",
        "Un remariage du même couple reste bien deux unions distinctes, avec "
        "leurs deux dates de mariage.",
        "Import GEDCOM plus robuste : les liens sont lus quelle que soit la mise "
        "en forme du fichier, et reconstruits même quand un enregistrement de "
        "famille est incomplet.",
        "Si un import ne parvient à lire aucun lien de parenté, l'application le "
        "dit clairement au lieu d'annoncer une réussite trompeuse.",
    ]},
    {"version": "1.7.4", "date": "2026-07-09", "points": [
        "Nouvelle source : on indique désormais QUI l'acte concerne dès la "
        "création (l'enfant et ses parents, tout un foyer au recensement, les "
        "témoins…). Jusqu'ici, relier une personne n'était possible qu'après coup.",
        "Le titre d'une source n'est plus à inventer : il se construit tout seul "
        "à partir du type d'acte, des personnes, de la date et du lieu — "
        "« Acte de naissance — Jean DUPONT — 12/03/1902 — Lyon, Rhône » — et "
        "reste modifiable à volonté.",
        "Vos scans peuvent être renommés « 1902-03-12_N_DUPONT-Jean_Lyon.jpg » : "
        "rangés par date dans l'explorateur Windows, lisibles d'un coup d'œil. "
        "Proposé, décochable, jamais imposé.",
        "Si Arboriane s'arrête (fenêtre de lancement fermée, mise en veille), la "
        "page vous le dit clairement au lieu de rester muette. La fenêtre de "
        "lancement rappelle qu'elle fait tourner le logiciel.",
        "Plan de recherche : les pistes sont mieux formulées (« Trouver l'acte de "
        "mariage » et non « l'acte de union »), et les lieux gardent leurs "
        "majuscules.",
    ]},
    {"version": "1.7.3", "date": "2026-07-09", "points": [
        "Correctif important : ajouter « ＋ Père » puis « ＋ Mère » créait une "
        "union fantôme (« conjoint·e inconnu·e ») sur le père. Les deux parents "
        "rejoignent désormais la même famille.",
        "Nouveau : MODIFIER UNE UNION. Depuis l'onglet Famille d'une fiche, "
        "saisissez enfin la date et le lieu du mariage — et le DIVORCE. Le divorce "
        "apparaît dans la chronologie, dans les repères de vie, et voyage en "
        "GEDCOM (balise DIV). Les preuves du mariage sont préservées.",
        "Le résumé de vie mentionne désormais les unions, le divorce et le nombre "
        "d'enfants (« mariée en 2000 à Lyon avec…, mère de 3 enfants »).",
        "Livre : un avertissement indique combien de personnes vivantes seront "
        "masquées — fini le livre étrangement vide sur une famille bien vivante.",
        "La première personne d'un arbre neuf (ou d'un GEDCOM importé) devient "
        "automatiquement la racine (Sosa 1) — et supprimer la personne racine ne "
        "rend plus l'écran Sosa muet : une autre personne prend le relais. "
        "Statistique « enfants par couple » corrigée (elle comptait par parent).",
        "La question « vérifier les mises à jour ? » ne barre plus l'écran de "
        "bienvenue : c'est un bandeau discret, qui décale la page au lieu de "
        "masquer l'en-tête. Vouvoiement harmonisé dans toute l'application.",
    ]},
    {"version": "1.7.2", "date": "2026-07-09", "points": [
        "Sourçage — une preuve, plusieurs personnes : « Prouver » relie désormais "
        "la même source à toutes les personnes qu'elle cite. Un acte de naissance "
        "se rattache à l'enfant ET à ses parents (proposés automatiquement) ; un "
        "recensement à tout le foyer. Une union reste prouvée pour les deux "
        "conjoint·es d'un seul geste.",
        "« Relier une source existante » devient une RECHERCHE par titre (fini le "
        "long menu déroulant) — pratique même avec des milliers de sources.",
        "Compteur « non reliées » corrigé : une source qui prouve un fait n'est "
        "plus comptée comme orpheline, et les preuves sans scan sont signalées "
        "avec un raccourci vers « Toutes les sources ».",
        "Recherche web : liens réparés (Filae), lien mort retiré (Géopatronyme), "
        "ajout de Gallica (BnF). Et une preuve d'union se pose sur la bonne union "
        "en cas de remariage.",
    ]},
    {"version": "1.7.1", "date": "2026-07-09", "points": [
        "Ajout d'un proche repensé : un seul écran, la fiche COMPLÈTE (comme "
        "« Nouvelle personne »), avec en tête un « Lien de parenté » — père, "
        "mère, conjoint·e, enfant, et désormais frère / sœur. Le lien est "
        "pré-rempli selon le bouton d'où l'on vient, ou « à déterminer » depuis "
        "« Nouvelle personne ». On peut créer une personne complète OU relier "
        "quelqu'un déjà dans l'arbre, toujours avec un bouton « Retour ».",
        "Correctif important sur les unions : une conjointe ajoutée apparaît "
        "désormais des DEUX côtés (fini l'union visible chez l'un mais pas chez "
        "l'autre), et les enfants ne partent plus dans une union fantôme "
        "« conjoint·e inconnu·e ».",
        "Le bouton « ＋ enfant » d'une union rattache l'enfant à CETTE union. "
        "Quand une personne a plusieurs unions, on choisit désormais à laquelle "
        "rattacher l'enfant (ou une nouvelle union, autre parent inconnu).",
        "La synthèse « Repères de vie » affiche toutes les unions, pas seulement "
        "la première. Réparation automatique des liens familiaux à chaque "
        "modification (robustesse des arbres importés).",
    ]},
    {"version": "1.7.0", "date": "2026-07-09", "points": [
        "Sourcer TOUS les faits (pas seulement naissance/mariage/décès) : un bouton "
        "« Prouver » sur chaque ligne de « Vie & chronologie » — résidences, "
        "professions, événements (décorations…) — avec un indice de fiabilité.",
        "« Prouver » ouvre le vrai formulaire de source détaillé (dépôt, cote, lien, "
        "pièces jointes, transcription) : source existante ou créée sur place, reliée "
        "au fait en un clic. Fini le détour obligatoire par « Actes / Sources ».",
        "Pièces jointes : les PDF et TIFF sont désormais acceptés (en plus des images).",
        "Ajouter un proche ou prouver un fait s'ouvre en plein écran, avec un bouton "
        "« ← Retour à la fiche ».",
    ]},
    {"version": "1.6.9", "date": "2026-07-09", "points": [
        "Heure de naissance et de décès : un champ « heure » facultatif sur la "
        "fiche (ex. « né le 12 mars 1902 à 14:30 »). Pratique pour l'état civil "
        "moderne qui mentionne l'heure. Conservée à l'export et à l'import GEDCOM.",
    ]},
    {"version": "1.6.8", "date": "2026-07-09", "points": [
        "Ajouter un PARENT depuis une fiche : les boutons « ＋ Père » et « ＋ Mère » "
        "manquaient. On peut de nouveau remonter sa généalogie — créer un parent "
        "ou relier une personne existante — directement depuis la fiche et la "
        "cellule familiale.",
        "Nouvel audit « Présumés vivants trop âgés » (Qualité des sources) : repère "
        "les personnes sans date de décès trop âgées pour être en vie (âge déduit "
        "de leurs enfants/unions) et permet de les marquer décédées d'un clic, "
        "sans jamais inventer de date.",
        "Optimisation : le plan de recherche ne calcule plus deux fois les mêmes "
        "preuves — plus rapide sur les grands arbres.",
    ]},
    {"version": "1.6.7", "date": "2026-07-09", "points": [
        "Multi-ordinateurs, à la demande : rangez un arbre dans un dossier "
        "synchronisé (OneDrive, Google Drive, Dropbox, iCloud) et retrouvez-le "
        "sur vos autres ordinateurs — Arboriane reste 100 % local, sans compte.",
        "Garde-fou « un seul ordinateur à la fois » : Arboriane prévient si un "
        "arbre semble déjà ouvert ailleurs, et rappelle la règle d'or.",
        "Nouvelle aide « Sur plusieurs ordinateurs » et badge « ☁ synchronisé » "
        "sur les arbres rangés dans un cloud.",
    ]},
    {"version": "1.6.6", "date": "2026-07-09", "points": [
        "Parcours plus clair : un onglet qui a besoin d'un arbre vous ramène "
        "à l'accueil (qui vous guide) au lieu d'un message obscur.",
        "Aide enrichie : nouvelles fiches « Composer un livre », « Restaurer une "
        "sauvegarde », « Fusionner des doublons », « Les dépôts », « Calendrier "
        "républicain » et « Mises à jour ».",
        "Plus d'explications sur place (statuts d'acte lisibles, cote, dates, "
        "confidentialité, statut de vie…) et messages d'erreur plus clairs.",
    ]},
    {"version": "1.6.5", "date": "2026-07-09", "points": [
        "Fini les encarts « fantômes » (Arbre vide…) qui se superposaient au "
        "tableau de bord après un changement rapide d'onglet.",
    ]},
    {"version": "1.6.4", "date": "2026-07-09", "points": [
        "Import fusionnant : plus de liens d'association erronés ; dates du "
        "calendrier républicain conservées aussi sur les événements (baptême…).",
        "Fiabilité : suppression d'un arbre plus sûre, fiche personne sans "
        "affichage périmé au changement rapide d'onglet.",
    ]},
    {"version": "1.6.3", "date": "2026-07-09", "points": [
        "Import fusionnant : les actes de naissance et de décès ne sont plus perdus.",
        "Sauvegarde de sécurité toujours faite avant un « Remplacer tout l'arbre ».",
        "Petites finitions de fiabilité et d'accessibilité.",
    ]},
    {"version": "1.6.2", "date": "2026-07-09", "points": [
        "Livres : « Lire en ligne » et « Aperçu imprimable » s'ouvrent de nouveau "
        "(la fenêtre n'est plus bloquée comme pop-up par le navigateur).",
    ]},
    {"version": "1.6.1", "date": "2026-07-09", "points": [
        "Correctifs Livres : la création d'un livre fonctionne de nouveau, "
        "rendu plus robuste (photos, masquage des vivants, préface).",
        "Corrections de fond : couples de même sexe, filiation, sélecteurs de "
        "fichiers Windows, et divers points de fiabilité (audit complet).",
    ]},
    {"version": "1.6.0", "date": "2026-07-09", "points": [
        "Nouveau : les LIVRES biographiques ! Composez un livre à imprimer ou à "
        "offrir (menu Composer › Livres).",
        "Récit de vie, aïeux (Sosa) et descendance (d'Aboville), chronologie, album "
        "photos et index — 3 modèles au choix (Héritage, Épuré, Sépia), A4 ou A5.",
        "Lecture en ligne ou impression : un seul fichier, 100 % local, à envoyer par mail.",
    ]},
    {"version": "1.5.8", "date": "2026-07-09", "points": [
        "Passe qualité (audit complet) : robustesse, sécurité et fidélité renforcées.",
        "Import GEDCOM plus sûr (liens et sources réalignés, dates républicaines conservées).",
        "Confirmation avant « Remplacer tout l'arbre » et protection contre la double création.",
    ]},
    {"version": "1.5.7", "date": "2026-07-09", "points": [
        "Nouveau : « Restaurer une sauvegarde » — recharge un arbre complet (.zip, "
        "scans compris) via une fenêtre Windows, sans limite de taille.",
        "L'import d'un gros fichier ne fait plus planter la page : il propose la restauration.",
    ]},
    {"version": "1.5.6", "date": "2026-07-09", "points": [
        "« Quoi de neuf » à l'ouverture après chaque mise à jour.",
        "Vérification facultative des mises à jour (proposée une fois, réglable).",
    ]},
    {"version": "1.5.5", "date": "2026-07-09", "points": [
        "Arbre de démonstration enrichi (~100 personnes sur 12 générations).",
        "Installeur : choix du dossier, message de mise à jour, données conservées.",
    ]},
    {"version": "1.5.4", "date": "2026-07-08", "points": [
        "Le bouton « Prouver » fonctionne pour le fait Union.",
        "Lien de téléchargement stable d'une version à l'autre.",
    ]},
    {"version": "1.5.3", "date": "2026-07-08", "points": [
        "Ajout d'un enfant possible sans passer par un conjoint.",
        "Messages d'erreur plus clairs et avec la marche à suivre.",
    ]},
    {"version": "1.5.2", "date": "2026-07-08", "points": [
        "Repli automatique si le dossier Documents est protégé par Windows.",
    ]},
    {"version": "1.5.1", "date": "2026-07-08", "points": [
        "Charte graphique harmonisée ; mosaïque d'arbre en A3 et A0.",
    ]},
]


def _tuple(v):
    """« 1.5.10 » -> (1, 5, 10) pour comparer des versions numériquement."""
    parts = []
    for p in str(v).split("."):
        parts.append(int(p) if p.isdigit() else 0)
    return tuple(parts)


def notes_depuis(derniere_vue):
    """Nouveautés STRICTEMENT postérieures à `derniere_vue` (et jusqu'à la
    version courante incluse). Liste vide si `derniere_vue` est absente (premier
    lancement : rien à comparer) ou déjà à jour."""
    if not derniere_vue:
        return []
    seuil = _tuple(derniere_vue)
    return [n for n in NOTES if seuil < _tuple(n["version"]) <= _tuple(VERSION)]


def verifier_en_ligne(timeout=6):
    """Lit la dernière version publiée sur GitHub. Renvoie un dict :
    {ok, actuelle, derniere, disponible, url}. Ne lève JAMAIS : hors ligne ou
    erreur -> {ok: False}. N'envoie aucune donnée (simple GET public)."""
    url = "https://api.github.com/repos/%s/releases/latest" % DEPOT
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Arboriane/%s" % VERSION,
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as rep:
            data = json.loads(rep.read().decode("utf-8", "replace"))
    except Exception:
        return {"ok": False}
    tag = (data.get("tag_name") or "").lstrip("vV")
    if not tag:
        return {"ok": False}
    disponible = _tuple(tag) > _tuple(VERSION)
    return {"ok": True, "actuelle": VERSION, "derniere": tag, "disponible": disponible,
            "url": PAGE, "installeur": _url_installeur(data.get("assets"))}


def _url_installeur(assets):
    """URL DIRECTE de l'installeur (.exe) parmi les assets d'une release GitHub —
    le bouton « Télécharger » doit récupérer l'exécutable, jamais la page ni le
    fichier « .sha256 » (l'utilisateur tombait sinon sur un fichier non
    exécutable). '' si aucun .exe."""
    for a in assets or []:
        nom = (a.get("name") or "").lower()
        if nom.endswith(".exe") and a.get("browser_download_url"):
            return a["browser_download_url"]
    return ""
