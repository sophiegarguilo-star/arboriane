// Onglet Carnet de bord — journal de recherche.
import { h, vider } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { badge } from "../composants/badge.js";
import { toast } from "../composants/toast.js";
import { confirmer } from "../composants/modale.js";
import { boutonMicro } from "../composants/micro.js";
import { champPersonne } from "../composants/champ.js";

const TYPES = [["seance", "Séance"], ["piste", "Piste"], ["trouvaille", "Trouvaille"],
               ["reflexion", "Réflexion"], ["afaire", "À faire"], ["ia", "IA"]];
const LIB = Object.fromEntries(TYPES);
const GENRE = { piste: "info", trouvaille: "ok", afaire: "attention" };

export async function vueCarnet(vue) {
  vue.append(h("h1", {}, "Carnet de bord"));
  vue.append(h("p", { class: "sous-titre" },
    "Votre journal de recherche : séances, pistes, trouvailles, réflexions. "
    + "Rappel : une piste va au carnet ; une preuve va aux sources."));

  const zone = h("div", {});
  let filtreType = "";
  let q = "";
  let editionId = null;   // id de l'entrée en cours d'édition (sinon création)

  // liste des personnes de l'arbre, pour tagger une note
  const liste = await apiGet("/api/individus").catch(() => []);

  // formulaire d'ajout / d'édition
  const titreForm = h("h2", {}, "Nouvelle entrée");
  const fType = h("select", {}, ...TYPES.map(([v, l]) => h("option", { value: v }, l)));
  const fTitre = h("input", { placeholder: "Titre", style: "flex:1;min-width:200px" });
  const fTexte = h("textarea", { rows: 2, placeholder: "Notes…", style: "width:100%" });
  const btnValider = h("button", { class: "bouton" }, "Ajouter au carnet");
  const btnAnnulerEdit = h("button", { class: "bouton secondaire", style: "display:none" }, "Annuler");

  // personnes taguées (chips) — une piste/à-faire ainsi taguée remonte au plan
  let taggees = [];   // [{id, nom}]
  const puces = h("div", { style: "display:flex;gap:6px;flex-wrap:wrap;margin:2px 0" });
  function rendrePuces() {
    vider(puces);
    taggees.forEach((p, i) => puces.append(h("span", { class: "puce-pers" },
      "👤 " + (p.nom || p.id),
      h("button", { class: "lien", style: "margin-left:6px;font-size:11px",
        onclick: () => { taggees.splice(i, 1); rendrePuces(); } }, "✕"))));
  }
  const tagger = champPersonne(liste, { placeholder: "Tagger une personne…",
    onChoix: (pid) => {
      if (pid && !taggees.some((p) => p.id === pid)) {
        const info = liste.find((x) => x.id === pid);
        taggees.push({ id: pid, nom: info ? info.nom : pid });
        rendrePuces();
      }
      const inp = tagger.element.querySelector("input");
      if (inp) inp.value = "";
    } });
  const fStatut = h("input", { type: "checkbox" });
  const ligneStatut = h("label", { style: "display:none;align-items:center;gap:6px;font-size:13px;color:var(--gris)" },
    fStatut, "Marquer comme fait (sort du plan de recherche)");
  function majStatut() {
    ligneStatut.style.display = (fType.value === "piste" || fType.value === "afaire") ? "flex" : "none";
  }
  fType.addEventListener("change", majStatut); majStatut();

  function reinit() {
    editionId = null; fType.value = TYPES[0][0]; fTitre.value = ""; fTexte.value = "";
    taggees = []; rendrePuces(); fStatut.checked = false; majStatut();
    titreForm.textContent = "Nouvelle entrée";
    btnValider.textContent = "Ajouter au carnet";
    btnAnnulerEdit.style.display = "none";
  }
  function editer(e) {
    editionId = e.id; fType.value = e.type; fTitre.value = e.titre || ""; fTexte.value = e.texte || "";
    taggees = (e.personnes_noms || []).map((p) => ({ id: p.id, nom: p.nom })); rendrePuces();
    fStatut.checked = e.statut === "fait"; majStatut();
    titreForm.textContent = "Modifier l'entrée";
    btnValider.textContent = "Enregistrer les modifications";
    btnAnnulerEdit.style.display = "";
    titreForm.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  btnAnnulerEdit.addEventListener("click", reinit);
  btnValider.addEventListener("click", async () => {
    if (!fTitre.value.trim() && !fTexte.value.trim()) { toast("Écrivez quelque chose."); return; }
    const corps = { type: fType.value, titre: fTitre.value, texte: fTexte.value,
      personnes: taggees.map((p) => p.id), statut: fStatut.checked ? "fait" : "" };
    try {
      if (editionId) {
        await apiJson("/api/carnet/" + editionId, "PUT", corps);
        toast("Entrée modifiée.");
      } else {
        await apiJson("/api/carnet", "POST", corps);
        toast("Entrée ajoutée.");
      }
      reinit(); charger();
    } catch (e) { toast(e.message); }
  });
  const micro = boutonMicro(fTexte);   // null si le navigateur ne sait pas dicter
  vue.append(h("div", { class: "carte" },
    titreForm,
    h("div", { style: "display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px" }, fType, fTitre),
    fTexte,
    h("div", { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px" },
      tagger.element, ligneStatut),
    puces,
    h("div", { class: "barre-actions", style: "margin-top:8px" },
      btnValider, btnAnnulerEdit, micro ? h("span", { style: "margin-left:auto" }) : null, micro)));

  // filtres
  const rech = h("input", { type: "search", placeholder: "Rechercher…" });
  const selF = h("select", {}, h("option", { value: "" }, "Tous les types"),
    ...TYPES.map(([v, l]) => h("option", { value: v }, l)));
  rech.addEventListener("input", () => { q = rech.value.toLowerCase(); charger(); });
  selF.addEventListener("change", () => { filtreType = selF.value; charger(); });
  vue.append(h("div", { class: "barre-actions", style: "margin:14px 0" }, rech, selF,
    h("button", { class: "bouton secondaire petit", onclick: imprimer }, "🖨 Imprimer")));
  vue.append(zone);

  async function charger() {
    vider(zone);
    const r = await apiGet("/api/carnet").catch(() => ({ entrees: [] }));
    let lst = r.entrees;
    if (filtreType) lst = lst.filter((e) => e.type === filtreType);
    if (q) lst = lst.filter((e) => (e.titre + e.texte).toLowerCase().includes(q));
    if (!lst.length) { zone.append(h("div", { class: "vide" }, "Aucune entrée.")); return; }
    lst.forEach((e) => zone.append(entree(e, charger, editer)));
  }
  charger();
}

function entree(e, recharger, editer) {
  return h("div", { class: "carte" },
    h("div", { style: "display:flex;align-items:center;gap:8px;flex-wrap:wrap" },
      badge(LIB[e.type] || e.type, GENRE[e.type] || ""),
      // un badge de statut UNIQUEMENT quand c'est fait (« à faire » ferait
      // doublon avec le type « À faire »).
      ((e.type === "piste" || e.type === "afaire") && e.statut === "fait")
        ? badge("✓ fait", "ok") : null,
      h("strong", {}, e.titre || "(sans titre)"),
      h("span", { style: "color:var(--gris-clair);font-size:12px" }, e.date),
      ...((e.personnes_noms || []).map((p) =>
        h("span", { class: "puce-pers", onclick: () => aller("personnes", { fiche: p.id }) }, "👤 " + (p.nom || p.id)))),
      h("span", { style: "margin-left:auto" }),
      h("button", { class: "lien", style: "font-size:12px",
        onclick: () => editer(e) }, "éditer"),
      h("button", { class: "lien", style: "font-size:12px;color:var(--alerte)",
        onclick: async () => {
          if (!await confirmer("Supprimer cette entrée du carnet ?",
            { titre: "Supprimer l'entrée", valider: "Supprimer" })) return;
          await apiJson("/api/carnet/" + e.id, "DELETE", {});
          toast("Entrée supprimée."); recharger();
        } }, "supprimer")),
    e.texte ? h("p", { style: "margin:8px 0 0;white-space:pre-wrap" }, e.texte) : null);
}

// Impression / PDF propre : page dédiée (pas le reste de l'application).
async function imprimer() {
  const r = await apiGet("/api/carnet").catch(() => ({ entrees: [] }));
  const entrees = r.entrees || [];
  const esc = (s) => String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const blocs = entrees.map((e) =>
    "<article><h2>" + esc(e.titre || "(sans titre)")
    + "<span class='meta'>" + esc((LIB[e.type] || e.type) + " · " + (e.date || "")) + "</span></h2>"
    + (e.texte ? "<p>" + esc(e.texte).replace(/\n/g, "<br>") + "</p>" : "") + "</article>").join("");
  const doc = "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
    + "<title>Carnet de bord — Arboriane</title><style>"
    + "body{font-family:Georgia,serif;max-width:720px;margin:24px auto;padding:0 16px;color:#2a2b28}"
    + "h1{color:#1f4636;border-bottom:2px solid #1f4636;padding-bottom:6px}"
    + "article{break-inside:avoid;margin:16px 0;padding-bottom:12px;border-bottom:1px solid #e4e1d6}"
    + "h2{font-size:16px;margin:0 0 6px;display:flex;justify-content:space-between;align-items:baseline;gap:12px}"
    + ".meta{font-size:12px;color:#6b7280;font-weight:normal;font-family:system-ui,sans-serif}"
    + "p{margin:0;white-space:pre-wrap;line-height:1.5}"
    + "@media print{body{margin:0}}"
    + "</style></head><body><h1>Carnet de bord</h1>"
    + (blocs || "<p>Aucune entrée.</p>")
    + "<script>window.onload=function(){window.print()}<\/script></body></html>";
  const w = window.open("", "_blank");
  if (!w) { toast("Autorisez les fenêtres pop-up pour imprimer."); return; }
  w.document.write(doc); w.document.close();
}
