// Onglet Lieux / Carte — agrégation des lieux + carte des migrations dans le
// temps. Le géocodage (OpenStreetMap / Nominatim) est strictement opt-in :
// il n'envoie QUE les noms de lieux, et seulement sur action explicite.
import { h, vider } from "../noyau/dom.js";
import { aller, etat, surNavigation } from "../noyau/etat.js";
import { apiGet, apiJson } from "../noyau/api.js";
import { champPersonne } from "../composants/champ.js";

// Nettoyage en quittant l'onglet : on arrête l'animation des migrations (sinon
// le timer tourne indéfiniment en tâche de fond) et on détruit la carte de la
// liste (sinon Leaflet la garde en vie via ses écouteurs globaux -> fuite).
let _carteListe = null;
surNavigation((nom) => {
  if (nom !== "lieux") {
    stopLecture();
    if (_carteListe) { try { _carteListe.remove(); } catch (e) { /* */ } _carteListe = null; }
  }
});

// Couleurs de la charte lues depuis les tokens CSS (Leaflet dessine sur un
// canvas : il lui faut une valeur de couleur, pas une classe).
function tok(nom, repli) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(nom).trim();
  return v || repli;
}

const MIG_TYPE = {
  N: ["●", "Naissance"], M: ["⚭", "Mariage"], D: ["✝", "Décès"],
  R: ["⌂", "Résidence"], E: ["◆", "Événement"],
};

// Sous-onglet mémorisé entre les rendus.
let _onglet = "tous";
// Autorisation locale d'envoi à OpenStreetMap (opt-in, DÉSACTIVÉ par défaut).
let _geocodageActif = false;
// Timer de lecture de la carte des migrations (nettoyé à chaque re-render).
let _migTimer = null;

/* Charge Leaflet à la demande depuis le CDN. Rejette si hors-ligne. */
let _leafletP = null;
function chargerLeaflet() {
  if (window.L) return Promise.resolve(window.L);
  if (_leafletP) return _leafletP;
  _leafletP = new Promise((res, rej) => {
    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = "/vendor/leaflet/leaflet.css";       // hébergé localement (pas de CDN)
    document.head.append(css);
    const s = document.createElement("script");
    s.src = "/vendor/leaflet/leaflet.js";
    s.onload = () => {
      // les marqueurs par défaut cherchent leurs images à côté du CSS
      if (window.L) window.L.Icon.Default.imagePath = "/vendor/leaflet/images/";
      res(window.L);
    };
    s.onerror = () => { _leafletP = null; rej(new Error("Leaflet indisponible")); };
    document.head.append(s);
  });
  return _leafletP;
}

function stopLecture() {
  if (_migTimer) { clearInterval(_migTimer); _migTimer = null; }
}

let _focusLieu = null;   // lieu à mettre en évidence (venu d'une fiche)

export async function vueLieux(vue, arg) {
  stopLecture();
  if (arg && arg.focus) { _focusLieu = arg.focus; _onglet = "tous"; }
  vue.append(h("h1", {}, "Lieux / Carte"));

  const onglet = (id, txt) => h("button", {
    class: "sous-onglet" + (_onglet === id ? " actif" : ""),
    onclick: () => { _onglet = id; aller("lieux"); },
  }, txt);
  vue.append(h("div", { class: "sous-onglets" },
    onglet("tous", "🗺 Tous les lieux"),
    onglet("migrations", "🧭 Migrations & temps")));

  const zone = h("div", {});
  vue.append(zone);
  if (_onglet === "migrations") return rendreMigrations(zone);
  return rendreTousLieux(zone);
}

