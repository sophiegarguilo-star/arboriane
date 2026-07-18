# -*- coding: utf-8 -*-
"""
Arboriane — serveur local.

Un atelier de généalogie sourcée, 100 % local et privé. Ce module ne fait que
le transport : il écoute sur 127.0.0.1, sert l'interface (web/) et route l'API
vers routes/. Toute la logique vit dans core/ et services/.

Lancement : python app.py  (ou double-clic sur le lanceur).
Rien ne sort de la machine : pas de cloud, pas de télémétrie.
"""

import atexit
import json
import mimetypes
import os
import shutil
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from core import instance
from core import navigateur
from core import securite
from core.validation import lire_json, ErreurValidation
from core.application import Application
from core.version import VERSION
import routes

# ── Emplacements : bundle (ressources) vs dossier app (données) ──────────
def _inscriptible(dossier):
    """Vrai si on peut créer `dossier` et y écrire un fichier — sinon il est
    protégé (accès contrôlé aux dossiers / antivirus), en lecture seule, etc."""
    try:
        os.makedirs(dossier, exist_ok=True)
        sonde = os.path.join(dossier, ".ecriture_test")
        with open(sonde, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(sonde)
        return True
    except OSError:
        return False


ICI = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):           # exe PyInstaller
    BUNDLE = sys._MEIPASS
    # Données dans Documents\Arboriane (repérable par l'utilisatrice) — l'exe peut
    # être installé dans Program Files (non inscriptible). MAIS Documents peut être
    # protégé (« accès contrôlé aux dossiers » de Windows / antivirus) ou redirigé :
    # on VÉRIFIE qu'on peut y écrire, sinon on se replie sur %LOCALAPPDATA%\Arboriane
    # (jamais protégé). Évite le cryptique « Failed to fetch » à la création d'un arbre.
    _docs = os.path.join(os.path.expanduser("~"), "Documents")
    APP_DIR = os.path.join(_docs if os.path.isdir(_docs)
                           else os.path.expanduser("~"), "Arboriane")
    if not os.environ.get("ARBORIANE_DONNEES") and not _inscriptible(APP_DIR):
        # NE PAS se replier si des données existent déjà ici : basculer de racine
        # rouvrirait l'app sur un registre VIDE (arbres « disparus »). Mieux vaut
        # garder ce dossier et laisser un message d'écriture clair apparaître.
        _a_des_donnees = (os.path.isdir(os.path.join(APP_DIR, "Mes arbres"))
                          or os.path.isfile(os.path.join(APP_DIR, "espaces.json")))
        if not _a_des_donnees:
            _repli = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            APP_DIR = os.path.join(_repli, "Arboriane")
else:                                        # script (développement)
    BUNDLE = ICI
    APP_DIR = ICI

# Permet de relocaliser les données (banc de test isolé, dossier partagé…).
APP_DIR = os.environ.get("ARBORIANE_DONNEES") or APP_DIR

DOSSIER_WEB = os.path.join(BUNDLE, "web")
PORT_DEFAUT = 8770

APP = Application(APP_DIR)
routes.charger_modules()


