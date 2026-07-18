// Champ « choisir une source » : autocomplétion cherchable par titre (+ cote,
// lieu, date pour désambiguïser les homonymes), navigable au clavier et
// accessible (ARIA combobox). Calqué sur champPersonne (composants/champ.js) —
// même API { element, valeur(), definir(id), vider() } — pour un menu déroulant
// utilisable même avec des milliers de sources.
import { h, vider } from "../noyau/dom.js";

let _seq = 0;

export function champSource(liste, { placeholder = "Rechercher une source par titre…",
                                     initial = "", onChoix } = {}) {
  let choisi = initial || "";
  let actif = -1;
  const idMenu = "cs-menu-" + (++_seq);
  const tri = [...liste].sort((a, b) => (a.titre || "").localeCompare(b.titre || "", "fr"));

  const input = h("input", { type: "search", placeholder, autocomplete: "off",
    role: "combobox", "aria-autocomplete": "list", "aria-expanded": "false",
    "aria-controls": idMenu, style: "width:100%" });
  const menu = h("div", { class: "champ-menu", id: idMenu, role: "listbox" });
  const boite = h("div", { class: "champ-auto" }, input, menu);
  let options = [];

  const _sub = (s) => [s.date, s.type, s.lieu, s.cote].filter(Boolean).join(" · ");
  function poser(s) { if (s) input.value = s.titre || s.id; }
  if (initial) poser(tri.find((x) => x.id === initial));

  function fermer() { menu.classList.remove("on"); input.setAttribute("aria-expanded", "false"); actif = -1; }
  function surligner(n) {
    options.forEach((o, k) => o.classList.toggle("actif", k === n));
    if (options[n]) options[n].scrollIntoView({ block: "nearest" });
    actif = n;
  }
  function choisir(s) {
    choisi = s.id; poser(s); fermer();
    if (onChoix) onChoix(choisi);
  }
  function ouvrir(filtre) {
    vider(menu); options = [];
    const q = (filtre || "").trim().toLowerCase();
    const res = tri.filter((s) => !q ||
      (s.titre + " " + (s.cote || "") + " " + (s.lieu || "")).toLowerCase().includes(q)).slice(0, 40);
    if (!res.length) { fermer(); return; }
    res.forEach((s) => {
      const sub = _sub(s);
      const o = h("div", { class: "champ-option", role: "option",
        onmousedown: (e) => { e.preventDefault(); choisir(s); } },
        h("span", {}, s.titre || s.id),
        sub ? h("span", { style: "color:var(--gris-clair);font-size:12px;margin-left:8px" }, sub) : null);
      menu.append(o); options.push(o);
    });
    menu.classList.add("on"); input.setAttribute("aria-expanded", "true"); actif = -1;
  }

  input.addEventListener("input", () => { choisi = ""; ouvrir(input.value); });
  input.addEventListener("focus", () => ouvrir(input.value));
  input.addEventListener("keydown", (e) => {
    if (!menu.classList.contains("on")) { if (e.key === "ArrowDown") ouvrir(input.value); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); surligner(Math.min(actif + 1, options.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); surligner(Math.max(actif - 1, 0)); }
    else if (e.key === "Enter" && actif >= 0) { e.preventDefault(); options[actif].dispatchEvent(new Event("mousedown")); }
    else if (e.key === "Escape") { fermer(); }
  });
  document.addEventListener("click", (e) => { if (!boite.contains(e.target)) fermer(); });

  return {
    element: boite,
    valeur: () => choisi,
    definir: (id) => { choisi = id; poser(tri.find((x) => x.id === id)); },
    vider: () => { choisi = ""; input.value = ""; },
  };
}
