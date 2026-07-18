// Onglet « Chronologie & contemporains » (L11) — deux vues :
//  • Contemporains d'une personne (qui vivait à la même époque, lié / sans lien)
//  • Frise multi-personnes (barres de vie sur un axe des années).
import { h, vider } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet } from "../noyau/api.js";
import { badge, pastilleSexe } from "../composants/badge.js";
import { toast } from "../composants/toast.js";
import { champPersonne } from "../composants/champ.js";

const COUL = { M: "var(--sexe-h)", F: "var(--sexe-f)", U: "var(--sexe-u)" };

function periode(p) {
  const n = p.naissance != null ? p.naissance : "?";
  const d = p.deces != null ? p.deces : "?";
  return n + "–" + d;
}

export async function vueContemporains(vue) {
  vue.append(h("h1", {}, "🕰 Chronologie & contemporains"));
  const liste = await apiGet("/api/individus").catch(() => []);
  if (!liste.length) {
    vue.append(h("div", { class: "vide" }, "Ouvrez un arbre pour explorer sa chronologie."));
    return;
  }
  let mode = "contemporains";
  const tabs = h("div", { class: "pers-tabs" });
  const panneau = h("div", { style: "margin-top:14px" });
  function majTabs() {
    vider(tabs);
    [["contemporains", "Contemporains d'une personne"], ["frise", "Frise multi-personnes"]]
      .forEach(([id, lib]) => tabs.append(h("button", {
        class: "pers-tab" + (mode === id ? " actif" : ""),
        onclick: () => { mode = id; majTabs(); rendre(); } }, lib)));
  }
  function rendre() {
    vider(panneau);
    if (mode === "contemporains") panelContemporains(panneau, liste);
    else panelFrise(panneau, liste);
  }
  vue.append(tabs, panneau);
  majTabs(); rendre();
}

// ── Contemporains d'une personne ────────────────────────────────────────────
function panelContemporains(zone, liste) {
  const pick = champPersonne(liste, { placeholder: "Choisir une personne…" });
  const sortie = h("div", { style: "margin-top:12px" });
  zone.append(h("div", { class: "carte", style: "max-width:520px" },
    h("label", {}, "Qui vivait à la même époque que…"), pick.element,
    h("div", { class: "barre-actions", style: "margin-top:8px" },
      h("button", { class: "bouton petit", onclick: () => charger() }, "Voir les contemporains"))),
    sortie);

  let filtre = "tous";
  async function charger() {
    const id = pick.valeur();
    if (!id) { toast("Choisissez une personne."); return; }
    vider(sortie);
    let c;
    try { c = await apiGet("/api/chronologie/contemporains?id=" + id); }
    catch (e) { sortie.append(h("div", { class: "vide" }, e.message)); return; }
    const [d0, f0] = c.intervalle;
    sortie.append(h("h2", {}, c.nom, h("span", { style: "color:var(--gris);font-weight:400;font-size:14px" },
      "  " + d0 + "–" + f0)));
    const chips = h("div", { class: "barre-actions", style: "margin:6px 0" });
    [["tous", "Tous (" + c.contemporains.length + ")"],
     ["lies", "Apparentés (" + c.nb_lies + ")"],
     ["sans", "Sans lien (" + c.nb_sans_lien + ")"]].forEach(([id2, lib]) =>
      chips.append(h("button", { class: "tri-chip" + (filtre === id2 ? " actif" : ""),
        onclick: () => { filtre = id2; liste2(); } }, lib)));
    const box = h("div", { class: "liste-pers" });
    sortie.append(chips, box);
    function liste2() {
      chips.querySelectorAll(".tri-chip").forEach((b) =>
        b.classList.toggle("actif", b.textContent.startsWith(
          { tous: "Tous", lies: "Apparentés", sans: "Sans lien" }[filtre])));
      vider(box);
      const lst = c.contemporains.filter((x) =>
        filtre === "tous" || (filtre === "lies" ? x.lie : !x.lie));
      if (!lst.length) { box.append(h("div", { class: "vide" }, "Personne dans ce filtre.")); return; }
      lst.forEach((x) => box.append(h("div", { class: "ligne-pers",
        onclick: () => aller("personnes", { fiche: x.id }) },
        pastilleSexe(x.sexe),
        h("span", { class: "nom" }, x.nom),
        h("span", { class: "meta" }, periode(x)),
        h("span", { class: "pousse" }),
        h("span", { class: "badge info" }, "≈ " + x.annees + " ans communs (" + x.chevauchement[0] + "–" + x.chevauchement[1] + ")"),
        x.lie ? badge("apparenté", "ok") : badge("sans lien"))));
    }
    liste2();
  }
}

