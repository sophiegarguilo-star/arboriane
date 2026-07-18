// Onglet « Livres » (L10 — Jalon 1) : composer un livre biographique à offrir.
// Le rendu (récit + mise en page) est fait par le serveur ; ici on choisit le
// référent, le modèle et les réglages, puis on ouvre le livre (lecture/impression).
import { h, vider } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { toast } from "../composants/toast.js";
import { badge } from "../composants/badge.js";
import { confirmer, demander, ouvrirModale, fermerModale } from "../composants/modale.js";
import { champPersonne } from "../composants/champ.js";

const THEMES = [["heritage", "Héritage"], ["epure", "Épuré"], ["sepia", "Sépia"]];
const FORMATS = [["a4", "A4"], ["a5", "A5 livret"]];
const COUVERTURES = [["classique", "Médaillon"], ["sobre", "Sobre"]];
const SECTIONS = {
  comment_lire: "Comment lire ce livre", biographie: "Biographie",
  filiation: "Filiation", unions: "Unions & enfants",
  ascendance: "Les aïeux (ascendance narrée)",
  descendance: "La descendance (d'Aboville)",
  album: "Album photos",
  preface: "Préface (texte libre)",
  chronologie: "Chronologie de vie",
  index: "Index (noms & lieux)",
  dedicace: "Dédicace", remerciements: "Remerciements",
  introduction: "Introduction", chapitre: "Chapitre personnel",
};
// Sections dont le corps est un texte saisi (une ligne = un paragraphe).
const TYPES_TEXTE = ["preface", "dedicace", "remerciements", "introduction", "chapitre"];
// Sections que l'utilisateur peut AJOUTER (autant de fois qu'il veut).
const AJOUTABLES = [["dedicace", "Dédicace"], ["remerciements", "Remerciements"],
                    ["introduction", "Introduction"], ["chapitre", "Chapitre libre"]];
// Dans un livret d'ascendance, seules ces sections ont un sens (le corps = les
// chapitres-couples générés) : on masque les sections « données d'une personne ».
const ASC_SECTIONS = ["comment_lire", "preface", "dedicace", "remerciements",
                      "introduction", "chapitre", "index"];

// ── Liste des livres ──────────────────────────────────────────────────
async function nouveauLivre() {
  let liste = [];
  try { liste = await apiGet("/api/individus"); } catch { liste = []; }
  if (!liste.length) { toast("Ajoutez d'abord des personnes à votre arbre."); return; }
  let typeChoisi = "monographie";
  async function creerLivre(id) {
    if (!id) return;
    fermerModale();
    try {
      const r = await apiJson("/api/livres", "POST", { referent: id, type: typeChoisi });
      toast("Livre créé.");
      aller("livres", { livre: r.livre.id });
    } catch (e) { toast(e.message); }
  }
  const picker = champPersonne(liste, {
    placeholder: typeChoisi === "ascendance"
      ? "Choisir le point de départ (vous, en général)…" : "Chercher la personne à raconter…",
    onChoix: creerLivre,
  });
  // Choix du type de livre (une pastille active).
  const rangeeType = h("div", { class: "barre-actions", style: "gap:6px;margin-bottom:10px" });
  const sousTitre = h("p", { class: "sous-titre" }, "De qui voulez-vous raconter la vie ?");
  const TYPES = [
    ["monographie", "📖 Une personne", "De qui voulez-vous raconter la vie ?"],
    ["ascendance", "🌳 Ascendance complète", "Livret complet : un chapitre par couple, de cette personne jusqu'aux aïeux."],
  ];
  function rendreType() {
    vider(rangeeType);
    for (const [val, txt, aide] of TYPES) {
      rangeeType.append(h("button", {
        class: "bouton petit" + (typeChoisi === val ? "" : " secondaire"),
        onclick: () => { typeChoisi = val; sousTitre.textContent = aide; rendreType(); },
      }, txt));
    }
  }
  rendreType();
  ouvrirModale(h("div", {}, rangeeType, sousTitre, picker.element),
    { titre: "Nouveau livre", largeur: 460 });
}

function carteLivre(l) {
  return h("div", { class: "carte" },
    h("div", { class: "rangee" },
      h("strong", {}, l.titre || "Livre"),
      l.referent_nom ? badge(l.referent_nom, "info") : null),
    h("div", { class: "barre-actions", style: "margin-top:10px" },
      h("button", { class: "bouton petit", onclick: () => aller("livres", { livre: l.id }) },
        "Ouvrir"),
      h("button", { class: "bouton secondaire petit danger", onclick: async () => {
        if (!await confirmer("Supprimer le livre « " + (l.titre || "") + " » ? "
          + "(Votre arbre et vos personnes ne sont pas touchés.)",
          { titre: "Supprimer le livre", valider: "Supprimer", danger: true })) return;
        try { await apiJson("/api/livres/" + l.id, "DELETE", {}); toast("Livre supprimé."); aller("livres"); }
        catch (e) { toast(e.message); }
      } }, "Supprimer")));
}