/* ── Sous-vue « Tous les lieux » ──────────────────────────────────── */
async function rendreTousLieux(zone) {
  zone.append(h("p", { class: "sous-titre" },
    "Tous les lieux cités dans votre arbre (naissances, décès, mariages, "
    + "résidences). Le géocodage place les lieux sur la carte et enregistre "
    + "leurs coordonnées dans l'arbre."));

  const rep = await apiGet("/api/lieux").catch(() => ({ lieux: [], nb_a_geocoder: 0 }));
  // Reflète l'état RÉEL du réglage serveur (le géocodage est gardé côté serveur) :
  // sans ça, la page pouvait « activer » localement alors que le serveur refusait.
  const reg = await apiGet("/api/reglages").catch(() => ({}));
  _geocodageActif = !!reg.geocodage_ok;
  const lieux = rep.lieux || [];
  if (!lieux.length) {
    zone.append(h("div", { class: "carte" }, h("p", { class: "vide" },
      "Aucun lieu renseigné pour l'instant. Ajoutez des lieux de naissance, "
      + "décès ou mariage aux fiches : ils apparaîtront ici.")));
    return;
  }
  const avecCoords = lieux.filter((l) => l.lat != null);

  // — Bandeau géocodage (opt-in, désactivé par défaut) —
  const bandeau = h("div", { class: "carte" });
  function rendreBandeau() {
    vider(bandeau);
    bandeau.append(h("div", { class: "stats" },
      stat(lieux.length, "lieu(x)"),
      stat(avecCoords.length, "placé(s) sur la carte"),
      stat(rep.nb_a_geocoder, "à géocoder")));

    if (!_geocodageActif) {
      bandeau.append(
        h("p", { class: "sous-titre" },
          "Le géocodage envoie SEULEMENT les noms de lieux à OpenStreetMap "
          + "(Nominatim) pour obtenir leurs coordonnées, à raison d'un lieu par "
          + "seconde. Aucune donnée personnelle n'est transmise. C'est optionnel "
          + "et désactivé par défaut."),
        h("button", {
          class: "bouton",
          onclick: async (ev) => {
            const b = ev.currentTarget; b.disabled = true;
            // Persiste le VRAI réglage serveur (sinon « Géocoder » serait refusé).
            try { await apiJson("/api/reglages", "PUT", { geocodage_ok: true }); }
            catch (e) { b.disabled = false; return; }
            _geocodageActif = true; rendreBandeau();
          },
        }, "Activer le géocodage (OpenStreetMap)"));
    } else if (rep.nb_a_geocoder) {
      const prog = h("span", { class: "sous-titre", style: "margin-left:10px" });
      const btn = h("button", { class: "bouton" },
        "🌍 Géocoder " + rep.nb_a_geocoder + " lieu(x)");
      btn.addEventListener("click", () => geocoderTout(btn, prog));
      bandeau.append(h("div", { class: "barre-actions" },
        btn, prog,
        h("button", {
          class: "bouton secondaire",
          onclick: async () => {
            try { await apiJson("/api/reglages", "PUT", { geocodage_ok: false }); }
            catch (e) { /* réglage best-effort */ }
            _geocodageActif = false; rendreBandeau();
          },
        }, "Désactiver")));
    } else {
      bandeau.append(h("p", { style: "color:var(--vert)" }, "Tous les lieux sont géocodés. 🎉"));
    }
  }
  async function geocoderTout(btn, prog) {
    btn.disabled = true;
    let restants = rep.nb_a_geocoder;
    const total = restants;
    prog.textContent = "Géocodage… 0 / " + total + " (≈ 1 lieu/seconde)";
    while (restants > 0) {
      const r = await apiJson("/api/lieux/geocoder", "POST", {})
        .catch((e) => ({ erreur: e.message || "réseau" }));
      if (r.erreur) { prog.textContent = "⚠ " + r.erreur; btn.disabled = false; return; }
      if (r.geocodage_ok === false) {   // le serveur refuse : réglage désactivé
        prog.textContent = "⚠ Le géocodage est désactivé dans les Réglages. "
          + "Activez-le pour placer les lieux sur la carte.";
        btn.disabled = false; return;
      }
      if (r.restants >= restants) {     // aucun progrès : lieux introuvables
        prog.textContent = r.restants + " lieu(x) introuvable(s) chez OpenStreetMap.";
        break;
      }
      restants = r.restants;
      prog.textContent = "Géocodage… " + (total - restants) + " / " + total;
    }
    if (etat.vue === "lieux") aller("lieux");   // ne pas arracher l'utilisateur d'un autre onglet
  }
  rendreBandeau();
  zone.append(bandeau);

  // — Carte Leaflet (si en ligne et des coords) —
  const carteBox = h("div", { class: "carte" });
  const mapDiv = h("div", { style: "height:420px;border-radius:var(--rayon);overflow:hidden" });
  carteBox.append(mapDiv);
  zone.append(carteBox);
  if (avecCoords.length) {
    chargerLeaflet().then((L) => {
      if (_carteListe) { try { _carteListe.remove(); } catch (e) { /* */ } }
      const map = L.map(mapDiv).setView([avecCoords[0].lat, avecCoords[0].lon], 5);
      _carteListe = map;
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(map);
      const marqueurs = [];
      avecCoords.forEach((l) => {
        const noms = l.personnes.map((p) => p.nom).join(", ");
        const m = L.marker([l.lat, l.lon]).addTo(map)
          .bindPopup("<strong>" + echapHtml(l.nom) + "</strong><br>" + l.nb
            + " occurrence(s)" + (noms ? "<br>" + echapHtml(noms) : ""));
        marqueurs.push(m);
      });
      if (marqueurs.length > 1) map.fitBounds(L.featureGroup(marqueurs).getBounds().pad(0.2));
      setTimeout(() => map.invalidateSize(), 60);
    }).catch(() => {
      carteBox.append(h("p", { class: "sous-titre" },
        "Carte indisponible (hors-ligne). La liste ci-dessous reste utilisable."));
    });
  } else {
    carteBox.append(h("p", { class: "vide" },
      _geocodageActif ? "Lancez le géocodage pour placer les lieux sur la carte."
        : "Activez le géocodage pour placer les lieux sur la carte."));
  }

  // — Liste des lieux —
  const table = h("table", { style: "width:100%;border-collapse:collapse" },
    h("thead", {}, h("tr", {},
      th("Lieu"), th("Occurrences", "120px"), th("Personnes", "120px"),
      th("Coordonnées", "170px"))));
  const corps = h("tbody", {});
  let ligneFocus = null;
  lieux.forEach((l) => {
    const surligne = _focusLieu && l.nom.toLowerCase() === _focusLieu.toLowerCase();
    const persos = l.personnes || [];
    // Colonne « Personnes » cliquable : déplie la liste des personnes de ce lieu,
    // chacune menant à sa fiche (parcours lieu → personne, avec retour naturel).
    let tr, detail = null;
    const basculer = () => {
      if (detail) { detail.remove(); detail = null; return; }
      detail = h("tr", {}, h("td", { colspan: "4",
        style: "padding:6px 12px;background:var(--ivoire)" },
        h("div", { class: "rangee serre", style: "flex-wrap:wrap;gap:6px" },
          ...persos.map((p) => h("button", { class: "puce-pers",
            onclick: () => aller("personnes", { fiche: p.id }) }, p.nom)),
          l.nb_personnes > persos.length
            ? h("span", { class: "meta" }, "… +" + (l.nb_personnes - persos.length)) : null)));
      tr.after(detail);
    };
    const cellPers = persos.length
      ? h("td", { style: "padding:6px 8px" },
          h("button", { class: "lien", title: "Voir les personnes de ce lieu",
            onclick: basculer }, String(l.nb_personnes) + " ▾"))
      : td(String(l.nb_personnes));
    tr = h("tr", { style: "border-bottom:1px solid var(--bord)"
      + (surligne ? ";background:var(--sauge-pale)" : "") },
      td(l.nom), td(String(l.nb)), cellPers,
      td(l.lat != null ? l.lat.toFixed(4) + ", " + l.lon.toFixed(4) : "à géocoder",
        l.lat == null ? "color:var(--gris)" : ""));
    if (surligne) ligneFocus = tr;
    corps.append(tr);
  });
  table.append(corps);
  zone.append(h("div", { class: "carte" }, h("h2", {}, "Liste des lieux"), table));
  if (ligneFocus) {
    ligneFocus.scrollIntoView({ behavior: "smooth", block: "center" });
    _focusLieu = null;   // ne surligne qu'une fois
  }
}

