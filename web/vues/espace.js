// Onglet « Espace de travail » — un arbre = un dossier.
import { h, actionnable } from "../noyau/dom.js";
import { aller, majEspace } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { badge } from "../composants/badge.js";
import { toast } from "../composants/toast.js";
import { confirmer, demander, choix } from "../composants/modale.js";

function humaniser(octets) {
  for (const [u, s] of [["Go", 1e9], ["Mo", 1e6], ["Ko", 1e3]])
    if (octets >= s) return (octets / s).toFixed(1).replace(".", ",") + " " + u;
  return octets + " o";
}

async function rafraichir() { await majEspace(apiGet); await aller("espace"); }

// Bandeau « fichier corrompu » (DAT-03) : affiché ici et au tableau de bord
// quand /api/espace signale que le JSON a été mis en quarantaine au chargement.
export function bandeauCorrompu() {
  return h("div", { class: "carte", role: "alert",
    style: "border-color:var(--alerte, #c0392b);margin-bottom:14px" },
    h("p", { style: "margin:0 0 8px" }, "⚠️ ",
      h("strong", {}, "Votre fichier était illisible"),
      " ; une copie a été mise de côté et l'arbre est reparti de la dernière "
      + "version saine. Vous pouvez restaurer une sauvegarde ci-dessous."),
    h("button", { class: "bouton petit", onclick: () => aller("espace") },
      "⏪ Revenir en arrière"));
}

// ── « Revenir en arrière » (GED-02) : copies automatiques de l'arbre actif ──
async function restaurerArchive(a) {
  const quoi = "la copie du " + a.date
    + (a.personnes != null ? " (" + a.personnes + " personne(s))" : "");
  if (!await confirmer("Revenir à " + quoi + " ? L'état actuel sera lui-même "
    + "sauvegardé d'abord : rien n'est perdu, vous pourrez y revenir.",
    { titre: "Revenir en arrière", valider: "Restaurer cette copie" })) return;
  try {
    const r = await apiJson("/api/archives/restaurer", "POST", { nom: a.nom });
    await majEspace(apiGet);
    toast("Arbre restauré : " + r.personnes + " personne(s).");
    aller("accueil");
  } catch (e) { toast(e.message, { type: "erreur" }); }
}

async function blocArchives() {
  const carte = h("div", { class: "carte", style: "margin-top:18px" },
    h("h2", {}, "⏪ Revenir en arrière"),
    h("p", { class: "sous-titre" },
      "Arboriane garde des copies automatiques de l'arbre actif (dossier "
      + "Sauvegardes/). Restaurer une copie remet l'arbre dans l'état de ce "
      + "moment-là — l'état actuel est lui-même sauvegardé d'abord."));
  let archives = [];
  try { archives = (await apiGet("/api/archives")).archives || []; }
  catch { /* pas d'arbre ouvert : bloc masqué par l'appelant */ }
  if (!archives.length) {
    carte.append(h("div", { class: "vide compacte" },
      "Aucune copie automatique pour l'instant : elles se créent au fil de "
      + "vos modifications."));
    return carte;
  }
  archives.slice(0, 15).forEach((a) => carte.append(
    h("div", { class: "rangee", style: "padding:6px 0;border-bottom:1px solid var(--bord);gap:10px" },
      h("span", {}, "🕘 " + a.date),
      h("span", { style: "color:var(--gris);font-size:13px" },
        a.personnes != null ? a.personnes + " personne(s)" : "contenu illisible"),
      h("button", { class: "bouton secondaire petit pousse",
        onclick: () => restaurerArchive(a) }, "Restaurer"))));
  return carte;
}