async function vueListe(vue) {
  vue.append(h("h1", {}, "Livres"));
  vue.append(h("p", { class: "sous-titre" },
    "Composez un livre à imprimer ou à offrir : un récit de vie fidèle à vos "
    + "données, avec couverture, filiation et unions. Lisible par toute la famille."));
  vue.append(h("div", { class: "barre-actions", style: "margin:6px 0 18px" },
    h("button", { class: "bouton", onclick: nouveauLivre }, "📖 Nouveau livre")));
  let livres = [];
  try { livres = (await apiGet("/api/livres")).livres; } catch { /* vide */ }
  if (!livres.length) {
    vue.append(h("div", { class: "vide" }, "Aucun livre pour l'instant. "
      + "Cliquez « Nouveau livre » et choisissez une personne."));
    return;
  }
  const grille = h("div", { class: "grille-cartes" });
  livres.forEach((l) => grille.append(carteLivre(l)));
  vue.append(grille);
}

// ── Éditeur d'un livre ────────────────────────────────────────────────
async function vueEditeur(vue, lid) {
  let livre;
  try { livre = (await apiGet("/api/livres/" + lid)).livre; }
  catch (e) { toast(e.message); return aller("livres"); }
  const mep = livre.mise_en_page || (livre.mise_en_page = {});

  let tSauve = null;
  function sauver() {                       // enregistrement différé (regroupe les clics)
    clearTimeout(tSauve);
    tSauve = setTimeout(() => apiJson("/api/livres/" + lid, "PUT", livre)
      .catch((e) => toast(e.message)), 350);
  }
  async function vider_diff() {             // force l'envoi en attente et l'attend
    if (tSauve) { clearTimeout(tSauve); tSauve = null; }
    try { await apiJson("/api/livres/" + lid, "PUT", livre); } catch (e) { toast(e.message); }
  }

  async function ouvrirRendu(imprimer) {
    // Ouvrir la fenêtre IMMÉDIATEMENT, dans le geste du clic : si on l'ouvre
    // après un await (réseau), le navigateur la bloque comme pop-up intempestive.
    const w = window.open("", "_blank");
    if (!w) {
      toast("Le navigateur a bloqué la fenêtre. Autorisez les pop-ups pour ce site, puis réessayez.",
        { duree: 7000 });
      return;
    }
    try {
      w.document.write('<!doctype html><meta charset="utf-8"><title>Livre</title>'
        + '<p style="font:16px system-ui;color:#777;padding:2rem">Préparation du livre…</p>');
      await vider_diff();                   // le rendu reflète les derniers réglages
      const { html } = await apiGet("/api/livres/" + lid + "/html");
      w.document.open(); w.document.write(html); w.document.close();
      if (imprimer) { w.focus(); setTimeout(() => { try { w.print(); } catch (e) { /* */ } }, 500); }
    } catch (e) {
      toast(e.message);
      try { w.close(); } catch (_) { /* */ }
    }
  }

  // fabrique une rangée de « pastilles » (une seule active) reliée à mep[cle]
  function chips(cle, options, apres) {
    const rangee = h("span", { class: "barre-actions", style: "gap:6px;flex-wrap:wrap" });
    const rendre = () => {
      vider(rangee);
      for (const [val, txt] of options) {
        const actif = (mep[cle] || options[0][0]) === val;
        rangee.append(h("button", {
          class: "bouton petit" + (actif ? "" : " secondaire"),
          onclick: () => { mep[cle] = val; rendre(); sauver(); if (apres) apres(); },
        }, txt));
      }
    };
    rendre();
    return rangee;
  }

  function ligne(label, controle) {
    return h("div", { class: "champ" }, h("label", {}, label), controle);
  }

  vue.append(h("div", { class: "barre-actions", style: "margin-bottom:6px" },
    h("button", { class: "lien", onclick: () => aller("livres") }, "← Tous les livres")));
  vue.append(h("h1", {}, livre.titre || "Livre"));

  // — Identité du livre —
  const inTitre = h("input", { value: livre.titre || "", style: "width:100%" });
  inTitre.addEventListener("input", () => { livre.titre = inTitre.value; sauver(); });
  const inSous = h("input", { value: livre.sous_titre || "", style: "width:100%",
    placeholder: "sous-titre (facultatif)" });
  inSous.addEventListener("input", () => { livre.sous_titre = inSous.value; sauver(); });
  const inAuteur = h("input", { value: livre.auteur || "", style: "width:100%",
    placeholder: "votre nom (facultatif)" });
  inAuteur.addEventListener("input", () => { livre.auteur = inAuteur.value; sauver(); });

  const carteLivre = h("div", { class: "carte" },
    h("h2", {}, "Le livre"),
    ligne("Type", h("span", {},
      livre.type === "ascendance"
        ? "🌳 Ascendance complète (un chapitre par couple)"
        : "📖 Monographie (une personne)")),
    ligne("Titre", inTitre), ligne("Sous-titre", inSous), ligne("Auteur", inAuteur));
  // Profondeur du livret d'ascendance (nombre de générations remontées).
  if (livre.type === "ascendance") {
    const val = h("span", { style: "min-width:22px;text-align:center;display:inline-block" },
      String(livre.generations || 5));
    const pas = (d) => () => {
      livre.generations = Math.max(2, Math.min(8, (livre.generations || 5) + d));
      val.textContent = String(livre.generations); sauver();
    };
    carteLivre.append(ligne("Profondeur", h("span", { class: "barre-actions", style: "gap:8px" },
      h("button", { class: "bouton petit secondaire", onclick: pas(-1) }, "−"),
      val, "générations",
      h("button", { class: "bouton petit secondaire", onclick: pas(1) }, "+"))));
  }
  vue.append(carteLivre);

  // — Mise en page —
  const pctTaille = h("span", { style: "min-width:46px;text-align:center;display:inline-block" },
    (mep.taille || 100) + " %");
  function bougeTaille(sens) {
    mep.taille = Math.max(85, Math.min(130, (mep.taille || 100) + sens * 5));
    pctTaille.textContent = mep.taille + " %"; sauver();
  }
  const chkVivants = h("input", { type: "checkbox",
    checked: livre.masquer_vivants ? "checked" : null });
  // Sans avertissement, un livre sur une famille vivante sort quasiment VIDE
  // (parents, conjoints, enfants masqués) sans que rien ne l'explique.
  const avertVivants = h("div", { style: "font-size:13px;color:var(--gris);margin:4px 0 0 26px" });
  async function majAvertVivants() {
    if (!chkVivants.checked) { avertVivants.textContent = ""; return; }
    const liste = await apiGet("/api/individus").catch(() => []);
    const n = liste.filter((p) => p.vivant).length;
    avertVivants.textContent = n
      ? "⚠ " + n + " personne" + (n > 1 ? "s" : "") + " présumée" + (n > 1 ? "s" : "")
        + " vivante" + (n > 1 ? "s" : "") + " ser" + (n > 1 ? "ont" : "a")
        + " masquée" + (n > 1 ? "s" : "") + " : nom et faits cachés. "
        + "Décochez pour un livre destiné à la famille."
      : "";
  }
  chkVivants.addEventListener("change", () => {
    livre.masquer_vivants = chkVivants.checked; sauver(); majAvertVivants();
  });
  majAvertVivants();

  vue.append(h("div", { class: "carte" },
    h("h2", {}, "Mise en page"),
    ligne("Modèle", chips("theme", THEMES)),
    ligne("Format", chips("format", FORMATS)),
    ligne("Taille du texte", h("span", { class: "barre-actions", style: "gap:8px" },
      h("button", { class: "bouton petit secondaire", onclick: () => bougeTaille(-1),
        "aria-label": "Réduire le texte" }, "A−"),
      pctTaille,
      h("button", { class: "bouton petit secondaire", onclick: () => bougeTaille(1),
        "aria-label": "Agrandir le texte" }, "A+"))),
    ligne("Couverture", chips("couverture", COUVERTURES)),
    h("label", { style: "display:flex;align-items:center;gap:8px;margin-top:8px" },
      chkVivants, "Masquer les personnes vivantes (recommandé pour offrir)"),
    avertVivants));

  // — Sections (réordonnables, éditables, extensibles — Palier A) —
  const carteSections = h("div", { class: "carte" });

  function deplace(i, d) {
    const j = i + d;
    if (j < 1 || j >= livre.sections.length) return;   // garder la couverture en tête
    const a = livre.sections;
    const tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    rendreSections(); sauver();
  }
  function supprime(i) {
    livre.sections.splice(i, 1); rendreSections(); sauver();
  }
  function ajoute(type) {
    const cle = type + "-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
    const s = { type, cle, actif: true, mode: "manuel", texte: "" };
    if (type === "chapitre") s.titre = "";
    livre.sections.push(s); rendreSections(); sauver();
  }

  function rendreSections() {
    vider(carteSections);
    carteSections.append(h("h2", {}, "Contenu"));
    carteSections.append(h("p", { class: "sous-titre" },
      "Cochez ce qui apparaît, réordonnez avec ▲▼, retouchez les textes, "
      + "et ajoutez vos propres pages. L'ordre ici est l'ordre du livre."));
    livre.sections.forEach((s, i) => {
      if (s.type === "couverture") return;
      if (livre.type === "ascendance" && !ASC_SECTIONS.includes(s.type)) return;
      const perso = !!s.cle;                 // section ajoutée par l'utilisateur
      const libTxt = (s.type === "chapitre" && (s.titre || "").trim())
        ? s.titre.trim() : (SECTIONS[s.type] || s.type);
      const libSpan = h("span", {}, libTxt);
      const chk = h("input", { type: "checkbox", checked: s.actif ? "checked" : null });
      chk.addEventListener("change", () => { s.actif = chk.checked; sauver(); });
      carteSections.append(h("div", {
        style: "display:flex;align-items:center;gap:6px;padding:6px 0;border-top:1px solid var(--bordure,#0001)" },
        h("button", { class: "bouton petit secondaire", title: "Monter",
          onclick: () => deplace(i, -1) }, "▲"),
        h("button", { class: "bouton petit secondaire", title: "Descendre",
          onclick: () => deplace(i, 1) }, "▼"),
        h("label", { style: "display:flex;align-items:center;gap:8px;flex:1;margin:0" },
          chk, libSpan),
        perso ? h("button", { class: "bouton petit secondaire danger",
          title: "Supprimer cette page", onclick: () => supprime(i) }, "🗑") : null));

      if (s.generations != null) {
        const val = h("span", { style: "min-width:18px;text-align:center;display:inline-block" },
          String(s.generations || 4));
        const maxi = s.type === "descendance" ? 6 : 8;
        const pas = (d) => () => {
          s.generations = Math.max(2, Math.min(maxi, (s.generations || 4) + d));
          val.textContent = String(s.generations); sauver();
        };
        carteSections.append(h("div", {
          style: "display:flex;align-items:center;gap:8px;margin:0 0 8px 60px;"
            + "color:var(--gris);font-size:14px" },
          "Profondeur :",
          h("button", { class: "bouton petit secondaire", onclick: pas(-1) }, "−"),
          val, "générations",
          h("button", { class: "bouton petit secondaire", onclick: pas(1) }, "+")));
      }
      if (s.type === "chapitre") {
        const it = h("input", { value: s.titre || "", placeholder: "Titre du chapitre…",
          style: "width:calc(100% - 60px);margin:2px 0 6px 60px" });
        it.addEventListener("input", () => {
          s.titre = it.value; libSpan.textContent = it.value.trim() || "Chapitre personnel"; sauver();
        });
        carteSections.append(it);
      }
      if (TYPES_TEXTE.includes(s.type)) {
        const ta = h("textarea", { rows: "4",
          style: "width:calc(100% - 60px);margin:2px 0 10px 60px",
          placeholder: "Votre texte (une ligne = un paragraphe)…" });
        ta.value = s.texte || "";
        ta.addEventListener("input", () => { s.texte = ta.value; sauver(); });
        carteSections.append(ta);
      }
    });
    const barre = h("div", { class: "barre-actions", style: "margin-top:12px;flex-wrap:wrap" },
      h("span", { class: "sous-titre", style: "align-self:center;margin-right:2px" }, "Ajouter :"));
    AJOUTABLES.forEach(([t, lbl]) => barre.append(
      h("button", { class: "bouton petit secondaire", onclick: () => ajoute(t) }, "＋ " + lbl)));
    carteSections.append(barre);
  }
  rendreSections();
  vue.append(carteSections);

  // — Actions —
  vue.append(h("div", { class: "barre-actions", style: "margin-top:18px;flex-wrap:wrap" },
    h("button", { class: "bouton", onclick: () => ouvrirRendu(false) }, "🌐 Lire en ligne"),
    h("button", { class: "bouton secondaire", onclick: () => ouvrirRendu(true) },
      "🖨 Aperçu imprimable")));
}

export async function vueLivres(vue, arg) {
  if (arg && arg.livre) return vueEditeur(vue, arg.livre);
  return vueListe(vue);
}