// ── Frise multi-personnes ────────────────────────────────────────────────────
function panelFrise(zone, liste) {
  const choisis = [];                         // ids sélectionnés
  const pick = champPersonne(liste, { placeholder: "Ajouter une personne à la frise…" });
  const chips = h("div", { class: "barre-actions", style: "margin:8px 0" });
  const dessin = h("div", { style: "margin-top:12px;overflow-x:auto" });
  const nomDe = (id) => { const p = liste.find((x) => x.id === id); return p ? (p.nom || p.nom_complet || id) : id; };

  zone.append(h("div", { class: "carte", style: "max-width:560px" },
    h("label", {}, "Comparer les vies de plusieurs personnes"), pick.element,
    h("div", { class: "barre-actions", style: "margin-top:8px" },
      h("button", { class: "bouton petit", onclick: () => ajouter() }, "➕ Ajouter"),
      h("button", { class: "bouton secondaire petit", onclick: () => { choisis.length = 0; majChips(); rafraichir(); } }, "Vider"))),
    chips, dessin);

  function ajouter() {
    const id = pick.valeur();
    if (!id) { toast("Choisissez une personne."); return; }
    if (!choisis.includes(id)) { choisis.push(id); majChips(); rafraichir(); }
  }
  function majChips() {
    vider(chips);
    choisis.forEach((id) => chips.append(h("span", { class: "puce-pers" },
      nomDe(id), h("button", { class: "lien danger", style: "margin-left:6px",
        onclick: () => { choisis.splice(choisis.indexOf(id), 1); majChips(); rafraichir(); } }, "✕"))));
  }
  async function rafraichir() {
    vider(dessin);
    if (choisis.length < 1) { dessin.append(h("div", { class: "vide" }, "Ajoutez des personnes pour tracer la frise.")); return; }
    let f;
    try { f = await apiGet("/api/chronologie/frise?ids=" + choisis.join(",")); }
    catch (e) { dessin.append(h("div", { class: "vide" }, e.message)); return; }
    if (!f.personnes.length) { dessin.append(h("div", { class: "vide" }, "Aucune date exploitable pour ces personnes.")); return; }
    dessin.append(friseHTML(f));
  }
  rafraichir();
}

function friseHTML(f) {
  const min = f.min, max = f.max, span = Math.max(1, max - min);
  const pct = (an) => ((an - min) / span * 100);
  const box = h("div", { style: "min-width:640px" });
  // axe : quelques repères décennaux
  const axe = h("div", { style: "position:relative;height:18px;margin-left:170px;border-bottom:1px solid var(--bord)" });
  const pas = span <= 60 ? 10 : (span <= 150 ? 25 : 50);
  for (let an = Math.ceil(min / pas) * pas; an <= max; an += pas) {
    axe.append(h("span", { style: "position:absolute;left:" + pct(an) + "%;font-size:10px;color:var(--gris);transform:translateX(-50%)" }, String(an)));
  }
  box.append(axe);
  f.personnes.forEach((p) => {
    const track = h("div", { style: "position:relative;height:20px;flex:1;background:var(--sauge-pale);border-radius:11px" });
    const barre = h("div", { title: periode(p) + (p.estime ? " (fin estimée)" : ""),
      style: "position:absolute;top:2px;height:16px;border-radius:8px;left:" + pct(p.debut) + "%;"
        + "width:" + Math.max(1, pct(p.fin) - pct(p.debut)) + "%;background:" + (COUL[p.sexe] || COUL.U)
        + (p.estime ? ";opacity:.55;border:1px dashed var(--bord)" : "") });
    track.append(barre);
    box.append(h("div", { style: "display:flex;align-items:center;gap:8px;margin:5px 0" },
      h("span", { style: "width:162px;flex:none;font-size:13px;text-align:right;cursor:pointer;overflow:hidden;text-overflow:ellipsis;white-space:nowrap",
        onclick: () => aller("personnes", { fiche: p.id }) }, p.nom + " "),
      track,
      h("span", { style: "width:70px;flex:none;font-size:11px;color:var(--gris)" }, periode(p))));
  });
  return box;
}
