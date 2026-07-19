// Champ « choisir une personne » : autocomplétion triée par nom de famille,
// navigable au clavier (↑/↓/Entrée/Échap) et accessible (ARIA combobox).
// Renvoie { element, valeur(), definir(id), vider() }.
import { h, vider } from "../noyau/dom.js";
import { normaliser } from "../noyau/texte.js";

let _seq = 0;

export function champPersonne(liste, { placeholder = "Rechercher une personne…",
                                       initial = "", onChoix } = {}) {
  let choisi = initial || "";
  let actif = -1;                       // option surlignée au clavier
  const idMenu = "cp-menu-" + (++_seq);
  const tri = [...liste].sort((a, b) =>
    (a.nom_famille || a.nom).localeCompare(b.nom_famille || b.nom, "fr")
    || (a.prenoms || "").localeCompare(b.prenoms || "", "fr"));

  const input = h("input", { type: "search", placeholder, autocomplete: "off",
    role: "combobox", "aria-autocomplete": "list", "aria-expanded": "false",
    "aria-controls": idMenu, style: "width:320px;max-width:100%" });
  const menu = h("div", { class: "champ-menu", id: idMenu, role: "listbox" });
  const boite = h("div", { class: "champ-auto" }, input, menu);
  let options = [];

  function poser(p) {
    if (p) input.value = p.nom + (p.periode ? " (" + p.periode + ")" : "");
  }
  if (initial) poser(tri.find((x) => x.id === initial));

  function fermer() { menu.classList.remove("on"); input.setAttribute("aria-expanded", "false"); actif = -1; }
  function surligner(n) {
    options.forEach((o, k) => o.classList.toggle("actif", k === n));
    if (options[n]) options[n].scrollIntoView({ block: "nearest" });
    actif = n;
  }
  function choisir(p) {
    choisi = p.id; poser(p); fermer();
    if (onChoix) onChoix(choisi);
  }
  function ouvrir(filtre) {
    vider(menu); options = [];
    const q = normaliser((filtre || "").trim());
    const res = tri.filter((p) => !q || normaliser(p.nom).includes(q)).slice(0, 40);
    if (!res.length) { fermer(); return; }
    res.forEach((p) => {
      const o = h("div", { class: "champ-option", role: "option",
        onmousedown: (e) => { e.preventDefault(); choisir(p); } },
        p.nom + (p.periode ? "  " + p.periode : ""));
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
