// Tests du bouton « ← Retour » unifié (web/composants/boutonRetour.js).
//
// Règle maison : un retour revient à l'ÉCRAN PRÉCÉDENT (historique du routeur
// web/noyau/etat.js), jamais à une destination codée en dur ; le repli
// (repliVue) ne sert que si aucun écran n'est empilé. Plutôt que de mocker
// etat.js (lourd sans chargeur de modules), on pilote le VRAI routeur avec des
// vues factices : le stub DOM est complété du strict nécessaire à aller().
//
// Limite assumée du harnais : l'historique du routeur est un état de module
// partagé — les tests de ce fichier s'exécutent donc DANS L'ORDRE (repli
// d'abord, tant que l'historique est vide, puis historique). node --test les
// exécute séquentiellement dans un même fichier, c'est garanti.
//
//   node --test tests/js/
import { test } from "node:test";
import assert from "node:assert/strict";
import { installerDOM } from "./stub-dom.mjs";

installerDOM();
// compléments au stub, requis par aller() : le conteneur #vue, window.scrollTo
// et un localStorage muet (la mémorisation de la dernière vue est un confort).
const conteneurVue = globalThis.document.createElement("div");
globalThis.document.getElementById = () => conteneurVue;
globalThis.window = { scrollTo() {} };
globalThis.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };

const { VUES, etat, aller, peutRevenir } = await import("../../web/noyau/etat.js");
const { boutonRetour } = await import("../../web/composants/boutonRetour.js");

// Vues factices : elles notent leur rendu et n'ajoutent RIEN au conteneur
// (le stub ne déplace pas les nœuds comme le vrai DOM).
const rendus = [];
for (const nom of ["depart", "suivant", "repli"]) {
  VUES[nom] = async (_conteneur, arg) => { rendus.push({ nom, arg }); };
}

const clic = (bouton) => bouton.listeners.click[0]();

test("rendu : un vrai bouton, libellé par défaut et personnalisé", () => {
  const b = boutonRetour("repli");
  assert.equal(b.tagName, "BUTTON");
  assert.equal(b.textContent, "← Retour");
  assert.equal(b.listeners.click.length, 1);
  assert.equal(boutonRetour("repli", null, "← Fiche").textContent, "← Fiche");
});

test("sans historique : le clic va au REPLI", async () => {
  assert.equal(peutRevenir(), false);          // rien d'empilé au démarrage
  clic(boutonRetour("repli", { de: "test" }));
  await Promise.resolve();
  assert.equal(etat.vue, "repli");
  assert.deepEqual(rendus.at(-1), { nom: "repli", arg: { de: "test" } });
});

test("avec historique : le clic REVIENT à l'écran précédent (pas au repli)", async () => {
  await aller("depart", { fiche: "I1" });
  await aller("suivant");
  assert.equal(peutRevenir(), true);
  clic(boutonRetour("repli"));                 // repli fourni mais IGNORÉ
  await Promise.resolve();
  assert.equal(etat.vue, "depart");            // revenu d'où l'on venait…
  assert.deepEqual(etat.arg, { fiche: "I1" }); // …avec le même argument
  assert.notEqual(rendus.at(-1).nom, "repli");
});

test("le retour DÉPILE : il ne rallonge pas l'historique", async () => {
  // après le retour précédent, revenir encore doit dépiler vers « repli »
  assert.equal(peutRevenir(), true);
  clic(boutonRetour("depart"));
  await Promise.resolve();
  assert.equal(etat.vue, "repli");             // l'écran encore en dessous
});
