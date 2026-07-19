// Onglet « Parenté avancée » (Lot 7) — implexe, consanguinité, Aboville,
// Sosa permanent. Le grisage des branches dans l'arbre est un chantier distinct
// (après découpage de arbre.py) — ici on ne fait que calculer et afficher.
import { h, vider, actionnable } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { badge } from "../composants/badge.js";
import { toast } from "../composants/toast.js";

export async function vueImplexe(vue) {
  vue.append(h("h1", {}, "🧬 Implexe & consanguinité"));
  vue.append(h("p", { class: "sous-titre" },
    "L'implexe (quand un même ancêtre revient par plusieurs branches), la "
    + "consanguinité, la numérotation d'Aboville et le Sosa permanent — calculés "
    + "à partir de la personne racine du dossier."));
  const cont = h("div", {});
  vue.append(cont);
  const [imp, inds, sp] = await Promise.all([
    apiGet("/api/implexe").catch(() => null),
    apiGet("/api/individus").catch(() => []),
    apiGet("/api/sosa-permanent").catch(() => ({ total: 0 })),
  ]);
  cont.append(carteImplexe(imp), carteConsang(inds), carteAboville(), carteSosaPerm(sp));
}

function stat(n, label, alerte) {
  return h("div", { class: "stat" },
    h("strong", { style: alerte && n ? "color:var(--alerte)" : "" }, String(n)),
    h("span", {}, label));
}

function carteImplexe(imp) {
  const c = h("div", { class: "carte" }, h("h2", {}, "Implexe"));
  if (!imp) {
    c.append(h("div", { class: "vide compacte" },
      "Aucune personne racine. Ouvrez une fiche et « définir comme racine »."));
    return c;
  }
  c.append(h("p", { class: "sous-titre" }, "Ascendance de " + imp.racine_nom + "."));
  c.append(h("div", { class: "stats" },
    stat(imp.taux + " %", "taux d'implexe"),
    stat(imp.ancetres_distincts, "ancêtres distincts"),
    stat(imp.implexe_total, "positions redondantes", true)));
  const gens = imp.generations.filter((g) => g.positions > 0);
  if (gens.length) {
    const t = h("table", { class: "tableau" },
      h("tr", {}, h("th", {}, "Génération"), h("th", {}, "Positions"),
        h("th", {}, "Distincts"), h("th", {}, "Implexe")));
    gens.forEach((g) => t.append(h("tr", {},
      h("td", {}, "G" + g.generation), h("td", {}, String(g.positions)),
      h("td", {}, String(g.distincts)),
      h("td", {}, g.implexe ? badge(String(g.implexe), "attention") : "0"))));
    c.append(t);
  }
  if (imp.ancetres_multiples.length) {
    const det = h("details", {}, h("summary", {},
      "Ancêtres à Sosa multiples (" + imp.ancetres_multiples.length + ")"));
    const box = h("div", { class: "liste-pers compacte" });
    imp.ancetres_multiples.forEach((m) => box.append(
      actionnable(h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: m.id }) },
        h("strong", {}, m.nom), h("span", { class: "meta" }, "Sosa " + m.sosas.join(", "))))));
    det.append(box); c.append(det);
  } else {
    c.append(h("div", { class: "vide compacte" },
      h("span", { class: "grand" }, "🎉"), "Aucun implexe détecté."));
  }
  return c;
}

