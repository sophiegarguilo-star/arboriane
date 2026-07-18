// Bloc « personnes citées par cette source » — l'indexation des noms.
//
// Un acte ne concerne presque jamais une seule personne : l'acte de naissance
// cite l'enfant ET ses parents, le recensement tout un foyer, le mariage les
// deux époux et leurs témoins. On saisit ces rattachements au moment où on
// décrit la source, pas plus tard dans un écran séparé qu'on n'ouvrira jamais.
import { h } from "../../noyau/dom.js";
import { champPersonne } from "../../composants/champ.js";
import { ROLES } from "./commun.js";

// presets : [{id, role}] déjà cités. onChange : prévenu à chaque modification
// (le titre suggéré en dépend). Renvoie { element, valeurs() }.
export function blocPersonnes(personnes, { presets = [], libelle, aide, onChange } = {}) {
  const rows = [];
  const liste = h("div", {});
  const prevenir = () => { if (onChange) onChange(); };

  function ligne(preset) {
    // onChoix, et non un écouteur « change » : le composant annonce la personne
    // retenue par ce rappel — un clic dans sa liste n'émet aucun événement DOM.
    const pick = champPersonne(personnes, { placeholder: "Rechercher une personne…",
      initial: (preset && preset.id) || "", onChoix: prevenir });
    const selRole = h("select", { style: "width:100%" }, ...ROLES.map((r) =>
      h("option", { value: r, selected: preset && preset.role === r ? "selected" : null }, r)));
    selRole.addEventListener("change", prevenir);
    const entree = { pick, selRole };
    const retirer = h("button", { class: "bouton fantome petit", title: "Retirer",
      onclick: () => {
        entree.ligne.remove();
        const i = rows.indexOf(entree); if (i >= 0) rows.splice(i, 1);
        prevenir();
      } }, "✕");
    entree.ligne = h("div", { style: "display:flex;gap:8px;align-items:center;margin-bottom:6px" },
      h("div", { style: "flex:1;min-width:0" }, pick.element),
      h("div", { style: "width:130px" }, selRole), retirer);
    rows.push(entree);
    liste.append(entree.ligne);
  }
  presets.forEach(ligne);

  const element = h("div", { class: "champ" },
    h("label", {}, libelle),
    h("p", { style: "color:var(--gris);font-size:13px;margin:2px 0 8px" }, aide),
    liste,
    h("button", { class: "bouton secondaire petit",
      onclick: () => { ligne(null); prevenir(); } }, "＋ Ajouter une personne"));

  // Une personne ne peut être citée qu'une fois : le dernier rôle choisi gagne.
  function valeurs() {
    const vus = new Set();
    const out = [];
    rows.forEach((r) => {
      const id = r.pick.valeur();
      if (id && !vus.has(id)) { vus.add(id); out.push({ id, role: r.selRole.value }); }
    });
    return out;
  }

  return { element, valeurs };
}
