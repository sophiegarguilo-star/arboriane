// Champ « lieu » avec autocomplétion :
//  1) les lieux déjà présents dans l'arbre (instantané, hors ligne) ;
//  2) si le géocodage est autorisé (Réglages), de vraies communes géolocalisées
//     proposées par OpenStreetMap (Nominatim). Choisir une commune géolocalisée
//     mémorise ses coordonnées → elle apparaît aussitôt sur la carte.
// La saisie reste LIBRE. Renvoie { element, valeur() }.
import { h, vider } from "../noyau/dom.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { normaliser } from "../noyau/texte.js";

let _cacheLieux = null;

// Récupère (une fois) la liste des lieux connus de l'arbre.
export async function chargerLieux(apiGetFn) {
  if (_cacheLieux) return _cacheLieux;
  try {
    const r = await (apiGetFn || apiGet)("/api/lieux");
    _cacheLieux = (r.lieux || []).map((l) => l.nom).filter(Boolean);
  } catch { _cacheLieux = []; }
  return _cacheLieux;
}

export function oublierCacheLieux() { _cacheLieux = null; }

// Raccourcit un libellé OSM « Reims, Marne, Grand Est, France » → « Reims, Marne ».
function libelleCourt(nom) {
  return (nom || "").split(",").map((s) => s.trim()).filter(Boolean).slice(0, 2).join(", ");
}

export function champLieu(connus, { valeur = "", placeholder = "Ville, département…",
                                    largeur = "100%" } = {}) {
  const input = h("input", { type: "text", value: valeur, placeholder,
    autocomplete: "off", style: "width:" + largeur });
  const menu = h("div", { class: "champ-menu" });
  const boite = h("div", { class: "champ-auto" }, input, menu);
  const liste = connus || [];
  let tGeo = null;

  function fermer() { menu.classList.remove("on"); }

  // rendre(locaux, geo, activable) : lieux de l'arbre + communes en ligne +
  // (option) une ligne pour activer les suggestions en ligne d'un clic.
  function rendre(locaux, geo, activable) {
    vider(menu);
    if (!locaux.length && !geo.length && !activable) { fermer(); return; }
    locaux.forEach((l) => menu.append(h("div", { class: "champ-option",
      onmousedown: (e) => { e.preventDefault(); input.value = l; fermer(); } }, l)));
    geo.forEach((g) => {
      const court = libelleCourt(g.nom);
      menu.append(h("div", { class: "champ-option",
        onmousedown: async (e) => {
          e.preventDefault(); input.value = court; fermer();
          // mémorise les coordonnées connues : le lieu est prêt pour la carte
          try { await apiJson("/api/lieux/coords", "POST", { nom: court, lat: g.lat, lon: g.lon }); }
          catch { /* sans réseau : tant pis, le lieu reste utilisable */ }
        } },
        h("span", {}, "📍 " + court),
        h("span", { style: "color:var(--gris-clair);font-size:12px" },
          g.pays ? "  · " + g.pays : "")));
    });
    if (activable) {
      menu.append(h("div", { class: "champ-option", style: "color:var(--accent)",
        onmousedown: async (e) => {
          e.preventDefault();
          try {
            await apiJson("/api/reglages", "PUT", { geocodage_ok: true });
            interrogerEnLigne(locaux, input.value.trim());   // relance aussitôt
          } catch { /* ignore */ }
        } }, "🌍 Proposer de vraies communes (activer, une seule fois)"));
    }
    menu.classList.add("on");
  }

  async function interrogerEnLigne(locaux, saisie) {
    if (saisie.length < 3) return;
    try {
      const r = await apiGet("/api/lieux/suggest?q=" + encodeURIComponent(saisie));
      if (input.value.trim().toLowerCase() !== saisie.toLowerCase()) return;  // saisie changée
      if (r.geocodage_ok === false) { rendre(locaux, [], true); return; }     // proposer d'activer
      if ((r.suggestions || []).length) rendre(locaux, r.suggestions);
    } catch { /* pas de suggestions en ligne */ }
  }

  function ouvrir() {
    const q = normaliser(input.value.trim());
    if (q.length < 2) { fermer(); return; }
    const locaux = liste.filter((l) => normaliser(l).includes(q)).slice(0, 6);
    rendre(locaux, []);
    clearTimeout(tGeo);
    tGeo = setTimeout(() => interrogerEnLigne(locaux, input.value.trim()), 350);
  }
  input.addEventListener("input", ouvrir);
  input.addEventListener("focus", ouvrir);
  input.addEventListener("blur", () => setTimeout(fermer, 200));

  return { element: boite, valeur: () => input.value.trim() };
}
