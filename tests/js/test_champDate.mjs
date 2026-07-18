// Sélecteur de date : format INTERNE français.
// L'éditeur relit une date française (« 20/07/1984 », « vers 1850 ») pour
// pré-remplir ses champs, et re-sérialise en français. La traduction GEDCOM se
// fait ailleurs (import/export). Ce test verrouille la langue interne.
//
//   node --test tests/js/test_champDate.mjs
import { test } from "node:test";
import assert from "node:assert/strict";

const { _analyser, _serialiserBloc, _bloc } = await import("../../web/composants/champDate.js");

test("analyse une date exacte française", () => {
  const e = _analyser("20/07/1984");
  assert.equal(e.prec, "exacte");
  assert.deepEqual([e.j, e.m, e.a], ["20", "7", "1984"]);
});

test("analyse mois+année et année seule", () => {
  assert.deepEqual(_bloc("07/1984"), { j: "", m: "7", a: "1984" });
  assert.deepEqual(_bloc("1984"), { j: "", m: "", a: "1984" });
});

test("analyse les préfixes français", () => {
  assert.equal(_analyser("vers 1850").prec, "ABT");
  assert.equal(_analyser("avant 1900").prec, "BEF");
  assert.equal(_analyser("après 1800").prec, "AFT");
  assert.equal(_analyser("estimé 1750").prec, "EST");
});

test("analyse un intervalle « entre … et … »", () => {
  const e = _analyser("entre 1850 et 1860");
  assert.equal(e.prec, "BET");
  assert.equal(e.a, "1850");
  assert.equal(e.a2, "1860");
});

test("sérialise en français, avec zéro initial", () => {
  assert.equal(_serialiserBloc("5", "1", "1900"), "05/01/1900");
  assert.equal(_serialiserBloc("", "7", "1984"), "07/1984");
  assert.equal(_serialiserBloc("", "", "1984"), "1984");
  assert.equal(_serialiserBloc("", "", ""), "");
});

test("aucun mois anglais dans la sortie", () => {
  const out = _serialiserBloc("20", "7", "1984");
  assert.doesNotMatch(out, /JAN|JUL|MAR|DEC/);
  assert.equal(out, "20/07/1984");
});
