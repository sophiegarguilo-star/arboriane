// Fiche d'une source : métadonnées, scans (visionneuse), transcription,
// personnes citées.
import { h, vider, actionnable } from "../../noyau/dom.js";
import { aller } from "../../noyau/etat.js";
import { boutonRetour } from "../../composants/boutonRetour.js";
import { apiGet, apiJson } from "../../noyau/api.js";
import { toast } from "../../composants/toast.js";
import { ouvrirVisionneuse } from "../../composants/visionneuse.js";
import { confirmer, demander } from "../../composants/modale.js";
import { champPersonne } from "../../composants/champ.js";
import { formatNonAffichable, MSG_FORMAT_NON_AFFICHABLE } from "../../composants/media.js";
import { lireBase64 } from "./commun.js";
import { formulaire } from "./formulaire.js";

export async function detail(sid) {
  const s = await apiGet("/api/sources/" + sid).catch(() => null);
  if (!s) { toast("Source introuvable."); return; }
  const vue = document.getElementById("vue");
  vider(vue);
  // Retour vers l'écran d'où l'on vient (fiche personne, liste, recherche,
  // Qualité des sources…) grâce à l'historique — plus jamais la liste globale
  // codée en dur qui « perdait » la personne d'origine. Repli : la liste.
  vue.append(boutonRetour("actes"));
  vue.append(h("h1", {}, s.titre || s.id));

  // métadonnées
  const meta = h("div", { class: "carte" }, h("h2", {}, "Fiche de la source"));
  [["Type", s.type], ["Date", s.date], ["Lieu", s.lieu || s.ville],
   ["Dépôt", s.depot], ["Cote", s.cote], ["Page", s.page],
   ["Fiabilité", s.fiabilite], ["Statut", s.statut],
   ["ARK / URL", s.ark]].forEach(([k, v]) => {
    if (v) meta.append(h("div", { class: "def-ligne" },
      h("span", { class: "def-cle" }, k),
      k === "ARK / URL" ? h("a", { class: "def-val", href: v, target: "_blank" }, v) : h("span", { class: "def-val" }, v)));
  });
  meta.append(h("div", { class: "barre-actions", style: "margin-top:10px" },
    h("button", { class: "bouton petit", onclick: () => formulaire(s) }, "✏️ Modifier"),
    h("button", { class: "bouton danger petit",
      onclick: async () => {
        if (!await confirmer("Supprimer cette source ? Les citations liées seront retirées.",
          { titre: "Supprimer la source", valider: "Supprimer", danger: true })) return;
        await apiJson("/api/sources/" + sid, "DELETE", {});
        toast("Source supprimée."); aller("actes");
      } }, "🗑 Supprimer")));
  vue.append(meta);

  // visionneuse : images + transcription
  const viz = h("div", { class: "carte" }, h("h2", {}, "Pièces & transcription"));
  const urls = s.fichiers_resolus.map((f) => "/media/Sources/" + encodeURIComponent(f));
  const estPdf = (u) => /\.pdf(\?|$)/i.test(u);
  const images = urls.filter((u) => !estPdf(u));   // la visionneuse (zoom) ne gère que les images
  let majTrans = null;   // synchronise le champ de la fiche quand on sauve depuis la visionneuse
  function ouvrir(url) {
    ouvrirVisionneuse(images, { index: Math.max(0, images.indexOf(url)), titre: s.titre,
      transcription: s.transcription || "",
      onTranscription: async (txt) => {
        await apiJson("/api/sources/" + sid, "PUT", { transcription: txt });
        s.transcription = txt;
        if (majTrans) majTrans(txt);   // garde la fiche à jour (sinon on l'écraserait)
        toast("Transcription enregistrée.");
      } });
  }
  if (s.fichiers_resolus.length) {
    // Aperçu de la 1re pièce, remplaçable via les vignettes. Les PDF s'affichent
    // dans la visionneuse intégrée du navigateur (pas en <img>, qui reste blanc).
    const grande = h("div", {});
    function montrer(url) {
      vider(grande);
      if (estPdf(url)) {
        grande.append(
          h("embed", { src: url, type: "application/pdf",
            style: "width:100%;height:520px;border:1px solid var(--bord);border-radius:8px" }),
          h("p", { style: "font-size:12px;margin-top:6px" },
            h("a", { href: url, target: "_blank", rel: "noopener" }, "Ouvrir le PDF dans un onglet ↗")));
      } else {
        grande.append(h("img", { src: url,
          style: "max-width:100%;max-height:460px;border:1px solid var(--bord);border-radius:8px;cursor:zoom-in",
          title: "Cliquer pour agrandir (zoom, transcription)", onclick: () => ouvrir(url) }));
      }
    }
    montrer(urls[0]);
    viz.append(grande);
    if (s.fichiers_resolus.length > 1) {
      const minis = h("div", { class: "rangee serre", style: "margin-top:8px" });
      urls.forEach((u) => minis.append(estPdf(u)
        ? actionnable(h("div", { title: "PDF", onclick: () => montrer(u),
            style: "width:64px;height:64px;border-radius:6px;cursor:pointer;border:1px solid var(--bord);"
              + "display:flex;align-items:center;justify-content:center;font-size:11px;background:var(--accent-pale)" }, "📄 PDF"))
        : h("img", { src: u,
            style: "width:64px;height:64px;object-fit:cover;border-radius:6px;cursor:pointer;border:1px solid var(--bord)",
            onclick: () => montrer(u) })));
      viz.append(minis);
    }
    viz.append(h("p", { style: "font-size:12px;color:var(--gris-clair);margin-top:6px" },
      "Cliquez une image pour l'agrandir (zoom molette, déplacement, navigation ←/→, transcription à côté). Les PDF s'affichent directement."));
  } else {
    viz.append(h("p", { class: "sous-titre" }, "Aucun scan rattaché."));
  }
  // ajout de scans : sélection multiple + glisser-déposer
  const inputImg = h("input", { type: "file", multiple: true, style: "display:none",
    accept: "image/jpeg,image/png,image/gif,image/webp,application/pdf,.pdf" });
  const _accepte = (f) => (f.type.startsWith("image/") || f.type === "application/pdf"
    || /\.pdf$/i.test(f.name)) && !formatNonAffichable(f.name);
  async function ajouterFichiers(fichiers) {
    const tous = [...fichiers];
    const imgs = tous.filter(_accepte);
    if (tous.some((x) => formatNonAffichable(x.name))) toast(MSG_FORMAT_NON_AFFICHABLE);
    if (!imgs.length) { if (!tous.some((x) => formatNonAffichable(x.name))) toast("Déposez des scans : images ou PDF."); return; }
    toast(imgs.length > 1 ? "Ajout de " + imgs.length + " pièces…" : "Ajout de la pièce…");
    let fics = (s.fichiers || []).slice();
    for (const f of imgs) {
      const data = await lireBase64(f);
      const r = await apiJson("/api/media/Sources", "POST", { nom: f.name, data });
      fics = fics.concat([r.fichier]);
    }
    await apiJson("/api/sources/" + sid, "PUT", { fichiers: fics });
    toast(imgs.length + " scan(s) ajouté(s)."); detail(sid);
  }
  inputImg.addEventListener("change", () => { if (inputImg.files.length) ajouterFichiers(inputImg.files); });
  async function ajouterDepuisUrl() {
    const url = await demander("Adresse (URL) de l'image à télécharger :",
      { titre: "Image depuis une URL", valider: "Télécharger" });
    if (!url) return;
    try {
      toast("Téléchargement de l'image…");
      const r = await apiJson("/api/media/Sources/url", "POST", { url: url.trim() });
      const fics = (s.fichiers || []).concat([r.fichier]);
      await apiJson("/api/sources/" + sid, "PUT", { fichiers: fics });
      toast("Image ajoutée."); detail(sid);
    } catch (e) { toast(e.message, { type: "erreur" }); }
  }
  const drop = h("div", { class: "zone-depot" },
    "🖼 Glissez vos scans ici, ou ",
    h("button", { class: "bouton secondaire petit", onclick: () => inputImg.click() }, "parcourir"),
    " · ",
    h("button", { class: "bouton secondaire petit", onclick: ajouterDepuisUrl }, "🔗 depuis une URL"),
    inputImg);
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("survol"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("survol"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault(); drop.classList.remove("survol");
    if (e.dataTransfer.files.length) ajouterFichiers(e.dataTransfer.files);
  });
  viz.append(h("div", { style: "margin-top:10px" }, drop));

  // transcription éditable — avec confirmation visible « ✓ Enregistré »
  const trans = h("textarea", { rows: 6, style: "width:100%;margin-top:10px",
    placeholder: "Transcription de l'acte…" }, s.transcription || "");
  const statutTrans = h("span", { style: "font-size:13px;color:var(--vert)" });
  const marqueEnr = () => { statutTrans.textContent = "✓ Enregistré"; statutTrans.style.color = "var(--vert)"; };
  const marqueMod = () => {
    statutTrans.textContent = "● Modifié — non enregistré"; statutTrans.style.color = "var(--gris)";
  };
  trans.addEventListener("input", marqueMod);
  majTrans = (v) => { trans.value = v; marqueEnr(); };   // appelé depuis la visionneuse
  const btnTrans = h("button", { class: "bouton secondaire petit", onclick: async () => {
    btnTrans.disabled = true;
    try {
      await apiJson("/api/sources/" + sid, "PUT", { transcription: trans.value });
      s.transcription = trans.value; toast("Transcription enregistrée."); marqueEnr();
    } catch (e) { toast(e.message, { type: "erreur" }); } finally { btnTrans.disabled = false; }
  } }, "Enregistrer la transcription");
  viz.append(h("label", { style: "margin-top:12px" }, "Transcription"), trans,
    h("div", { class: "barre-actions", style: "align-items:center;gap:10px;margin-top:6px" },
      btnTrans, statutTrans));
  vue.append(viz);

  // personnes citées + reliage direct depuis la source
  const pers = h("div", { class: "carte" }, h("h2", {}, "Personnes citées"));
  const puces = h("div", { class: "rangee serre" });
  if (s.personnes_resolues.length) {
    s.personnes_resolues.forEach((p) => puces.append(actionnable(h("span", {
      class: "puce-pers", onclick: () => aller("personnes", { fiche: p.id }) },
      p.nom + (p.role ? " · " + p.role : "")))));
  } else {
    puces.append(h("p", { class: "sous-titre", style: "margin:0" }, "Aucune personne reliée pour l'instant."));
  }
  pers.append(puces);

  // 1) relier une personne DÉJÀ dans l'arbre (choix + rôle)
  const liste = await apiGet("/api/individus").catch(() => []);
  const champP = champPersonne(liste, { placeholder: "Relier une personne de l'arbre…" });
  const inpRole = h("input", { placeholder: "rôle (sujet, témoin, parrain…)", style: "width:180px" });
  pers.append(h("div", { class: "barre-actions", style: "margin-top:12px;align-items:flex-end" },
    h("div", {}, h("label", {}, "Relier une personne existante"), champP.element),
    h("div", {}, h("label", {}, "Rôle"), inpRole),
    h("button", { class: "bouton petit", onclick: async () => {
      const pid = champP.valeur();
      if (!pid) { toast("Choisissez une personne dans la liste, ou créez-en une ci-dessous."); return; }
      try {
        await apiJson("/api/sources/" + sid + "/personne", "POST",
          { id: pid, role: inpRole.value.trim() });
        toast("Personne reliée à la source."); detail(sid);
      } catch (e) { toast(e.message, { type: "erreur" }); }
    } }, "➕ Relier")));

  // 2) CRÉER une personne (témoin, officier… non rattachée à l'arbre) ET la citer,
  //    sans devoir la créer ailleurs d'abord. Répond au cas « je ne peux pas citer
  //    un témoin qui n'existe pas encore ».
  const nNom = h("input", { placeholder: "NOM", style: "width:150px" });
  const nPre = h("input", { placeholder: "Prénoms", style: "width:170px" });
  const nRole = h("input", { placeholder: "rôle (témoin, officier…)", style: "width:180px" });
  pers.append(h("p", { class: "sous-titre", style: "margin:16px 0 4px" },
    "— ou créer une personne (témoin, officier…) et la citer directement :"));
  pers.append(h("div", { class: "barre-actions", style: "align-items:flex-end" },
    h("div", {}, h("label", {}, "Nom"), nNom),
    h("div", {}, h("label", {}, "Prénoms"), nPre),
    h("div", {}, h("label", {}, "Rôle"), nRole),
    h("button", { class: "bouton secondaire petit", onclick: async () => {
      if (!nNom.value.trim() && !nPre.value.trim()) { toast("Indiquez au moins un nom ou un prénom."); return; }
      try {
        const r = await apiJson("/api/individus", "POST", {
          nom: nNom.value.trim(), prenoms: nPre.value.trim(),
          note: "Personne citée par une source (témoin, officier…), non rattachée à l'arbre." });
        await apiJson("/api/sources/" + sid + "/personne", "POST",
          { id: r.id, role: nRole.value.trim() });
        toast("Personne créée et citée."); detail(sid);
      } catch (e) { toast(e.message, { type: "erreur" }); }
    } }, "＋ Créer et citer")));
  vue.append(pers);
}