class Gestionnaire(BaseHTTPRequestHandler):
    server_version = "Arboriane"

    def log_message(self, *a):               # pas de bruit dans la console
        pass

    # ── Réponses ──────────────────────────────────────────────────────
    def _json(self, code, valeur):
        corps = json.dumps(valeur, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def _erreur(self, code, message):
        self._json(code, {"erreur": message})

    # ── GET : statiques + API ─────────────────────────────────────────
    def do_GET(self):
        url = urlparse(self.path)
        chemin = url.path
        # Les lectures de données privées (API + médias) exigent un Host local :
        # c'est ce qui bloque le DNS rebinding (une page tierce ne peut pas lire
        # l'arbre). Les fichiers statiques (web/) ne sont pas sensibles.
        if chemin.startswith("/api/") or chemin.startswith("/media/"):
            refus = securite.verifier_lecture(self.headers)
            if refus:
                return self._erreur(refus[0], refus[1])
        if chemin.startswith("/api/"):
            params = {k: v[0] for k, v in parse_qs(url.query).items()}
            code, payload = routes.dispatch(APP, "GET", chemin, params, {})
            return self._json(code, payload)
        if chemin.startswith("/media/"):
            return self._servir_media(chemin)
        return self._servir_statique(chemin)

    def _servir_media(self, chemin):
        """Sert une image de l'arbre actif (/media/Sources/x.jpg …)."""
        from urllib.parse import unquote
        parties = chemin[len("/media/"):].split("/", 1)
        if len(parties) != 2:
            return self._erreur(404, "Média introuvable.")
        cible = APP.chemin_media(parties[0], unquote(parties[1]))
        if not cible:
            return self._erreur(404, "Média introuvable.")
        type_mime, _ = mimetypes.guess_type(cible)
        # Ouverture protégée : un scan verrouillé (antivirus) ou supprimé entre
        # le contrôle et l'ouverture donne un 404 propre, pas un « Failed to fetch ».
        try:
            taille = os.path.getsize(cible)
            f = open(cible, "rb")
        except OSError:
            return self._erreur(404, "Média illisible pour le moment.")
        try:
            self.send_response(200)
            self.send_header("Content-Type", type_mime or "application/octet-stream")
            self.send_header("Content-Length", str(taille))
            self.end_headers()
            shutil.copyfileobj(f, self.wfile, 64 * 1024)   # par blocs : pas tout en RAM
        except (OSError, ValueError):
            pass                                 # navigation annulée / connexion coupée
        finally:
            f.close()

    def _servir_statique(self, chemin):
        if chemin in ("/", ""):
            chemin = "/index.html"
        rel = chemin.lstrip("/")
        cible = os.path.abspath(os.path.join(DOSSIER_WEB, rel))
        racine = os.path.abspath(DOSSIER_WEB)
        if cible != racine and not cible.startswith(racine + os.sep):
            return self._erreur(403, "Accès refusé.")
        if not os.path.isfile(cible):
            return self._erreur(404, "Fichier introuvable.")
        # Revalidation systématique : le navigateur DOIT revérifier avant de
        # servir depuis son cache (fini le vieux JS resservi après une mise à
        # jour). ETag = signature (date + taille) ; 304 si inchangé, sinon 200.
        st = os.stat(cible)
        etag = '"%d-%d"' % (int(st.st_mtime), st.st_size)
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            return
        type_mime, _ = mimetypes.guess_type(cible)
        # les modules ES doivent être servis en JavaScript
        if cible.endswith(".js"):
            type_mime = "text/javascript"
        try:
            with open(cible, "rb") as f:
                donnees = f.read()
        except OSError:
            return self._erreur(404, "Fichier illisible.")
        self.send_response(200)
        self.send_header("Content-Type", (type_mime or "application/octet-stream")
                         + ("; charset=utf-8" if (type_mime or "").startswith("text") else ""))
        self.send_header("Content-Length", str(len(donnees)))
        self.send_header("ETag", etag)
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(donnees)

    # ── Mutations : POST / PUT / DELETE ───────────────────────────────
    def _mutation(self, methode):
        refus = securite.verifier_mutation(self.headers)
        if refus:
            return self._erreur(*refus)
        try:
            taille = int(self.headers.get("Content-Length") or 0)
            brut = self.rfile.read(taille) if taille else b""
            corps = lire_json(brut)
        except ErreurValidation as e:
            return self._erreur(400, str(e))
        url = urlparse(self.path)
        params = {k: v[0] for k, v in parse_qs(url.query).items()}
        code, payload = routes.dispatch(APP, methode, url.path, params, corps)
        self._json(code, payload)

    def do_POST(self):
        self._mutation("POST")

    def do_PUT(self):
        self._mutation("PUT")

    def do_DELETE(self):
        self._mutation("DELETE")


def demarrer(port=None, ouvrir_navigateur=True):
    """Démarre le serveur sur le premier port libre ≥ port.

    Garantit UNE SEULE instance par dossier de données (verrou OS, core/instance).
    Si une instance sert déjà ce dossier, on NE démarre PAS un 2e serveur : on
    renvoie (None, port_existant, url_existante) pour que l'appelant rouvre la
    fenêtre existante. `serveur` vaut None dans ce cas.

    ARBORIANE_MULTI=1 désactive le verrou (bancs de test lançant plusieurs
    serveurs sur le même dossier).
    """
    verrou = not os.environ.get("ARBORIANE_MULTI")
    if verrou and not instance.acquerir(APP.dossier_donnees):
        infos = instance.lire_infos(APP.dossier_donnees)
        url = infos.get("url") or ("http://127.0.0.1:%s/" % infos.get("port", ""))
        if ouvrir_navigateur and not os.environ.get("ARBORIANE_SANS_NAVIGATEUR"):
            try:
                navigateur.ouvrir(url, navigateur.lire_prefere(APP.dossier_donnees))
            except Exception:
                pass
        return None, infos.get("port"), url

    port = port or PORT_DEFAUT
    serveur = None
    for essai in range(port, port + 50):
        try:
            serveur = ThreadingHTTPServer(("127.0.0.1", essai), Gestionnaire)
            port = essai
            break
        except OSError:
            continue
    if serveur is None:
        raise OSError("Aucun port libre entre %d et %d." % (port, port + 50))
    url = "http://127.0.0.1:%d/" % port
    try:                                     # mémoriser le port réel (lanceur)
        with open(os.path.join(APP.dossier_donnees, "port.txt"), "w") as f:
            f.write(str(port))
    except OSError:
        pass
    if verrou:                               # publier l'identité de l'instance vive
        instance.ecrire_infos(APP.dossier_donnees,
                              {"pid": os.getpid(), "port": port,
                               "url": url, "version": VERSION})
        atexit.register(instance.liberer, APP.dossier_donnees)
    if ouvrir_navigateur and not os.environ.get("ARBORIANE_SANS_NAVIGATEUR"):
        try:
            navigateur.ouvrir(url, navigateur.lire_prefere(APP.dossier_donnees))
        except Exception:
            pass
    return serveur, port, url


if __name__ == "__main__":
    serveur, port, url = demarrer()
    if serveur is None:
        print("Arboriane est déjà ouvert — %s" % url)
    else:
        print("Arboriane — %s  (Ctrl+C pour arrêter)" % url)
        try:
            serveur.serve_forever()
        except KeyboardInterrupt:
            print("\nArrêt.")