/* ── Sous-vue « Migrations & temps » ──────────────────────────────── */
async function rendreMigrations(zone) {
  const liste = await apiGet("/api/individus").catch(() => []);
  if (!liste.length) { zone.append(h("div", { class: "vide" }, "Arbre vide.")); return; }
  const racine = (etat.espace || {}).racine_id;
  let pid = (racine && liste.find((p) => p.id === racine)) ? racine : liste[0].id;

  const sel = champPersonne(liste, { initial: pid, placeholder: "Personne…",
    onChoix: (id) => { if (id) { pid = id; charger(); } } });
  const scopeSel = h("select", {},
    h("option", { value: "personne" }, "Parcours de la personne"),
    h("option", { value: "lignee" }, "Toute sa lignée (ancêtres)"));
  const btnPlay = h("button", { type: "button", title: "Lecture / pause",
    class: "bouton" }, "▶");
  const lblAnnee = h("div", { style: "font-weight:600;min-width:64px;text-align:right" }, "—");
  const curseur = h("input", { type: "range", min: "0", max: "1", value: "0",
    style: "width:100%;accent-color:var(--accent)" });
  const mapDiv = h("div", { style: "height:440px;border-radius:var(--rayon);overflow:hidden;margin-top:10px" });
  const noteMono = h("div", {});          // hint « rien à animer » (persistant)
  const infoAna = h("div", { style: "margin-top:10px" });

  zone.append(
    h("p", { class: "sous-titre" },
      "Suivez les déplacements dans le temps : glissez le curseur ou appuyez sur ▶. "
      + "Un ⚠ signale un nom de lieu anachronique à sa date."),
    h("div", { class: "carte" },
      h("div", { style: "display:flex;gap:14px;align-items:flex-end;flex-wrap:wrap" },
        h("div", {}, h("label", {}, "Personne"), sel.element),
        h("div", {}, h("label", {}, "Portée"), scopeSel),
        h("div", { style: "flex:1" }),
        btnPlay, lblAnnee),
      h("div", { style: "margin-top:12px" }, curseur),
      legende(),
      mapDiv,
      noteMono,
      infoAna));

  let L = null, map = null, couche = null, trace = null;
  let evs = [], minA = 0, maxA = 0;
  // Couleurs des marqueurs/tracé (canvas Leaflet) : tokens de la charte.
  const COUL_ACCENT = tok("--accent", "#c76b2a");
  const COUL_AVENIR = tok("--gris-clair", "#c9b99a");
  const COUL_ANA = tok("--alerte", "#b3541e");
  const COUL_BLANC = tok("--blanc", "#ffffff");

  function stop() { stopLecture(); btnPlay.textContent = "▶"; }

  function rendre(an) {
    an = +an; lblAnnee.textContent = an;
    if (!couche) return;
    couche.clearLayers();
    const perso = scopeSel.value === "personne";
    evs.forEach((e) => {
      const vu = e.annee <= an;
      const m = L.circleMarker([e.lat, e.lon], {
        radius: vu ? 7 : 5, weight: 2,
        color: e.anachronisme ? COUL_ANA : (vu ? COUL_ACCENT : COUL_AVENIR),
        fillColor: vu ? COUL_ACCENT : COUL_BLANC, fillOpacity: vu ? 0.9 : 0.5,
      }).bindPopup("<b>" + echapHtml(e.nom) + "</b><br>" + MIG_TYPE[e.type][1] + " · "
        + echapHtml(e.lieu) + " (" + e.annee + ")"
        + (e.anachronisme ? "<br>⚠ " + echapHtml(e.anachronisme) : ""));
      couche.addLayer(m);
    });
    trace.setLatLngs(perso ? evs.filter((e) => e.annee <= an).map((e) => [e.lat, e.lon]) : []);
    const anas = evs.filter((e) => e.anachronisme && e.annee <= an);
    vider(infoAna);
    if (anas.length) {
      infoAna.append(h("div", { class: "encart attention" },
        h("div", { class: "encart-tete" },
          h("span", { class: "encart-ico" }, "⚠"),
          h("strong", { class: "encart-titre" },
            anas.length + " anachronisme(s) possible(s)")),
        h("div", { class: "encart-corps" },
          ...anas.map((e) => h("div", { style: "margin-top:4px" },
            h("strong", {}, e.lieu + " (" + e.annee + ")"), " — " + e.anachronisme)))));
    }
  }

  function initCarte() {
    if (map) { map.remove(); map = null; }
    mapDiv.innerHTML = "";
    map = L.map(mapDiv);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 18, attribution: "© OpenStreetMap" }).addTo(map);
    couche = L.layerGroup().addTo(map);
    trace = L.polyline([], { color: COUL_ACCENT, weight: 3, opacity: 0.85 }).addTo(map);
    map.fitBounds(L.latLngBounds(evs.map((e) => [e.lat, e.lon])).pad(0.25));
    setTimeout(() => map.invalidateSize(), 80);
  }

  async function charger() {
    stop();
    const data = await apiGet("/api/carte?id=" + encodeURIComponent(pid)
      + "&mode=" + scopeSel.value).catch(() => ({ evenements: [] }));
    evs = data.evenements || [];
    vider(infoAna); vider(noteMono);
    if (!evs.length) {
      mapDiv.innerHTML = "";
      mapDiv.append(h("div", { class: "vide", style: "padding:24px" },
        "Aucun lieu géocodé pour cette sélection. Ouvrez « Tous les lieux » pour "
        + "activer le géocodage et placer les lieux sur la carte."));
      lblAnnee.textContent = "—"; curseur.disabled = true;
      return;
    }
    if (evs.length < 2 || data.min === data.max) {
      noteMono.append(h("div", { class: "vide", style: "padding:10px 12px;margin-top:8px" },
        "Un seul lieu daté pour cette sélection : rien à animer dans le temps. "
        + "Ajoutez des dates aux événements, ou élargissez la portée à « Toute sa "
        + "lignée » pour voir les migrations se dessiner."));
    }
    curseur.disabled = false;
    minA = data.min; maxA = data.max;
    curseur.min = minA; curseur.max = maxA; curseur.value = minA;
    if (!L) L = await chargerLeaflet().catch(() => null);
    if (!L) {
      mapDiv.innerHTML = "";
      mapDiv.append(h("div", { class: "vide" }, "Carte indisponible (hors-ligne)."));
      return;
    }
    initCarte();
    rendre(minA);
  }

  curseur.addEventListener("input", () => { stop(); rendre(curseur.value); });
  scopeSel.addEventListener("change", charger);
  btnPlay.addEventListener("click", () => {
    if (_migTimer) { stop(); return; }
    if (+curseur.value >= maxA) curseur.value = minA;
    btnPlay.textContent = "⏸";
    const pas = Math.max(1, Math.round((maxA - minA) / 120));
    _migTimer = setInterval(() => {
      let v = +curseur.value + pas;
      if (v >= maxA) { v = maxA; curseur.value = v; rendre(v); stop(); return; }
      curseur.value = v; rendre(v);
    }, 90);
  });

  return charger();
}

/* ── Petits helpers de présentation ───────────────────────────────── */
function stat(n, label) {
  return h("div", { class: "stat" }, h("strong", {}, String(n)), h("span", {}, label));
}
function th(txt, largeur) {
  return h("th", { style: "text-align:left;padding:6px 8px;border-bottom:2px solid var(--bord)"
    + (largeur ? ";width:" + largeur : "") }, txt);
}
function td(txt, extra) {
  return h("td", { style: "padding:6px 8px" + (extra ? ";" + extra : "") }, txt);
}
function legende() {
  const item = (sw, txt) => h("span", { class: "legende-item" }, sw, txt);
  const pastille = (couleur) => h("i", { class: "legende-pastille",
    style: "background:" + couleur });
  return h("div", { class: "legende" },
    item(pastille("var(--accent)"), "visité"),
    item(pastille("var(--gris-clair)"), "à venir"),
    item("", "● naissance"), item("", "⚭ mariage"),
    item("", "⌂ résidence"), item("", "✝ décès"), item("", "⚠ anachronisme"));
}
function echapHtml(t) {
  return String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
