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
