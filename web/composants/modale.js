// Modale centrée : confirmations et petits formulaires. Ferme par Échap ou
// clic sur le fond. Une seule modale à la fois.
import { h, vider } from "../noyau/dom.js";

let _onFermer = null;

export function ouvrirModale(contenu, { titre = "", largeur = 460 } = {}) {
  const fond = document.getElementById("modale-fond");
  const boite = document.getElementById("modale");
  vider(boite);
  boite.style.maxWidth = largeur + "px";
  if (titre) boite.append(h("h2", { class: "modale-titre" }, titre));
  boite.append(contenu);
  fond.classList.remove("cache");
  requestAnimationFrame(() => boite.classList.add("visible"));
  // focus au premier champ / bouton
  const cible = boite.querySelector("input, textarea, select, button");
  if (cible) cible.focus();
  return boite;
}

export function fermerModale() {
  const fond = document.getElementById("modale-fond");
  const boite = document.getElementById("modale");
  boite.classList.remove("visible");
  fond.classList.add("cache");
  if (_onFermer) { const f = _onFermer; _onFermer = null; f(); }
}

export function modaleOuverte() {
  return !document.getElementById("modale-fond").classList.contains("cache");
}

// Confirmation élégante (remplace confirm()). Renvoie une Promise<bool>.
// `finir` garantit une seule résolution : la fermeture (Échap/fond) vaut
// « Annuler », mais un clic sur Confirmer ne doit PAS être écrasé par elle.
export function confirmer(message, { titre = "Confirmer",
                                     valider = "Confirmer", danger = false } = {}) {
  return new Promise((resolve) => {
    let regle = false;
    const finir = (val) => { if (regle) return; regle = true; _onFermer = null; fermerModale(); resolve(val); };
    const corps = h("div", {},
      h("p", { style: "margin:0 0 16px" }, message),
      h("div", { class: "barre-actions", style: "justify-content:flex-end" },
        h("button", { class: "bouton secondaire", onclick: () => finir(false) }, "Annuler"),
        h("button", { class: "bouton" + (danger ? " danger" : ""),
          onclick: () => finir(true) }, valider)));
    _onFermer = () => finir(false);
    ouvrirModale(corps, { titre });
  });
}

// Choix parmi plusieurs actions. `boutons` = [{cle, texte, secondaire, danger}].
// Renvoie une Promise<string|null> : la clé du bouton cliqué, ou null si on
// annule (bouton Annuler, Échap ou clic sur le fond).
export function choix(message, boutons = [], { titre = "" } = {}) {
  return new Promise((resolve) => {
    let regle = false;
    const finir = (val) => { if (regle) return; regle = true; _onFermer = null; fermerModale(); resolve(val); };
    const barre = h("div", { class: "barre-actions",
      style: "justify-content:flex-end;flex-wrap:wrap;gap:8px" });
    barre.append(h("button", { class: "bouton secondaire", onclick: () => finir(null) }, "Annuler"));
    for (const b of boutons) {
      barre.append(h("button", {
        class: "bouton" + (b.secondaire ? " secondaire" : "") + (b.danger ? " danger" : ""),
        onclick: () => finir(b.cle),
      }, b.texte));
    }
    const corps = h("div", {},
      h("p", { style: "margin:0 0 16px;white-space:pre-line" }, message), barre);
    _onFermer = () => finir(null);
    ouvrirModale(corps, { titre });
  });
}

// Saisie d'une valeur (remplace prompt()). Renvoie une Promise<string|null>.
export function demander(message, { titre = "", defaut = "", placeholder = "",
                                    valider = "Valider" } = {}) {
  return new Promise((resolve) => {
    let regle = false;
    const champ = h("input", { value: defaut, placeholder, style: "width:100%" });
    const finir = (val) => { if (regle) return; regle = true; _onFermer = null; fermerModale(); resolve(val); };
    const valider_ = () => finir(champ.value.trim() || null);
    champ.addEventListener("keydown", (e) => { if (e.key === "Enter") valider_(); });
    const corps = h("div", {},
      message ? h("p", { style: "margin:0 0 10px" }, message) : null,
      champ,
      h("div", { class: "barre-actions", style: "justify-content:flex-end;margin-top:16px" },
        h("button", { class: "bouton secondaire", onclick: () => finir(null) }, "Annuler"),
        h("button", { class: "bouton", onclick: valider_ }, valider)));
    _onFermer = () => finir(null);
    ouvrirModale(corps, { titre });
  });
}

// initialise le clic sur le fond (appelé une fois par app.js)
export function initModale() {
  const fond = document.getElementById("modale-fond");
  fond.addEventListener("click", (e) => { if (e.target === fond) fermerModale(); });
}
