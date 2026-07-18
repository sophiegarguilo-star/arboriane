// Personnes — doublons probables & fusion (volet latéral).
import { h } from "../../noyau/dom.js";
import { aller } from "../../noyau/etat.js";
import { apiGet, apiJson } from "../../noyau/api.js";
import { toast } from "../../composants/toast.js";
import { ouvrirVolet, fermerVolet } from "../../composants/volet.js";
import { confirmer } from "../../composants/modale.js";

export async function ouvrirDoublons() {
  const r = await apiGet("/api/doublons").catch(() => ({ }));
  const paires = Array.isArray(r) ? r : (r.doublons || r.paires || []);
  const contenu = h("div", {});
  if (!paires.length) {
    contenu.append(h("div", { class: "vide" },
      h("span", { class: "grand" }, "🎉"),
      "Aucun doublon probable détecté."));
  } else {
    contenu.append(h("p", { class: "sous-titre" },
      "Personnes très semblables. Fusionner conserve la première et y verse "
      + "les informations de la seconde (sans rien écraser)."));
    paires.forEach((p) => {
      const ligne = h("div", { class: "carte" },
        h("div", {}, h("b", { class: "nom" }, p.nom || "?")),
        p.raison ? h("div", { class: "meta" }, p.raison) : null,
        h("div", { class: "barre-actions", style: "margin-top:8px" },
          h("button", { class: "bouton petit", onclick: async () => {
            const ok = await confirmer("Fusionner ces deux fiches ? La seconde sera "
              + "absorbée dans la première.", { titre: "Fusionner", valider: "Fusionner" });
            if (!ok) return;
            try {
              await apiJson("/api/individus/fusionner", "POST", { garde: p.a, absorbe: p.b });
              toast("Fusion effectuée."); fermerVolet(); aller("personnes");
            } catch (e) { toast(e.message); }
          } }, "Fusionner"),
          h("button", { class: "bouton secondaire petit",
            onclick: () => { fermerVolet(); aller("personnes", { fiche: p.a }); } }, "Voir A"),
          h("button", { class: "bouton secondaire petit",
            onclick: () => { fermerVolet(); aller("personnes", { fiche: p.b }); } }, "Voir B")));
      contenu.append(ligne);
    });
  }
  ouvrirVolet(contenu, { titre: "Doublons possibles" });
}
