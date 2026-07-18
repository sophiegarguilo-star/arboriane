// Onglet « Dépôts d'archives » (L5+) — le dépôt (AD, mairie, site…) devient une
// entité réutilisable : 3e niveau du sourçage Dépôt → Source → Citation.
import { h, vider } from "../noyau/dom.js";
import { aller } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { badge } from "../composants/badge.js";
import { toast } from "../composants/toast.js";
import { confirmer } from "../composants/modale.js";

const TYPES = ["Archives départementales", "Archives municipales", "Archives nationales",
  "Mairie", "Site en ligne", "Bibliothèque", "Archives privées", "Autre"];

export async function vueDepots(vue) {
  vue.append(h("h1", {}, "🏛️ Dépôts d'archives"));
  vue.append(h("p", { class: "sous-titre" },
    "Où vos actes sont conservés (AD, mairie, site…). Un dépôt est un niveau du "
    + "sourçage : Dépôt → Source → Citation, et s'exporte en GEDCOM (REPO)."));
  const cont = h("div", {});
  vue.append(cont);
  await recharger(cont);
}

async function recharger(cont) {
  vider(cont);
  const data = await apiGet("/api/depots").catch(() => ({ depots: [] }));
  cont.append(h("div", { class: "barre-actions", style: "margin-bottom:1rem" },
    h("button", { class: "bouton secondaire", onclick: () => formulaire(cont, null) }, "➕ Ajouter un dépôt"),
    h("button", {
      class: "bouton",
      onclick: async () => {
        try {
          const r = await apiJson("/api/depots/promouvoir", "POST", {});
          toast(r.crees + " dépôt(s) créé(s), " + r.lies + " source(s) reliée(s).");
          recharger(cont);
        } catch (e) { toast(e.message); }
      },
    }, "✨ Promouvoir depuis les sources")));
  if (!data.depots.length) {
    cont.append(h("div", { class: "vide" },
      h("span", { class: "grand" }, "🏛️"),
      "Aucun dépôt. Ajoutez-en un, ou cliquez « Promouvoir depuis les sources » "
      + "pour les extraire automatiquement de vos actes existants."));
    return;
  }
  const box = h("div", { class: "grille-cartes large" });
  data.depots.forEach((d) => box.append(carteDepot(d, cont)));
  cont.append(box);
}

function carteDepot(d, cont) {
  const c = h("div", { class: "carte" },
    h("h2", {}, (d.nom || "(sans nom)") + " ",
      badge(d.nb_sources + " source" + (d.nb_sources > 1 ? "s" : ""))));
  if (d.type || d.lieu) {
    c.append(h("p", { class: "sous-titre" }, [d.type, d.lieu].filter(Boolean).join(" · ")));
  }
  if (d.www) {
    c.append(h("p", {}, h("a", { href: d.www, target: "_blank", rel: "noopener noreferrer" }, d.www)));
  }
  if (d.note) c.append(h("p", { class: "sous-titre" }, d.note));
  c.append(h("div", { class: "barre-actions", style: "margin-top:.6rem" },
    d.nb_sources ? h("button", { class: "bouton secondaire petit",
      onclick: () => aller("actes", { depot: d.nom }) }, "📄 Voir les sources") : null,
    h("button", { class: "bouton secondaire petit", onclick: () => formulaire(cont, d) }, "Modifier"),
    h("button", { class: "bouton danger petit",
      onclick: async () => {
        if (!await confirmer("Supprimer le dépôt « " + d.nom + " » ? Les sources "
          + "gardent leur nom en clair (rien n'est perdu).",
          { titre: "Supprimer le dépôt", valider: "Supprimer", danger: true })) return;
        try {
          await apiJson("/api/depots/" + encodeURIComponent(d.id), "DELETE", {});
          toast("Dépôt supprimé."); recharger(cont);
        } catch (e) { toast(e.message); }
      } }, "Supprimer")));
  return c;
}

function ligneChamp(label, control) {
  return h("label", { style: "display:block;margin:.5rem 0" },
    h("span", { class: "sous-titre", style: "display:block;margin-bottom:2px" }, label),
    control);
}

function formulaire(cont, d) {
  vider(cont);
  const edit = !!d;
  d = d || {};
  const nom = h("input", { value: d.nom || "", placeholder: "ex. Archives départementales du Nord" });
  const type = h("select", {});
  type.append(h("option", { value: "" }, "— type —"));
  TYPES.forEach((t) => type.append(h("option", Object.assign({ value: t }, d.type === t ? { selected: true } : {}), t)));
  const lieu = h("input", { value: d.lieu || "", placeholder: "ville / adresse" });
  const www = h("input", { value: d.www || "", type: "url", placeholder: "https://…" });
  const note = h("textarea", { rows: "2" }, d.note || "");
  cont.append(h("div", { class: "carte" },
    h("h2", {}, edit ? "Modifier le dépôt" : "Nouveau dépôt"),
    ligneChamp("Nom *", nom),
    ligneChamp("Type", type),
    ligneChamp("Lieu / adresse", lieu),
    ligneChamp("Site web", www),
    ligneChamp("Note", note),
    h("div", { class: "barre-actions", style: "margin-top:.6rem" },
      h("button", {
        class: "bouton",
        onclick: async () => {
          const payload = { nom: nom.value.trim(), type: type.value, lieu: lieu.value.trim(),
            www: www.value.trim(), note: note.value.trim() };
          if (!payload.nom) { toast("Le nom est requis."); return; }
          try {
            if (edit) await apiJson("/api/depots/" + encodeURIComponent(d.id), "PUT", payload);
            else await apiJson("/api/depots", "POST", payload);
            toast("Dépôt enregistré."); recharger(cont);
          } catch (e) { toast(e.message); }
        },
      }, edit ? "Enregistrer" : "Créer"),
      h("button", { class: "bouton secondaire", onclick: () => recharger(cont) }, "Annuler"))));
}
