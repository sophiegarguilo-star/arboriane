// Onglet « Fusion assistée » (L14) — doublons de personnes scorés + assistant
// de fusion champ par champ (garde-fou sexe), et fusion des variantes de lieux.
import { h, vider } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { badge } from "../composants/badge.js";
import { toast } from "../composants/toast.js";
import { confirmer } from "../composants/modale.js";
import { ouvrirVolet, fermerVolet } from "../composants/volet.js";

const NIVEAU = {
  eleve: ["Confiance élevée", "ok"], moyen: ["Confiance moyenne", "info"],
  faible: ["Confiance faible", "attention"],
};

export async function vueFusion(vue) {
  vue.append(h("h1", {}, "🔀 Fusion assistée"));
  vue.append(h("p", { class: "sous-titre" },
    "Repérez et fusionnez les doublons — personnes homonymes et variantes "
    + "d'orthographe des lieux. Rien n'est écrasé : la fusion complète les vides, "
    + "elle ne supprime pas d'information."));
  const zonePers = h("div", {});
  const zoneLieux = h("div", {});
  vue.append(h("h2", { style: "margin-top:18px" }, "👥 Personnes en double"), zonePers,
    h("h2", { style: "margin-top:26px" }, "📍 Lieux en double (orthographe)"), zoneLieux);
  await chargerPersonnes(zonePers);
  await chargerLieux(zoneLieux);
}

// ── Personnes ──────────────────────────────────────────────────────────────
async function chargerPersonnes(zone) {
  vider(zone);
  let d;
  try { d = await apiGet("/api/fusion/doublons"); }
  catch (e) { zone.append(h("div", { class: "vide" }, e.message)); return; }
  const paires = d.paires || [];
  if (!paires.length) {
    zone.append(h("div", { class: "vide" }, h("span", { class: "grand" }, "🎉"), "Aucun doublon probable.")); return;
  }
  paires.forEach((p) => {
    const [lib, genre] = NIVEAU[p.niveau] || ["", ""];
    const carte = h("div", { class: "carte compacte" },
      h("div", { class: "rangee" },
        h("strong", {}, p.nom),
        badge(lib + " · " + p.score + "%", genre),
        h("span", { style: "color:var(--gris);font-size:12px" }, (p.indices || []).join(" · "))),
      h("div", { class: "barre-actions", style: "margin-top:8px" },
        h("button", { class: "bouton petit", onclick: () => assistant(p) }, "Comparer & fusionner"),
        h("button", { class: "bouton secondaire petit",
          title: "Marquer que ces deux personnes sont distinctes — ne plus la proposer",
          onclick: () => ecarterPaire(p, carte, zone) }, "Ce n'est pas un doublon")));
    zone.append(carte);
  });
}

// Écarte une paire (« pas un doublon ») : elle ne sera plus jamais proposée.
async function ecarterPaire(p, carte, zone) {
  try {
    await apiJson("/api/fusion/ecarter", "POST", { a: p.a, b: p.b });
    carte.remove();
    toast("Paire écartée : « " + p.nom + " » ne sera plus signalée en doublon.");
    if (!zone.querySelector(".carte"))
      zone.append(h("div", { class: "vide" },
        h("span", { class: "grand" }, "🎉"), "Aucun doublon probable."));
  } catch (e) { toast(e.message); }
}

