// Onglet Plan de recherche — l'arbre transformé en actions concrètes.
// Interactif : personne de référence (pour les branches Sosa), profondeur,
// filtre par catégorie et par priorité.
import { h, vider } from "../noyau/dom.js";
import { aller, etat, majEspace } from "../noyau/etat.js";
import { apiGet } from "../noyau/api.js";
import { badge } from "../composants/badge.js";
import { champPersonne } from "../composants/champ.js";

const PRIO = { 3: ["Prioritaire", "attention"], 2: ["Utile", "info"], 1: ["Plus tard", ""] };

export async function vueRecherche(vue) {
  vue.append(h("h1", {}, "Plan de recherche"));
  vue.append(h("p", { class: "sous-titre" },
    "Que chercher maintenant ? Arboriane transforme votre arbre en pistes "
    + "concrètes : quoi chercher, pourquoi, et où regarder. Ce n'est pas la "
    + "barre de recherche en haut — c'est votre feuille de route."));

  await majEspace(apiGet);
  const liste = await apiGet("/api/individus").catch(() => []);

  let reference = (etat.espace || {}).racine_id || (liste[0] && liste[0].id) || null;
  let profondeur = 12;
  let filtreCat = "";
  let filtrePrio = 0;

  // barre de contrôle
  const pick = liste.length
    ? champPersonne(liste, { initial: reference, placeholder: "Personne de référence…",
        onChoix: (id) => { if (id) { reference = id; charger(); } } })
    : null;
  const selGen = h("select", {}, ...[6, 8, 10, 12, 16].map((n) =>
    h("option", { value: n, selected: n === profondeur ? "selected" : null }, n + " générations")));
  selGen.addEventListener("change", () => { profondeur = +selGen.value; charger(); });

  const selCat = h("select", {}, h("option", { value: "" }, "Toutes les catégories"));
  const selPrio = h("select", {},
    h("option", { value: "0" }, "Toutes priorités"),
    h("option", { value: "3" }, "Prioritaire"),
    h("option", { value: "2" }, "Utile et +"),
    h("option", { value: "1" }, "Plus tard et +"));
  selCat.addEventListener("change", () => { filtreCat = selCat.value; rendre(); });
  selPrio.addEventListener("change", () => { filtrePrio = +selPrio.value; rendre(); });

  const controle = h("div", { class: "carte" },
    h("div", { style: "display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end" },
      pick ? h("div", {}, h("label", {}, "Personne de référence (branches)"), pick.element) : null,
      h("div", {}, h("label", {}, "Profondeur"), selGen),
      h("div", {}, h("label", {}, "Catégorie"), selCat),
      h("div", {}, h("label", {}, "Priorité"), selPrio),
      h("div", { class: "barre-actions pousse" },
        h("button", { class: "bouton secondaire petit", onclick: () => window.print() }, "🖨 Imprimer"),
        h("button", { class: "bouton secondaire petit", onclick: () => exporterCsv() }, "⬇ CSV"))));
  vue.append(controle);

  const compteur = h("p", {});
  const zone = h("div", {});
  vue.append(compteur, zone);

  let dernier = null;   // dernier plan chargé (pour re-filtrer sans requête)

  async function charger() {
    vider(zone); compteur.textContent = "";
    const url = "/api/plan?gen=" + profondeur + (reference ? "&id=" + reference : "");
    const p = await apiGet(url).catch(() => null);
    if (!p) { zone.append(h("div", { class: "vide" }, "Impossible d'établir le plan.")); return; }
    dernier = p;
    // (re)remplir le filtre de catégories
    const cats = p.categories.map((c) => c.nom);
    const garde = filtreCat;
    vider(selCat); selCat.append(h("option", { value: "" }, "Toutes les catégories"));
    cats.forEach((c) => selCat.append(h("option", { value: c, selected: c === garde ? "selected" : null }, c)));
    if (!cats.includes(garde)) filtreCat = "";
    rendre();
  }

  function rendre() {
    vider(zone);
    if (!dernier || !dernier.total) {
      zone.append(h("div", { class: "vide" },
        h("span", { class: "grand" }, "🎉"),
        "Rien d'urgent à chercher : votre arbre est bien documenté !"));
      compteur.textContent = "";
      return;
    }
    let cats = dernier.categories;
    if (filtreCat) cats = cats.filter((c) => c.nom === filtreCat);
    let affichees = 0;
    cats.forEach((cat) => {
      const pistes = filtrePrio ? cat.pistes.filter((p) => p.priorite >= filtrePrio) : cat.pistes;
      if (!pistes.length) return;
      affichees += pistes.length;
      const carte = h("div", { class: "carte" });
      carte.append(h("h2", {}, cat.nom + " ", badge(String(pistes.length))));
      pistes.forEach((pi) => {
        const [lib, genre] = PRIO[pi.priorite] || ["", ""];
        carte.append(h("div", { style: "padding:8px 0;border-bottom:1px solid var(--bord)" },
          h("div", { class: "rangee serre" },
            badge(lib, genre),
            h("strong", { class: "lien", onclick: () => aller("personnes", { fiche: pi.personne }) },
              pi.personne_nom),
            h("span", {}, "— " + pi.quoi)),
          h("div", { class: "message" }, pi.pourquoi),
          pi.ou ? h("div", { style: "font-size:13px;color:var(--accent);margin-top:2px" }, "📍 " + pi.ou) : null));
      });
      zone.append(carte);
    });
    compteur.append(badge(affichees + " piste(s) affichée(s) sur " + dernier.total, "info"));
    if (!affichees) zone.append(h("div", { class: "vide" }, "Aucune piste pour ce filtre."));
  }

  const PRIO_TXT = { 3: "Prioritaire", 2: "Utile", 1: "Plus tard" };
  function exporterCsv() {
    if (!dernier || !dernier.total) { return; }
    const entete = ["Catégorie", "Priorité", "Personne", "À chercher", "Pourquoi", "Où"];
    const lignes = [];
    dernier.categories.forEach((cat) => {
      const pistes = filtreCat && cat.nom !== filtreCat ? []
        : (filtrePrio ? cat.pistes.filter((p) => p.priorite >= filtrePrio) : cat.pistes);
      pistes.forEach((pi) => lignes.push(
        [cat.nom, PRIO_TXT[pi.priorite] || "", pi.personne_nom, pi.quoi, pi.pourquoi, pi.ou || ""]
          .map((v) => '"' + String(v || "").replace(/"/g, '""') + '"').join(";")));
    });
    const csv = "﻿" + [entete.join(";")].concat(lignes).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "plan-de-recherche.csv";
    a.click();
  }

  charger();
}
