// Liste de lignes répétables (variantes de nom, résidences, événements,
// personnes liées…). On fournit `creerLigne(valeurInitiale)` qui renvoie
// { element, lire() } ; lire() renvoie la donnée de la ligne, ou null pour
// l'ignorer. Renvoie { element, valeur() } — valeur() = tableau des lignes non
// nulles.
import { h } from "../noyau/dom.js";

export function listeRepetable({ ajouterLabel = "+ Ajouter", creerLigne, valeurs = [] }) {
  const lignes = [];   // { wrap, lire }
  const box = h("div", { class: "liste-rep" });

  function ajouter(valeurInit) {
    const l = creerLigne(valeurInit || {});
    const btnX = h("button", { type: "button", class: "rep-x", title: "Retirer",
      onclick: () => { wrap.remove(); const i = lignes.indexOf(entree); if (i >= 0) lignes.splice(i, 1); } }, "✕");
    const wrap = h("div", { class: "rep-ligne" }, h("div", { style: "flex:1;min-width:0" }, l.element), btnX);
    const entree = { wrap, lire: l.lire };
    lignes.push(entree);
    box.append(wrap);
  }

  (valeurs || []).forEach((v) => ajouter(v));

  const bouton = h("button", { type: "button", class: "bouton secondaire petit",
    onclick: () => ajouter({}) }, ajouterLabel);

  return {
    element: h("div", {}, box, bouton),
    valeur: () => lignes.map((e) => e.lire()).filter((v) => v != null),
  };
}
