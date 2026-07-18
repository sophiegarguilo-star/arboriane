// Onglet Cohérence — anomalies généalogiques, classées et actionnables.
import { h, vider } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet } from "../noyau/api.js";
import { badge } from "../composants/badge.js";
import { ouvrirDoublons } from "./personnes.js";

const COULEUR = { haute: "attention", moyenne: "info", basse: "" };
const LIB_GRAVITE = { haute: "À corriger", moyenne: "À vérifier", basse: "Remarque" };

export async function vueCoherence(vue) {
  vue.append(h("h1", {}, "Cohérence"));
  vue.append(h("p", { class: "sous-titre" },
    "Les anomalies détectées dans l'arbre, des plus importantes aux simples "
    + "remarques. Chaque alerte renvoie à la fiche concernée."));
  const [c, dbl] = await Promise.all([
    apiGet("/api/coherence").catch(() => null),
    apiGet("/api/doublons").catch(() => ({ doublons: [] })),
  ]);
  if (!c) { vue.append(h("div", { class: "vide" }, "Impossible d'analyser.")); return; }

  // Doublons probables — même parité que l'ancienne version (fusion en 1 clic)
  const paires = (dbl && dbl.doublons) || [];
  const carteDbl = h("div", { class: "carte" },
    h("h2", {}, "Doublons probables ", badge(String(paires.length), paires.length ? "attention" : "ok")));
  if (!paires.length) {
    carteDbl.append(h("p", { class: "sous-titre", style: "margin-bottom:0" },
      "Aucun doublon évident. 👍"));
  } else {
    carteDbl.append(h("p", { class: "sous-titre" },
      "Mêmes nom et prénom, dates de naissance proches. À vérifier — la fusion conserve la première fiche."),
      h("button", { class: "bouton petit", onclick: ouvrirDoublons },
        "Examiner et fusionner les doublons →"));
  }
  vue.append(carteDbl);

  if (!c.total) {
    vue.append(h("div", { class: "carte" },
      h("h2", {}, "Anomalies"),
      h("p", { class: "sous-titre", style: "margin-bottom:0" },
        "Aucune anomalie chronologique ni lien cassé détecté. Bel arbre ! ✅")));
    return;
  }

  vue.append(h("div", { class: "stats" },
    stat(c.par_gravite.haute, "à corriger"),
    stat(c.par_gravite.moyenne, "à vérifier"),
    stat(c.par_gravite.basse, "remarques")));

  // regrouper par catégorie
  const parCat = {};
  c.alertes.forEach((a) => (parCat[a.categorie] = parCat[a.categorie] || []).push(a));
  Object.entries(parCat).forEach(([cat, alertes]) => {
    const carte = h("div", { class: "carte" });
    carte.append(h("h2", {}, cat + " ", badge(String(alertes.length))));
    const box = h("div", { class: "liste-pers" });
    alertes.forEach((a) => box.append(h("div", {
      class: "ligne-pers", onclick: () => aller("personnes", { fiche: a.personne }) },
      badge(LIB_GRAVITE[a.gravite], COULEUR[a.gravite]),
      h("span", {}, h("strong", {}, a.personne_nom), " — " + a.message))));
    carte.append(box);
    vue.append(carte);
  });
}

function stat(n, label) {
  return h("div", { class: "stat" }, h("strong", {}, String(n)), h("span", {}, label));
}
