// Onglet Santé de l'arbre — solidité documentaire, ton encourageant.
import { h } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet } from "../noyau/api.js";
import { badge } from "../composants/badge.js";

export async function vueSante(vue) {
  vue.append(h("h1", {}, "🩺 Santé de l'arbre"));
  const s = await apiGet("/api/sante").catch(() => null);
  if (!s || !s.nb_personnes) {
    vue.append(h("div", { class: "vide" },
      h("span", { class: "grand" }, "🌱"),
      "Votre arbre est encore vide — c'est le bon moment pour commencer."));
    return;
  }
  vue.append(h("p", { class: "sous-titre" }, s.humeur));

  vue.append(h("div", { class: "stats" },
    stat(s.pct_prouves + "%", "faits prouvés par acte (" + s.faits_actes + "/" + s.faits_total + ")"),
    stat(s.nb_personnes_sans_source, "sans aucune source", true),
    stat(s.sources_sans_scan.length, "sources sans scan", true),
    stat(s.sources_inutiles.length, "sources reliées à rien", true),
    stat(s.pistes_ouvertes, "pistes ouvertes")));

  controle(vue, "Personnes sans aucune source", s.personnes_sans_source,
    (it) => h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: it.id }) },
      h("strong", {}, it.nom), it.periode ? h("span", { class: "meta" }, it.periode) : null),
    "Rien ne prouve encore ce qu'on affirme sur elles. Ouvrez la fiche → « Prouver ».");

  controle(vue, "Sources sans scan", s.sources_sans_scan,
    (it) => h("div", { class: "ligne-pers", onclick: () => aller("actes", { source: it.id }) },
      h("strong", {}, it.titre)),
    "La source existe mais aucune image n'y est rattachée. Ajoutez le scan quand vous l'avez.");

  controle(vue, "Sources reliées à rien", s.sources_inutiles,
    (it) => h("div", { class: "ligne-pers", onclick: () => aller("actes", { source: it.id }) },
      h("strong", {}, it.titre)),
    "Ces sources ne prouvent aucun fait : à relier à une personne, ou à retirer.");
}

function controle(vue, titre, items, rendre, explication) {
  const carte = h("div", { class: "carte" },
    h("h2", {}, badge(String(items.length), items.length ? "attention" : "ok"), " " + titre));
  if (explication) carte.append(h("p", { class: "sous-titre" }, explication));
  if (!items.length) { carte.append(h("div", { class: "vide compacte" }, h("span", { class: "grand" }, "🎉"), "Rien à signaler ici.")); }
  else {
    const det = h("details", {}, h("summary", {}, "Voir la liste (" + items.length + ")"));
    const box = h("div", { class: "liste-pers compacte" });
    items.forEach((it) => box.append(rendre(it)));
    det.append(box); carte.append(det);
  }
  vue.append(carte);
}

function stat(n, label, alerte) {
  return h("div", { class: alerte && n ? "stat alerte" : "stat" },
    h("strong", {}, String(n)),
    h("span", {}, label));
}