function carteConsang(inds) {
  const c = h("div", { class: "carte" }, h("h2", {}, "Consanguinité d'un couple"),
    h("p", { class: "sous-titre" },
      "Coefficient de consanguinité de l'enfant de deux personnes (via leurs ancêtres communs)."));
  const tri = inds.slice().sort((a, b) => (a.nom || "").localeCompare(b.nom || ""));
  const faireSelect = (placeholder) => {
    const s = h("select", { style: "max-width:46%" });
    s.append(h("option", { value: "" }, placeholder));
    tri.forEach((p) => s.append(h("option", { value: p.id },
      p.nom + (p.periode ? " (" + p.periode + ")" : ""))));
    return s;
  };
  const selA = faireSelect("— conjoint 1 —");
  const selB = faireSelect("— conjoint 2 —");
  const res = h("div", { style: "margin-top:.7rem" });
  const btn = h("button", { class: "bouton" }, "Calculer");
  btn.onclick = async () => {
    if (!selA.value || !selB.value) { toast("Choisissez deux personnes."); return; }
    vider(res); res.append(h("p", { class: "message" }, "Calcul…"));
    try {
      const r = await apiGet("/api/consanguinite?a=" + encodeURIComponent(selA.value)
        + "&b=" + encodeURIComponent(selB.value));
      vider(res);
      res.append(h("p", {},
        h("strong", { style: r.consanguin ? "color:var(--alerte)" : "" }, r.pourcentage + " %"),
        " — coefficient " + r.coefficient.toFixed(5)));
      if (r.consanguin) {
        const box = h("div", { class: "liste-pers compacte" });
        r.ancetres_communs.forEach((a) => box.append(
          actionnable(h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: a.id }) },
            h("strong", {}, a.nom),
            h("span", { class: "meta" }, "apport " + (a.contribution * 100).toFixed(3) + " %")))));
        res.append(h("p", { class: "sous-titre" }, r.nb_ancetres_communs + " ancêtre(s) commun(s) :"), box);
      } else {
        res.append(h("div", { class: "vide compacte" },
          h("span", { class: "grand" }, "🎉"), "Aucun lien de consanguinité."));
      }
    } catch (e) { vider(res); res.append(h("p", { class: "message" }, e.message)); }
  };
  c.append(h("div", { class: "barre-actions" },
    selA, selB, btn), res);
  return c;
}

function carteAboville() {
  const c = h("div", { class: "carte" }, h("h2", {}, "Numérotation d'Aboville"),
    h("p", { class: "sous-titre" }, "Descendance numérotée (1, 1.1, 1.2.1…) à partir de la racine."));
  const zone = h("div", {});
  const btn = h("button", { class: "bouton" }, "Générer la liste");
  btn.onclick = async () => {
    btn.disabled = true; vider(zone); zone.append(h("p", { class: "message" }, "Calcul…"));
    try {
      const r = await apiGet("/api/aboville");
      vider(zone);
      zone.append(h("p", { class: "sous-titre" },
        r.total + " personnes dans la descendance de " + r.racine_nom + "."));
      const box = h("div", { class: "liste-pers compacte liste-defilante" });
      r.personnes.forEach((p) => box.append(
        actionnable(h("div", { class: "ligne-pers", onclick: () => aller("personnes", { fiche: p.id }) },
          h("strong", { style: "font-variant-numeric:tabular-nums" }, p.numero),
          h("span", { class: "meta" }, p.nom + (p.periode ? " · " + p.periode : ""))))));
      zone.append(box);
    } catch (e) { vider(zone); zone.append(h("p", { class: "message" }, e.message)); }
    btn.disabled = false;
  };
  c.append(btn, zone);
  return c;
}

function carteSosaPerm(sp) {
  const c = h("div", { class: "carte" }, h("h2", {}, "Sosa permanent"),
    h("p", { class: "sous-titre" },
      "Fige les numéros Sosa dans l'arbre (exportés en GEDCOM _SOSA). Le calcul à la volée reste la référence."));
  const etat = h("p", {}, sp && sp.total
    ? sp.total + " personnes portent un Sosa figé."
    : "Aucun Sosa figé pour l'instant.");
  const figer = h("button", { class: "bouton" }, "Figer depuis la racine");
  figer.onclick = async () => {
    figer.disabled = true;
    try {
      const r = await apiJson("/api/sosa-permanent/figer", "POST", {});
      toast(r.numerotees + " personnes numérotées.");
      aller("implexe");
    } catch (e) { toast(e.message, { type: "erreur" }); figer.disabled = false; }
  };
  const eff = h("button", { class: "bouton secondaire" }, "Effacer");
  eff.onclick = async () => {
    eff.disabled = true;
    try {
      const r = await apiJson("/api/sosa-permanent/effacer", "POST", {});
      toast(r.effacees + " Sosa effacés.");
      aller("implexe");
    } catch (e) { toast(e.message, { type: "erreur" }); eff.disabled = false; }
  };
  c.append(etat, h("div", { class: "barre-actions" }, figer, eff));
  return c;
}
