// Onglet « Aide & Tutoriels » + pages légales.
// Une vue autonome : sommaire à gauche, rubrique à droite, recherche par
// mot-clé. `arg` peut être une clé de rubrique pour l'ouvrir directement
// depuis un autre onglet, ex. aller("aide", "premiers-pas").
import { h, vider, echapper } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet } from "../noyau/api.js";

const CONTACT = "arboriane.app@gmail.com";
let histoireDemo = "";   // résumé de la famille de démo (chargé à l'ouverture)

/* ── Encarts réutilisables ─────────────────────────────────────────────
   encart("attention"|"astuce"|"aretenir", contenu…) — bordure + fond doux. */
const ICONE_ENCART = { attention: "⚠", astuce: "💡", aretenir: "📌" };
const TITRE_ENCART = { attention: "Attention", astuce: "Astuce", aretenir: "À retenir" };

export function encart(genre, ...contenu) {
  return h("div", { class: "encart " + genre, role: "note" },
    h("div", { class: "encart-tete" },
      h("span", { class: "encart-ico", "aria-hidden": "true" }, ICONE_ENCART[genre] || "•"),
      h("span", { class: "encart-titre" }, TITRE_ENCART[genre] || "Note")),
    h("div", { class: "encart-corps" }, ...contenu));
}

/* Un bouton « Aller à l'onglet X » sous un tutoriel. */
function versOnglet(nom, libelle, arg) {
  return h("div", { class: "aide-cta" },
    h("button", { class: "bouton petit", onclick: () => aller(nom, arg) }, libelle));
}

/* Liste d'étapes numérotées : etapes(["…", "…"]) ou avec nœuds. */
function etapes(items) {
  return h("ol", { class: "aide-etapes" },
    ...items.map((it) => h("li", {}, it)));
}

/* Titre de section interne à une rubrique. */
function bloc(titre, ...contenu) {
  return h("section", { class: "aide-bloc" },
    titre ? h("h3", {}, titre) : null, ...contenu);
}

function p(...c) { return h("p", {}, ...c); }
function fort(t) { return h("strong", {}, t); }

// Numéro de version : lu depuis le backend (source unique core/version.py),
// jamais recopié en dur — évite la dérive entre l'exe, l'installeur et l'aide.
function spanVersion() {
  const s = h("span", {}, "…");
  apiGet("/api/version").then(d => { if (d && d.version) s.textContent = d.version; })
    .catch(() => { s.textContent = ""; });
  return s;
}

// Légende des codes de nomenclature : lue depuis le backend (source unique
// services/taxonomie_actes.py), rendue en tableau. Reste synchro avec la
// taxonomie sans recopier la liste dans l'aide.
function tableauLegende() {
  const conteneur = h("div", { class: "aide-legende" }, h("p", {}, "Chargement de la légende…"));
  apiGet("/api/nomenclature/legende").then((d) => {
    vider(conteneur);
    const rows = (d && d.entrees) || [];
    if (!rows.length) { conteneur.append(h("p", {}, "Légende indisponible.")); return; }
    conteneur.append(h("table", { class: "aide-table" },
      h("thead", {}, h("tr", {}, h("th", {}, "Code"), h("th", {}, "Type de document"))),
      h("tbody", {}, ...rows.map((e) =>
        h("tr", {},
          h("td", {}, h("code", {}, e.code)),
          h("td", {}, (e.types || []).join(" / ")))))));
  }).catch(() => { vider(conteneur); conteneur.append(h("p", {}, "Légende indisponible.")); });
  return conteneur;
}

/* ══════════════════════════════════════════════════════════════════════
   RUBRIQUES. Chaque rubrique : { cle, titre, groupe, mots, rendu() }.
   `mots` alimente la recherche ; `rendu` construit le contenu à la volée.
   ══════════════════════════════════════════════════════════════════════ */
