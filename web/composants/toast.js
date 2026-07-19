// Notifications éphémères. Options : durée, bouton d'action, mode persistant.
// Déduplication : un même message n'apparaît pas deux fois en même temps.
import { h } from "../noyau/dom.js";

const _actifs = new Set();

export function toast(message, { duree = 3500, action = null, actionLabel = "",
                                 persistant = false, type = "" } = {}) {
  if (_actifs.has(message)) return null;
  _actifs.add(message);
  const zone = document.getElementById("toasts");
  // Une ERREUR ne doit pas ressembler à un succès (audit DES-01) : fond alerte,
  // icône ⚠, lecture assertive, et elle reste affichée plus longtemps.
  const erreur = type === "erreur";
  if (erreur && duree === 3500) duree = 7000;
  const el = h("div", { class: "toast" + (erreur ? " erreur" : ""),
    role: erreur ? "alert" : "status" },
    h("span", {}, (erreur ? "⚠ " : "") + message));
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
