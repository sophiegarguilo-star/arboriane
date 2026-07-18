# -*- coding: utf-8 -*-
"""
Assistant IA — FACULTATIF. Ne fonctionne qu'avec la clé de l'utilisateur.

Garde-fous absolus :
- l'IA ne modifie JAMAIS l'arbre elle-même (elle produit un brouillon à valider) ;
- aucune image n'est envoyée ; seules les données de la mission choisie partent ;
- rien n'est publié ; l'utilisateur valide toujours.

Fournisseurs : Anthropic, OpenAI, Gemini. Appels via urllib (aucune dépendance).
"""

import json
import urllib.request

from core import modele
from core.modele import nom_complet, periode
from services import sources as src_svc
from services import recherche as recherche_svc

MISSIONS = {
    "biographie": "Brouillon de biographie",
    "recherches": "Prochaines recherches",
    "coherence": "Contrôle de cohérence",
    "documenter": "Personnes à documenter",
}

_SYSTEME = (
    "Tu es l'assistant d'un généalogiste, dans un logiciel local et privé. "
    "Tu rédiges en français, avec prudence : tu ne inventes jamais de faits, tu "
    "distingues ce qui est prouvé de ce qui est supposé, et tu proposes des "
    "pistes vérifiables. Tes réponses sont des BROUILLONS À VÉRIFIER par l'humain.")


# ── Construction du contexte (jamais d'images) ────────────────────────
def _fiche_texte(donnees, pid):
    ind = donnees["individus"].get(pid)
    if not ind:
        return ""
    lignes = ["Personne : %s (%s)" % (nom_complet(ind), periode(ind) or "dates inconnues")]
    for etq, cle in (("Naissance", "naissance"), ("Décès", "deces")):
        ev = ind.get(cle) or {}
        if ev.get("date") or ev.get("lieu"):
            lignes.append("%s : %s %s" % (etq, ev.get("date", ""), ev.get("lieu", "")))
    profs = [p.get("valeur") for p in ind.get("professions", []) if p.get("valeur")]
    if profs:
        lignes.append("Professions : " + ", ".join(profs))
    pere, mere = modele.parents(donnees, pid)
    if pere:
        lignes.append("Père : " + nom_complet(donnees["individus"].get(pere, {})))
    if mere:
        lignes.append("Mère : " + nom_complet(donnees["individus"].get(mere, {})))
    pv = src_svc.preuves_personne(donnees, pid)
    lignes.append("Faits prouvés par acte : %d/%d" % (pv["prouves"], pv["total"]))
    return "\n".join(lignes)


def _contexte_mission(app, type_mission, cible):
    d = app.base.donnees
    if type_mission == "biographie" and cible:
        return ("Rédige une courte biographie (prudente, sourcée) à partir de :\n\n"
                + _fiche_texte(d, cible))
    if type_mission == "coherence":
        from services import coherence as coh
        alertes = coh.analyser(d)["alertes"][:20]
        txt = "\n".join("- %s : %s" % (a["personne_nom"], a["message"]) for a in alertes)
        return ("Voici des anomalies détectées automatiquement. Explique-les "
                "simplement et propose comment les lever :\n\n" + (txt or "Aucune."))
    if type_mission == "recherches":
        pl = recherche_svc.plan(d, app.manifeste.get("racine_id"))
        bouts = []
        for cat in pl["categories"][:4]:
            bouts.append(cat["nom"] + " :")
            for p in cat["pistes"][:5]:
                bouts.append("  - %s : %s" % (p["personne_nom"], p["quoi"]))
        return ("Priorise ces pistes de recherche et explique par où commencer :\n\n"
                + "\n".join(bouts))
    if type_mission == "documenter":
        s = [nom_complet(i) for i in d["individus"].values()
             if not src_svc.preuves_personne(d, i["id"])["prouves"]][:30]
        return ("Ces personnes manquent de preuves. Propose, pour chacune, un type "
                "de source à chercher :\n\n" + "\n".join("- " + n for n in s))
    return "Aide-moi sur mon arbre généalogique."


# ── Appel du fournisseur ──────────────────────────────────────────────
def _appeler(reglages, systeme, message):
    fournisseur = reglages.get("ia_fournisseur", "anthropic")
    cle = reglages.get("ia_cle") or ""
    if not cle:
        raise ValueError("Aucune clé API configurée.")
    modele_ia = reglages.get("ia_modele") or _MODELE_DEFAUT.get(fournisseur, "")
    if fournisseur == "anthropic":
        return _appeler_anthropic(cle, modele_ia, systeme, message)
    if fournisseur == "openai":
        return _appeler_openai(cle, modele_ia, systeme, message)
    if fournisseur == "gemini":
        return _appeler_gemini(cle, modele_ia, systeme, message)
    raise ValueError("Fournisseur inconnu : %s" % fournisseur)


_MODELE_DEFAUT = {"anthropic": "claude-3-5-haiku-latest",
                  "openai": "gpt-4o-mini", "gemini": "gemini-1.5-flash"}


def _poster(url, entetes, charge):
    req = urllib.request.Request(url, data=json.dumps(charge).encode("utf-8"),
                                 headers=entetes, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def _appeler_anthropic(cle, modele_ia, systeme, message):
    rep = _poster("https://api.anthropic.com/v1/messages",
                  {"x-api-key": cle, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"},
                  {"model": modele_ia, "max_tokens": 1500, "system": systeme,
                   "messages": [{"role": "user", "content": message}]})
    return "".join(b.get("text", "") for b in rep.get("content", []))


def _appeler_openai(cle, modele_ia, systeme, message):
    rep = _poster("https://api.openai.com/v1/chat/completions",
                  {"Authorization": "Bearer " + cle, "content-type": "application/json"},
                  {"model": modele_ia, "messages": [
                      {"role": "system", "content": systeme},
                      {"role": "user", "content": message}]})
    return rep["choices"][0]["message"]["content"]


def _appeler_gemini(cle, modele_ia, systeme, message):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
           % modele_ia)
    # Clé dans un en-tête (x-goog-api-key), pas dans l'URL : évite qu'elle
    # apparaisse dans d'éventuels journaux de proxy.
    rep = _poster(url, {"content-type": "application/json", "x-goog-api-key": cle},
                  {"system_instruction": {"parts": [{"text": systeme}]},
                   "contents": [{"parts": [{"text": message}]}]})
    return rep["candidates"][0]["content"]["parts"][0]["text"]


# ── API de service ────────────────────────────────────────────────────
def _reglages_avec_cle(app):
    """Réglages + clé API déchiffrée à la volée (uniquement pour l'appel)."""
    reglages = dict(app.lire_reglages())
    reglages["ia_cle"] = app.cle_ia()
    return reglages


def mission(app, type_mission, cible=None):
    reglages = _reglages_avec_cle(app)
    message = _contexte_mission(app, type_mission, cible)
    texte = _appeler(reglages, _SYSTEME, message)
    return {"mission": MISSIONS.get(type_mission, type_mission),
            "texte": texte, "avertissement": "Brouillon IA — à vérifier."}


def chat(app, message):
    reglages = _reglages_avec_cle(app)
    return {"texte": _appeler(reglages, _SYSTEME, message),
            "avertissement": "Brouillon IA — à vérifier."}
