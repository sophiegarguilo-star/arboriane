@echo off
rem ============================================================
rem  Arboriane — double-cliquez ce fichier pour ouvrir l'appli.
rem  (Aucune fenetre noire : pythonw lance l'interface Tkinter.)
rem ============================================================
cd /d "%~dp0"

rem Essaie pythonw (sans console) ; repli sur le lanceur "py" si absent.
where pythonw.exe >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw.exe "%~dp0lanceur.py"
) else (
    start "" py.exe -w "%~dp0lanceur.py"
)
