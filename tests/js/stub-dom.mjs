// Stub DOM minimal, sans dépendance, pour tester le noyau frontend sous Node.
//
// Node n'a pas de DOM. Plutôt que d'installer jsdom (une dépendance, contraire à
// l'esprit d'Arboriane), on reproduit le strict nécessaire — createElement,
// createTextNode, et les quelques méthodes/propriétés que web/noyau/dom.js
// utilise. On teste le CODE, pas ce stub : les assertions portent sur ce que h()
// fait des attributs, des écouteurs et des enfants.

class Noeud {
  constructor(tag) {
    this.tagName = tag ? tag.toUpperCase() : "";
    this.nodeType = 1;
    this.childNodes = [];
    this.attributes = {};
    this.listeners = {};
    this.style = {};
    this.className = "";
    this._html = null;
  }
  setAttribute(k, v) { this.attributes[k] = String(v); }
  getAttribute(k) { return k in this.attributes ? this.attributes[k] : null; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  set innerHTML(v) { this._html = v; this.childNodes = []; }
  get innerHTML() { return this._html; }
  append(...noeuds) {
    for (const n of noeuds) this.childNodes.push(n);
  }
  appendChild(n) { this.childNodes.push(n); return n; }
  removeChild(n) {
    this.childNodes = this.childNodes.filter((c) => c !== n);
    return n;
  }
  get firstChild() { return this.childNodes[0] || null; }
  // confort pour les assertions
  get textContent() {
    return this.childNodes.map((c) => c.nodeType === 3 ? c.data : c.textContent).join("");
  }
}

class NoeudTexte {
  constructor(data) { this.nodeType = 3; this.data = String(data); }
  get textContent() { return this.data; }
}

export function installerDOM() {
  globalThis.document = {
    createElement: (tag) => new Noeud(tag),
    createTextNode: (data) => new NoeudTexte(data),
  };
}