// Verrou souple : demande confirmation si l'arbre (dossier synchronisé) semble
// ouvert sur un AUTRE ordinateur. Renvoie true si on doit ouvrir quand même.
export function confirmerVerrou(v) {
  return confirmer(
    "Cet arbre semble ouvert sur « " + v.machine + " » (il y a " + v.age_min + " min). "
    + "Le modifier sur deux ordinateurs à la fois peut créer des conflits de "
    + "synchronisation. Ouvrir quand même ?",
    { titre: "Ouvert sur un autre ordinateur", valider: "Ouvrir quand même", danger: true });
}

async function ouvrir(chemin) {
  try {
    let r = await apiJson("/api/espaces/ouvrir", "POST", { chemin });
    if (r && r.ok === false && r.verrou) {
      if (!await confirmerVerrou(r.verrou)) return;
      r = await apiJson("/api/espaces/ouvrir", "POST", { chemin, forcer: true });
    }
    await majEspace(apiGet);
    toast("Arbre « " + r.nom + " » ouvert.");
    aller("accueil");                    // droit au tableau de bord
  } catch (e) { toast(e.message, { type: "erreur" }); }
}

async function creerArbre() {
  const nom = await demander("Comment s'appelle ce nouvel arbre ?",
    { titre: "Créer un arbre", placeholder: "ex. Famille Martin", valider: "Créer" });
  if (nom == null) return;

  // Où le ranger ? « Mes arbres » (par défaut) ou un dossier au choix
  // (ex. un autre disque). Le dialogue de dossier est natif (côté serveur).
  const ou = await choix(
    "Où ranger cet arbre ?\n\n« Mes arbres » est l'emplacement habituel. Vous "
    + "pouvez aussi le ranger ailleurs, par exemple sur un autre disque.",
    [{ cle: "defaut", texte: "Mes arbres (par défaut)" },
     { cle: "choisir", texte: "Choisir un dossier…", secondaire: true }],
    { titre: "Emplacement de l'arbre" });
  if (ou == null) return;                        // annulé

  let emplacement = null;
  if (ou === "choisir") {
    try {
      toast("Choisissez le dossier dans la fenêtre Windows…");
      const d = await apiJson("/api/espaces/choisir-dossier", "POST", {});
      if (!d.chemin) { toast("Aucun dossier choisi."); return; }
      emplacement = d.chemin;
    } catch (e) { toast(e.message, { type: "erreur" }); return; }
  }

  try {
    const r = await apiJson("/api/espaces/creer", "POST",
      emplacement ? { nom, emplacement } : { nom });
    await majEspace(apiGet);
    toast(emplacement ? ("Arbre « " + r.nom + " » créé dans " + emplacement)
                      : ("Arbre « " + r.nom + " » créé."));
    aller("accueil");
  } catch (e) { toast(e.message, { type: "erreur" }); }
}

async function ouvrirDemo() {
  try {
    await apiJson("/api/espaces/demo", "POST", {});
    await majEspace(apiGet);
    toast("Arbre de démonstration ouvert.");
    aller("accueil");
  } catch (e) { toast(e.message, { type: "erreur" }); }
}

// Restauration d'une SAUVEGARDE complète (.zip) : le fichier est choisi dans un
// dialogue Windows natif et extrait par le SERVEUR — aucun transfert par le
// navigateur, donc pas de saturation même pour un arbre lourd (scans compris).
async function restaurerSauvegarde() {
  try {
    toast("Choisissez le fichier .zip dans la fenêtre Windows…");
    const r = await apiJson("/api/espaces/restaurer", "POST", {});
    if (r.annule) { toast("Restauration annulée."); return; }
    await majEspace(apiGet);
    toast("Arbre « " + r.nom + " » restauré.");
    aller("accueil");
  } catch (e) { toast(e.message, { type: "erreur" }); }
}

