// Onglet Sosa — ascendance numérotée d'un de cujus.
import { h, vider } from "../noyau/dom.js";
import { aller, etat, majEspace } from "../noyau/etat.js";
import { apiGet } from "../noyau/api.js";
import { champPersonne } from "../composants/champ.js";
import { badge, pastilleSexe } from "../composants/badge.js";

// Noms des générations d'ascendance (g.generation : 1 = parents, 2 = grands-…).
const NOMS_GEN = {
  1: "Parents", 2: "Grands-parents", 3: "Arrière-grands-parents",
  4: "Trisaïeuls", 5: "Quadrisaïeuls", 6: "Quintaïeuls",
  7: "Sextaïeuls", 8: "Septaïeuls", 9: "Octaïeuls", 10: "Nonaïeuls",
};

export async function vueSosa(vue, arg) {
  const a = arg || {};
  vue.append(h("h1", {}, "Sosa"));
  vue.append(h("p", { class: "sous-titre" },
    "Ascendance numérotée : 1 = la personne, 2 = son père, 3 = sa mère… "
    + "Les ruptures montrent où chercher pour remonter plus loin."));
  await majEspace(apiGet);
  const liste = await apiGet("/api/individus").catch(() => []);
  if (!liste.length) { vue.append(h("div", { class: "vide" }, "Arbre vide.")); return; }

  // État repris de l'historique (arg) si on revient ici, sinon valeurs par défaut :
  // ainsi « ← Retour » depuis une fiche redonne le MÊME de cujus et la MÊME
  // profondeur (mémoriser() garde l'arg à jour pour l'historique).
  let deCujus = a.deCujus || (etat.espace || {}).racine_id || liste[0].id;
  let generations = a.generations || 8;
  const memoriser = () => { etat.arg = { deCujus, generations }; };
  memoriser();
  const zone = h("div", {});

  const pick = champPersonne(liste, { initial: deCujus, placeholder: "De cujus…",
    onChoix: (id) => { if (id) { deCujus = id; memoriser(); charger(); } } });
  const selGen = h("select", {}, ...[5, 6, 7, 8, 10, 12].map((n) =>
    h("option", { value: n, selected: n === generations ? "selected" : null }, n + " générations")));
  selGen.addEventListener("change", () => { generations = +selGen.value; memoriser(); charger(); });
  vue.append(h("div", { class: "barre-actions", style: "margin-bottom:16px" },
    h("div", {}, h("label", {}, "Personne"), pick.element),
    h("div", {}, h("label", {}, "Profondeur"), selGen)));
  vue.append(zone);

  async function charger() {
    vider(zone);
    const s = await apiGet("/api/sosa?de_cujus=" + deCujus + "&generations=" + generations)
      .catch(() => null);
    if (!s) { zone.append(h("div", { class: "vide" }, "Impossible.")); return; }

    zone.append(h("div", { class: "stats" },
      stat(s.total_connus, "ancêtres connus"),
      stat(s.ruptures.length, "branches à explorer")));

    s.generations.forEach((g) => {
      if (g.generation === 0) return;
      const carte = h("div", { class: "carte" });
      const nomGen = NOMS_GEN[g.generation];
      carte.append(h("h2", {}, "Génération " + g.generation
        + (nomGen ? " — " + nomGen + " " : " "),
        badge(g.connus + " / " + g.attendus + " (" + g.taux + "%)",
          g.taux === 100 ? "ok" : g.taux >= 50 ? "info" : "attention")));
      const box = h("div", { class: "liste-pers compacte" });
      g.personnes.forEach((p) => box.append(h("div", {
        class: "ligne-pers", onclick: () => aller("personnes", { fiche: p.id }) },
        h("span", { class: "badge info" }, "Sosa " + p.sosa),
        pastilleSexe(p.sexe), h("span", { class: "nom" }, p.nom),
        h("span", { class: "meta" }, p.periode || "—"))));
      carte.append(box);
      zone.append(carte);
    });

    if (s.ruptures.length) {
      const carte = h("div", { class: "carte" });
      carte.append(h("h2", {}, "🔍 Branches à explorer (" + s.ruptures.length + ")"));
      carte.append(h("p", { class: "sous-titre" },
        "Ces personnes sont connues mais il leur manque un parent : c'est là qu'il faut chercher."));
      const box = h("div", { class: "liste-pers compacte" });
      s.ruptures.forEach((r) => box.append(h("div", {
        class: "ligne-pers", onclick: () => aller("personnes", { fiche: r.id }) },
        h("span", { class: "badge attention" }, "manque : " + r.manque),
        h("span", { class: "nom" }, r.nom),
        h("span", { class: "meta" }, "Sosa " + r.sosa))));
      carte.append(box);
      zone.append(carte);
    }
  }
  charger();
}

function stat(n, label) {
  return h("div", { class: "stat" }, h("strong", {}, String(n)), h("span", {}, label));
}
