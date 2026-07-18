// Façade — la vue « Personnes » a été découpée en modules (voir vues/personnes/).
// Ce fichier ne fait que ré-exporter le point d'entrée et l'action doublons,
// pour que les imports existants (app.js, coherence.js) restent inchangés.
export { vuePersonnes, ouvrirDoublons } from "./personnes/index.js";
