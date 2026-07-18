// Tests du noyau DOM (web/noyau/dom.js).
//
// h() est la fonction la plus utilisée de toute l'interface : chaque écran la
// convoque des dizaines de fois. Si elle se casse, tout se casse. Neuf mille
// lignes de front n'avaient aucun test — celui-ci pose la première pierre.
//
//   node --test tests/js/
import { test } from "node:test";
import assert from "node:assert/strict";
import { installerDOM } from "./stub-dom.mjs";

installerDOM();
const { h, vider, echapper } = await import("../../web/noyau/dom.js");

test("h crée un élément du bon tag", () => {
  assert.equal(h("div").tagName, "DIV");
  assert.equal(h("span").tagName, "SPAN");
});

test("class devient className, pas un attribut", () => {
  const el = h("div", { class: "carte active" });
  assert.equal(el.className, "carte active");
  assert.equal(el.getAttribute("class"), null);
});

test("un attribut on… devient un écouteur, pas un attribut", () => {
  let clics = 0;
  const el = h("button", { onclick: () => clics++ });
  assert.equal(el.getAttribute("onclick"), null);
  assert.equal(el.listeners.click.length, 1);
  el.listeners.click[0]();
  assert.equal(clics, 1);
});

test("un style objet est fusionné dans element.style", () => {
  const el = h("div", { style: { color: "red", display: "flex" } });
  assert.equal(el.style.color, "red");
  assert.equal(el.style.display, "flex");
});

test("les attributs null / false / undefined sont ignorés", () => {
  const el = h("div", { title: null, hidden: false, "data-x": undefined, id: "ok" });
  assert.equal(el.getAttribute("title"), null);
  assert.equal(el.getAttribute("hidden"), null);
  assert.equal(el.getAttribute("data-x"), null);
  assert.equal(el.getAttribute("id"), "ok");
});

test("un enfant null / false / '' est ignoré (conditions en ligne)", () => {
  const el = h("div", {}, "a", null, false, "", "b");
  assert.equal(el.childNodes.length, 2);
  assert.equal(el.textContent, "ab");
});

test("un enfant texte devient un nœud texte", () => {
  const el = h("div", {}, "bonjour");
  assert.equal(el.childNodes[0].nodeType, 3);
  assert.equal(el.textContent, "bonjour");
});

test("un enfant élément est inséré tel quel", () => {
  const enfant = h("span", {}, "x");
  const el = h("div", {}, enfant);
  assert.equal(el.childNodes[0], enfant);
});

test("les enfants passés en tableau sont aplatis", () => {
  const el = h("ul", {}, [h("li", {}, "1"), h("li", {}, "2")]);
  assert.equal(el.childNodes.length, 2);
});

test("vider retire tous les enfants", () => {
  const el = h("div", {}, "a", "b", "c");
  assert.equal(el.childNodes.length, 3);
  vider(el);
  assert.equal(el.childNodes.length, 0);
});

test("echapper neutralise le HTML", () => {
  assert.equal(echapper("<b>&\"</b>"), "&lt;b&gt;&amp;\"&lt;/b&gt;");
});
