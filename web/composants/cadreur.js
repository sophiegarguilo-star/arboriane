// Cadrage carré NON DESTRUCTIF d'une photo : on choisit quelle partie de la
// photo apparaît dans le carré (galerie, portrait de fiche, cartes de l'arbre).
// Le fichier n'est jamais modifié — on stocke juste une position CSS
// (« 50% 30% ») appliquée en object-position / background-position.
//
// ouvrirCadreur(url, cadrageInitial) -> Promise<string|null>
//   résout la nouvelle position (« x% y% ») à l'enregistrement, ou null si annulé.
import { h } from "../noyau/dom.js";

function _parse(c) {
  const m = /(\d+(?:\.\d+)?)%\s+(\d+(?:\.\d+)?)%/.exec(c || "");
  return m ? { x: +m[1], y: +m[2] } : { x: 50, y: 50 };
}

export function ouvrirCadreur(url, cadrageInitial) {
  return new Promise((resolve) => {
    let pos = _parse(cadrageInitial);
    const carre = h("div", { class: "cadreur-carre" });
    carre.style.backgroundImage = "url('" + url + "')";
    const appliquer = () => { carre.style.backgroundPosition = pos.x + "% " + pos.y + "%"; };
    appliquer();

    let drag = null;
    carre.addEventListener("pointerdown", (e) => {
      drag = { x: e.clientX, y: e.clientY, px: pos.x, py: pos.y };
      carre.setPointerCapture(e.pointerId); carre.style.cursor = "grabbing";
    });
    carre.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const r = carre.getBoundingClientRect();
      // glisser l'image : on déplace la fenêtre visible dans le sens inverse
      pos.x = Math.min(100, Math.max(0, drag.px - (e.clientX - drag.x) / r.width * 100));
      pos.y = Math.min(100, Math.max(0, drag.py - (e.clientY - drag.y) / r.height * 100));
      appliquer();
    });
    const fin = () => { drag = null; carre.style.cursor = "grab"; };
    carre.addEventListener("pointerup", fin);
    carre.addEventListener("pointercancel", fin);

    const fermer = (val) => { document.removeEventListener("keydown", clavier); overlay.remove(); resolve(val); };
    const clavier = (e) => { if (e.key === "Escape") fermer(null); };
    document.addEventListener("keydown", clavier);

    const overlay = h("div", { class: "cadreur-overlay",
      onclick: (e) => { if (e.target === overlay) fermer(null); } },
      h("div", { class: "carte", style: "max-width:90vw;margin:0" },
        h("h3", { style: "margin-top:0" }, "Cadrer la photo"),
        h("p", { class: "sous-titre", style: "margin:0 0 10px" },
          "Faites glisser l'image pour choisir la partie visible dans le carré."),
        carre,
        h("div", { class: "barre-actions", style: "margin-top:12px" },
          h("button", { class: "bouton petit",
            onclick: () => fermer(pos.x + "% " + pos.y + "%") }, "Enregistrer le cadrage"),
          h("button", { class: "bouton secondaire petit", onclick: () => fermer(null) }, "Annuler"),
          h("button", { class: "lien", style: "margin-left:auto",
            onclick: () => { pos = { x: 50, y: 50 }; appliquer(); } }, "recentrer"))));
    document.body.append(overlay);
  });
}
