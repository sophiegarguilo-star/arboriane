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

const { bilanImport, messageNonLues, resumeNonLues } =
  await import("../../web/composants/bilanImport.js");

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

// ── PARC-11 : balises non reprises ────────────────────────────────────────

test("resumeNonLues : tri par fréquence et total", () => {
  const r = resumeNonLues({ BAPL: 2, AGE: 5, SLGC: 1 });
  assert.equal(r.total, 8);
  assert.deepEqual(r.entrees[0], ["AGE", 5]);
});

test("resumeNonLues : rien à dire -> null", () => {
  assert.equal(resumeNonLues({}), null);
  assert.equal(resumeNonLues(undefined), null);
  assert.equal(resumeNonLues({ BAPL: 0 }), null);
});

test("messageNonLues : total, balises et conseil de garder le fichier", () => {
  const m = messageNonLues({ BAPL: 2, AGE: 1 });
  assert.match(m, /3 informations du fichier non reprises/);
  assert.match(m, /BAPL ×2/);
  assert.match(m, /Conservez votre fichier \.ged d'origine/);
});

test("messageNonLues : accord au singulier", () => {
  const m = messageNonLues({ SLGC: 1 });
  assert.match(m, /1 information du fichier non reprise /);
  assert.match(m, /balise : SLGC ×1/);
});

test("bilanImport : non_lues apparaît dans le texte et allonge le toast", () => {
  const b = bilanImport({ personnes: 5, familles: 2, liens: 6,
                          non_lues: { BAPL: 2 } });
  assert.equal(b.alerte, true);
  assert.match(b.texte, /2 informations du fichier non reprises/);
});

test("bilanImport : sans non_lues, rien ne change", () => {
  const b = bilanImport({ personnes: 5, familles: 2, liens: 6, non_lues: {} });
  assert.equal(b.alerte, false);
  assert.doesNotMatch(b.texte, /non reprise/);
});

test("bilanImport : hors navigateur, le dépliant est null (pas de plantage)", () => {
  const b = bilanImport({ personnes: 5, familles: 2, liens: 6,
                          non_lues: { BAPL: 1 } });
  assert.equal(b.detail, null);
});
