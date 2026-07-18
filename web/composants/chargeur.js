// Petit indicateur de chargement animé.
import { h } from "../noyau/dom.js";

export function chargeur(texte = "") {
  return h("div", { class: "chargeur-boite" },
    h("span", { class: "chargeur" }),
    texte ? h("span", { style: "color:var(--gris)" }, texte) : null);
}
