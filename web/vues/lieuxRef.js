// Onglet « Référentiel des lieux » (L15) — les lieux en hiérarchie (commune →
// département → pays) avec des noms alternatifs datés. Couche parallèle : les
// événements gardent leur texte, la carte existante n'est pas touchée.
import { h, vider } from "../noyau/dom.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { toast } from "../composants/toast.js";
import { confirmer } from "../composants/modale.js";

const TYPES = ["lieu-dit", "commune", "canton", "département", "région", "pays"];

export async function vueLieuxRef(vue) {
  vue.append(h("h1", {}, "🗂️ Référentiel des lieux"));
  vue.append(h("p", { class: "sous-titre" },
    "Vos lieux en hiérarchie (commune → département → pays) avec des noms datés "
    + "(« Basses-Alpes » avant 1970…). Les événements gardent leur texte : c'est "
    + "une couche de référence, exportable et recalculable."));
  const cont = h("div", {});
  vue.append(cont);
  await recharger(cont);
}

async function recharger(cont) {
  vider(cont);
  const data = await apiGet("/api/lieux-ref").catch(() => ({ lieux: [] }));
  cont.append(h("div", { class: "barre-actions", style: "margin-bottom:1rem" },
    h("button", { class: "bouton secondaire", onclick: () => formulaire(cont, null, data.lieux) }, "➕ Ajouter un lieu"),
    h("button", {
      class: "bouton",
      onclick: async () => {
        try {
          const r = await apiJson("/api/lieux-ref/construire", "POST", {});
          toast(r.crees + " lieu(x) créé(s) — total " + r.total + ".");
          recharger(cont);
        } catch (e) { toast(e.message); }
      },
    }, "✨ Construire depuis les événements")));
  if (!data.lieux.length) {
    cont.append(h("p", { class: "message" },
      "Référentiel vide. Cliquez « Construire depuis les événements » pour le "
      + "générer automatiquement depuis vos actes."));
    return;
  }
  const box = h("div", { class: "liste-pers" });
  data.lieux.forEach((l) => box.append(ligne(l, cont, data.lieux)));
  cont.append(box);
}

function ligne(l, cont, tous) {
  const meta = [l.type, l.noms_dates.length ? l.noms_dates.length + " nom(s) daté(s)" : ""]
    .filter(Boolean).join(" · ");
  return h("div", { class: "ligne-pers", onclick: () => formulaire(cont, l, tous) },
    h("strong", {}, l.chemin || l.nom),
    meta ? h("span", { class: "meta" }, meta) : null);
}

function champ(label, control) {
  return h("label", { style: "display:block;margin:.5rem 0" },
    h("span", { class: "sous-titre", style: "display:block;margin-bottom:2px" }, label), control);
}

function formulaire(cont, l, tous) {
  vider(cont);
  const edit = !!l;
  l = l || { noms_dates: [] };
  const nom = h("input", { value: l.nom || "" });
  const type = h("select", {});
  type.append(h("option", { value: "" }, "— type —"));
  TYPES.forEach((t) => type.append(h("option", Object.assign({ value: t }, l.type === t ? { selected: true } : {}), t)));
  const parent = h("select", {});
  parent.append(h("option", { value: "" }, "— aucun parent —"));
  tous.filter((x) => x.id !== l.id).forEach((x) =>
    parent.append(h("option", Object.assign({ value: x.id }, l.parent === x.id ? { selected: true } : {}), x.chemin || x.nom)));

  const ndBox = h("div", {});
  const rangs = [];
  function ajoutRang(nd) {
    nd = nd || { nom: "", apres: "", avant: "" };
    const rnom = h("input", { value: nd.nom || "", placeholder: "nom historique", style: "flex:2;min-width:120px" });
    const rap = h("input", { value: nd.apres == null ? "" : nd.apres, placeholder: "après (an)", type: "number", style: "flex:1;min-width:70px" });
    const rav = h("input", { value: nd.avant == null ? "" : nd.avant, placeholder: "avant (an)", type: "number", style: "flex:1;min-width:70px" });
    const ref = { rnom, rap, rav };
    const row = h("div", { class: "rangee serre", style: "margin:.3rem 0" },
      rnom, rap, rav,
      h("button", { class: "bouton secondaire petit",
        onclick: () => { row.remove(); const i = rangs.indexOf(ref); if (i >= 0) rangs.splice(i, 1); } }, "✕"));
    rangs.push(ref);
    ndBox.append(row);
  }
  (l.noms_dates || []).forEach(ajoutRang);

  cont.append(h("div", { class: "carte" },
    h("h2", {}, edit ? "Modifier le lieu" : "Nouveau lieu"),
    champ("Nom courant *", nom),
    champ("Type", type),
    champ("Rattaché à (parent)", parent),
    h("div", { style: "margin:.7rem 0 .2rem" },
      h("span", { class: "sous-titre" }, "Noms datés (alternatifs, historiques)")),
    ndBox,
    h("button", { class: "bouton secondaire petit", onclick: () => ajoutRang() }, "＋ Ajouter un nom daté"),
    h("div", { class: "barre-actions", style: "margin-top:.9rem" },
      h("button", {
        class: "bouton",
        onclick: async () => {
          const noms_dates = rangs.map((r) => ({ nom: r.rnom.value.trim(), apres: r.rap.value, avant: r.rav.value }))
            .filter((x) => x.nom);
          const payload = { nom: nom.value.trim(), type: type.value, parent: parent.value, noms_dates };
          if (!payload.nom) { toast("Le nom est requis."); return; }
          try {
            if (edit) await apiJson("/api/lieux-ref/" + encodeURIComponent(l.id), "PUT", payload);
            else await apiJson("/api/lieux-ref", "POST", payload);
            toast("Lieu enregistré."); recharger(cont);
          } catch (e) { toast(e.message); }
        },
      }, edit ? "Enregistrer" : "Créer"),
      edit ? h("button", {
        class: "bouton danger",
        onclick: async () => {
          if (!await confirmer("Supprimer « " + l.nom + " » du référentiel ? "
            + "(les événements gardent leur texte)",
            { titre: "Supprimer le lieu", valider: "Supprimer", danger: true })) return;
          try {
            await apiJson("/api/lieux-ref/" + encodeURIComponent(l.id), "DELETE", {});
            toast("Lieu supprimé."); recharger(cont);
          } catch (e) { toast(e.message); }
        },
      }, "Supprimer") : null,
      h("button", { class: "bouton secondaire", onclick: () => recharger(cont) }, "Annuler"))));
}
