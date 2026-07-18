// Onglet « Listes & index » (Lot 8) — index des métiers, unions, ascendance /
// descendance textuelles, éphéméride. Chaque liste s'exporte en CSV (côté client).
import { h, vider } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet } from "../noyau/api.js";
import { badge } from "../composants/badge.js";

export async function vueListes(vue) {
  vue.append(h("h1", {}, "📋 Listes & index"));
  vue.append(h("p", { class: "sous-titre" },
    "Index des métiers, unions, ascendance/descendance et éphéméride — chacun exportable."));
  const cont = h("div", {});
  vue.append(cont);
  const [metiers, unions, eph] = await Promise.all([
    apiGet("/api/index-metiers").catch(() => null),
    apiGet("/api/unions").catch(() => null),
    apiGet("/api/ephemeride").catch(() => null),
  ]);
  cont.append(
    carteMetiers(metiers),
    carteUnions(unions),
    carteLignee("Ascendance (Sosa)", "/api/ascendance-texte", "sosa"),
    carteLignee("Descendance (Aboville)", "/api/descendance-texte", "numero"),
    carteEphemeride(eph));
}

function carteMetiers(m) {
  const c = h("div", { class: "carte" }, h("h2", {}, "Index des métiers"));
  if (!m || !m.total_metiers) {
    c.append(h("div", { class: "vide compacte" }, h("span", { class: "grand" }, "💼"), "Aucun métier renseigné.")); return c;
  }
  c.append(h("p", { class: "sous-titre" }, m.total_metiers + " métiers, " + m.total_personnes + " personnes."));
  c.append(boutonExport("metiers.csv", ["Métier", "Nb", "Personnes"],
    m.metiers.map((x) => [x.metier, x.nb, x.personnes.map((p) => p.nom).join(" | ")])));
  m.metiers.slice(0, 50).forEach((x) => {
    const det = h("details", {}, h("summary", {}, h("strong", {}, x.metier), " ", badge(String(x.nb))));
    const box = h("div", { class: "liste-pers compacte" });
    x.personnes.forEach((p) => box.append(
      h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: p.id }) },
        h("strong", {}, p.nom), p.periode ? h("span", { class: "meta" }, p.periode) : null)));
    det.append(box); c.append(det);
  });
  return c;
}

function carteUnions(u) {
  const c = h("div", { class: "carte" }, h("h2", {}, "Unions"));
  if (!u || !u.total) { c.append(h("div", { class: "vide compacte" }, h("span", { class: "grand" }, "💍"), "Aucune union.")); return c; }
  c.append(h("p", { class: "sous-titre" }, u.total + " unions."));
  c.append(boutonExport("unions.csv", ["Époux", "Épouse", "Type", "Date", "Lieu"],
    u.unions.map((x) => [x.mari, x.epouse, x.type || "", x.date, x.lieu])));
  const box = h("div", { class: "liste-pers compacte liste-defilante" });
  u.unions.forEach((x) => box.append(h("div", { class: "ligne-pers" },
    h("strong", {}, x.mari + " × " + x.epouse),
    h("span", { class: "meta" },
      [x.type, [x.date, x.lieu].filter(Boolean).join(" · ")].filter(Boolean).join(" — ")))));
  c.append(box); return c;
}

function carteLignee(titre, url, champ) {
  const c = h("div", { class: "carte" }, h("h2", {}, titre));
  const zone = h("div", {});
  const btn = h("button", { class: "bouton" }, "Générer");
  btn.onclick = async () => {
    btn.disabled = true; vider(zone); zone.append(h("p", { class: "message" }, "Calcul…"));
    try {
      const r = await apiGet(url);
      vider(zone);
      zone.append(h("p", { class: "sous-titre" }, r.total + " personnes (racine : " + r.racine_nom + ")."));
      zone.append(boutonExport(url.split("/").pop() + ".csv", ["N°", "Nom", "Période"],
        r.lignes.map((l) => [String(l[champ]), l.nom, l.periode])));
      const box = h("div", { class: "liste-pers compacte liste-defilante" });
      r.lignes.forEach((l) => box.append(
        h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: l.id }) },
          h("strong", { class: "pers-num" }, String(l[champ])),
          h("span", { class: "meta" }, l.nom + (l.periode ? " · " + l.periode : "")))));
      zone.append(box);
    } catch (e) { vider(zone); zone.append(h("div", { class: "vide compacte" }, e.message)); }
    btn.disabled = false;
  };
  c.append(btn, zone);
  return c;
}

function carteEphemeride(e) {
  const c = h("div", { class: "carte" }, h("h2", {}, "Éphéméride des naissances"));
  if (!e || !e.total) {
    c.append(h("div", { class: "vide compacte" }, h("span", { class: "grand" }, "🎂"), "Aucune date de naissance exploitable.")); return c;
  }
  c.append(h("p", { class: "sous-titre" }, e.total + " naissances datées, classées par jour de l'année."));
  c.append(boutonExport("ephemeride.csv", ["Jour", "Mois", "Nom", "Année"],
    e.personnes.map((p) => [String(p.jour), p.mois_nom, p.nom, String(p.annee || "")])));
  const box = h("div", { class: "liste-pers compacte liste-defilante" });
  e.personnes.forEach((p) => box.append(
    h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: p.id }) },
      h("strong", {}, p.jour + " " + p.mois_nom),
      h("span", { class: "meta" }, p.nom + (p.annee ? " (" + p.annee + ")" : "")))));
  c.append(box); return c;
}

// ── Export CSV (côté client, aucune donnée ne quitte la machine) ────────
function boutonExport(nom, entetes, lignes) {
  return h("div", { class: "barre-actions" },
    h("button", { class: "bouton secondaire petit",
      onclick: () => telecharger(nom, csv(entetes, lignes), "text/csv;charset=utf-8") },
      "⬇ Exporter (CSV)"));
}

function csv(entetes, lignes) {
  const esc = (s) => '"' + String(s == null ? "" : s).replace(/"/g, '""') + '"';
  return [entetes.map(esc).join(";")]
    .concat(lignes.map((r) => r.map(esc).join(";"))).join("\r\n");
}

function telecharger(nom, contenu, type) {
  const blob = new Blob(["﻿" + contenu], { type });
  const url = URL.createObjectURL(blob);
  const a = h("a", { href: url, download: nom });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
