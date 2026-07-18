# -*- coding: utf-8 -*-
"""
Sélecteur de dossier natif (Windows).

Arboriane s'affiche dans un navigateur : pas d'accès direct au système de
fichiers pour un « file picker » standard. On ouvre donc le dialogue Windows
natif « Parcourir… » via PowerShell dans un SOUS-PROCESSUS.

Pourquoi PowerShell et pas tkinter ? tkinter exige le thread principal, or le
lanceur y tient déjà sa fenêtre (mainloop) ; l'appeler depuis le thread d'une
requête HTTP gèlerait. PowerShell est un composant du système, fonctionne aussi
dans l'exe (aucun interpréteur Python à invoquer), et s'exécute hors-process.

`choisir()` ne lève JAMAIS : en cas d'échec ou d'annulation, renvoie "".
"""

import os
import subprocess

_CREATE_NO_WINDOW = 0x08000000

_SCRIPT = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true; $owner.ShowInTaskbar = $false
$owner.WindowState = 'Minimized'; $owner.Opacity = 0
$owner.Show()
$dlg = New-Object System.Windows.Forms.FolderBrowserDialog
$dlg.Description = '{desc}'
$dlg.ShowNewFolderButton = $true
if ('{depart}' -ne '') { try { $dlg.SelectedPath = '{depart}' } catch {} }
$r = $dlg.ShowDialog($owner)
$owner.Close()
if ($r -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::Out.Write($dlg.SelectedPath) }
"""


def _echapper_ps(s):
    return (s or "").replace("'", "''")


_SCRIPT_FICHIER = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true; $owner.ShowInTaskbar = $false
$owner.WindowState = 'Minimized'; $owner.Opacity = 0
$owner.Show()
$dlg = New-Object System.Windows.Forms.OpenFileDialog
$dlg.Title = '{desc}'
$dlg.Filter = '{filtre}'
$dlg.Multiselect = $false
if ('{depart}' -ne '') { try { $dlg.InitialDirectory = '{depart}' } catch {} }
$r = $dlg.ShowDialog($owner)
$owner.Close()
if ($r -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::Out.Write($dlg.FileName) }
"""


def choisir(titre="Choisissez un dossier", depart=""):
    """Ouvre le dialogue natif et renvoie le chemin absolu choisi, ou "" si
    l'utilisateur annule / si le dialogue n'est pas disponible."""
    if os.name != "nt":
        return ""                            # pas de dialogue natif hors Windows
    # .replace (et non .format) : le script PowerShell contient des accolades
    # littérales { } que str.format interpréterait comme des champs (ValueError).
    ps = (_SCRIPT.replace("{desc}", _echapper_ps(titre))
                 .replace("{depart}", _echapper_ps(depart)))
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, encoding="utf-8",
            timeout=300, creationflags=_CREATE_NO_WINDOW)
    except Exception:
        return ""
    chemin = (out.stdout or "").strip()
    return chemin if chemin and os.path.isdir(chemin) else ""


def choisir_fichier(titre="Choisissez un fichier", depart="",
                    filtre="Archives (*.zip)|*.zip|Tous les fichiers (*.*)|*.*"):
    """Ouvre le dialogue natif « Ouvrir un fichier » et renvoie le chemin absolu
    du fichier choisi, ou "" (annulation / indisponible). Ne lève jamais."""
    if os.name != "nt":
        return ""
    ps = (_SCRIPT_FICHIER.replace("{desc}", _echapper_ps(titre))
                         .replace("{depart}", _echapper_ps(depart))
                         .replace("{filtre}", _echapper_ps(filtre)))
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, encoding="utf-8",
            timeout=300, creationflags=_CREATE_NO_WINDOW)
    except Exception:
        return ""
    chemin = (out.stdout or "").strip()
    return chemin if chemin and os.path.isfile(chemin) else ""
