// GARDE-FOU COUCHE 2 — chaque vue/composant doit se CHARGER sans erreur.
//
// Le contrôle de syntaxe (test_syntaxe_vues) attrape les SyntaxError. Ici on va
// plus loin : on IMPORTE réellement chaque module sous un stub DOM. Cela attrape
// aussi ce qui se parse bien mais échoue au CHARGEMENT — un chemin d'import
// erroné, un symbole importé qui n'est pas (ou plus) exporté, une erreur levée
// au niveau haut d'un module. Autant de causes d'écran cassé invisibles côté API.
//
// On n'importe PAS app.js : son boot() lance des timers/fetch asynchrones (bruit
// ingérable pour node --test). Comme app.js importe statiquement toutes ces vues,
// une erreur de chargement dans l'une d'elles est détectée en l'important ici.
//
// Exécuter :  node --test tests/js/test_vues_chargent.mjs
import { test } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const ICI = path.dirname(fileURLToPath(import.meta.url));
const WEB = path.resolve(ICI, "..", "..", "web");

// Le boot éventuel d'un module peut produire du bruit asynchrone APRÈS le test
// (le stub n'est pas un vrai navigateur) : on ne veut pas qu'il fasse échouer le
// run. On ne teste que le CHARGEMENT (erreurs synchrones à l'import).
process.on("unhandledRejection", () => {});
process.on("uncaughtException", () => {});

// ── Stub navigateur minimal : au CHARGEMENT, les modules ne font que RÉFÉRENCER
// document/window/localStorage/etc. — il suffit qu'ils existent. ──
function noeud() {
  return new Proxy(function () {}, {
    get: (_t, k) => {
      if (k === "style" || k === "classList" || k === "dataset") return noeud();
      if (k === "children" || k === "childNodes") return [];
      if (typeof k === "string") return () => noeud();
      return undefined;
    },
    apply: () => noeud(),
  });
}
function poser(nom, val) {                 // affectation défensive : certains globals
  try {                                    // Node sont en lecture seule (navigator…)
    Object.defineProperty(globalThis, nom, { value: val, configurable: true, writable: true });
  } catch { /* on garde celui de Node */ }
}
poser("document", noeud());
poser("window", globalThis);
poser("localStorage", noeud());
poser("location", { hash: "", href: "http://127.0.0.1/", reload() {} });
poser("history", { pushState() {}, back() {} });
poser("addEventListener", () => {});
poser("matchMedia", () => ({ matches: false, addEventListener() {} }));
poser("fetch", () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}), text: () => Promise.resolve("") }));
poser("requestAnimationFrame", (f) => setTimeout(f, 0));

function listerJs(dir) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...listerJs(p));
    else if (e.name.endsWith(".js")) out.push(p);
  }
  return out;
}

const cibles = [
  ...listerJs(path.join(WEB, "vues")),
  ...listerJs(path.join(WEB, "composants")),
];

test("toutes les vues et composants se chargent sans erreur", async () => {
  const echecs = [];
  for (const f of cibles) {
    try {
      await import(pathToFileURL(f).href);
    } catch (e) {
      const msg = String(e && (e.message || e));
      echecs.push(path.relative(WEB, f) + " → " + e.constructor.name + ": " + msg.slice(0, 160));
    }
  }
  assert.deepStrictEqual(echecs, [],
    "Modules qui NE SE CHARGENT PAS (l'app ne démarrerait pas) :\n  " + echecs.join("\n  "));
});
