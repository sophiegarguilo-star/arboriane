// Bouton de dictée vocale (Web Speech API, français). Ajoute le texte reconnu
// au champ fourni. Renvoie un <button>, ou null si le navigateur ne sait pas
// faire de reconnaissance vocale (rien ne s'affiche alors).
// La reconnaissance passe par un service en ligne du navigateur : à n'utiliser
// que sur demande explicite de l'utilisatrice (clic sur le bouton).
import { h } from "../noyau/dom.js";
import { toast } from "./toast.js";

export function boutonMicro(champ) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  let reco = null, actif = false;
  const btn = h("button", { type: "button", class: "bouton secondaire petit btn-micro",
    title: "Dicter à la voix (français) — utilise le service de reconnaissance du navigateur" },
    "🎤 Dicter");

  function arreter() {
    actif = false; btn.classList.remove("actif"); btn.textContent = "🎤 Dicter";
    if (reco) { try { reco.stop(); } catch { /* déjà arrêté */ } }
  }

  btn.addEventListener("click", () => {
    if (actif) { arreter(); return; }
    reco = new SR();
    reco.lang = "fr-FR"; reco.interimResults = false; reco.continuous = true;
    reco.onresult = (e) => {
      let fin = "";
      for (let i = e.resultIndex; i < e.results.length; i++)
        if (e.results[i].isFinal) fin += e.results[i][0].transcript;
      fin = fin.trim();
      if (fin) {
        const sep = champ.value && !/\s$/.test(champ.value) ? " " : "";
        champ.value += sep + fin;
        champ.dispatchEvent(new Event("input", { bubbles: true }));
      }
    };
    reco.onerror = (e) => {
      arreter();
      toast((e.error === "not-allowed" || e.error === "service-not-allowed")
        ? "🎤 Micro refusé — autorisez le microphone dans le navigateur, puis réessayez."
        : "🎤 Dictée indisponible (" + (e.error || "erreur") + ").");
    };
    reco.onend = () => arreter();
    try {
      reco.start(); actif = true;
      btn.classList.add("actif"); btn.textContent = "⏹ Arrêter la dictée";
    } catch { toast("🎤 Impossible de démarrer la dictée."); }
  });
  return btn;
}
