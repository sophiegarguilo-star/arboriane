# -*- coding: utf-8 -*-
"""
Arboriane — lanceur (point d'entrée de l'exe Windows).

Ouvre une petite fenêtre Tkinter (pas de console noire), démarre le serveur
local dans un thread, ouvre le navigateur une fois prêt, et arrête proprement
le serveur à la fermeture.

Fonctionne aussi en mode script (`python lanceur.py`) et en mode frozen (exe).
Si Tkinter est absent, repli sur un démarrage console avec message clair.
"""

import os
import shutil
import sys
import threading
import webbrowser


# ── Ouverture d'un navigateur MODERNE (évite Internet Explorer) ──────────
# Logique centralisée dans core/navigateur.py (partagée avec app.py, pour que le
# SERVEUR aussi évite IE — notamment à la réouverture d'une instance existante).
def ouvrir_navigateur_moderne(url):
    from core import navigateur
    dossier = ""
    try:
        import app
        dossier = app.APP.dossier_donnees
    except Exception:
        pass
    return navigateur.ouvrir(url, navigateur.lire_prefere(dossier) if dossier else None)


# ── Emplacement des ressources (web/ : logo…) ────────────────────────────
def _base_ressources():
    """Dossier contenant web/ : le bundle _MEIPASS en exe, sinon le dossier
    du lanceur."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# ── Raccourcis « Arboriane » (Bureau + Menu Démarrer, Windows, 1er lancement) ──
def _dossier_special(nom, repli_rel):
    """Chemin d'un dossier spécial Windows (Desktop, Programs…) via PowerShell,
    avec repli relatif au profil utilisateur."""
    import subprocess
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Environment]::GetFolderPath('%s')" % nom],
            capture_output=True, text=True, timeout=10, creationflags=0x08000000)
        d = (out.stdout or "").strip()
        if d and os.path.isdir(d):
            return d
    except Exception:
        pass
    repli = os.path.join(os.path.expanduser("~"), repli_rel)
    return repli if os.path.isdir(repli) else None


def _ecrire_lnk(lnk, cible, args, workdir, icone):
    """Crée un fichier .lnk Windows via WScript.Shell (PowerShell). Silencieux."""
    import subprocess
    ps = (
        "$w=New-Object -ComObject WScript.Shell;"
        "$s=$w.CreateShortcut('{lnk}');"
        "$s.TargetPath='{cible}';"
        "$s.Arguments='{args}';"
        "$s.WorkingDirectory='{wd}';"
        "$s.IconLocation='{icone}';"
        "$s.Description='Arboriane - genealogie locale et privee';"
        "$s.Save()"
    ).format(lnk=lnk.replace("'", "''"), cible=cible.replace("'", "''"),
             args=args.replace("'", "''"), wd=workdir.replace("'", "''"),
             icone=icone.replace("'", "''"))
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                   timeout=15, creationflags=0x08000000)


def creer_raccourci_bureau(force=False):
    """Crée les raccourcis « Arboriane » sur le Bureau ET dans le menu Démarrer
    (Windows uniquement). Silencieux ; par défaut une seule fois (marqueur dans
    %LOCALAPPDATA%\\Arboriane). Renvoie la liste des .lnk créés."""
    if os.name != "nt":
        return []
    crees = []
    try:
        base_marq = os.path.join(
            os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "Arboriane")
        os.makedirs(base_marq, exist_ok=True)
        marqueur = os.path.join(base_marq, "raccourci_cree")
        if os.path.exists(marqueur) and not force:
            return []

        base = _base_ressources()
        icone = os.path.join(base, "web", "favicon.ico")
        if getattr(sys, "frozen", False):        # exe autonome : cible = l'exe
            cible, args, workdir = sys.executable, "", os.path.dirname(sys.executable)
        else:                                    # script : pythonw + lanceur.py
            cible = shutil.which("pythonw") or shutil.which("python") or sys.executable
            args = '"%s"' % os.path.join(base, "lanceur.py")
            workdir = base

        # Bureau
        bureau = _dossier_special("Desktop", "Desktop")
        if bureau:
            lnk = os.path.join(bureau, "Arboriane.lnk")
            _ecrire_lnk(lnk, cible, args, workdir, icone)
            crees.append(lnk)
        # Menu Démarrer (dossier Programmes de l'utilisateur)
        programmes = _dossier_special(
            "Programs", os.path.join("AppData", "Roaming", "Microsoft",
                                     "Windows", "Start Menu", "Programs"))
        if programmes:
            lnk = os.path.join(programmes, "Arboriane.lnk")
            _ecrire_lnk(lnk, cible, args, workdir, icone)
            crees.append(lnk)

        with open(marqueur, "w", encoding="utf-8") as f:
            f.write("1")
    except Exception:
        pass
    return crees


# ── Import de app en ajustant sys.path si besoin ─────────────────────────
def _importer_app():
    """Importe le module app en s'assurant que son dossier est sur sys.path.

    - En frozen (exe), les modules sont dans sys._MEIPASS.
    - En script, le dossier du lanceur contient app.py.
    """
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    if base not in sys.path:
        sys.path.insert(0, base)
    import app  # noqa: E402
    return app


# ── Repli console si Tkinter indisponible ────────────────────────────────
def _demarrage_console(app, erreur_tk=None):
    if erreur_tk:
        print("Interface graphique indisponible (%s) — démarrage console." % erreur_tk)
    serveur, port, url = app.demarrer()
    if serveur is None:                      # une instance sert déjà ce dossier
        print("Arboriane est déjà ouvert — %s" % url)
        return
    print("Arboriane — %s  (Ctrl+C pour arrêter)" % url)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt.")
    finally:
        try:
            serveur.shutdown()
        except Exception:
            pass


# ── Interface Tkinter ────────────────────────────────────────────────────
def _demarrage_fenetre(app):
    import tkinter as tk
    from tkinter import font as tkfont
    try:
        from core.version import VERSION
    except Exception:
        VERSION = ""

    CREME, VERT, VERT_CLAIR = "#fbfaf5", "#1f4636", "#2d5c47"

    etat = {"serveur": None, "url": None, "erreur": None, "deja": False}

    racine = tk.Tk()
    racine.title("Arboriane " + VERSION)
    racine.configure(bg=CREME)
    racine.resizable(False, False)

    # icône de la fenêtre (barre de titre + barre des tâches) = l'emblème
    base_ress = _base_ressources()
    try:
        icone = tk.PhotoImage(file=os.path.join(base_ress, "web", "favicon-96x96.png"))
        racine.iconphoto(True, icone)
        racine._icone = icone
    except Exception:
        pass

    corps = tk.Frame(racine, bg=CREME, padx=34, pady=26)
    corps.pack(fill="both", expand=True)

    # logo
    try:
        logo = tk.PhotoImage(file=os.path.join(base_ress, "web", "logo-lanceur.png"))
        racine._logo = logo
        tk.Label(corps, image=logo, bg=CREME).pack()
    except Exception:
        tk.Label(corps, text="🌳 Arboriane", font=tkfont.Font(family="Georgia", size=20),
                 bg=CREME, fg=VERT).pack()

    # accroche
    tk.Label(corps, text="Votre atelier de généalogie, local et privé",
             font=tkfont.Font(family="Georgia", size=11, slant="italic"),
             bg=CREME, fg="#5c6f60").pack(pady=(2, 16))

    # badge d'état (pastille + texte)
    badge = tk.Frame(corps, bg="#eef5ef", padx=14, pady=7,
                     highlightbackground="#d6e6da", highlightthickness=1)
    badge.pack()
    tk.Label(badge, text="●", font=tkfont.Font(size=10), bg="#eef5ef", fg="#3d7a54").pack(side="left")
    var_etat = tk.StringVar(value="Démarrage…")
    lbl_etat = tk.Label(badge, textvariable=var_etat,
                        font=tkfont.Font(family="Segoe UI", size=10),
                        bg="#eef5ef", fg="#2f5c47", justify="left")
    lbl_etat.pack(side="left", padx=(8, 0))

    # Cette fenêtre EST le logiciel : la refermer coupe le serveur qui sert la
    # page. Rien ne le disait, et on la ferme par réflexe. On le dit.
    tk.Label(corps,
             text="Gardez cette fenêtre ouverte pendant que vous\n"
                  "utilisez Arboriane : elle fait tourner le logiciel.",
             font=tkfont.Font(family="Segoe UI", size=9),
             bg=CREME, fg="#7a6f5d", justify="center").pack(pady=(11, 0))

    def _ouvrir():
        if etat["url"]:
            ouvrir_navigateur_moderne(etat["url"])

    def _quitter():
        srv = etat["serveur"]
        if srv is not None:
            try:
                srv.shutdown()
            except Exception:
                pass
        try:
            racine.destroy()
        except Exception:
            pass

    boutons = tk.Frame(corps, bg=CREME)
    boutons.pack(pady=(18, 4), fill="x")
    btn_ouvrir = tk.Button(boutons, text="Ouvrir Arboriane", command=_ouvrir,
                           state="disabled", cursor="hand2", relief="flat",
                           bg=VERT, fg="#ffffff", activebackground=VERT_CLAIR,
                           activeforeground="#ffffff", disabledforeground="#bcd2c5",
                           font=tkfont.Font(family="Segoe UI", size=11, weight="bold"),
                           padx=10, pady=9)
    btn_ouvrir.pack(fill="x")
    btn_quitter = tk.Button(boutons, text="Quitter", command=_quitter,
                            cursor="hand2", relief="flat", bg="#efece3", fg="#3a4a40",
                            activebackground="#e3ded0", activeforeground="#3a4a40",
                            font=tkfont.Font(family="Segoe UI", size=10), pady=7)
    btn_quitter.pack(fill="x", pady=(9, 0))

    tk.Label(corps, text="Arboriane " + VERSION + "  ·  100 % local  ·  arboriane.app@gmail.com",
             font=tkfont.Font(family="Segoe UI", size=8), bg=CREME, fg="#9a9384").pack(pady=(16, 0))

    racine.protocol("WM_DELETE_WINDOW", _quitter)

    # ── Démarrage serveur dans un thread ─────────────────────────────────
    def _travail():
        try:
            # On gère l'ouverture du navigateur nous-mêmes (une fois prêt).
            serveur, port, url = app.demarrer(ouvrir_navigateur=False)
            etat["serveur"] = serveur
            etat["url"] = url
            etat["deja"] = serveur is None      # instance déjà en cours
            # servir dans un second thread pour ne pas bloquer celui-ci
            if serveur is not None:
                threading.Thread(target=serveur.serve_forever, daemon=True).start()
        except Exception as e:  # noqa: BLE001
            etat["erreur"] = str(e)

    threading.Thread(target=_travail, daemon=True).start()

    # ── Sondage de l'état côté UI (thread principal Tkinter) ─────────────
    def _sonder():
        if etat["erreur"] is not None:
            var_etat.set("Erreur : %s" % etat["erreur"])
            lbl_etat.configure(fg="#b00020")
            return
        if etat["url"] is not None:
            prefixe = "Déjà en cours" if etat.get("deja") else "Prêt"
            var_etat.set(prefixe + "  ·  " + etat["url"])
            btn_ouvrir.configure(state="normal")
            if not os.environ.get("ARBORIANE_SANS_NAVIGATEUR"):
                _ouvrir()
            return
        racine.after(120, _sonder)

    racine.after(120, _sonder)
    racine.mainloop()

    # après fermeture de la fenêtre : arrêt propre du serveur
    srv = etat["serveur"]
    if srv is not None:
        try:
            srv.shutdown()
        except Exception:
            pass


def main():
    app = _importer_app()
    creer_raccourci_bureau()   # 1er lancement Windows : raccourci Bureau (silencieux)
    try:
        import tkinter  # noqa: F401
    except Exception as e:  # noqa: BLE001
        return _demarrage_console(app, erreur_tk=e)
    try:
        _demarrage_fenetre(app)
    except Exception as e:  # noqa: BLE001
        # Si l'UI échoue à l'exécution (pas d'affichage, etc.), repli console.
        _demarrage_console(app, erreur_tk=e)


if __name__ == "__main__":
    main()
