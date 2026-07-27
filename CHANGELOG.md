# Journal des versions

Toutes les versions notables d'Arboriane. Format inspiré de
[Keep a Changelog](https://keepachangelog.com/fr/), versions selon
[SemVer](https://semver.org/lang/fr/).

> Ce fichier est **généré** depuis les notes de l'application
> (`services/maj.py`) : ne le modifiez pas à la main, lancez
> `python -X utf8 outils/generer_changelog.py`.


## [1.10.0](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.10.0) — 2026-07-24

- Export optimisé selon le site de destination : un nouveau menu « Optimiser pour » (Générique, Geneanet, MyHeritage, Ancestry, Filae) range chaque information là où le site sait la conserver. Un bloc de provenance (dépôt, cote, lien de l'acte) est désormais préservé partout, et vous pouvez choisir d'inclure ou non la transcription intégrale des actes.
- Les preuves ne disparaissent plus : relier une source à un métier, une résidence ou un événement était perdu dès qu'on ré-enregistrait la fiche. C'est corrigé — un lien vers une source reste définitif.
- Sources d'union mieux prises en compte : une source attachée à la famille (au mariage) crédite maintenant les deux époux, même quand un conjoint est inconnu. Fini les personnes signalées « sans source » à tort.
- Import plus respectueux : un fait déjà sourcé mais sans niveau de fiabilité (fréquent après un import GEDCOM) n'est plus redemandé « à valider ». Seuls les faits réellement sans aucune source restent au plan de recherche.
- Fusion des doublons : nouveau bouton « Ce n'est pas un doublon » qui écarte définitivement une paire pour ne plus jamais la reproposer ; la comparaison en deux colonnes est conservée.
- Types d'actes enrichis : nouvelle rubrique « Tables et index » (index de baptêmes, naissances, mariages, décès, et tables décennales).

## [1.9.5](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.9.5) — 2026-07-12

- Import GEDCOM ANSI : correction d'un cas où un seul caractère non reconnu suffisait à casser TOUS les accents du fichier (ils devenaient « � »). Les fichiers ANSI (Windows-1252) sont maintenant lus correctement même s'ils contiennent un octet douteux.
- Import GEDCOM : les scans référencés dans une source (OBJE/FILE, y compris sous une citation) sont désormais rattachés à la source. Si le fichier était sur un autre disque, il apparaît « à retrouver » — il suffit de rejoindre le vrai fichier.
- Géocodage des lieux à plusieurs champs (« Ville, Paroisse, Département, Pays ») : les champs vides sont nettoyés et, à défaut de résultat, Arboriane retente avec « ville, pays » puis « ville ».

## [1.9.4](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.9.4) — 2026-07-12

- Bouton « Télécharger » de l'annonce de mise à jour : il récupère désormais directement l'installeur (.exe), au lieu d'ouvrir une page d'où l'on repartait avec un fichier non exécutable.
- Choix du navigateur : dans Réglages › « Navigateur d'ouverture », vous pouvez imposer Edge, Chrome, Firefox ou le navigateur par défaut du système (au lieu du choix automatique). Prend effet au prochain démarrage.
- Arbre en Descendance : une union sans enfant (PACS, mariage sans enfant) n'apparaît plus — elle encombrait l'arbre et « chaînait » les conjoints par erreur. La fiche Personne garde, elle, toutes les unions.

## [1.9.3](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.9.3) — 2026-07-12

- Qualité des sources : nouvelle carte « Lieux sans pays ». Elle repère les lieux qui n'indiquent pas de pays et, si vous avez défini un « Pays par défaut » (Réglages), permet de l'ajouter à tous en un clic — très pratique après avoir importé un GEDCOM d'un autre logiciel.

## [1.9.2](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.9.2) — 2026-07-12

- Barre de défilement plus jolie : fine, arrondie, dans les tons verts, qui fonce au survol — elle apparaît là où ça défile (menus, longues listes) sans encombrer. L'arbre reste sans barre (navigation au glisser).
- Un indicateur « Traitement en cours… » s'affiche pour les opérations qui prennent un peu de temps (import volumineux, géocodage…).
- Géocodage : nouveau réglage « Pays par défaut ». Il est ajouté à la recherche d'un lieu qui n'indique pas de pays — pratique si votre arbre est surtout dans un pays (ex. « Neufchâteau » cherché en Belgique, pas dans les Vosges).
- Import GEDCOM : l'Aide rappelle que les encodages UTF-8, UTF-16, ANSI (Windows-1252) et ANSEL sont détectés automatiquement.
- Correctif : l'infobulle d'une carte d'arbre sans dates n'affiche plus « nullnullnull ».

## [1.9.1](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.9.1) — 2026-07-12

- Cohérence : les personnes hors famille (officier d'état civil, témoin… cités sans lien de parenté) ne sont plus signalées comme « sans lien familial » — leur absence de lien est normale, ce n'est pas une anomalie.

## [1.9.0](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.9.0) — 2026-07-12

- Qualité des sources : le contrôle « dates douteuses » reconnaît désormais le format français JJ/MM/AAAA. Vos vraies dates (12/06/1925, etc.) ne sont plus signalées à tort — seules les dates vraiment mal formées restent listées.

## [1.8.9](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.9) — 2026-07-11

- Onglet Famille plus lisible : chaque fait d'un couple a désormais sa propre ligne, dans l'ordre — PACS, Mariage, Divorce. Un mariage ne peut plus « disparaître » derrière un PACS ou un divorce.

## [1.8.8](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.8) — 2026-07-11

- Preuves par fait, plus clair : une personne présumée vivante n'affiche plus « Décès — À prouver » (ça n'avait pas de sens), et un PACS est libellé « PACS » / « Dissolution de PACS » au lieu de « EVEN ».
- Chronologie : un couple pacsé (sans mariage) n'affiche plus de ligne « Mariage » fantôme — seul le PACS apparaît.
- Robustesse renforcée : une donnée mal formée ne peut plus abîmer une fiche, et les preuves d'une naissance ou d'un décès ne sont plus perdues lors d'une simple modification de date.

## [1.8.7](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.7) — 2026-07-11

- Personnes — on distingue d'un coup d'œil qui est de la famille : dans « Tout le monde », une pastille de couleur indique la lignée directe (ancêtres), la famille élargie (frères/sœurs, oncles, cousins, conjoints, enfants) et les personnes hors famille (officier d'état civil, témoin, partenaire cité). Un filtre « Hors famille : afficher / masquer / seules » permet de désencombrer la liste.
- PACS / union libre : on peut enregistrer un couple non marié dans l'éditeur d'union — date de début, lieu, et date de fin si l'union est terminée. La fiche affiche « en cours » ou « dissolution … (terminée) ». Conservé à l'export GEDCOM (EVEN / TYPE PACS).

## [1.8.6](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.6) — 2026-07-11

- Galerie photos repensée : cliquez une photo pour l'ouvrir en grand (zoom à la molette, déplacement, navigation ←/→, Échap pour fermer). On peut écrire une légende sous chaque photo, changer leur ordre (◀ ▶), désigner le portrait, et télécharger une photo. Vignettes plus grandes et actions au même endroit.
- Cadrage des photos : vous pouvez choisir quelle partie d'une photo apparaît dans le carré (portrait de la fiche, cartes de l'arbre, vignettes) — pratique quand un visage n'est pas centré. Le cadrage est non destructif : la photo d'origine n'est jamais modifiée.
- Le portrait en haut de la fiche se met à jour tout de suite quand on ajoute une photo, désigne un portrait ou le recadre — sans recharger.

## [1.8.5](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.5) — 2026-07-11

- Le menu des événements d'une personne est réorganisé par moment de vie (Enfance & religion · Vie civile · Décès & sépulture · Militaire · Autre) — plus facile de trouver le bon.
- Nouveaux événements standard : baptême de nourrisson, ordination, bar / bat mitzvah, et les fiançailles (sur l'union, à côté du mariage et du divorce). Tous au format GEDCOM standard, interopérables.

## [1.8.4](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.4) — 2026-07-10

- Après avoir prouvé un fait, la fiche revient sur l'onglet « Sources & preuves » (et non plus « Synthèse ») : on enchaîne les preuves sans avoir à y retourner à chaque fois.
- Deux nouveaux types de source : « Pierre tombale / sépulture » (pour une photo de tombe) et « Faire-part ».

## [1.8.3](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.3) — 2026-07-10

- La date d'une union s'affiche maintenant dans « Preuves par fait », comme la naissance et le décès (elle restait vide auparavant).
- Les événements militaires utilisent désormais le format GEDCOM standard (EVEN / TYPE), lisible par tous les logiciels de généalogie, et leur intitulé précis (« Affectation », « Prisonnier de guerre »…) apparaît dans la chronologie plutôt que « Autre événement ».

## [1.8.2](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.2) — 2026-07-10

- Correctif important : Arboriane s'ouvre désormais de préférence dans Edge ou Chrome, jamais dans Internet Explorer. Sur certaines machines, IE empêchait l'application de fonctionner et bloquait le téléchargement des mises à jour — c'est réglé.
- Nouveau filtre « par personne » dans Actes / Sources : n'afficher que les actes et sources qui citent une personne donnée.
- Petit défaut d'affichage corrigé dans le carnet : une note « À faire » montrait deux fois la même étiquette.
- Nouveau groupe d'événements « Militaire » (affectation, décoration, prisonnier de guerre, blessure, campagne, fait libre) pour retracer une carrière militaire directement sur la fiche d'une personne.

## [1.8.1](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.1) — 2026-07-10

- Les PDF joints à une source s'affichent enfin directement dans Arboriane (visionneuse du navigateur, avec un lien pour l'ouvrir en grand), au lieu d'une vignette blanche. On peut aussi déposer des PDF depuis l'interface, pas seulement des images.
- Garde-fou sur les formats de photo et de scan : un fichier que le navigateur ne sait pas afficher (HEIC — le format par défaut des iPhone —, TIFF, RAW d'appareil photo) est maintenant refusé avec un message clair (« convertissez-le en JPEG ou PNG »), au lieu de créer une image blanche silencieuse.

## [1.8.0](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.8.0) — 2026-07-10

- Le carnet de bord parle enfin avec l'arbre : une note peut désormais citer PLUSIEURS personnes, et une note de type « piste » ou « à faire » remonte automatiquement dans le plan de recherche, sous chaque personne concernée. Le carnet n'est plus un cul-de-sac.
- Chaque fiche gagne un onglet « Carnet » qui rassemble toutes les notes du carnet citant cette personne (trouvailles, réflexions, pistes…). Une case « fait / à faire » permet de sortir une piste du plan une fois traitée.
- Sur une source, vous pouvez maintenant CRÉER une personne (témoin, officier d'état civil…) et la citer directement, sans devoir la créer ailleurs au préalable.
- Correction : supprimer une personne nettoie désormais les sources qui la citaient — plus de « lien fantôme » vers quelqu'un qui n'existe plus.

## [1.7.9](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.9) — 2026-07-10

- Les dates s'affichent en français partout dans l'application (« 20/07/1984 », « vers 1850 », « entre 1850 et 1860 »), tout en étant exportées au format exact de la norme GEDCOM (« 20 JUL 1984 ») : vos fichiers sont mieux relus par les autres logiciels, sans que vous ayez jamais à voir de mois en anglais. Les arbres déjà existants sont convertis automatiquement à l'ouverture.
- Un divorce — et plus largement tout événement de couple — peut désormais être « prouvé » comme le mariage : le bouton « Prouver » et le badge « Prouvé par acte » apparaissent bien sur la frise de vie.
- L'écran « Preuves par fait » est réorganisé en tableau clair (fait, date, preuve, action), avec des libellés courts au lieu de longs textes sur plusieurs lignes.

## [1.7.8](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.8) — 2026-07-10

- Interopérabilité renforcée : les fichiers GEDCOM produits par Arboriane sont désormais pleinement conformes à la norme 5.5.1. Les titres, noms, lieux et longues valeurs sont correctement découpés — plus aucune perte de caractère quand un autre logiciel relit votre export.
- Une source qui vous revient d'un autre logiciel « aplatie » en une simple phrase (comportement de Geneanet et des sites GeneWeb) redevient une vraie source consultable, au lieu d'une citation vide.
- La note d'un dépôt d'archives n'est plus perdue lors d'un import.
- Un dépôt que vous avez saisi mais pas encore rattaché à une source figure maintenant dans l'export.
- Un fichier au format GEDCOM 7.0 s'importe toujours, mais l'application vous prévient que certaines informations récentes peuvent manquer — Arboriane lit le 5.5.1.

## [1.7.7](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.7) — 2026-07-10

- Export GEDCOM : une note longue perdait une espace à chaque coupure de ligne, lorsqu'elle était relue par un AUTRE logiciel de généalogie. Le texte est désormais transmis au caractère près.
- L'indentation d'une note (espaces en début de ligne) était écrasée à chaque import ou export. Elle est préservée.
- Arboriane est publiée sous licence libre AGPL v3 : vous pouvez l'étudier, la modifier et la partager, à condition que vos versions restent libres.

## [1.7.6](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.6) — 2026-07-10

- Correctif important : « Fusionner » un fichier GEDCOM pouvait faire disparaître des personnes. Deux homonymes sans date de naissance, ou deux personnes sans nom, étaient confondus en un seul individu. Sur un arbre de 501 personnes, 81 s'évanouissaient en silence. Une personne n'est désormais rapprochée d'une autre que si son nom ET son année de naissance concordent.
- Correctif important : « Fusionner » supprimait les familles dont un seul époux est connu, même lorsqu'elles portent une date de mariage. Sur un grand arbre, cela effaçait des centaines d'unions.
- Les deux modes d'import, « Remplacer » et « Fusionner », donnent enfin exactement le même arbre — vérifié sur 26 fichiers réels produits par d'autres logiciels de généalogie.
- Chaque publication est désormais vérifiée automatiquement avant d'être mise en ligne, et l'empreinte SHA-256 de l'installateur est publiée : vous pouvez contrôler que le fichier téléchargé est bien le nôtre.

## [1.7.5](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.5) — 2026-07-10

- Correctif important, signalé par un utilisateur : « Fusionner » un fichier GEDCOM importait bien les personnes mais AUCUN lien de parenté. Père, mère, conjoint et enfants restaient vides, et l'arbre se réduisait à une seule personne. Les familles sont désormais reprises, sans dupliquer un couple déjà présent.
- Un remariage du même couple reste bien deux unions distinctes, avec leurs deux dates de mariage.
- Import GEDCOM plus robuste : les liens sont lus quelle que soit la mise en forme du fichier, et reconstruits même quand un enregistrement de famille est incomplet.
- Si un import ne parvient à lire aucun lien de parenté, l'application le dit clairement au lieu d'annoncer une réussite trompeuse.

## [1.7.4](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.4) — 2026-07-09

- Nouvelle source : on indique désormais QUI l'acte concerne dès la création (l'enfant et ses parents, tout un foyer au recensement, les témoins…). Jusqu'ici, relier une personne n'était possible qu'après coup.
- Le titre d'une source n'est plus à inventer : il se construit tout seul à partir du type d'acte, des personnes, de la date et du lieu — « Acte de naissance — Jean DUPONT — 12/03/1902 — Lyon, Rhône » — et reste modifiable à volonté.
- Vos scans peuvent être renommés « 1902-03-12_N_DUPONT-Jean_Lyon.jpg » : rangés par date dans l'explorateur Windows, lisibles d'un coup d'œil. Proposé, décochable, jamais imposé.
- Si Arboriane s'arrête (fenêtre de lancement fermée, mise en veille), la page vous le dit clairement au lieu de rester muette. La fenêtre de lancement rappelle qu'elle fait tourner le logiciel.
- Plan de recherche : les pistes sont mieux formulées (« Trouver l'acte de mariage » et non « l'acte de union »), et les lieux gardent leurs majuscules.

## [1.7.3](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.3) — 2026-07-09

- Correctif important : ajouter « ＋ Père » puis « ＋ Mère » créait une union fantôme (« conjoint·e inconnu·e ») sur le père. Les deux parents rejoignent désormais la même famille.
- Nouveau : MODIFIER UNE UNION. Depuis l'onglet Famille d'une fiche, saisissez enfin la date et le lieu du mariage — et le DIVORCE. Le divorce apparaît dans la chronologie, dans les repères de vie, et voyage en GEDCOM (balise DIV). Les preuves du mariage sont préservées.
- Le résumé de vie mentionne désormais les unions, le divorce et le nombre d'enfants (« mariée en 2000 à Lyon avec…, mère de 3 enfants »).
- Livre : un avertissement indique combien de personnes vivantes seront masquées — fini le livre étrangement vide sur une famille bien vivante.
- La première personne d'un arbre neuf (ou d'un GEDCOM importé) devient automatiquement la racine (Sosa 1) — et supprimer la personne racine ne rend plus l'écran Sosa muet : une autre personne prend le relais. Statistique « enfants par couple » corrigée (elle comptait par parent).
- La question « vérifier les mises à jour ? » ne barre plus l'écran de bienvenue : c'est un bandeau discret, qui décale la page au lieu de masquer l'en-tête. Vouvoiement harmonisé dans toute l'application.

## [1.7.2](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.2) — 2026-07-09

- Sourçage — une preuve, plusieurs personnes : « Prouver » relie désormais la même source à toutes les personnes qu'elle cite. Un acte de naissance se rattache à l'enfant ET à ses parents (proposés automatiquement) ; un recensement à tout le foyer. Une union reste prouvée pour les deux conjoint·es d'un seul geste.
- « Relier une source existante » devient une RECHERCHE par titre (fini le long menu déroulant) — pratique même avec des milliers de sources.
- Compteur « non reliées » corrigé : une source qui prouve un fait n'est plus comptée comme orpheline, et les preuves sans scan sont signalées avec un raccourci vers « Toutes les sources ».
- Recherche web : liens réparés (Filae), lien mort retiré (Géopatronyme), ajout de Gallica (BnF). Et une preuve d'union se pose sur la bonne union en cas de remariage.

## [1.7.1](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.1) — 2026-07-09

- Ajout d'un proche repensé : un seul écran, la fiche COMPLÈTE (comme « Nouvelle personne »), avec en tête un « Lien de parenté » — père, mère, conjoint·e, enfant, et désormais frère / sœur. Le lien est pré-rempli selon le bouton d'où l'on vient, ou « à déterminer » depuis « Nouvelle personne ». On peut créer une personne complète OU relier quelqu'un déjà dans l'arbre, toujours avec un bouton « Retour ».
- Correctif important sur les unions : une conjointe ajoutée apparaît désormais des DEUX côtés (fini l'union visible chez l'un mais pas chez l'autre), et les enfants ne partent plus dans une union fantôme « conjoint·e inconnu·e ».
- Le bouton « ＋ enfant » d'une union rattache l'enfant à CETTE union. Quand une personne a plusieurs unions, on choisit désormais à laquelle rattacher l'enfant (ou une nouvelle union, autre parent inconnu).
- La synthèse « Repères de vie » affiche toutes les unions, pas seulement la première. Réparation automatique des liens familiaux à chaque modification (robustesse des arbres importés).

## [1.7.0](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.7.0) — 2026-07-09

- Sourcer TOUS les faits (pas seulement naissance/mariage/décès) : un bouton « Prouver » sur chaque ligne de « Vie & chronologie » — résidences, professions, événements (décorations…) — avec un indice de fiabilité.
- « Prouver » ouvre le vrai formulaire de source détaillé (dépôt, cote, lien, pièces jointes, transcription) : source existante ou créée sur place, reliée au fait en un clic. Fini le détour obligatoire par « Actes / Sources ».
- Pièces jointes : les PDF et TIFF sont désormais acceptés (en plus des images).
- Ajouter un proche ou prouver un fait s'ouvre en plein écran, avec un bouton « ← Retour à la fiche ».

## [1.6.9](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.9) — 2026-07-09

- Heure de naissance et de décès : un champ « heure » facultatif sur la fiche (ex. « né le 12 mars 1902 à 14:30 »). Pratique pour l'état civil moderne qui mentionne l'heure. Conservée à l'export et à l'import GEDCOM.

## [1.6.8](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.8) — 2026-07-09

- Ajouter un PARENT depuis une fiche : les boutons « ＋ Père » et « ＋ Mère » manquaient. On peut de nouveau remonter sa généalogie — créer un parent ou relier une personne existante — directement depuis la fiche et la cellule familiale.
- Nouvel audit « Présumés vivants trop âgés » (Qualité des sources) : repère les personnes sans date de décès trop âgées pour être en vie (âge déduit de leurs enfants/unions) et permet de les marquer décédées d'un clic, sans jamais inventer de date.
- Optimisation : le plan de recherche ne calcule plus deux fois les mêmes preuves — plus rapide sur les grands arbres.

## [1.6.7](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.7) — 2026-07-09

- Multi-ordinateurs, à la demande : rangez un arbre dans un dossier synchronisé (OneDrive, Google Drive, Dropbox, iCloud) et retrouvez-le sur vos autres ordinateurs — Arboriane reste 100 % local, sans compte.
- Garde-fou « un seul ordinateur à la fois » : Arboriane prévient si un arbre semble déjà ouvert ailleurs, et rappelle la règle d'or.
- Nouvelle aide « Sur plusieurs ordinateurs » et badge « ☁ synchronisé » sur les arbres rangés dans un cloud.

## [1.6.6](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.6) — 2026-07-09

- Parcours plus clair : un onglet qui a besoin d'un arbre vous ramène à l'accueil (qui vous guide) au lieu d'un message obscur.
- Aide enrichie : nouvelles fiches « Composer un livre », « Restaurer une sauvegarde », « Fusionner des doublons », « Les dépôts », « Calendrier républicain » et « Mises à jour ».
- Plus d'explications sur place (statuts d'acte lisibles, cote, dates, confidentialité, statut de vie…) et messages d'erreur plus clairs.

## [1.6.5](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.5) — 2026-07-09

- Fini les encarts « fantômes » (Arbre vide…) qui se superposaient au tableau de bord après un changement rapide d'onglet.

## [1.6.4](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.4) — 2026-07-09

- Import fusionnant : plus de liens d'association erronés ; dates du calendrier républicain conservées aussi sur les événements (baptême…).
- Fiabilité : suppression d'un arbre plus sûre, fiche personne sans affichage périmé au changement rapide d'onglet.

## [1.6.3](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.3) — 2026-07-09

- Import fusionnant : les actes de naissance et de décès ne sont plus perdus.
- Sauvegarde de sécurité toujours faite avant un « Remplacer tout l'arbre ».
- Petites finitions de fiabilité et d'accessibilité.

## [1.6.2](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.2) — 2026-07-09

- Livres : « Lire en ligne » et « Aperçu imprimable » s'ouvrent de nouveau (la fenêtre n'est plus bloquée comme pop-up par le navigateur).

## [1.6.1](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.1) — 2026-07-09

- Correctifs Livres : la création d'un livre fonctionne de nouveau, rendu plus robuste (photos, masquage des vivants, préface).
- Corrections de fond : couples de même sexe, filiation, sélecteurs de fichiers Windows, et divers points de fiabilité (audit complet).

## [1.6.0](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.6.0) — 2026-07-09

- Nouveau : les LIVRES biographiques ! Composez un livre à imprimer ou à offrir (menu Composer › Livres).
- Récit de vie, aïeux (Sosa) et descendance (d'Aboville), chronologie, album photos et index — 3 modèles au choix (Héritage, Épuré, Sépia), A4 ou A5.
- Lecture en ligne ou impression : un seul fichier, 100 % local, à envoyer par mail.

## [1.5.8](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.5.8) — 2026-07-09

- Passe qualité (audit complet) : robustesse, sécurité et fidélité renforcées.
- Import GEDCOM plus sûr (liens et sources réalignés, dates républicaines conservées).
- Confirmation avant « Remplacer tout l'arbre » et protection contre la double création.

## [1.5.7](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.5.7) — 2026-07-09

- Nouveau : « Restaurer une sauvegarde » — recharge un arbre complet (.zip, scans compris) via une fenêtre Windows, sans limite de taille.
- L'import d'un gros fichier ne fait plus planter la page : il propose la restauration.

## [1.5.6](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.5.6) — 2026-07-09

- « Quoi de neuf » à l'ouverture après chaque mise à jour.
- Vérification facultative des mises à jour (proposée une fois, réglable).

## [1.5.5](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.5.5) — 2026-07-09

- Arbre de démonstration enrichi (~100 personnes sur 12 générations).
- Installeur : choix du dossier, message de mise à jour, données conservées.

## [1.5.4](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.5.4) — 2026-07-08

- Le bouton « Prouver » fonctionne pour le fait Union.
- Lien de téléchargement stable d'une version à l'autre.

## [1.5.3](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.5.3) — 2026-07-08

- Ajout d'un enfant possible sans passer par un conjoint.
- Messages d'erreur plus clairs et avec la marche à suivre.

## [1.5.2](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.5.2) — 2026-07-08

- Repli automatique si le dossier Documents est protégé par Windows.

## [1.5.1](https://github.com/sophiegarguilo-star/arboriane/releases/tag/v1.5.1) — 2026-07-08

- Charte graphique harmonisée ; mosaïque d'arbre en A3 et A0.