function carteArbre(a) {
  const actions = h("div", { class: "barre-actions", style: "margin-top:6px" });
  if (!a.actif) actions.append(h("button", { class: "bouton petit",
    onclick: () => ouvrir(a.chemin) }, "Ouvrir"));
  actions.append(
    h("button", { class: "bouton secondaire petit", onclick: async () => {
      const nom = await demander("Nouveau nom de l'arbre :",
        { titre: "Renommer", defaut: a.nom, valider: "Renommer" });
      if (nom == null) return;
      try {
        await apiJson("/api/espaces/renommer", "POST", { chemin: a.chemin, nom });
        toast("Arbre renommé."); rafraichir();
      } catch (e) { toast(e.message, { type: "erreur" }); }
    } }, "Renommer"),
    h("button", { class: "bouton secondaire petit", onclick: async () => {
      try {
        const r = await apiJson("/api/espaces/dupliquer", "POST", { chemin: a.chemin });
        toast("Arbre dupliqué."); rafraichir();
      } catch (e) { toast(e.message, { type: "erreur" }); }
    }, title: "Créer une copie indépendante" }, "Dupliquer"),
    h("button", { class: "bouton secondaire petit", onclick: async () => {
      try {
        const r = await apiJson("/api/espaces/sauvegarde", "POST", {});
        toast("Sauvegarde créée : " + r.fichier);
      } catch (e) { toast(e.message, { type: "erreur" }); }
    }, title: "Sauvegarde complète .zip (arbre actif)",
       "aria-label": "Créer une sauvegarde complète" }, "💾 Sauvegarde"),
    h("button", { class: "bouton secondaire petit", onclick: async () => {
      if (!await confirmer("Retirer « " + a.nom + " » de la liste ? Le dossier n'est PAS "
        + "supprimé : vous pourrez le rouvrir plus tard.",
        { titre: "Retirer de la liste", valider: "Retirer" })) return;
      try {
        await apiJson("/api/espaces/oublier", "POST", { chemin: a.chemin });
        toast("Arbre retiré de la liste."); rafraichir();
      } catch (e) { toast(e.message, { type: "erreur" }); }
    } }, "Retirer"),
    h("button", { class: "bouton danger petit",
      onclick: async () => {
        if (!await confirmer("SUPPRIMER définitivement « " + a.nom + " » ? Une archive de "
          + "sécurité (.zip) est déposée avant l'effacement.",
          { titre: "Supprimer l'arbre", valider: "Supprimer définitivement", danger: true })) return;
        try {
          const r = await apiJson("/api/espaces/supprimer", "POST", { chemin: a.chemin });
          toast("Arbre supprimé (archive : " + r.archive + ")."); rafraichir();
        } catch (e) { toast(e.message, { type: "erreur" }); }
      } }, "Supprimer"));

  if (a.actif) actions.append(h("button", { class: "bouton secondaire petit",
    onclick: async () => {
      try { await apiJson("/api/espaces/ouvrir-dossier", "POST", {}); }
      catch (e) { toast(e.message, { type: "erreur" }); }
    }, title: "Ouvrir le dossier de l'arbre dans l'explorateur de fichiers" }, "📂 Dossier"));

  return h("div", { class: "carte-arbre" + (a.actif ? " actif" : "") },
    h("div", { class: "rangee" },
      h("span", { class: "nom" }, a.nom),
      a.actif ? badge("Actif", "ok") : null,
      a.demo ? badge("Démo", "info") : null,
      a.cloud ? badge("☁ " + a.cloud.fournisseur, "attention") : null),
    h("div", { class: "chemin" }, a.chemin),
    h("div", { class: "meta" },
      "👥 " + a.personnes + " personnes · 📄 " + a.sources + " sources · " + humaniser(a.taille)),
    actions);
}

