// Onglet Statistiques — portrait chiffré de l'arbre.
import { h } from "../noyau/dom.js";
import { apiGet } from "../noyau/api.js";

export async function vueStats(vue) {
  vue.append(h("h1", {}, "Statistiques"));
  const s = await apiGet("/api/statistiques").catch(() => null);
  if (!s) { vue.append(h("div", { class: "vide" }, "Impossible.")); return; }

  vue.append(h("div", { class: "stats" },
    stat(s.personnes, "personnes"),
    stat(s.familles, "familles"),
    stat(s.sources, "sources"),
    stat(s.sexes.M, "hommes"),
    stat(s.sexes.F, "femmes"),
    stat(s.age_median != null ? s.age_median + " ans" : "—", "âge médian au décès"),
    stat(s.enfants_moyen != null ? s.enfants_moyen : "—", "enfants / couple")));

  // complétude (barres)
  const comp = h("div", { class: "carte" }, h("h2", {}, "Complétude"));
  const libelles = {
    date_naissance: "Date de naissance", au_moins_un_parent: "Au moins un parent",
    lieu_naissance: "Lieu de naissance", source: "Au moins une source",
    fiche_complete: "Fiche complète (date + parent + lieu)",
  };
  Object.entries(s.completude).forEach(([cle, pct]) => {
    comp.append(h("div", { style: "margin:8px 0" },
      h("div", { style: "display:flex;justify-content:space-between;font-size:13px" },
        h("span", {}, libelles[cle] || cle), h("span", {}, pct + " %")),
      h("div", { class: "barre-progres" },
        h("i", { style: "width:" + pct + "%" }))));
  });
  vue.append(comp);

  // par siècle
  if (s.par_siecle.length) {
    const carte = h("div", { class: "carte" }, h("h2", {}, "Naissances par siècle"));
    const max = Math.max(...s.par_siecle.map((x) => x.n));
    s.par_siecle.forEach((x) => carte.append(h("div", {
      class: "rangee", style: "margin:4px 0" },
      h("span", { style: "width:60px;color:var(--gris)" }, x.siecle + "ᵉ s."),
      h("div", { class: "barre-progres", style: "flex:1" },
        h("i", { style: "width:" + (x.n / max * 100) + "%;background:var(--vert-clair)" })),
      h("span", { style: "width:36px;text-align:right" }, String(x.n)))));
    vue.append(carte);
  }

  // patronymes & prénoms fréquents (deux colonnes)
  const cols = h("div", { class: "grille-cartes" });
  const pat = tableFreq("Patronymes les plus portés", s.patronymes_frequents);
  const pre = tableFreq("Prénoms les plus donnés", s.prenoms_frequents);
  if (pat) cols.append(pat);
  if (pre) cols.append(pre);
  if (cols.children.length) vue.append(cols);

  // lieux fréquents
  if (s.lieux_frequents.length) {
    const carte = h("div", { class: "carte" }, h("h2", {}, "Lieux les plus fréquents"));
    s.lieux_frequents.forEach((l) => carte.append(h("div", {
      style: "display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid var(--bord)" },
      h("span", {}, l.lieu), h("span", { class: "badge" }, String(l.n)))));
    vue.append(carte);
  }
}

function tableFreq(titre, items) {
  if (!items || !items.length) return null;
  const carte = h("div", { class: "carte" }, h("h2", {}, titre));
  items.forEach((it) => carte.append(h("div", {
    style: "display:flex;justify-content:space-between;padding:3px 0;border-bottom:1px solid var(--bord)" },
    h("span", {}, it.valeur), h("span", { class: "badge" }, String(it.n)))));
  return carte;
}

function stat(n, label) {
  return h("div", { class: "stat" }, h("strong", {}, String(n)), h("span", {}, label));
}
