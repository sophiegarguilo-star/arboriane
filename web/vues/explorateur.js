// Explorateur de fichiers de l'arbre : parcourir les dossiers de l'arbre actif
// (Sources, Photos, Exports, Sauvegardes, GEDCOM, journaux…), aperçu des images,
// et ouverture d'un dossier dans l'explorateur Windows. Confiné à l'arbre.
import { h, vider, actionnable } from "../noyau/dom.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { toast } from "../composants/toast.js";
import { ouvrirModale } from "../composants/modale.js";

const IMG = ["jpg", "jpeg", "png", "gif", "webp", "bmp", "tif", "tiff"];

function taille(o) {
  if (o < 1024) return o + " o";
  if (o < 1048576) return Math.round(o / 1024) + " Ko";
  return (o / 1048576).toFixed(1) + " Mo";
}
function quand(ts) {
  try { return new Date(ts * 1000).toLocaleDateString("fr-FR"); } catch (e) { return ""; }
}
function icone(ext) {
  if (IMG.includes(ext)) return "🖼";
  if (ext === "pdf") return "📕";
  if (ext === "ged") return "🌳";
  if (ext === "zip") return "🗜";
  if (["json", "csv", "log", "txt", "md"].includes(ext)) return "📄";
  return "📄";
}

export async function vueExplorateur(vue, arg) {
  vue.append(h("h1", {}, "Explorateur de fichiers"));
  vue.append(h("p", { class: "sous-titre" },
    "Parcourez les fichiers de votre arbre : scans (Sources), photos, exports, "
    + "sauvegardes, journaux. Tout reste dans le dossier de l'arbre."));
  const zone = h("div", {});
  vue.append(zone);
  let chemin = (arg && arg.chemin) || "";

  async function rendre() {
    vider(zone);
    let d;
    try { d = await apiGet("/api/explorateur?chemin=" + encodeURIComponent(chemin)); }
    catch (e) { zone.append(h("div", { class: "vide" }, e.message)); return; }

    // — Fil d'Ariane + « ouvrir dans l'explorateur » —
    const fil = h("div", { class: "barre-actions", style: "flex-wrap:wrap;gap:4px;align-items:center;margin-bottom:8px" });
    fil.append(h("button", { class: "lien", onclick: () => { chemin = ""; rendre(); } },
      "🗂 " + d.racine_nom));
    let acc = "";
    d.parties.forEach((p) => {
      acc = acc ? acc + "/" + p : p;
      const c = acc;
      fil.append(h("span", { class: "doux" }, "/"));
      fil.append(h("button", { class: "lien", onclick: () => { chemin = c; rendre(); } }, p));
    });
    fil.append(h("span", { style: "flex:1" }));
    fil.append(h("button", { class: "bouton petit secondaire", onclick: async () => {
      try { await apiJson("/api/explorateur/ouvrir", "POST", { chemin }); }
      catch (e) { toast(e.message, { type: "erreur" }); }
    } }, "Ouvrir dans l'explorateur Windows"));
    zone.append(fil);

    // — Liste —
    const carte = h("div", { class: "carte" });
    if (chemin) {
      carte.append(actionnable(h("div", { class: "ligne-pers", onclick: () => {
        chemin = chemin.split("/").slice(0, -1).join("/"); rendre();
      } }, h("strong", {}, "⬆ Dossier parent"))));
    }
    if (!d.dossiers.length && !d.fichiers.length) {
      carte.append(h("p", { class: "vide compacte" }, "Dossier vide."));
    }
    d.dossiers.forEach((f) => carte.append(
      actionnable(h("div", { class: "ligne-pers", onclick: () => {
        chemin = chemin ? chemin + "/" + f.nom : f.nom; rendre();
      } },
        h("strong", {}, "📁 " + f.nom),
        h("span", { class: "meta" }, quand(f.modifie))))));
    d.fichiers.forEach((f) => {
      const rel = chemin ? chemin + "/" + f.nom : f.nom;
      const ligne = h("div", { class: "ligne-pers" },
        h("strong", {}, icone(f.ext) + " " + f.nom),
        h("span", { class: "meta" }, taille(f.taille) + " · " + quand(f.modifie)));
      ligne.addEventListener("click", async () => {
        if (IMG.includes(f.ext)) {
          const r = await apiGet("/api/explorateur/apercu?chemin=" + encodeURIComponent(rel))
            .catch(() => ({}));
          if (r.data) {
            ouvrirModale(h("img", { src: r.data, alt: f.nom,
              style: "max-width:100%;max-height:70vh;display:block;margin:0 auto" }),
              { titre: f.nom, largeur: 760 });
          } else { toast("Aperçu indisponible pour ce fichier."); }
        } else {
          try { await apiJson("/api/explorateur/ouvrir", "POST", { chemin: rel }); }
          catch (e) { toast(e.message, { type: "erreur" }); }
        }
      });
      carte.append(ligne);
    });
    zone.append(carte);
  }
  await rendre();
}
