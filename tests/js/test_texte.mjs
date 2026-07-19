// Tests de la normalisation de recherche (web/noyau/texte.js).
//
// normaliser() est appliquée AUX DEUX CÔTÉS de chaque comparaison de texte
// libre (recherche globale, filtres de listes, autocomplétions) : si elle
// dérive, « Génealogie » ne retrouve plus « généalogie » et toutes les
// recherches deviennent silencieusement à moitié sourdes.
//
//   node --test tests/js/
import { test } from "node:test";
import assert from "node:assert/strict";

const { normaliser } = await import("../../web/noyau/texte.js");

test("abaisse la casse", () => {
  assert.equal(normaliser("MARTIN"), "martin");
  assert.equal(normaliser("DuPont"), "dupont");
});

test("retire les diacritiques (é, è, ç, ï, ô…)", () => {
  assert.equal(normaliser("généalogie"), "genealogie");
  assert.equal(normaliser("François NOËL"), "francois noel");
  assert.equal(normaliser("Île-de-Française"), "ile-de-francaise");
});

test("les trois graphies du même mot se rejoignent", () => {
  const attendu = normaliser("genealogie");
  assert.equal(normaliser("Génealogie"), attendu);
  assert.equal(normaliser("GÉNÉALOGIE"), attendu);
});

test("entrées vides ou absentes → chaîne vide (jamais d'erreur)", () => {
  assert.equal(normaliser(""), "");
  assert.equal(normaliser(null), "");
  assert.equal(normaliser(undefined), "");
});

test("une valeur non-chaîne est convertie sans casser", () => {
  assert.equal(normaliser(1848), "1848");
});

test("ne touche ni les chiffres ni la ponctuation utile", () => {
  assert.equal(normaliser("Saint-Étienne (42)"), "saint-etienne (42)");
});