const RUBRIQUES = [
  // ── Accueil de l'aide ────────────────────────────────────────────────
  {
    cle: "accueil", groupe: "Découvrir", titre: "Bienvenue dans l'aide",
    mots: "aide bienvenue commencer sommaire présentation atelier",
    rendu: () => [
      p("Arboriane est un atelier ", fort("local"), " de généalogie sourcée. "
        + "Vous y transformez vos documents en preuves, vos preuves en faits, "
        + "et vos faits en histoire familiale — sans jamais rien publier par défaut."),
      encart("aretenir",
        "Un principe fondateur : ", fort("un arbre = un dossier"), " sur votre "
        + "ordinateur. Tout reste en fichiers lisibles, vous gardez la main."),
      bloc("Par où commencer ?",
        p("Selon votre situation :"),
        etapes([
          h("span", {}, fort("Vous partez de zéro"), " : créez un arbre vide puis "
            + "saisissez votre première personne."),
          h("span", {}, fort("Vous avez déjà un arbre"), " ailleurs (Geneanet, "
            + "Heredis, MyHeritage…) : importez son fichier GEDCOM."),
          h("span", {}, fort("Vous voulez juste explorer"), " : ouvrez l'arbre de "
            + "démonstration, sans aucun risque pour vos données."),
        ])),
      h("div", { class: "aide-cta" },
        h("button", { class: "bouton petit", onclick: () => aller("espace") }, "Espace de travail"),
        h("button", { class: "bouton secondaire petit", onclick: () => aller("accueil") }, "Tableau de bord")),
      encart("astuce", "Perdu·e ? Le champ de recherche en haut du sommaire filtre "
        + "toutes les rubriques par mot-clé (ex. « source », « GEDCOM », « vivants »)."),
      p(fort("Arboriane — version "), spanVersion(),
        " · atelier de généalogie 100 % local · contact : arboriane.app@gmail.com"),
    ],
  },

  // ── L'arbre de démonstration ─────────────────────────────────────────
  {
    cle: "demo-histoire", groupe: "Découvrir", titre: "L'arbre de démonstration",
    mots: "démo démonstration exemple famille histoire martin whitaker fictif test sosa",
    rendu: () => [
      p("L'arbre de démonstration est une famille ", fort("100 % fictive"),
        " — les MARTIN du Val de Loire, avec une branche anglaise — prévue pour "
        + "découvrir toutes les fonctions d'Arboriane sans jamais toucher à vos données."),
      encart("astuce", "Ouvrez-le depuis l'Espace de travail. Vos arbres réels sont "
        + "rangés dans d'autres dossiers et ne sont jamais modifiés par la démo."),
      bloc("L'histoire de cette famille",
        h("div", { class: "aide-histoire",
          style: "white-space:pre-wrap;font-size:14px;line-height:1.55" },
          histoireDemo || "Ouvrez d'abord un arbre pour afficher son histoire.")),
      h("div", { class: "aide-cta" },
        h("button", { class: "bouton petit", onclick: () => aller("espace") },
          "Ouvrir la démonstration")),
    ],
  },

  // ── Soutenir Arboriane ───────────────────────────────────────────────
  {
    cle: "soutenir", groupe: "Découvrir", titre: "Soutenir Arboriane",
    mots: "soutenir don café coffee gratuit merci financer aider contribuer buymeacoffee",
    rendu: () => [
      h("a", { href: "https://buymeacoffee.com/arborianea5", target: "_blank",
        rel: "noopener noreferrer", class: "accueil-banniere",
        title: "Offrir un café ☕" },
        h("img", { src: "/banniere-arboriane.png",
          alt: "Arboriane — le logiciel de généalogie gratuit, local et sourcé" })),
      p("Arboriane est ", fort("gratuit"), ", 100 % local et sans publicité. "
        + "Si l'outil vous rend service, vous pouvez soutenir son développement "
        + "en m'offrant un café — c'est facultatif, mais ça fait chaud au cœur."),
      h("div", { class: "aide-cta" },
        h("a", { class: "bouton petit", href: "https://buymeacoffee.com/arborianea5",
          target: "_blank", rel: "noopener noreferrer" }, "☕ Offrir un café")),
      encart("aretenir", "Chaque contribution encourage le développement et aide "
        + "à couvrir les outils qui le rendent possible — merci du fond du cœur à "
        + "celles et ceux qui participent."),
    ],
  },

  // ── Premiers pas ─────────────────────────────────────────────────────
  {
    cle: "premiers-pas", groupe: "Découvrir", titre: "Premiers pas",
    mots: "premiers pas débuter créer ouvrir arbre dossier gedcom importer commencer",
    rendu: () => [
      p("Trois gestes suffisent pour démarrer : ouvrir un arbre, comprendre qu'un "
        + "arbre est un dossier, et — si besoin — importer un GEDCOM existant."),
      bloc("1. Créer ou ouvrir un arbre",
        etapes([
          "Ouvrez l'onglet « Espace de travail ».",
          "Cliquez sur « Créer un nouvel arbre » et donnez-lui un nom, "
            + "ou « Ouvrir » sur un arbre déjà présent dans la liste.",
          "L'arbre ouvert devient l'arbre actif : tous les autres onglets "
            + "travaillent dessus.",
        ]),
        versOnglet("espace", "Ouvrir l'espace de travail")),
      bloc("2. Un arbre = un dossier",
        p("Chaque arbre vit dans son propre dossier, avec ses personnes, ses "
          + "sources, ses images et son carnet. Rien n'est mélangé entre deux arbres."),
        encart("astuce", "Pour sauvegarder ou déplacer un arbre, il suffit de copier "
          + "son dossier. Aucune base cachée, aucun compte en ligne.")),
      bloc("3. Importer un GEDCOM (facultatif)",
        p("Si vous venez d'un autre logiciel, exportez-y un fichier ", fort(".ged"),
          " puis importez-le dans Arboriane depuis l'onglet Sauvegarde et export."),
        versOnglet("donnees", "Ouvrir Sauvegarde et export")),
    ],
  },
  {
    cle: "quoi-de-neuf", groupe: "Découvrir", titre: "Mises à jour & « Quoi de neuf »",
    mots: "mise à jour maj version quoi de neuf nouveautés changelog mettre à jour installer notes évolution",
    rendu: () => [
      p("À chaque nouvelle version, Arboriane affiche un court « Quoi de neuf » au "
        + "démarrage pour vous montrer ce qui a changé. ", fort("Une mise à jour "
        + "remplace le programme, pas vos arbres"), " : ceux-ci restent dans leurs "
        + "dossiers, intacts."),
      bloc("Vérifier les mises à jour",
        p("La vérification en ligne est ", fort("facultative"), " et se règle dans "
          + "les Réglages. Quand elle est active, Arboriane lit simplement le numéro "
          + "de la dernière version publiée — aucune donnée personnelle n'est envoyée."),
        versOnglet("reglages", "Ouvrir les Réglages")),
    ],
  },

  // ── Tutoriels ────────────────────────────────────────────────────────
  {
    cle: "tuto-arbre", groupe: "Tutoriels", titre: "Créer ou ouvrir un arbre",
    mots: "créer ouvrir arbre nouveau dossier espace travail",
    rendu: () => [
      etapes([
        "Onglet « Espace de travail ».",
        "« Créer un nouvel arbre » → saisissez un nom → validez.",
        "Pour rouvrir un arbre existant, cliquez « Ouvrir » sur sa carte.",
      ]),
      encart("aretenir", "L'arbre actif est signalé par le badge « Actif ». "
        + "Un seul arbre est ouvert à la fois."),
      versOnglet("espace", "Aller à l'espace de travail"),
    ],
  },
  {
    cle: "tuto-gedcom", groupe: "Tutoriels", titre: "Importer un GEDCOM",
    mots: "gedcom import importer ged geneanet heredis myheritage fichier transfert",
    rendu: () => [
      p("Le GEDCOM est le format d'échange universel de la généalogie. Il permet "
        + "de récupérer un arbre construit dans un autre logiciel."),
      etapes([
        "Dans votre ancien logiciel, exportez un fichier GEDCOM (.ged).",
        "Dans Arboriane, ouvrez « Sauvegarde et export ».",
        "Choisissez « Importer un GEDCOM » et sélectionnez le fichier.",
        "Vérifiez ensuite la cohérence de l'arbre importé.",
      ]),
      encart("attention", "Un import ajoute des personnes à l'arbre actif. "
        + "Créez d'abord un arbre neuf pour ne pas mélanger deux généalogies."),
      encart("astuce", "Arboriane détecte automatiquement l'encodage du fichier "
        + "(balise « 1 CHAR » et BOM) : UTF-8, UTF-16, ANSI (Windows-1252) et "
        + "ANSEL sont pris en charge — les accents sont préservés."),
      versOnglet("donnees", "Importer un GEDCOM"),
    ],
  },
  {
    cle: "tuto-un-dossier", groupe: "Tutoriels", titre: "Un arbre = un dossier",
    mots: "dossier fichier arbre local sauvegarde copie déplacer emplacement",
    rendu: () => [
      p("Comprendre ce principe rend les sauvegardes et déplacements triviaux."),
      etapes([
        "Chaque arbre = un dossier sur votre disque (personnes, sources, images, carnet).",
        "Sauvegarder = copier ce dossier (ou créer une archive .zip).",
        "Déplacer sur un autre ordinateur = copier le dossier, puis « Ouvrir ».",
      ]),
      encart("astuce", "Le chemin exact du dossier est affiché sous chaque arbre "
        + "dans l'espace de travail."),
      versOnglet("espace", "Voir mes dossiers d'arbres"),
    ],
  },
  {
    cle: "tuto-personne", groupe: "Tutoriels", titre: "Créer une personne",
    mots: "créer personne individu fiche nom prénom naissance saisir ajouter",
    rendu: () => [
      etapes([
        "Onglet « Personnes ».",
        "« Nouvelle personne » → renseignez au minimum un nom.",
        "Ajoutez ensuite les faits connus : naissance, décès, profession…",
        "Enregistrez : la fiche est créée et reliable au reste de l'arbre.",
      ]),
      encart("astuce", "Saisissez d'abord ce qui est ", fort("certain"), ". "
        + "Une date approximative peut attendre une source qui la confirme."),
      versOnglet("personnes", "Créer une personne", { creer: true }),
    ],
  },
  {
    cle: "tuto-famille", groupe: "Tutoriels", titre: "Relier une famille",
    mots: "relier famille parents enfants conjoint union mariage lien relation",
    rendu: () => [
      p("Une fois deux personnes créées, reliez-les pour bâtir l'arbre."),
      etapes([
        "Ouvrez la fiche d'une personne.",
        "Dans les relations, ajoutez un parent, un conjoint ou un enfant.",
        "Choisissez une personne existante, ou créez-la à la volée.",
      ]),
      encart("aretenir", "Un lien est réciproque : ajouter un enfant à un parent "
        + "crée aussi le lien parent chez l'enfant."),
      versOnglet("personnes", "Aller aux personnes"),
    ],
  },
  {
    cle: "tuto-photos", groupe: "Tutoriels", titre: "Ajouter des photos",
    mots: "photo photos portrait image illustrer médias personne",
    rendu: () => [
      etapes([
        "Ouvrez la fiche de la personne concernée.",
        "Dans la section médias, ajoutez une ou plusieurs photos.",
        "Les images sont copiées dans le dossier de l'arbre.",
      ]),
      encart("attention", "Une photo illustre une personne ; elle ne ", fort("prouve"),
        " pas un fait. Pour prouver, ajoutez plutôt une source (voir plus bas)."),
      versOnglet("personnes", "Aller aux personnes"),
    ],
  },
  {
    cle: "tuto-source", groupe: "Tutoriels", titre: "Ajouter une source",
    mots: "source ajouter registre acte relevé preuve citation référence documentaire",
    rendu: () => [
      p("Une source est un document (registre, acte, relevé) qui atteste vos faits."),
      etapes([
        "Onglet « Actes / Sources ».",
        "« Nouvelle source » → décrivez-la (type, cote, date, dépôt…).",
        "Reliez-la aux personnes et aux faits qu'elle prouve.",
      ]),
      encart("aretenir", "Idéal : ", fort("chaque fait renvoie à au moins une source"),
        ". C'est ce qui distingue une généalogie sérieuse d'une simple liste de noms."),
      versOnglet("actes", "Ajouter une source"),
    ],
  },
  {
    cle: "tuto-acte-image", groupe: "Tutoriels", titre: "Ajouter l'image d'un acte",
    mots: "acte image scan photo registre numérisation document pièce jointe joindre",
    rendu: () => [
      etapes([
        "Onglet « Actes / Sources », sous-vue « Documents & actes ».",
        "Ouvrez (ou créez) la source correspondante.",
        "Joignez le scan ou la photo de l'acte : il est copié dans le dossier.",
      ]),
      encart("attention", "Vérifiez vos ", fort("droits de diffusion"), " avant de "
        + "publier l'image d'un acte : certains dépôts d'archives limitent la "
        + "rediffusion de leurs reproductions."),
      versOnglet("actes", "Aller aux actes"),
    ],
  },
  {
    cle: "tuto-nomenclature", groupe: "Tutoriels", titre: "Comment vos pièces sont nommées",
    mots: "nom fichier scan renommer rangement ranger code nomenclature tri chronologique "
      + "légende date explorateur indexation abréviation",
    rendu: () => [
      p("Quand vous « rangez les pièces », Arboriane renomme chaque scan avec un nom "
        + "triable : la date en tête, un code de type, la ou les personnes, la ville, et "
        + "un éventuel repère de la vue (qualité, page, mention)."),
      bloc("Format du nom",
        h("pre", { class: "aide-mono" }, "<date>_<CODE>_<NOM-Prénom>_<Ville>[_<variante>].jpg"),
        p("Exemple : ", h("code", {},
          "1866_M_AMBROSINO-Michel-et-REFUTO-Marie_Procida_ameliore.jpg"))),
      encart("astuce", "La date en tête (année-mois-jour) fait que l'Explorateur range "
        + "vos actes ", fort("dans l'ordre chronologique"), " tout seul."),
      encart("aretenir", "Le ", fort("titre"), " de la source, lui, reste lisible et "
        + "n'est pas modifié : le code sert au rangement des fichiers, pas à la lecture."),
      bloc("Légende des codes", tableauLegende()),
      encart("astuce", "Cette légende est aussi écrite dans le fichier ",
        fort("Sources\\_LEGENDE-codes.txt"), " de votre arbre, pour l'avoir sous la main "
        + "dans l'explorateur."),
      versOnglet("actes", "Aller aux actes"),
    ],
  },
  {
    cle: "tuto-transcription", groupe: "Tutoriels", titre: "Corriger une transcription",
    mots: "transcription corriger texte lire déchiffrer acte relire ocr paléographie",
    rendu: () => [
      p("La transcription est votre lecture du document. La corriger fiabilise "
        + "tout ce qui en découle."),
      etapes([
        "Ouvrez la source portant l'image de l'acte.",
        "Modifiez le champ de transcription en regard du scan.",
        "Enregistrez : les faits qui s'y appuient restent liés.",
      ]),
      encart("astuce", "Notez les mots douteux entre crochets, ex. [Marguerite ?]. "
        + "Vous saurez d'un coup d'œil ce qui reste à vérifier."),
      versOnglet("actes", "Aller aux actes"),
    ],
  },
  {
    cle: "tuto-source-vs-piste", groupe: "Tutoriels", titre: "Source ou piste ?",
    mots: "source piste différence preuve recherche à faire hypothèse distinction",
    rendu: () => [
      p("Deux notions à ne pas confondre :"),
      h("ul", { class: "aide-liste" },
        h("li", {}, fort("Source"), " : un document qui ", fort("prouve"),
          " un fait déjà établi (un acte, un relevé)."),
        h("li", {}, fort("Piste"), " : une recherche ", fort("à faire"),
          ", une hypothèse non encore prouvée (« vérifier le mariage vers 1830 »).")),
      encart("aretenir", "Une piste devient une source quand vous trouvez le "
        + "document qui la confirme — ou se referme quand vous concluez."),
    ],
  },
  {
    cle: "tuto-carnet", groupe: "Tutoriels", titre: "Utiliser le carnet",
    mots: "carnet notes journal recherche piste noter consigner brouillon",
    rendu: () => [
      p("Le carnet est votre journal de recherche : notes, hypothèses, pistes, "
        + "impasses. Il vit dans le dossier de l'arbre."),
      etapes([
        "Ouvrez l'onglet « Carnet de bord ».",
        "Consignez ce que vous cherchez, où, et ce que vous avez trouvé.",
        "Datez vos entrées pour retrouver votre cheminement plus tard.",
      ]),
      encart("astuce", "Tenez le carnet ", fort("même quand vous ne trouvez rien"),
        ". Savoir qu'un registre a déjà été dépouillé sans succès vous fait "
        + "gagner des heures la fois suivante."),
      versOnglet("carnet", "Ouvrir le carnet de bord"),
    ],
  },
  {
    cle: "tuto-piste", groupe: "Tutoriels", titre: "Suivre une piste",
    mots: "piste suivre recherche hypothèse vérifier avancer résoudre conclure",
    rendu: () => [
      etapes([
        "Ouvrez une piste depuis la personne concernée ou le carnet.",
        "Notez l'action prévue (registre à consulter, hypothèse à tester).",
        "Une fois le document trouvé, créez la source correspondante.",
        "Concluez la piste : confirmée, infirmée, ou en attente.",
      ]),
      encart("aretenir", "Une piste confirmée doit toujours aboutir à une "
        + "source liée au fait — c'est la trace de la preuve."),
    ],
  },
  {
    cle: "tuto-coherence", groupe: "Tutoriels", titre: "Vérifier la cohérence",
    mots: "cohérence vérifier contrôle anomalie erreur date impossible incohérence qualité",
    rendu: () => [
      p("Le contrôle de cohérence repère les anomalies : dates impossibles, "
        + "parent plus jeune que l'enfant, décès avant naissance, etc."),
      etapes([
        "Ouvrez l'onglet « Cohérence ».",
        "Parcourez les anomalies signalées, de la plus grave à la plus légère.",
        "Cliquez une anomalie pour ouvrir la fiche concernée et corriger.",
      ]),
      encart("astuce", "Lancez un contrôle après chaque gros import GEDCOM : "
        + "c'est là que les erreurs se glissent le plus souvent."),
      versOnglet("coherence", "Vérifier la cohérence"),
    ],
  },
  {
    cle: "tuto-archiver", groupe: "Tutoriels", titre: "Archiver, supprimer, réimporter un arbre",
    mots: "archiver supprimer retirer réimporter oublier restaurer zip archive effacer",
    rendu: () => [
      p("Depuis l'espace de travail, chaque arbre porte ses propres actions :"),
      h("ul", { class: "aide-liste" },
        h("li", {}, fort("Retirer"), " : sort l'arbre de la liste sans effacer le "
          + "dossier. Vous pourrez le rouvrir plus tard."),
        h("li", {}, fort("Supprimer"), " : efface le dossier. Une archive .zip de "
          + "sécurité est déposée juste avant l'effacement."),
        h("li", {}, fort("Sauvegarde"), " : crée à tout moment une archive .zip "
          + "complète de l'arbre actif.")),
      encart("attention", "La suppression est définitive une fois l'archive de "
        + "sécurité écartée. Conservez-la si vous n'êtes pas certain·e."),
      versOnglet("espace", "Gérer mes arbres"),
    ],
  },
  {
    cle: "restaurer", groupe: "Tutoriels", titre: "Restaurer une sauvegarde",
    mots: "restaurer restauration sauvegarde zip récupérer remettre changer ordinateur perdu importer archive rétablir récupération",
    rendu: () => [
      p("Vous avez une archive .zip (créée depuis l'espace de travail) et vous "
        + "voulez la remettre — après une perte de données, ou sur un nouvel "
        + "ordinateur. Deux chemins, selon votre fichier :"),
      h("ul", { class: "aide-liste" },
        h("li", {}, fort("♻️ Restaurer une sauvegarde"), " : pour une sauvegarde "
          + "COMPLÈTE (scans et photos compris), même très lourde. Le fichier est "
          + "traité directement par Arboriane, sans passer par le navigateur — "
          + "c'est la méthode recommandée."),
        h("li", {}, fort("📥 Importer un arbre (.zip)"), " : pour un petit fichier "
          + "d'échange léger, sans gros médias.")),
      etapes([
        "Ouvrez l'onglet « Espace de travail ».",
        "Cliquez « ♻️ Restaurer une sauvegarde » et choisissez votre fichier .zip "
          + "dans la fenêtre Windows.",
        "L'arbre restauré s'ouvre tout seul.",
      ]),
      encart("aretenir", "La restauration crée un nouvel arbre à partir de "
        + "l'archive : elle n'écrase aucun arbre existant."),
      versOnglet("espace", "Aller à l'espace de travail"),
    ],
  },
  {
    cle: "tuto-livre", groupe: "Tutoriels", titre: "Composer un livre",
    mots: "livre livres composer biographie récit ascendance descendance imprimer offrir album composition aïeux héritage épuré sépia a4 a5",
    rendu: () => [
      p("Arboriane assemble une ", fort("histoire familiale à imprimer ou à offrir"),
        " à partir de vos données : récit de vie, aïeux (Sosa), descendance "
        + "(d'Aboville), chronologie, album photos et index."),
      etapes([
        "Ouvrez l'onglet « Livres » (groupe Composer).",
        "Créez un livre et choisissez la personne de départ.",
        "Choisissez un modèle (Héritage, Épuré, Sépia) et le format (A4 ou A5).",
        "Prévisualisez, puis lisez en ligne ou imprimez.",
      ]),
      encart("astuce", "Tout se fabrique sur votre ordinateur : le livre est un "
        + "seul fichier, que vous pouvez envoyer par mail ou faire imprimer."),
      versOnglet("livres", "Composer un livre"),
    ],
  },
  {
    cle: "tuto-fusion", groupe: "Tutoriels", titre: "Fusionner des doublons",
    mots: "fusion fusionner doublon doublons dédoublonner même personne lieu regrouper assistée réunir",
    rendu: () => [
      p("Après un import, la même personne (ou le même lieu) peut apparaître en "
        + "double. La fusion assistée réunit ces doublons en une seule fiche, "
        + "sans rien perdre."),
      etapes([
        "Ouvrez l'onglet « Fusion assistée ».",
        "Arboriane propose les doublons probables (noms et dates proches).",
        "Vérifiez chaque paire, puis fusionnez celles qui sont bien la même personne.",
      ]),
      encart("attention", fort("Vérifiez toujours avant de fusionner"), " : une "
        + "fusion réunit deux fiches définitivement. Dans le doute, sauvegardez d'abord."),
      versOnglet("fusion", "Aller à la fusion assistée"),
    ],
  },
  {
    cle: "tuto-depots", groupe: "Tutoriels", titre: "Les dépôts (où sont conservés les actes)",
    mots: "dépôt dépôts depots archives conservation mairie ad archives départementales cote fonds lieu de conservation gallica",
    rendu: () => [
      p("Un ", fort("dépôt"), " est l'endroit où un document est conservé : archives "
        + "départementales, mairie, site en ligne (Gallica, Geneanet)… Le renseigner "
        + "vous aide à retrouver l'original plus tard et à regrouper toutes les "
        + "sources d'un même fonds."),
      etapes([
        "Ouvrez l'onglet « Dépôts » pour créer vos dépôts habituels.",
        "En saisissant une source (onglet Actes / Sources), reliez-la à son dépôt.",
        "La « cote » précise l'emplacement exact du registre dans ce dépôt.",
      ]),
      encart("astuce", "Créez une fois pour toutes vos dépôts récurrents (ex. "
        + "« Archives départementales du Nord ») : vous les choisirez ensuite d'un "
        + "clic sur chaque acte."),
      versOnglet("depots", "Gérer mes dépôts"),
    ],
  },
  {
    cle: "tuto-exporter", groupe: "Tutoriels", titre: "Exporter",
    mots: "exporter export gedcom csv sortie partager transférer sauvegarde",
    rendu: () => [
      p("Exporter selon votre intention :"),
      h("ul", { class: "aide-liste" },
        h("li", {}, fort("GEDCOM (.ged)"), " : pour transférer l'arbre vers un autre logiciel."),
        h("li", {}, fort("Rameau (.ged)"), " : une seule branche — l'ascendance ou "
          + "la descendance d'une personne, avec ses sources."),
        h("li", {}, fort("GEDZIP (.gdz)"), " : le GEDCOM accompagné de vos scans et photos."),
        h("li", {}, fort("Archive .zip"), " : une sauvegarde complète, réimportable dans Arboriane.")),
      versOnglet("donnees", "Ouvrir Sauvegarde et export"),
    ],
  },
  {
    cle: "tuto-publier", groupe: "Tutoriels", titre: "Publier avec les vivants masqués",
    mots: "publier publication vivants masquer confidentialité diffusion privé rgpd protéger",
    rendu: () => [
      p("Avant de partager un arbre, vous pouvez masquer les personnes vivantes "
        + "pour protéger leur vie privée."),
      etapes([
        "Ouvrez « Sauvegarde et export ».",
        "Choisissez une exportation avec l'option « masquer les vivants ».",
        "Vérifiez le résultat avant toute diffusion.",
      ]),
      encart("attention", fort("Ne publiez jamais de données sur une personne "
        + "vivante sans son accord."), " Le masquage aide, mais la responsabilité "
        + "de la publication vous appartient."),
      versOnglet("donnees", "Préparer une publication"),
    ],
  },
  {
    cle: "tuto-geocodage", groupe: "Tutoriels", titre: "Géocodage (carte)",
    mots: "géocodage geocodage carte lieux openstreetmap nominatim coordonnées migrations opt-in",
    rendu: () => [
      p("Le géocodage place vos lieux sur une carte. Il est ", fort("désactivé par "
        + "défaut"), " et ne s'active que sur action explicite."),
      etapes([
        "Ouvrez l'onglet « Lieux / Carte ».",
        "Activez le géocodage : vous autorisez alors l'envoi des noms de lieux.",
        "Seuls les ", "noms de lieux sont transmis à OpenStreetMap (Nominatim), "
          + "jamais vos personnes ni vos dates.",
      ]),
      encart("aretenir", "Rien n'est envoyé tant que vous n'activez pas le "
        + "géocodage. Vous pouvez le désactiver à tout moment."),
      versOnglet("lieux", "Ouvrir la carte"),
    ],
  },
  {
    cle: "tuto-ia", groupe: "Tutoriels", titre: "Assistant IA (facultatif)",
    mots: "ia intelligence artificielle assistant clé api opt-in facultatif suggestion aide",
    rendu: () => [
      p("Un assistant IA peut vous aider (résumés, pistes de lecture). Il est "
        + fort("entièrement facultatif"), " et n'a aucune donnée par défaut."),
      etapes([
        "L'IA ne fonctionne que si vous fournissez votre propre clé.",
        "Sans clé, Arboriane fonctionne à 100 % sans aucune IA.",
        "Vous décidez, cas par cas, ce que vous soumettez à l'assistant.",
      ]),
      encart("attention", "Ce que vous envoyez à un service d'IA quitte votre "
        + "ordinateur. N'y soumettez pas de données que vous voulez garder strictement "
        + "privées, en particulier sur des personnes vivantes."),
      versOnglet("assistant", "Ouvrir l'Assistant"),
    ],
  },

  // ── Comprendre les notions ───────────────────────────────────────────
  {
    cle: "notions", groupe: "Comprendre", titre: "Les notions clés",
    mots: "notions personne fait source citation preuve piste sosa fiabilité quay gedcom vocabulaire lexique",
    rendu: () => [
      p("Le vocabulaire d'Arboriane, en une page :"),
      h("dl", { class: "aide-lexique" },
        ...defTerme("Personne", "Un individu de votre arbre, avec ses faits et ses relations."),
        ...defTerme("Fait", "Un événement daté et localisé : naissance, mariage, décès, "
          + "profession, résidence…"),
        ...defTerme("Source", "Un document qui atteste un ou plusieurs faits "
          + "(registre, acte, relevé)."),
        ...defTerme("Citation", "Le lien précis entre un fait et l'endroit d'une "
          + "source où il est attesté."),
        ...defTerme("Preuve", "Un fait solidement établi par une ou plusieurs sources "
          + "concordantes."),
        ...defTerme("Piste", "Une recherche à mener, une hypothèse non encore prouvée."),
        ...defTerme("Sosa", "La numérotation Sosa-Stradonitz des ancêtres : le "
          + "point de départ porte le n° 1, son père le 2, sa mère le 3, et ainsi "
          + "de suite (père = 2n, mère = 2n+1)."),
        ...defTerme("Fiabilité (QUAY)", "L'échelle GEDCOM de qualité d'une donnée, "
          + "de 0 (non fiable) à 3 (preuve directe). Dans Arboriane : basse, moyenne, haute."),
        ...defTerme("GEDCOM", "Le format texte standard d'échange de données "
          + "généalogiques entre logiciels.")),
      encart("astuce", "En résumé : documents → preuves → faits → histoire. "
        + "Chaque étape s'appuie sur la précédente."),
    ],
  },
  {
    cle: "notion-calendrier", groupe: "Comprendre", titre: "Le calendrier républicain",
    mots: "calendrier républicain révolutionnaire an vendémiaire brumaire date révolution 1792 1806 conversion grégorien",
    rendu: () => [
      p("Entre 1792 et 1806, l'état civil français a utilisé le ", fort("calendrier "
        + "républicain"), " (An I, Vendémiaire, Brumaire…). Les actes de cette période "
        + "portent souvent ce type de date."),
      p("Dans le champ date d'un fait, vous pouvez saisir une date républicaine : "
        + "Arboriane la reconnaît, la conserve telle quelle, et sait afficher son "
        + "équivalent grégorien."),
      encart("astuce", "Exemple : « 18 Brumaire An VIII » correspond au "
        + "9 novembre 1799."),
    ],
  },

  // ── Données & confidentialité ────────────────────────────────────────
  {
    cle: "donnees-vie-privee", groupe: "Données & confidentialité", titre: "Où sont mes données ?",
    mots: "données confidentialité vie privée local sauvegarde télémétrie collecte stockage sécurité",
    rendu: () => [
      bloc("Vos données restent chez vous",
        p("Tout ce que vous saisissez vit dans le dossier de l'arbre, sur "
          + "votre ordinateur. Aucune donnée n'est envoyée en ligne par défaut."),
        encart("aretenir", fort("Aucune télémétrie, aucune collecte, aucun compte."),
          " Arboriane ne « rappelle » rien à personne.")),
      bloc("Sauvegardes",
        p("Copiez le dossier de l'arbre, ou créez une archive .zip depuis "
          + "l'espace de travail. Faites-le régulièrement et gardez une copie ailleurs.")),
      bloc("Les seules exceptions, toujours opt-in",
        h("ul", { class: "aide-liste" },
          h("li", {}, fort("Assistant IA"), " : seulement si vous fournissez votre "
            + "propre clé, et seulement sur ce que vous soumettez."),
          h("li", {}, fort("Géocodage"), " : seulement si vous l'activez, et n'envoie "
            + "que des noms de lieux à OpenStreetMap."))),
    ],
  },
  {
    cle: "multi-ordi", groupe: "Données & confidentialité", titre: "Sur plusieurs ordinateurs",
    mots: "plusieurs ordinateurs multi synchroniser onedrive google drive dropbox icloud partager postes deux pc cloud portable fixe",
    rendu: () => [
      p("Arboriane est pensé pour ", fort("un ordinateur"), ". Mais comme un arbre "
        + "est un simple dossier, vous pouvez le ranger dans un dossier synchronisé "
        + "(OneDrive, Google Drive, Dropbox, iCloud) : votre cloud le recopie tout "
        + "seul sur vos autres ordinateurs. Arboriane reste 100 % local — c'est "
        + fort("votre"), " cloud qui synchronise, sans aucun compte Arboriane."),
      encart("attention", fort("Règle d'or : un seul ordinateur à la fois."),
        " Modifier le même arbre sur deux postes en même temps peut créer des "
        + "conflits ou des doublons de fichiers. Fermez Arboriane et laissez la "
        + "synchronisation se terminer (icône verte du cloud) avant d'ouvrir l'arbre "
        + "ailleurs. Arboriane vous prévient s'il détecte l'arbre déjà ouvert sur un "
        + "autre poste, mais ce garde-fou n'est pas infaillible."),
      bloc("Comment faire",
        etapes([
          "À la création de l'arbre, choisissez « Choisir un dossier… » et pointez "
            + "vers un dossier de votre cloud (OneDrive, Drive, Dropbox…).",
          "Sur le 2e ordinateur : installez Arboriane, laissez le cloud finir de "
            + "synchroniser, puis « Ouvrir » l'arbre depuis ce dossier.",
        ])),
      encart("aretenir", "En cas de doute, la méthode la plus sûre reste la "
        + "Sauvegarde/Restauration : créez une « Sauvegarde » .zip, transférez-la, "
        + "puis « Restaurer une sauvegarde » sur l'autre ordinateur."),
      versOnglet("espace", "Aller à l'espace de travail"),
    ],
  },

  // ── Bonnes pratiques ─────────────────────────────────────────────────
  {
    cle: "bonnes-pratiques", groupe: "Données & confidentialité", titre: "Bonnes pratiques",
    mots: "bonnes pratiques méthode sourcer carnet sauvegarder conseils rigueur qualité",
    rendu: () => [
      p("Trois habitudes qui font toute la différence :"),
      etapes([
        h("span", {}, fort("Sourcez chaque fait"), " : une date, un lieu, une "
          + "filiation — reliez-les à un document."),
        h("span", {}, fort("Tenez le carnet, même sans résultat"), " : notez ce que "
          + "vous avez cherché en vain pour ne pas y revenir par erreur."),
        h("span", {}, fort("Sauvegardez souvent"), " : une archive .zip avant chaque "
          + "gros chantier, une copie hors de l'ordinateur."),
      ]),
      encart("aretenir", "Une généalogie non sourcée n'est qu'une hypothèse. "
        + "Le sourçage est ce qui la rend transmissible et fiable."),
    ],
  },

  // ── Pages légales ────────────────────────────────────────────────────
  {
    cle: "cgu", groupe: "Mentions légales", titre: "Conditions d'utilisation",
    mots: "cgu conditions utilisation usage responsabilité garantie licence droit",
    rendu: () => [
      p("Arboriane est un logiciel de généalogie fonctionnant en ", fort("local"),
        " sur votre ordinateur."),
      h("ul", { class: "aide-liste" },
        h("li", {}, "L'usage est personnel et local : vous êtes seul·e maître de "
          + "vos données et de leur emplacement."),
        h("li", {}, "Vous êtes ", fort("responsable de ce que vous publiez ou "
          + "diffusez"), " à partir de vos arbres, notamment vis-à-vis des personnes "
          + "vivantes et des droits attachés aux documents."),
        h("li", {}, "Le logiciel est fourni « en l'état », ", fort("sans aucune "
          + "garantie"), " ; il vous appartient de sauvegarder régulièrement vos données.")),
      encart("attention", "Ne diffusez pas de données sur des personnes vivantes "
        + "sans leur accord, ni de reproductions d'actes dont vous n'avez pas les "
        + "droits de diffusion."),
    ],
  },
  {
    cle: "confidentialite", groupe: "Mentions légales", titre: "Politique de confidentialité",
    mots: "confidentialité vie privée rgpd données collecte télémétrie ia géocodage openstreetmap opt-in",
    rendu: () => [
      p("Le respect de votre vie privée est un principe de conception, pas une option."),
      h("ul", { class: "aide-liste" },
        h("li", {}, fort("Aucune collecte de données"), " : rien n'est transmis à "
          + "l'éditeur ni à un tiers."),
        h("li", {}, fort("Aucune télémétrie"), " : l'application ne rapporte pas votre "
          + "usage."),
        h("li", {}, fort("Données 100 % locales"), " : elles restent dans les dossiers "
          + "de vos arbres, sur votre ordinateur."),
        h("li", {}, fort("IA facultative"), " : n'utilise que votre propre clé, et "
          + "seulement sur ce que vous soumettez explicitement."),
        h("li", {}, fort("Géocodage opt-in"), " : désactivé par défaut ; une fois "
          + "activé, il n'envoie que des ", fort("noms de lieux"), " à OpenStreetMap "
          + "(Nominatim), jamais vos personnes ni vos dates.")),
      encart("aretenir", "Rien n'est envoyé en ligne par défaut. Les seuls envois "
        + "possibles (IA, géocodage) sont explicitement activés par vous."),
    ],
  },
  {
    cle: "mentions", groupe: "Mentions légales", titre: "Mentions légales",
    mots: "mentions légales éditeur contact responsable projet arboriane email",
    rendu: () => [
      h("dl", { class: "aide-lexique" },
        ...defTerme("Éditeur", "Projet Arboriane."),
        ...defTerme("Nature", "Logiciel de généalogie local, privé, sans service en ligne."),
        ...defTerme("Contact", null)),
      p("Pour toute question : ",
        h("a", { class: "lien", href: "mailto:" + CONTACT }, CONTACT), "."),
      encart("astuce", "Un bug, une idée, une gêne ? Écrivez-nous — c'est le seul "
        + "canal, et il est humain."),
    ],
  },
];

