// Tests du bilan d'import GEDCOM (web/composants/bilanImport.js).
//
// C'est ce module qui décide du message montré après un import : « réussi »,
// « aucun lien lu », « fichier au format 7.0 »… Sa logique a une histoire —
// chaque cas correspond à un vrai problème d'utilisateur (Dominique, les
// fichiers 7.0). Un accord de pluriel ou un seuil qui bougerait passerait
// inaperçu sans ce test.
//
//   node --test tests/js/
import { test } from "node:test";
import assert from "node:assert/strict";

const { bilanImport } = await import("../../web/composants/bilanImport.js");

test("import sain : message simple, pas d'alerte", () => {
  const b = bilanImport({ personnes: 297, familles: 148, sources: 2, liens: 440,
                          liens_ignores: 0, version_fichier: "5.5.1" });
  assert.equal(b.alerte, false);
  assert.match(b.texte, /297 personnes, 148 familles, 2 sources/);
});

test("accord du pluriel (1 vs plusieurs)", () => {
  assert.match(bilanImport({ personnes: 1, familles: 0, liens: 0 }).texte,
               /^Import réussi : 1 personne\./);
  assert.match(bilanImport({ personnes: 3, familles: 1, liens: 2 }).texte,
               /3 personnes, 1 famille\./);
});

test("aucun lien lu : alerte explicite", () => {
  const b = bilanImport({ personnes: 297, familles: 148, liens: 0, liens_ignores: 0 });
  assert.equal(b.alerte, true);
  assert.match(b.texte, /Aucun lien de parenté/);
});

test("une seule personne sans lien n'est pas une alerte", () => {
  const b = bilanImport({ personnes: 1, familles: 0, liens: 0 });
  assert.equal(b.alerte, false);
});

test("liens ignorés : alerte chiffrée", () => {
  const b = bilanImport({ personnes: 10, familles: 4, liens: 12, liens_ignores: 3 });
  assert.equal(b.alerte, true);
  assert.match(b.texte, /3 liens de parenté/);
});

test("fichier GEDCOM 7.0 : alerte de version, prioritaire", () => {
  const b = bilanImport({ personnes: 8, familles: 3, liens: 10, version_fichier: "7.0" });
  assert.equal(b.alerte, true);
  assert.match(b.texte, /format GEDCOM 7\.0/);
  assert.match(b.texte, /Arboriane lit le 5\.5\.1/);
});

test("7.0.14 est aussi reconnu comme du 7", () => {
  assert.equal(bilanImport({ personnes: 2, liens: 2, version_fichier: "7.0.14" }).alerte, true);
});

test("5.5.1 et 5.5.5 ne déclenchent aucune alerte de version", () => {
  for (const v of ["5.5.1", "5.5.5", ""]) {
    const b = bilanImport({ personnes: 3, familles: 1, liens: 3, version_fichier: v });
    assert.equal(b.alerte, false, "version " + JSON.stringify(v));
  }
});
