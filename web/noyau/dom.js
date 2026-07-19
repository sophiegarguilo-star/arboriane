// Aides DOM minimalistes — pas de framework, juste des fonctions.

// h("div", {class:"x", onclick:fn}, enfant1, enfant2, …) → HTMLElement.
// Un attribut commençant par "on" devient un écouteur. `null`/`false`/`""`
// comme enfant est ignoré, ce qui permet les conditions en ligne.
export function h(tag, attrs = {}, ...enfants) {
  const el = document.createElement(tag);
  for (const [cle, val] of Object.entries(attrs || {})) {
    if (val == null || val === false) continue;
    if (cle === "class") el.className = val;
    else if (cle === "style" && typeof val === "object") Object.assign(el.style, val);
    else if (cle.startsWith("on") && typeof val === "function") {
      el.addEventListener(cle.slice(2).toLowerCase(), val);
    } else if (cle === "html") el.innerHTML = val;
    else el.setAttribute(cle, val);
  }
  for (const enfant of enfants.flat()) {
    if (enfant == null || enfant === false || enfant === "") continue;
    el.append(enfant.nodeType ? enfant : document.createTextNode(String(enfant)));
  }
  return el;
}

export function vider(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

// Échappe un texte destiné à innerHTML (rarement nécessaire : h() crée des
// nœuds texte, mais utile pour le surlignage de recherche).
export function echapper(t) {
  return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Rend un élément NON-bouton actionnable au clavier (audit A11Y-01) : rôle
// bouton, focusable, Entrée/Espace = clic. Pour les lignes/cartes cliquables
// construites en div/span — les vrais <button> n'en ont pas besoin.
export function actionnable(el) {
  if (!el.hasAttribute("tabindex")) el.setAttribute("tabindex", "0");
  if (!el.hasAttribute("role")) el.setAttribute("role", "button");
  el.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); el.click(); }
  });
  return el;
}

// Associe automatiquement chaque <label> sans for= au champ qui le suit
// (audit A11Y-05). Filet générique appliqué à chaque rendu de vue : les
// écritures explicites via composants/ligneChamp.js restent la voie noble,
// ceci rattrape tous les motifs historiques sans réécrire chaque écran.
let _seqAuto = 0;
export function associerLabels(racine) {
  if (!racine || !racine.querySelectorAll) return;   // stub DOM des tests / robustesse
  racine.querySelectorAll("label:not([for])").forEach((lbl) => {
    if (lbl.querySelector("input,select,textarea")) return;  // label englobant : déjà lié
    let el = lbl.nextElementSibling, cible = null;
    while (el && !cible) {
      cible = el.matches && el.matches("input,select,textarea") ? el
        : (el.querySelector ? el.querySelector("input,select,textarea") : null);
      el = el.nextElementSibling;
    }
    if (!cible) return;
    if (!cible.id) cible.id = "champ-auto-" + (++_seqAuto);
    lbl.setAttribute("for", cible.id);
  });
}
