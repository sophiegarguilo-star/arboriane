// Volet latéral : éditer / consulter sans quitter la vue courante.
// Ferme par Échap, clic sur le fond, ou bouton ✕.
import { h, vider } from "../noyau/dom.js";

let _onFermer = null;

export function ouvrirVolet(contenu, { titre = "", onFermer = null } = {}) {
  const fond = document.getElementById("volet-fond");
  const volet = document.getElementById("volet");
  _onFermer = onFermer;
  vider(volet);
  volet.append(h("div", { class: "volet-tete" },
    h("h2", {}, titre),
    h("button", { class: "volet-fermer", "aria-label": "Fermer", onclick: fermerVolet }, "✕")));
  volet.append(h("div", { class: "volet-corps" }, contenu));
  fond.classList.remove("cache");
  volet.classList.remove("cache");   // sinon .cache{display:none} masque le panneau
  requestAnimationFrame(() => volet.classList.add("ouvert"));
  const cible = volet.querySelector("input, textarea, select, button:not(.volet-fermer)");
  if (cible) cible.focus();
  return volet;
}

export function fermerVolet() {
  const fond = document.getElementById("volet-fond");
  const volet = document.getElementById("volet");
  volet.classList.remove("ouvert");
  fond.classList.add("cache");
  // remasque le panneau après la glissade (sauf s'il a été rouvert entre-temps)
  setTimeout(() => { if (!volet.classList.contains("ouvert")) volet.classList.add("cache"); }, 300);
  if (_onFermer) { const f = _onFermer; _onFermer = null; f(); }
}

export function voletOuvert() {
  return document.getElementById("volet").classList.contains("ouvert");
}

export function initVolet() {
  const fond = document.getElementById("volet-fond");
  fond.addEventListener("click", fermerVolet);
}
