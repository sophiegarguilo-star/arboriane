// Lecture d'un fichier en base64 de ses OCTETS BRUTS (jamais en texte).
//
// IMPORTANT : ne JAMAIS lire un GEDCOM avec `fichier.text()` / FileReader.readAsText
// côté navigateur — ces API décodent TOUJOURS en UTF-8, ce qui transforme les
// accents d'un fichier ANSI/ANSEL/IBMPC en « � » AVANT même l'envoi au serveur
// (bug vécu). On envoie les octets bruts (base64) et c'est le serveur qui détecte
// l'encodage (`services/gedcom_charset`) et décode sans jamais perdre d'accent.
export async function lireOctetsB64(fichier) {
  const buf = new Uint8Array(await fichier.arrayBuffer());
  let bin = "";
  const pas = 0x8000;                          // découpe : évite de saturer la pile
  for (let i = 0; i < buf.length; i += pas) {
    bin += String.fromCharCode.apply(null, buf.subarray(i, i + pas));
  }
  return btoa(bin);
}