/* Terme de lexique → deux nœuds (dt + dd) prêts à étaler. */
function defTerme(terme, definition) {
  return [h("dt", {}, terme), definition ? h("dd", {}, definition) : h("dd", {},
    h("a", { class: "lien", href: "mailto:" + CONTACT }, CONTACT))];
}

/* Index rapide clé → rubrique et liste des groupes ordonnés. */
const PAR_CLE = Object.fromEntries(RUBRIQUES.map((r) => [r.cle, r]));
const GROUPES = [...new Set(RUBRIQUES.map((r) => r.groupe))];

/* ══════════════════════════════════════════════════════════════════════
   VUE
   ══════════════════════════════════════════════════════════════════════ */
export async function vueAide(vue, arg) {
  // Histoire de la famille de démonstration (source unique : services/demo).
  if (!histoireDemo) {
    histoireDemo = (await apiGet("/api/demo/histoire").catch(() => ({}))).texte || "";
  }
  // Rubrique de départ : si arg est une clé connue, on l'ouvre.
  let courante = (typeof arg === "string" && PAR_CLE[arg]) ? arg : "accueil";
  let filtre = "";

  vue.append(h("h1", {}, "Aide & tutoriels"));
  vue.append(h("p", { class: "sous-titre" },
    "Tutoriels courts, notions clés et pages légales. Tout se fait en local, "
    + "sur votre ordinateur."));

  const zone = h("div", { class: "aide-zone" });
  const colSomm = h("nav", { class: "aide-somm", "aria-label": "Sommaire de l'aide" });
  const colRub = h("div", { class: "aide-rubrique" });
  zone.append(colSomm, colRub);
  vue.append(zone);

  // ── Sommaire (avec recherche) ──────────────────────────────────────
  function rendreSommaire() {
    vider(colSomm);
    const champ = h("input", {
      type: "search", class: "aide-recherche", placeholder: "Rechercher dans l'aide…",
      value: filtre, "aria-label": "Rechercher dans l'aide",
      oninput: (e) => { filtre = e.target.value; rendreSommaire(); },
    });
    colSomm.append(champ);

    const q = filtre.trim().toLowerCase();
    const correspond = (r) => !q
      || r.titre.toLowerCase().includes(q) || r.mots.includes(q)
      || r.mots.split(/\s+/).some((m) => m.startsWith(q));

    let trouve = 0;
    GROUPES.forEach((g) => {
      const rubs = RUBRIQUES.filter((r) => r.groupe === g && correspond(r));
      if (!rubs.length) return;
      colSomm.append(h("div", { class: "aide-somm-groupe" }, g));
      rubs.forEach((r) => {
        trouve++;
        colSomm.append(h("button", {
          class: "aide-somm-lien" + (r.cle === courante ? " actif" : ""),
          onclick: () => { courante = r.cle; rendreSommaire(); rendreRubrique(); },
        }, r.titre));
      });
    });
    if (!trouve) colSomm.append(h("div", { class: "aide-somm-vide" },
      "Aucune rubrique pour « " + filtre + " »."));

    // Garder le focus dans le champ pendant la frappe.
    if (q) { champ.focus(); champ.setSelectionRange(filtre.length, filtre.length); }
  }

  // ── Rubrique affichée ──────────────────────────────────────────────
  function rendreRubrique() {
    vider(colRub);
    const r = PAR_CLE[courante] || PAR_CLE.accueil;
    colRub.append(h("div", { class: "aide-fil" }, r.groupe));
    colRub.append(h("h2", { class: "aide-titre" }, r.titre));
    for (const noeud of r.rendu()) if (noeud) colRub.append(noeud);
    colRub.scrollIntoView?.({ block: "nearest" });
  }

  rendreSommaire();
  rendreRubrique();
}
