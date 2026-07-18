// Badges et pastilles réutilisables.
import { h } from "../noyau/dom.js";

export function badge(texte, genre = "") {
  return h("span", { class: "badge" + (genre ? " " + genre : "") }, texte);
}

export function pastilleSexe(sexe) {
  return h("span", { class: "pastille-sexe " + (sexe || "U"),
    title: { M: "Homme", F: "Femme", U: "Inconnu", N: "Non consigné", X: "Intersexe" }[sexe] || "" });
}
