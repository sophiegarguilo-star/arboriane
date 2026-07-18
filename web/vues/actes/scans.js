// Bloc « pièces jointes » d'une source : dépôt des scans, vignettes, retrait.
//
// Les scans sont écrits sur le disque dès qu'on les dépose (l'aperçu les affiche
// depuis le serveur). Ceux qui sont ajoutés ici et jamais enregistrés sont donc
// effacés à l'abandon du formulaire — sinon le dossier Sources se remplirait de
// fichiers orphelins.
import { h, vider } from "../../noyau/dom.js";
import { apiJson } from "../../noyau/api.js";
import { toast } from "../../composants/toast.js";
import { demander } from "../../composants/modale.js";
import { estImageFichier, fichierAccepte, lireBase64 } from "./commun.js";

// initiaux : scans déjà enregistrés sur la source. onChange : prévenu à chaque
// ajout/retrait (le nom de fichier proposé en dépend).
export function blocScans(initiaux = [], { onChange } = {}) {
  const fichiers = initiaux.slice();   // tous les scans de la source
  const ajoutes = [];                  // ceux déposés ici, pas encore enregistrés
  const prevenir = () => { if (onChange) onChange(); };

  const apercus = h("div", { style: "display:flex;flex-wrap:wrap;gap:8px;margin-top:8px" });
  function rendre() {
    vider(apercus);
    if (!fichiers.length) {
      apercus.append(h("span", { style: "color:var(--gris-clair);font-size:13px" },
        "Aucun fichier pour l'instant."));
      return;
    }
    fichiers.forEach((f, i) => {
      const retirer = h("button", { class: "bouton fantome petit", title: "Retirer",
        style: "position:absolute;top:-8px;right:-8px;background:var(--fond);border-radius:50%",
        onclick: () => {
          const nom = fichiers[i];
          fichiers.splice(i, 1);
          const j = ajoutes.indexOf(nom);   // déposé ici, jamais enregistré : on l'efface du disque
          if (j >= 0) {
            ajoutes.splice(j, 1);
            apiJson("/api/media/Sources/" + encodeURIComponent(nom), "DELETE", {}).catch(() => {});
          }
          rendre(); prevenir();
        } }, "✕");
      const url = "/media/Sources/" + encodeURIComponent(f);
      const vignette = estImageFichier(f)
        ? h("img", { src: url, style: "width:78px;height:78px;object-fit:cover;"
            + "border-radius:8px;border:1px solid var(--bord)" })
        : h("a", { href: url, target: "_blank", rel: "noopener", title: "Ouvrir " + f,
            style: "width:78px;height:78px;border-radius:8px;border:1px solid var(--bord);"
              + "display:flex;flex-direction:column;align-items:center;justify-content:center;"
              + "gap:2px;text-decoration:none;color:var(--gris)" },
            h("span", { style: "font-size:24px" }, "📄"),
            h("span", { style: "font-size:11px" }, /\.pdf$/i.test(f) ? "PDF" : "TIFF"));
      apercus.append(h("div", { style: "position:relative" }, vignette, retirer));
    });
  }
  rendre();

  const inputFic = h("input", { type: "file",
    accept: "image/*,application/pdf,.pdf,.tif,.tiff", multiple: true, style: "display:none" });
  async function ajouter(liste) {
    const ok = [...liste].filter(fichierAccepte);
    if (!ok.length) { toast("Déposez un scan : image, PDF ou TIFF."); return; }
    toast(ok.length > 1 ? "Ajout de " + ok.length + " fichiers…" : "Ajout du fichier…");
    for (const f of ok) {
      const data = await lireBase64(f);
      const r = await apiJson("/api/media/Sources", "POST", { nom: f.name, data });
      fichiers.push(r.fichier); ajoutes.push(r.fichier);
    }
    inputFic.value = ""; rendre(); prevenir();
    toast(ok.length + " fichier(s) ajouté(s).");
  }
  inputFic.addEventListener("change", () => { if (inputFic.files.length) ajouter(inputFic.files); });

  async function ajouterUrl() {
    const url = await demander("Adresse (URL) de l'image à télécharger :",
      { titre: "Image depuis une URL", valider: "Télécharger" });
    if (!url) return;
    try {
      toast("Téléchargement de l'image…");
      const r = await apiJson("/api/media/Sources/url", "POST", { url: url.trim() });
      fichiers.push(r.fichier); ajoutes.push(r.fichier);
      rendre(); prevenir(); toast("Image ajoutée.");
    } catch (e) { toast(e.message); }
  }

  const drop = h("div", { class: "zone-depot" },
    "📎 Glissez vos scans ici (image, PDF, TIFF), ou ",
    h("button", { class: "bouton secondaire petit", onclick: () => inputFic.click() }, "parcourir"),
    " · ",
    h("button", { class: "bouton secondaire petit", onclick: ajouterUrl }, "🔗 depuis une URL"),
    inputFic);
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("survol"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("survol"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault(); drop.classList.remove("survol");
    if (e.dataTransfer.files.length) ajouter(e.dataTransfer.files);
  });

  const element = h("div", { class: "champ" },
    h("label", {}, "Pièces jointes (scans : image, PDF, TIFF)"), drop, apercus);

  return {
    element,
    fichiers: () => fichiers.slice(),
    ajoutes: () => ajoutes.slice(),
    // Après renommage : le fichier a changé de nom sur le disque.
    renomme(avant, apres) {
      const i = fichiers.indexOf(avant); if (i >= 0) fichiers[i] = apres;
      const j = ajoutes.indexOf(avant); if (j >= 0) ajoutes[j] = apres;
    },
    // Abandon du formulaire : on efface les scans déposés et non enregistrés.
    nettoyerAbandon() {
      ajoutes.forEach((f) =>
        apiJson("/api/media/Sources/" + encodeURIComponent(f), "DELETE", {}).catch(() => {}));
      ajoutes.length = 0;
    },
  };
}
