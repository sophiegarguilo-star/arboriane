# -*- coding: utf-8 -*-
"""
Ouverture d'un navigateur MODERNE — jamais Internet Explorer.

Arboriane s'affiche dans le navigateur (modules ES, fetch…). Internet Explorer
ne sait pas l'exécuter, et bloque en prime le téléchargement des mises à jour.
Or `webbrowser.open()` suit le navigateur PAR DÉFAUT du système, qui reste IE
sur certaines machines. On ouvre donc de préférence Edge, Chrome (ou Firefox),
avec repli sur le comportement par défaut.

L'utilisateur peut IMPOSER son navigateur via le réglage « navigateur » (Réglages
› Ouverture) : "edge" | "chrome" | "firefox" | "defaut" (navigateur système).
"""
import json
import os
import shutil
import subprocess
import webbrowser

# Chemins candidats par navigateur (nom court → résolu via PATH ; sinon absolu).
_NAVIGATEURS = {
    "edge": ["msedge",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"],
    "chrome": ["chrome",
               r"C:\Program Files\Google\Chrome\Application\chrome.exe",
               r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
    "firefox": ["firefox",
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"],
}
# Ordre d'essai par défaut (préférence historique : éviter Internet Explorer).
_ORDRE_DEFAUT = ["edge", "chrome", "firefox"]


def lire_prefere(dossier_donnees):
    """Navigateur préféré lu dans <dossier>/reglages.json ('' si absent/illisible)."""
    try:
        with open(os.path.join(dossier_donnees, "reglages.json"), "r", encoding="utf-8") as f:
            return (json.load(f).get("navigateur") or "").strip().lower()
    except (OSError, ValueError, AttributeError):
        return ""


def _lancer(navigateur, url):
    """Tente d'ouvrir `url` avec un navigateur nommé. True si lancé."""
    for c in _NAVIGATEURS.get(navigateur, ()):
        chemin = shutil.which(c) if os.path.basename(c) == c else c
        if chemin and os.path.exists(chemin):
            try:
                subprocess.Popen([chemin, url])
                return True
            except Exception:  # noqa: BLE001
                pass
    return False


def ouvrir(url, prefere=None):
    """Ouvre `url`. `prefere` ∈ {edge, chrome, firefox, defaut} force le choix ;
    None → Edge/Chrome/Firefox puis navigateur système. Ne lève jamais ; renvoie
    True si une ouverture a pu être lancée."""
    pref = (prefere or "").strip().lower()
    if pref == "defaut":                       # choix explicite : navigateur système
        try:
            webbrowser.open(url); return True
        except Exception:  # noqa: BLE001
            return False
    # ordre : le navigateur imposé d'abord (s'il est connu), puis les autres.
    ordre = ([pref] if pref in _NAVIGATEURS else []) + \
            [b for b in _ORDRE_DEFAUT if b != pref]
    for nav in ordre:
        if _lancer(nav, url):
            return True
    try:
        webbrowser.open(url); return True
    except Exception:  # noqa: BLE001
        return False
