// Éditeur enrichi MINI (mini WYSIWYG) pour la transcription d'une source.
// 100 % maison, aucune dépendance : un <div contenteditable> + une barre
// d'outils qui pilote document.execCommand (l'app tourne dans un webview
// Chromium, où execCommand fonctionne). Le HTML est TOUJOURS assaini (liste
// blanche de balises, aucun attribut) avant d'être lu ou réinjecté ; ainsi
// aucune balise dangereuse n'entre en base, et l'export GEDCOM (côté Python)
// reconvertit ce HTML en texte simple pour ne pas « mettre la panique ».
import { h, echapper } from "../noyau/dom.js";

// Seules balises conservées : mise en forme de base + listes + structure.
const AUTORISEES = new Set(["b", "strong", "i", "em", "u", "ul", "ol", "li", "br", "p", "div"]);

// Y a-t-il au moins une balise dans la chaîne ? (texte simple ⇒ pas de HTML)
const A_BALISE = /<[a-zA-Z/][^>]*>/;

// Assainit une chaîne HTML : retire script/style (avec leur contenu) et les
// commentaires, ne garde QUE les balises autorisées, SANS aucun attribut
// (donc plus d'onclick, de style, de src…). Approche par tokens, sans DOM :
// identique dans le navigateur et sous Node (tests), et sûre pour des données
// locales de l'utilisatrice.
export function assainirHtml(html) {
  let s = String(html == null ? "" : html);
  s = s.replace(/<(script|style)[\s\S]*?<\/\1\s*>/gi, "");   // blocs dangereux + contenu
  s = s.replace(/<(script|style)\b[^>]*>/gi, "");            // ouverture orpheline éventuelle
  s = s.replace(/<!--[\s\S]*?-->/g, "");                     // commentaires
  s = s.replace(/<\/?[a-zA-Z][^>]*>/g, (balise) => {
    const m = /^<\s*(\/?)\s*([a-zA-Z0-9]+)/.exec(balise);
    if (!m) return "";
    const nom = m[2].toLowerCase();
    if (!AUTORISEES.has(nom)) return "";                     // balise non autorisée : retirée
    if (nom === "br") return "<br>";
    return m[1] === "/" ? "</" + nom + ">" : "<" + nom + ">"; // balise nettoyée (sans attributs)
  });
  return s;
}

// Nœud DOM sûr pour AFFICHER une transcription en lecture : si elle contient du
// HTML → rendu assaini (balises autorisées seulement) ; si texte simple →
// échappé avec sauts de ligne préservés. À utiliser partout où on montre une
// transcription sans l'éditer.
export function rendreTranscription(valeur) {
  const v = String(valeur == null ? "" : valeur);
  const div = h("div", { class: "transcription-rendu", style: "line-height:1.6;white-space:pre-wrap" });
  if (A_BALISE.test(v)) {
    div.style.whiteSpace = "normal";        // le HTML gère lui-même ses sauts (<br>, <p>…)
    div.innerHTML = assainirHtml(v);
  } else {
    div.innerHTML = echapper(v).replace(/\n/g, "<br>");
  }
  return div;
}

// Construit l'éditeur riche. opts : { html?, placeholder?, onInput?() }.
// Renvoie { element, getHtml(), setHtml(html) }.
export function editeurRiche(opts = {}) {
  const zone = h("div", {
    class: "editeur-riche-zone",
    contenteditable: "true",
    "data-placeholder": opts.placeholder || "Transcription de l'acte…",
    style: "min-height:240px;padding:10px;border:1px solid var(--bord);border-radius:8px;"
      + "line-height:1.5;resize:vertical;overflow:auto;background:var(--fond-carte,#fff)",
  });
  if (opts.html) zone.innerHTML = assainirHtml(opts.html);
  if (typeof opts.onInput === "function") zone.addEventListener("input", opts.onInput);

  function cmd(nom) {
    zone.focus();
    try { document.execCommand(nom, false, null); } catch { /* webview only */ }
    if (typeof opts.onInput === "function") opts.onInput();
  }
  // onmousedown preventDefault : garde la sélection dans la zone au clic bouton.
  // La LETTRE de chaque bouton porte l'effet qu'il applique (G en gras, I en
  // italique, S souligné) : le sens saute aux yeux sans avoir à connaître le
  // raccourci — repère universel des traitements de texte.
  const bouton = (etiquette, commande, titre, styleTexte) => {
    const span = h("span", styleTexte ? { style: styleTexte } : {}, etiquette);
    return h("button", {
      type: "button", class: "bouton secondaire petit", title: titre,
      onmousedown: (e) => e.preventDefault(),
      onclick: () => cmd(commande),
    }, span);
  };

  const barre = h("div", { class: "editeur-riche-barre barre-actions",
    style: "gap:4px;margin-bottom:6px;flex-wrap:wrap" },
    bouton("G", "bold", "Gras (Ctrl+B)", "font-weight:800"),
    bouton("I", "italic", "Italique (Ctrl+I)", "font-style:italic"),
    bouton("S", "underline", "Souligné (Ctrl+U)", "text-decoration:underline"),
    bouton("• Liste à puces", "insertUnorderedList", "Liste à puces"),
    bouton("1. Liste numérotée", "insertOrderedList", "Liste numérotée"),
    bouton("⌫ Effacer la mise en forme", "removeFormat", "Enlève gras, italique, etc."));

  // Aide discrète : le réflexe « sélectionner d'abord » n'est pas évident pour
  // qui n'a jamais utilisé de traitement de texte.
  const aide = h("div", { class: "editeur-riche-aide",
    style: "font-size:12px;color:var(--gris,#777);margin-top:4px" },
    "Astuce : sélectionnez le texte, puis cliquez sur G, I ou S pour le mettre en forme.");

  const element = h("div", { class: "editeur-riche" }, barre, zone, aide);
  return {
    element,
    getHtml: () => assainirHtml(zone.innerHTML),
    setHtml: (html) => { zone.innerHTML = assainirHtml(html || ""); },
  };
}
