// GARDE-FOU COUCHE 2 (statique) — aucune vue n'appelle un helper partagé sans
// l'importer (sinon « ReferenceError: X is not defined » AU RENDU).
//
// Contexte : la 1.9.11 a livré un écran BLANC (formulaire de source) parce que
// actes/formulaire.js appelait `ligneChamp(...)` sans l'importer — une erreur
// qui ne survient qu'au RENDU (dans le corps d'une fonction), donc invisible
// pour un simple import du module et pour les tests backend. Ce test l'attrape
// SANS exécuter le rendu : par analyse statique.
//
// Principe : on découvre TOUS les helpers exportés par web/composants/*.js et les
// web/vues/**/commun.js, puis on vérifie que chaque vue qui APPELLE `helper(...)`
// l'importe (ou le définit / ré-exporte localement).
//
// Exécuter :  node --test tests/js/test_imports_vues.mjs
import { test } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ICI = path.dirname(fileURLToPath(import.meta.url));
const WEB = path.resolve(ICI, "..", "..", "web");

function listerJs(dir) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...listerJs(p));
    else if (e.name.endsWith(".js")) out.push(p);
  }
  return out;
}

function nomsExportes(src) {
  const noms = new Set();
  let m;
  const re1 = /export\s+(?:async\s+)?function\s+([A-Za-z_$][\w$]*)/g;
  const re2 = /export\s+const\s+([A-Za-z_$][\w$]*)/g;
  const re3 = /export\s*\{([^}]*)\}/g;               // export { a, b as c } [from ...]
  while ((m = re1.exec(src))) noms.add(m[1]);
  while ((m = re2.exec(src))) noms.add(m[1]);
  while ((m = re3.exec(src))) {
    for (let part of m[1].split(",")) {
      part = part.trim();
      if (!part) continue;
      const as = part.split(/\s+as\s+/);
      noms.add((as[1] || as[0]).trim());
    }
  }
  return noms;
}

// 1) Ensemble des helpers PARTAGÉS (composants + commun des vues).
const fichiersPartages = [
  ...listerJs(path.join(WEB, "composants")),
  ...listerJs(path.join(WEB, "vues")).filter((f) => path.basename(f) === "commun.js"),
];
const helpers = new Set();
for (const f of fichiersPartages) for (const n of nomsExportes(fs.readFileSync(f, "utf8"))) helpers.add(n);
for (const trivial of ["h"]) helpers.delete(trivial);   // h est importé partout : bruit inutile

// 2) Pour chaque fichier de web/, repérer helper(...) appelé mais NON disponible.
function identifiantsImportes(src) {
  const dispo = new Set();
  let m;
  const imp = /import\s*(?:[\w$]+\s*,\s*)?\{([^}]*)\}\s*from/g;    // import { a, b as c } from
  while ((m = imp.exec(src))) {
    for (let part of m[1].split(",")) {
      part = part.trim(); if (!part) continue;
      const as = part.split(/\s+as\s+/);
      dispo.add((as[1] || as[0]).trim());
    }
  }
  const impDef = /import\s+([\w$]+)\s*,?\s*from|import\s+([\w$]+)\s+from/g; // import def from
  while ((m = impDef.exec(src))) dispo.add(m[1] || m[2]);
  // déstructuration (dont import dynamique : const { a, b } = await import(...))
  const des = /(?:const|let|var)\s*\{([^}]*)\}\s*=/g;
  while ((m = des.exec(src))) {
    for (let p of m[1].split(",")) {
      p = p.trim(); if (!p) continue;
      p = p.split(":");                       // { a: b } → nom local = b
      dispo.add((p[1] || p[0]).trim());
    }
  }
  // définitions/ré-exports locaux
  const def = /(?:function|const|let|var)\s+([A-Za-z_$][\w$]*)|export\s*\{([^}]*)\}/g;
  while ((m = def.exec(src))) {
    if (m[1]) dispo.add(m[1]);
    if (m[2]) for (let p of m[2].split(",")) { p = p.trim().split(/\s+as\s+/); dispo.add((p[1] || p[0]).trim()); }
  }
  return dispo;
}

test("aucune vue n'appelle un helper partagé sans l'importer", () => {
  const violations = [];
  for (const f of listerJs(WEB)) {
    if (fichiersPartages.includes(f)) continue;          // les définitions elles-mêmes
    const src = fs.readFileSync(f, "utf8");
    const dispo = identifiantsImportes(src);
    for (const nom of helpers) {
      if (dispo.has(nom)) continue;
      // appel bare `nom(` non précédé d'un point (évite les méthodes .nom())
      const re = new RegExp("(^|[^.\\w$])" + nom.replace(/[$]/g, "\\$") + "\\s*\\(", "m");
      if (re.test(src)) {
        violations.push(path.relative(WEB, f) + " → appelle « " + nom + " » sans l'importer");
      }
    }
  }
  assert.deepStrictEqual(violations, [],
    "Helpers utilisés sans import (ReferenceError au rendu) :\n  " + violations.join("\n  "));
});
