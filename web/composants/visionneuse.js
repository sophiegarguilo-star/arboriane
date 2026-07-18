// Visionneuse d'actes plein écran : zoom (molette + boutons), déplacement à la
// main (pan), galerie (←/→), transcription à côté (lecture + édition).
import { h, vider } from "../noyau/dom.js";
import { toast } from "./toast.js";

let _fermer = null;

export function visionneuseOuverte() { return !!document.getElementById("visio"); }

export function fermerVisionneuse() {
  const el = document.getElementById("visio");
  if (el) el.remove();
  if (_fermer) { const f = _fermer; _fermer = null; f(); }
}

// images : [url, …]. opts : { index, titre, transcription, onTranscription(txt) }
export function ouvrirVisionneuse(images, opts = {}) {
  if (!images || !images.length) return;
  fermerVisionneuse();
  let i = opts.index || 0;
  let echelle = 1, tx = 0, ty = 0;          // zoom & déplacement
  const MIN = 0.4, MAX = 6;

  const img = h("img", { class: "visio-img", draggable: "false" });
  const scene = h("div", { class: "visio-scene" }, img);
  const compteur = h("span", { class: "visio-compteur" });

  function appliquer() {
    img.style.transform =
      "translate(" + tx + "px," + ty + "px) scale(" + echelle + ")";
  }
  function reset() { echelle = 1; tx = 0; ty = 0; appliquer(); }
  function charger() {
    img.src = images[i];
    compteur.textContent = (i + 1) + " / " + images.length;
    reset();
  }
  function zoomer(f, cx, cy) {
    const av = echelle;
    echelle = Math.min(MAX, Math.max(MIN, echelle * f));
    // zoom centré sur le curseur
    if (cx != null) {
      const r = echelle / av;
      tx = cx - (cx - tx) * r;
      ty = cy - (cy - ty) * r;
    }
    appliquer();
  }
  function aller(d) {
    i = (i + d + images.length) % images.length;
    charger();
  }

  // molette
  scene.addEventListener("wheel", (e) => {
    e.preventDefault();
    const r = scene.getBoundingClientRect();
    zoomer(e.deltaY < 0 ? 1.15 : 0.87, e.clientX - r.left, e.clientY - r.top);
  }, { passive: false });
  // pan à la main
  let drag = null;
  scene.addEventListener("pointerdown", (e) => {
    drag = { x: e.clientX - tx, y: e.clientY - ty };
    scene.setPointerCapture(e.pointerId);
    scene.style.cursor = "grabbing";
  });
  scene.addEventListener("pointermove", (e) => {
    if (!drag) return;
    tx = e.clientX - drag.x; ty = e.clientY - drag.y; appliquer();
  });
  scene.addEventListener("pointerup", (e) => {
    drag = null; scene.style.cursor = "grab";
    try { scene.releasePointerCapture(e.pointerId); } catch { /* */ }
  });
  // double-clic : bascule ×2.5
  scene.addEventListener("dblclick", (e) => {
    const r = scene.getBoundingClientRect();
    if (echelle > 1.2) reset();
    else zoomer(2.5, e.clientX - r.left, e.clientY - r.top);
  });

  const barre = h("div", { class: "visio-barre" },
    images.length > 1 ? h("button", { class: "visio-btn", title: "Précédent (←)", onclick: () => aller(-1) }, "‹") : null,
    compteur,
    images.length > 1 ? h("button", { class: "visio-btn", title: "Suivant (→)", onclick: () => aller(1) }, "›") : null,
    h("span", { style: "flex:1" }),
    h("button", { class: "visio-btn", title: "Zoom −", onclick: () => zoomer(0.8) }, "🔍−"),
    h("button", { class: "visio-btn", title: "Ajuster", onclick: reset }, "⤢"),
    h("button", { class: "visio-btn", title: "Zoom +", onclick: () => zoomer(1.25) }, "🔍+"),
    h("button", { class: "visio-btn", title: "Fermer (Échap)", onclick: fermerVisionneuse }, "✕"));

  // panneau transcription (optionnel)
  let panneau = null;
  if (opts.transcription != null || opts.onTranscription) {
    const zone = h("textarea", { class: "visio-trans-txt", rows: 20,
      placeholder: "Transcription de l'acte…" }, opts.transcription || "");
    zone.readOnly = !opts.onTranscription;
    let btnSave = null;
    if (opts.onTranscription) {
      btnSave = h("button", { class: "bouton petit", onclick: async () => {
        btnSave.disabled = true;
        try {
          await opts.onTranscription(zone.value);
          btnSave.textContent = "✓ Enregistré";
          setTimeout(() => {
            btnSave.textContent = "Enregistrer la transcription"; btnSave.disabled = false;
          }, 1800);
        } catch (e) { btnSave.disabled = false; toast(e.message || "Échec de l'enregistrement."); }
      } }, "Enregistrer la transcription");
    }
    const actions = btnSave ? h("div", { class: "barre-actions" }, btnSave) : null;
    panneau = h("div", { class: "visio-trans" },
      h("h3", {}, "Transcription"), zone, actions);
  }

  const corps = h("div", { class: "visio-corps" }, scene, panneau);
  const overlay = h("div", { id: "visio", class: "visio" },
    opts.titre ? h("div", { class: "visio-titre" }, opts.titre) : null,
    barre, corps);
  document.body.append(overlay);
  _fermer = opts.onFermer || null;
  charger();

  // navigation clavier (retirée à la fermeture via l'overlay retiré du DOM)
  overlay._clavier = (e) => {
    if (e.key === "Escape") { fermerVisionneuse(); return; }
    // Pendant la SAISIE de la transcription, ne pas détourner les touches :
    // flèches, +, − et = doivent écrire/déplacer le curseur, pas naviguer/zoomer.
    const t = e.target;
    if (t && (t.tagName === "TEXTAREA" || t.tagName === "INPUT" || t.isContentEditable)) return;
    if (e.key === "ArrowLeft") aller(-1);
    else if (e.key === "ArrowRight") aller(1);
    else if (e.key === "+" || e.key === "=") zoomer(1.25);
    else if (e.key === "-") zoomer(0.8);
  };
  document.addEventListener("keydown", overlay._clavier);
  const obs = new MutationObserver(() => {
    if (!document.getElementById("visio")) {
      document.removeEventListener("keydown", overlay._clavier);
      obs.disconnect();
    }
  });
  obs.observe(document.body, { childList: true });
}
