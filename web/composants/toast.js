// Notifications éphémères. Options : durée, bouton d'action, mode persistant.
// Déduplication : un même message n'apparaît pas deux fois en même temps.
import { h } from "../noyau/dom.js";

const _actifs = new Set();

export function toast(message, { duree = 3500, action = null, actionLabel = "",
                                 persistant = false } = {}) {
  if (_actifs.has(message)) return null;
  _actifs.add(message);
  const zone = document.getElementById("toasts");
  const el = h("div", { class: "toast" }, h("span", {}, message));
  const retirer = () => { el.remove(); _actifs.delete(message); };
  if (action) {
    el.append(h("button", { class: "toast-action",
      onclick: () => { retirer(); action(); } }, actionLabel || "OK"));
  }
  if (persistant || action) {
    el.append(h("button", { class: "toast-fermer", "aria-label": "Fermer",
      onclick: retirer }, "✕"));
  }
  zone.append(el);
  if (!persistant) setTimeout(retirer, duree);
  return el;
}
