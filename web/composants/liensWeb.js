// Composant « Recherche web » (Lot 6) — boutons ouvrant des recherches
// pré-remplies (Geneanet, FamilySearch, Géopatronyme…) pour une personne.
// Les URL sont construites côté serveur à partir de la fiche ; ici on ne fait
// qu'OUVRIR le lien : aucune donnée de l'arbre n'est transmise automatiquement.
import { h } from "../noyau/dom.js";
import { apiGet } from "../noyau/api.js";

export function blocLiensWeb(pid) {
  const boite = h("div", {});
  boite.append(h("p", { class: "sous-titre" },
    "Ouvre une recherche pré-remplie dans votre navigateur. Aucune donnée de "
    + "l'arbre n'est envoyée — l'application ne fait qu'ouvrir un lien."));
  const zone = h("div", {});
  boite.append(zone);
  apiGet("/api/liens?id=" + encodeURIComponent(pid)).then((r) => {
    const liens = r.liens || [];
    if (!liens.length) {
      zone.append(h("p", { class: "message" },
        "Ajoutez au moins un nom ou un prénom pour activer la recherche web."));
      return;
    }
    const cats = {};
    liens.forEach((l) => { (cats[l.categorie] = cats[l.categorie] || []).push(l); });
    Object.keys(cats).forEach((cat) => {
      zone.append(h("div", { class: "sur-titre" }, cat));
      const bar = h("div", { class: "barre-actions" });
      cats[cat].forEach((l) => bar.append(h("button", {
        class: "bouton secondaire petit",
        onclick: () => window.open(l.url, "_blank", "noopener,noreferrer") },
        "🔎 " + l.nom)));
      zone.append(bar);
    });
  }).catch(() => {
    zone.append(h("p", { class: "message" }, "Recherche web indisponible."));
  });
  return boite;
}
