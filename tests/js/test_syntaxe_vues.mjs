// GARDE-FOU COUCHE 1 — aucun fichier JS du front ne doit contenir de SyntaxError.
//
// Contexte : la 1.9.12 a livré une app qui ne DÉMARRAIT plus. `web/vues/depots.js`
// importait `ligneChamp` alors qu'il DÉFINISSAIT déjà cette fonction localement
// → `SyntaxError: Identifier 'ligneChamp' has already been declared`. Comme app.js
// importe statiquement toutes les vues au boot, un SEUL module qui refuse de se
// parser tue tout le démarrage. Invisible pour les tests backend (l'API répond).
//
// Principe : on passe CHAQUE fichier web/**/*.js (app.js inclus) à
// `node --check --input-type=module`. C'est un contrôle de SYNTAXE pur : aucune
// exécution, aucun DOM, aucune dépendance. Rapide et infalsifiable.
//
// Exécuter :  node --test tests/js/test_syntaxe_vues.mjs
import { test } from "node:test";
import assert from "node:assert";
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
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

test("tout le JavaScript du front se parse comme un module (aucune SyntaxError)", () => {
  const fautifs = [];
  for (const f of listerJs(WEB)) {
    const src = fs.readFileSync(f, "utf8");
    try {
      // Pas d'argument fichier : node lit le module sur stdin. --input-type=module
      // évite l'ambiguïté .js = CommonJS (où `import`/`export` seraient invalides).
      execFileSync(process.execPath, ["--check", "--input-type=module"],
        { input: src, stdio: ["pipe", "ignore", "pipe"] });
    } catch (e) {
      const details = String(e.stderr || e.message || e).split("\n")
        .map((l) => l.trim()).filter(Boolean).slice(0, 2).join(" — ");
      fautifs.push(path.relative(WEB, f) + " → " + details.slice(0, 180));
    }
  }
  assert.deepStrictEqual(fautifs, [],
    "Fichiers JS avec une SyntaxError (l'app ne démarrerait pas) :\n  " + fautifs.join("\n  "));
});
