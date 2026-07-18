// Bandeaux hauts, discrets et NON bloquants (mises à jour, serveur arrêté…).
//
// Ils DÉCALENT la page au lieu de la recouvrir : sinon ils masquent l'en-tête de
// l'application (logo, recherche) et donnent l'impression d'un écran cassé.
// Plusieurs bandeaux peuvent coexister : ils s'empilent au lieu de se superposer.
import { h } from "../noyau/dom.js";

const TONS = {
  info: "#2c6e49",       // vert Arboriane
  alerte: "#8c2f28",     // rouge sourd : quelque chose est cassé
};

// Replace les bandeaux les uns sous les autres et décale le corps d'autant.
function repositionner() {
  let y = 0;
  for (const el of document.querySelectorAll("[data-bandeau]")) {
    el.style.top = y + "px";
    y += el.offsetHeight;
  }
  document.body.style.paddingTop = y ? y + "px" : "";
}

// `boutons` : [{ texte, primaire, onclick(retirer) }]. Renvoie null si le
// bandeau `id` est déjà affiché (on ne l'empile pas deux fois).
export function bandeau(id, texte, boutons, { ton = "info" } = {}) {
  if (document.getElementById(id)) return null;
  const fond = TONS[ton] || TONS.info;
  const barre = h("div", { id, role: ton === "alerte" ? "alert" : "status",
    "data-bandeau": "1" });
  barre.style.cssText = [
    "position:fixed", "left:0", "right:0", "top:0", "z-index:99998",
    "background:" + fond, "color:#fff", "padding:9px 16px",
    "font:14px/1.4 'Segoe UI',system-ui,sans-serif",
    "display:flex", "align-items:center", "justify-content:center",
    "gap:10px", "flex-wrap:wrap",
    "box-shadow:0 2px 8px rgba(0,0,0,.25)",
  ].join(";");
  barre.append(h("span", {}, texte));
  const retirer = () => { barre.remove(); repositionner(); };
  for (const b of boutons) {
    barre.append(h("button", {
      onclick: () => b.onclick(retirer),
      style: "white-space:nowrap;border-radius:6px;cursor:pointer;padding:5px 12px;"
        + (b.primaire
          ? "background:#fff;color:" + fond + ";border:0;font-weight:600"
          : "background:transparent;color:#fff;border:1px solid rgba(255,255,255,.6)"),
    }, b.texte));
  }
  document.body.appendChild(barre);
  repositionner();
  return barre;
}

export function retirerBandeau(id) {
  const el = document.getElementById(id);
  if (!el) return false;
  el.remove();
  repositionner();
  return true;
}

export function bandeauAffiche(id) {
  return !!document.getElementById(id);
}
