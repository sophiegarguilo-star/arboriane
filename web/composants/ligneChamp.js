// Ligne « libellé + champ » ACCESSIBLE (audit A11Y-05).
//
// Associe le libellé au champ (for/id) : cliquer le libellé donne le focus, et
// le lecteur d'écran annonce le nom du champ. À utiliser PARTOUT à la place du
// motif nu h("div",{class:"champ"}, h("label",{},X), Y).
//
// Accepte aussi les composants composés ({ element }) et les conteneurs : on
// vise alors le premier input/select/textarea qu'ils contiennent.
import { h } from "../noyau/dom.js";

let _seqChamp = 0;

export function ligneChamp(label, champ) {
  const bloc = champ && champ.element ? champ.element : champ;
  const cible = (bloc && bloc.matches && bloc.matches("input,select,textarea"))
    ? bloc
    : (bloc && bloc.querySelector ? bloc.querySelector("input,select,textarea") : null);
  const lbl = h("label", {}, label);
  if (cible) {
    const id = cible.id || ("champ-" + (++_seqChamp));
    cible.id = id;
    lbl.setAttribute("for", id);
  }
  return h("div", { class: "champ" }, lbl, bloc);
}
