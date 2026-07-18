// Éditeur de date généalogique → date FRANÇAISE (format interne d'Arboriane).
// Précision (exacte, vers, avant, après, entre, estimée, inconnue) + jour/mois/
// année. Renvoie { element, valeur() } où valeur() donne la date en français
// (« 05/01/1900 », « vers 1900 », « entre 1900 et 1910 »…). La conversion vers
// la norme GEDCOM (« 5 JAN 1900 », « ABT 1900 ») se fait à l'export.
import { h } from "../noyau/dom.js";

const MOIS_GED = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
const MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                 "août", "septembre", "octobre", "novembre", "décembre"];
const PRECISIONS = [["exacte", "Exacte"], ["ABT", "Vers (~)"], ["BEF", "Avant"],
                    ["AFT", "Après"], ["BET", "Entre…et…"], ["EST", "Estimée"], ["?", "Inconnue"]];

// Exportées pour les tests (logique pure, sans DOM) — voir tests/js/test_champDate.mjs.
export { analyser as _analyser, _serialiserBloc, _bloc };

// Analyse une date FRANÇAISE (« 20/07/1984 », « vers 1850 », « entre … et … »)
// pour pré-remplir l'éditeur. Le format interne d'Arboriane est le français ;
// la traduction GEDCOM se fait au moment de l'import/export, pas ici.
const _PREF_FR = [["vers", "ABT"], ["avant", "BEF"], ["après", "AFT"],
  ["apres", "AFT"], ["estimé", "EST"], ["estime", "EST"],
  ["calculé", "EST"], ["calcule", "EST"]];

function analyser(s) {
  s = (s || "").trim();
  const vide = { prec: "exacte", j: "", m: "", a: "", j2: "", m2: "", a2: "" };
  if (!s) return vide;
  const bas = s.toLowerCase();
  const e = bas.match(/^entre\s+(.+?)\s+et\s+(.+)$/);
  if (e) {
    const d1 = _bloc(e[1]), d2 = _bloc(e[2]);
    return { prec: "BET", ...d1, j2: d2.j, m2: d2.m, a2: d2.a };
  }
  for (const [mot, code] of _PREF_FR) {
    if (bas.startsWith(mot + " ")) return { ...vide, prec: code, ..._bloc(s.slice(mot.length + 1)) };
  }
  return { ...vide, prec: "exacte", ..._bloc(s) };
}

// « 20/07/1984 » → {j,m,a} ; « 07/1984 » → mois+année ; « 1984 » → année seule.
function _bloc(s) {
  s = s.trim();
  let m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{1,4})$/);
  if (m) return { j: String(+m[1]), m: String(+m[2]), a: m[3] };
  m = s.match(/^(\d{1,2})\/(\d{1,4})$/);
  if (m) return { j: "", m: String(+m[1]), a: m[2] };
  m = s.match(/^(\d{3,4})$/);
  if (m) return { j: "", m: "", a: m[1] };
  return { j: "", m: "", a: "" };
}

function _pad2(x) { x = String(x).trim(); return x.length < 2 ? "0" + x : x; }

function _serialiserBloc(j, m, a) {
  if (!a) return "";
  if (j && m) return _pad2(j) + "/" + _pad2(m) + "/" + a;
  if (m) return _pad2(m) + "/" + a;
  return a;
}

export function champDate(valeurInitiale) {
  const e = analyser(valeurInitiale);
  const selPrec = h("select", { style: "width:110px" }, ...PRECISIONS.map(([v, l]) =>
    h("option", { value: v, selected: e.prec === v ? "selected" : null }, l)));
  const inpJ = h("input", { type: "number", min: 1, max: 31, placeholder: "jj", value: e.j, style: "width:56px" });
  const selM = h("select", { style: "width:110px" }, h("option", { value: "" }, "mois"),
    ...MOIS_FR.map((nom, i) => h("option", { value: i + 1, selected: e.m == i + 1 ? "selected" : null }, nom)));
  const inpA = h("input", { type: "number", placeholder: "année", value: e.a, style: "width:78px" });
  const inpJ2 = h("input", { type: "number", min: 1, max: 31, placeholder: "jj", value: e.j2, style: "width:56px" });
  const selM2 = h("select", { style: "width:110px" }, h("option", { value: "" }, "mois"),
    ...MOIS_FR.map((nom, i) => h("option", { value: i + 1, selected: e.m2 == i + 1 ? "selected" : null }, nom)));
  const inpA2 = h("input", { type: "number", placeholder: "année", value: e.a2, style: "width:78px" });

  const ligne1 = h("div", { style: "display:flex;gap:6px;flex-wrap:wrap;align-items:center" },
    selPrec, inpJ, selM, inpA);
  const ligne2 = h("div", { style: "display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:6px;display:none" },
    h("span", { style: "color:var(--gris);font-size:13px" }, "et"), inpJ2, selM2, inpA2);

  function maj() { ligne2.style.display = selPrec.value === "BET" ? "flex" : "none"; }
  selPrec.addEventListener("change", maj); maj();

  // Assistant « date républicaine » (repliable) : convertit vers le grégorien.
  const inpRep = h("input", { placeholder: "ex. 12 germinal an III", style: "flex:1;min-width:170px" });
  const avis = h("span", { style: "font-size:12px;color:var(--gris-clair)" });
  const btnRep = h("button", { type: "button", class: "bouton secondaire petit" }, "→ grégorien");
  btnRep.addEventListener("click", async () => {
    const t = inpRep.value.trim();
    if (!t) return;
    try {
      const r = await fetch("/api/date/convertir?texte=" + encodeURIComponent(t)).then((x) => x.json());
      if (r.gregorien) {
        const [jj, mm, aa] = r.gregorien.split("/");
        inpJ.value = String(+jj); selM.value = String(+mm); inpA.value = aa;
        selPrec.value = "exacte"; maj();
        avis.textContent = "= " + r.gregorien;
      } else { avis.textContent = "date non reconnue"; }
    } catch (e) { avis.textContent = ""; }
  });
  const ligneRep = h("div", { style: "display:none;gap:6px;flex-wrap:wrap;align-items:center;margin-top:6px" },
    inpRep, btnRep, avis);
  const toggleRep = h("button", { type: "button", class: "lien",
    style: "font-size:11px;margin-top:4px" },
    "＋ date républicaine");
  toggleRep.addEventListener("click", () => {
    ligneRep.style.display = ligneRep.style.display === "none" ? "flex" : "none";
  });

  return {
    element: h("div", {}, ligne1, ligne2, toggleRep, ligneRep),
    valeur() {
      const p = selPrec.value;
      if (p === "?") return "";
      const b1 = _serialiserBloc(inpJ.value.trim(), selM.value, inpA.value.trim());
      if (!b1) return "";
      if (p === "exacte") return b1;
      if (p === "BET") {
        const b2 = _serialiserBloc(inpJ2.value.trim(), selM2.value, inpA2.value.trim());
        return b2 ? "entre " + b1 + " et " + b2 : "vers " + b1;
      }
      // format interne français ; la traduction GEDCOM se fait à l'export
      return ({ ABT: "vers", BEF: "avant", AFT: "après", EST: "estimé" }[p] || "vers") + " " + b1;
    },
  };
}