export async function vueEspace(vue) {
  const esp = await majEspace(apiGet);
  vue.append(h("h1", {}, "Espace de travail"));
  // fichier mis en quarantaine au chargement : le dire, et guider vers les copies
  if (esp && esp.ouvert && esp.avertissement === "corrompu") {
    vue.append(bandeauCorrompu());
  }
  vue.append(h("p", { class: "sous-titre" },
    "Un arbre = un dossier : chacun a ses propres personnes, sources et carnet. "
    + "Tout reste en fichiers lisibles sur votre ordinateur."));

  const grille = h("div", { class: "grille-arbres" });
  grille.append(actionnable(h("div", { class: "carte-arbre carte-neuve", onclick: creerArbre },
    "➕ Créer un nouvel arbre")));

  let espaces = [];
  try { espaces = (await apiGet("/api/espaces")).espaces; } catch { /* vide */ }
  espaces.forEach((a) => grille.append(carteArbre(a)));
  vue.append(grille);

  // Un arbre vit dans un dossier synchronisé (OneDrive/Drive/Dropbox…) : rappeler
  // la règle d'or (un seul poste à la fois) et renvoyer vers l'aide dédiée.
  if (espaces.some((a) => a.cloud)) {
    vue.append(h("div", { class: "carte", style: "border-color:var(--accent);margin-top:12px" },
      h("p", { style: "margin:0 0 8px" }, "☁ ",
        h("strong", {}, "Arbre dans un dossier synchronisé"), " détecté. Règle d'or : ",
        h("strong", {}, "un seul ordinateur à la fois"), ". Fermez Arboriane et attendez la "
        + "fin de la synchronisation (icône verte du cloud) avant d'ouvrir cet arbre "
        + "sur un autre poste."),
      h("button", { class: "bouton secondaire petit",
        onclick: () => aller("apropos", "multi-ordi") }, "En savoir plus")));
  }

  const inputZip = h("input", { type: "file", accept: ".zip", style: "display:none" });
  inputZip.addEventListener("change", async () => {
    const f = inputZip.files[0]; if (!f) return;
    inputZip.value = "";                    // permet de re-choisir le même fichier
    // Garde-fou : l'import navigateur charge tout le fichier en mémoire (base64).
    // Au-delà de ~40 Mo, on redirige vers la restauration native (côté serveur)
    // pour éviter le plantage « Out of Memory » de l'onglet.
    if (f.size > 40 * 1024 * 1024) {
      const go = await confirmer(
        "Ce fichier est volumineux (" + humaniser(f.size) + "). L'import par le "
        + "navigateur est réservé aux petits fichiers d'échange. Pour une "
        + "sauvegarde complète (avec les scans), utilisez « Restaurer une "
        + "sauvegarde » : le fichier est traité directement, sans passer par le "
        + "navigateur.\n\nLancer la restauration maintenant ?",
        { titre: "Sauvegarde volumineuse", valider: "Restaurer une sauvegarde" });
      if (go) restaurerSauvegarde();
      return;
    }
    const data = await new Promise((res) => {
      const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(f);
    });
    try {
      const r = await apiJson("/api/espaces/importer-zip", "POST",
        { data, nom: f.name.replace(/\.zip$/i, "") });
      await majEspace(apiGet);
      toast("Arbre « " + r.nom + " » importé.");
      aller("accueil");
    } catch (e) { toast(e.message, { type: "erreur" }); }
  });

  // « Revenir en arrière » : seulement si un arbre est ouvert (les copies
  // automatiques appartiennent à l'arbre actif).
  if (esp && esp.ouvert) vue.append(await blocArchives());

  vue.append(h("div", { class: "barre-actions", style: "margin-top:18px;flex-wrap:wrap" },
    h("button", { class: "bouton secondaire", onclick: ouvrirDemo },
      "🌱 Ouvrir l'arbre de démonstration"),
    h("button", { class: "bouton secondaire", onclick: restaurerSauvegarde,
      title: "Restaurer une sauvegarde .zip complète (recommandé pour un arbre lourd)" },
      "♻️ Restaurer une sauvegarde"),
    h("button", { class: "bouton secondaire", onclick: () => inputZip.click(),
      title: "Importer un petit fichier d'échange .zip" },
      "📥 Importer un arbre (.zip)"),
    inputZip));
}