async function assistant(p) {
  let c;
  try { c = await apiGet("/api/fusion/comparer?a=" + p.a + "&b=" + p.b); }
  catch (e) { toast(e.message); return; }
  let garde = "a";                            // on garde A par défaut (permutable)
  const contenu = h("div", {});

  function rendre() {
    vider(contenu);
    const idGarde = garde === "a" ? c.a : c.b, idAbs = garde === "a" ? c.b : c.a;
    const nomGarde = garde === "a" ? c.nom_a : c.nom_b, nomAbs = garde === "a" ? c.nom_b : c.nom_a;
    const choix = {};
    contenu.append(h("p", { class: "sous-titre" },
      "On garde ", h("strong", {}, nomGarde), " et on y verse « ", nomAbs, " »."));
    contenu.append(h("button", { class: "bouton secondaire petit",
      onclick: () => { garde = garde === "a" ? "b" : "a"; rendre(); } },
      "⇄ Inverser (garder l'autre)"));
    const tbl = h("div", { style: "margin-top:12px" });
    tbl.append(h("div", { style: "display:grid;grid-template-columns:130px 1fr 1fr;gap:6px;"
      + "font-size:11px;text-transform:uppercase;color:var(--gris);padding-bottom:4px" },
      h("span", {}, "Champ"), h("span", {}, "Conservé"), h("span", {}, "Autre fiche")));
    c.lignes.forEach((l) => {
      const va = garde === "a" ? l.a : l.b, vb = garde === "a" ? l.b : l.a;
      let cellB;
      if (l.conflit) {
        const chk = h("input", { type: "checkbox" });
        chk.addEventListener("change", () => { choix[l.cle] = chk.checked ? "b" : "a"; });
        cellB = h("label", { style: "cursor:pointer;display:flex;gap:5px;align-items:baseline" },
          chk, h("span", {}, vb, h("span", { style: "color:var(--gris-clair);font-size:11px" }, " (prendre)")));
      } else {
        cellB = h("span", { style: "color:var(--gris-clair)" }, vb || "—");
      }
      tbl.append(h("div", { style: "display:grid;grid-template-columns:130px 1fr 1fr;gap:6px;"
        + "padding:5px 0;border-top:1px solid var(--bord);align-items:baseline" },
        h("span", { style: "font-size:12px;color:var(--gris)" }, l.libelle),
        h("span", {}, va || h("i", { style: "color:var(--gris-clair)" }, "vide")),
        cellB));
    });
    contenu.append(tbl);
    contenu.append(h("div", { class: "barre-actions", style: "margin-top:14px" },
      h("button", { class: "bouton", onclick: () => lancerFusion(idGarde, idAbs, choix, false) },
        "Fusionner"),
      h("button", { class: "bouton secondaire",
        title: "Ces deux personnes sont distinctes — ne plus proposer cette paire",
        onclick: async () => {
          try {
            await apiJson("/api/fusion/ecarter", "POST", { a: c.a, b: c.b });
            toast("Paire écartée : ne sera plus signalée en doublon.");
            fermerVolet(); aller("fusion");
          } catch (e) { toast(e.message); }
        } }, "Ce n'est pas un doublon"),
      h("button", { class: "bouton secondaire", onclick: fermerVolet }, "Annuler")));
  }
  rendre();
  ouvrirVolet(contenu, { titre: "Comparer & fusionner" });
}

async function lancerFusion(garde, absorbe, choix, forcer) {
  try {
    await apiJson("/api/fusion/personnes", "POST",
      { garde, absorbe, choix, forcer_sexe: forcer });
    toast("Fusion effectuée."); fermerVolet(); aller("fusion");
  } catch (e) {
    if (!forcer && /sexes différents/i.test(e.message || "")) {
      const ok = await confirmer(e.message + " Fusionner quand même ?",
        { titre: "Sexes différents", valider: "Fusionner", danger: true });
      if (ok) return lancerFusion(garde, absorbe, choix, true);
      return;
    }
    toast(e.message);
  }
}

// ── Lieux ──────────────────────────────────────────────────────────────────
async function chargerLieux(zone) {
  vider(zone);
  let d;
  try { d = await apiGet("/api/fusion/lieux"); }
  catch (e) { zone.append(h("div", { class: "vide" }, e.message)); return; }
  const groupes = d.groupes || [];
  if (!groupes.length) {
    zone.append(h("div", { class: "vide" }, h("span", { class: "grand" }, "🎉"), "Aucune variante d'orthographe détectée."));
    return;
  }
  groupes.forEach((g, gi) => {
    let canon = g.canonique;
    const carte = h("div", { class: "carte compacte" });
    carte.append(h("div", { style: "font-size:12px;color:var(--gris)" },
      g.total + " occurrence(s) · orthographe à conserver :"));
    const opts = h("div", { class: "rangee", style: "margin:8px 0" });
    g.variantes.forEach((v) => {
      opts.append(h("label", { style: "cursor:pointer;display:flex;align-items:center;gap:4px" },
        h("input", { type: "radio", name: "canon_" + gi,
          checked: v.nom === canon ? "checked" : null,
          onchange: () => { canon = v.nom; } }),
        h("span", {}, v.nom), badge(String(v.nb))));
    });
    carte.append(opts, h("div", { class: "barre-actions" },
      h("button", { class: "bouton petit", onclick: async () => {
        const absorbes = g.variantes.map((v) => v.nom).filter((n) => n !== canon);
        if (!absorbes.length) { toast("Rien à fusionner."); return; }
        try {
          const r = await apiJson("/api/fusion/lieux", "POST", { canonique: canon, absorbes });
          toast(r.modifies + " occurrence(s) réécrite(s) vers « " + canon + " »."); aller("fusion");
        } catch (e) { toast(e.message); }
      } }, "Fusionner ces variantes")));
    zone.append(carte);
  });
}
