// Accès à l'API locale. Tout est same-origin (127.0.0.1) : aucune donnée ne
// sort de la machine.

async function _lire(reponse) {
  let corps = {};
  try { corps = await reponse.json(); } catch { /* corps vide */ }
  if (!reponse.ok) {
    const err = new Error(corps.erreur || ("Erreur " + reponse.status));
    err.code = reponse.status;
    throw err;
  }
  return corps;
}

// Indicateur « traitement en cours » : un bandeau discret apparaît si une
// requête dure plus de 400 ms (import, géocodage, stats sur gros arbre…). Compte
// les requêtes concurrentes pour ne se cacher qu'une fois TOUT terminé.
let _enCours = 0, _minuteur = null, _bandeau = null;
function _afficherTraitement(oui) {
  if (oui && !_bandeau) {
    _bandeau = document.createElement("div");
    _bandeau.className = "traitement-encours";
    _bandeau.innerHTML = '<span class="traitement-rond"></span>Traitement en cours…';
    document.body.appendChild(_bandeau);
  }
  if (_bandeau) _bandeau.classList.toggle("visible", oui);
}
function _debutRequete() {
  _enCours += 1;
  if (_enCours === 1) _minuteur = setTimeout(() => _afficherTraitement(true), 400);
}
function _finRequete() {
  _enCours = Math.max(0, _enCours - 1);
  if (_enCours === 0) { clearTimeout(_minuteur); _minuteur = null; _afficherTraitement(false); }
}

// Enveloppe le fetch : une panne réseau (serveur arrêté) lève un TypeError
// « Failed to fetch » incompréhensible → on le remplace par un message clair.
async function _appel(chemin, options) {
  _debutRequete();
  try {
    let reponse;
    try {
      reponse = await fetch(chemin, options);
    } catch {
      const err = new Error("Arboriane ne répond pas. Vérifiez que l'application "
        + "est bien lancée, puis réessayez.");
      err.code = 0;
      throw err;
    }
    return await _lire(reponse);
  } finally {
    _finRequete();
  }
}

export async function apiGet(chemin) {
  return _appel(chemin, { headers: { "Accept": "application/json" } });
}

// Mutation : Content-Type application/json (exigé par la sécurité serveur).
export async function apiJson(chemin, methode, corps) {
  return _appel(chemin, {
    method: methode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corps || {}),
  });
}
