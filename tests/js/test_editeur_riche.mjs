// Éditeur enrichi des transcriptions : assainissement du HTML et rendu sûr.
// Exécuter :  node --test tests/js/test_editeur_riche.mjs
import { test } from "node:test";
import assert from "node:assert";
import { installerDOM } from "./stub-dom.mjs";

installerDOM();
const { assainirHtml, rendreTranscription, editeurRiche } =
  await import("../../web/composants/editeur_riche.js");

test("assainirHtml retire les scripts et leur contenu", () => {
  const sale = "<b>ok</b><script>alert(1)</script>fin";
  const propre = assainirHtml(sale);
  assert.ok(!/script/i.test(propre), "le <script> doit disparaître");
  assert.ok(!propre.includes("alert(1)"), "le contenu du script doit disparaître");
  assert.ok(propre.includes("<b>ok</b>"), "le gras autorisé reste");
});

test("assainirHtml retire les attributs (onclick, style, src)", () => {
  const propre = assainirHtml('<b onclick="alert(1)">x</b>');
  assert.strictEqual(propre, "<b>x</b>");
  assert.ok(!/onclick/i.test(propre));
});

test("assainirHtml retire les balises non autorisées mais garde le texte", () => {
  const propre = assainirHtml('<img src=x onerror=y>texte<span style="color:red">rouge</span>');
  assert.ok(!/img|span|onerror/i.test(propre));
  assert.ok(propre.includes("texte"));
  assert.ok(propre.includes("rouge"));
});

test("assainirHtml conserve la liste blanche et normalise <br>", () => {
  const propre = assainirHtml("<ul><li>a</li><li>b</li></ul><p>c</p><br/>");
  assert.ok(propre.includes("<ul>") && propre.includes("<li>a</li>"));
  assert.ok(propre.includes("<p>c</p>"));
  assert.ok(propre.includes("<br>"));
});

test("rendreTranscription échappe le texte simple", () => {
  const n = rendreTranscription("a < b & c\nligne2");
  assert.ok(n.innerHTML.includes("&lt;"), "le < doit être échappé");
  assert.ok(n.innerHTML.includes("&amp;"), "le & doit être échappé");
  assert.ok(!n.innerHTML.includes("<b>"), "aucune balise de mise en forme ne doit apparaître");
  assert.ok(n.innerHTML.includes("<br>"), "les sauts de ligne deviennent <br>");
});

test("rendreTranscription assainit le HTML fourni", () => {
  const n = rendreTranscription("<b>gras</b><script>mauvais()</script>");
  assert.ok(n.innerHTML.includes("<b>gras</b>"));
  assert.ok(!/script/i.test(n.innerHTML));
});

test("editeurRiche : getHtml assainit ce qui est dans la zone", () => {
  const ed = editeurRiche({ html: "<b>départ</b>" });
  assert.ok(ed.element, "expose element");
  // simule une saisie polluée directement dans la zone contenteditable
  ed.setHtml('<i>ital</i><script>x()</script><span onclick="h()">s</span>');
  const html = ed.getHtml();
  assert.ok(html.includes("<i>ital</i>"));
  assert.ok(!/script|onclick|span/i.test(html));
});
